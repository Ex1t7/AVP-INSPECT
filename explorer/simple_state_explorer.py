

import os
import time
import logging
import cv2
from typing import Optional, Tuple, List

from config import Config
from core_types import State, Button, PointerMoveResult
from state_graph import StateGraph
from mouse_controller import MouseController
from screenshot_manager import ScreenshotManager
from metrics_manager import MetricsManager


class StateExplorer:
    

    def __init__(self, config: Config, state_graph: StateGraph,
                 mouse_controller: MouseController, screenshot_manager: ScreenshotManager,
                 omniparser_client, metrics_manager: MetricsManager,
                 esp32, app_manager=None):
        self.config = config
        self.graph = state_graph
        self.mouse_controller = mouse_controller
        self.screenshot_manager = screenshot_manager
        self.omniparser_client = omniparser_client
        self.metrics_manager = metrics_manager
        self.esp32 = esp32
        self.app_manager = app_manager
        self.logger = logging.getLogger(__name__)

        self.current_state: Optional[State] = None
        self.clicks_since_new_state = 0
        self.last_trigger_button: Optional[Tuple[State, Button]] = None
        self.home_return_count = 0  
        
        
        self.click_counter = 0
        self.clicked_buttons_dir = ""
        self._setup_clicked_buttons_dir()

    def _setup_clicked_buttons_dir(self):
        
        try:
            
            app_dir = self.metrics_manager.get_app_dir()
            if app_dir:
                self.clicked_buttons_dir = os.path.join(app_dir, "clicked_buttons")
                os.makedirs(self.clicked_buttons_dir, exist_ok=True)
                self.logger.info(f"📸 Clicked buttons will be saved to: {self.clicked_buttons_dir}")
        except Exception as e:
            self.logger.warning(f"Could not setup clicked buttons directory: {e}")

    def save_clicked_button_image(self, button: Button, screenshot_path: str) -> Optional[str]:
        
        if not self.clicked_buttons_dir or not os.path.exists(screenshot_path):
            return None
            
        try:
            
            img = cv2.imread(screenshot_path)
            if img is None:
                self.logger.warning(f"Could not read screenshot: {screenshot_path}")
                return None
            
            height, width = img.shape[:2]
            
            
            x_min, y_min, x_max, y_max = button.bbox
            x1 = int(x_min * width)
            y1 = int(y_min * height)
            x2 = int(x_max * width)
            y2 = int(y_max * height)
            
            
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 3)
            
            
            label = f"#{self.click_counter}: {button.content[:30]}" if button.content else f"#{self.click_counter}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            
            
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            
            text_x = x1
            text_y = max(y1 - 10, text_height + 5)
            
            
            cv2.rectangle(img, 
                         (text_x - 2, text_y - text_height - 5),
                         (text_x + text_width + 2, text_y + 5),
                         (0, 0, 255), -1)
            
            
            cv2.putText(img, label, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
            
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"click_{self.click_counter:04d}_{timestamp}.jpg"
            save_path = os.path.join(self.clicked_buttons_dir, filename)
            
            cv2.imwrite(save_path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            self.logger.info(f"📸 Saved clicked button image: {filename}")
            
            return save_path
            
        except Exception as e:
            self.logger.error(f"Failed to save clicked button image: {e}")
            return None

    def check_current_state(self, clicked_button_id: Optional[str] = None) -> Tuple[bool, Optional[State]]:
        
        timing_start = time.time()

        
        if self.metrics_manager.is_timeout_reached():
            timeout_minutes = self.config.exploration.timeout_minutes
            self.logger.info(f"Exploration timeout reached ({timeout_minutes} minutes)")
            raise TimeoutError(f"Exploration timeout reached ({timeout_minutes} minutes)")

        
        try:
            omniparser_start = time.time()
            ui_elements = self.omniparser_client.get_ui_elements()
            omniparser_time = time.time() - omniparser_start
            self.logger.info(f"⏱️ OmniParser took {omniparser_time:.2f}s")

            
            

        except Exception as e:
            self.logger.error(f"Failed to get UI elements: {e}")
            return False, None

        
        processing_start = time.time()
        buttons = []
        for element in ui_elements:
            if element.get('interactivity', False):
                button = Button(
                    id=str(len(buttons)),
                    content=element.get('content', ''),
                    bbox=element.get('bbox', [0, 0, 0, 0]),
                    interactivity=element.get('interactivity', False),
                    source=element.get('source', '')
                )
                buttons.append(button)

        
        self.metrics_manager.record_button_found(len(buttons))
        if clicked_button_id is not None:
            self.metrics_manager.record_button_explored()

        
        screen_width, screen_height = self.screenshot_manager.get_screen_dimensions()
        new_state = State(buttons, screen_width, screen_height)

        
        state_check_start = time.time()
        similar_state = self.graph.find_similar_state(new_state)
        state_check_time = time.time() - state_check_start

        total_time = time.time() - timing_start
        self.logger.info(f"⏱️ State check total: {total_time:.2f}s (OmniParser: {omniparser_time:.2f}s, state comparison: {state_check_time:.2f}s)")
        if similar_state:
            
            if (self.current_state and self.current_state != similar_state and
                clicked_button_id is not None):
                
                clicked_button = self._find_button_by_id(self.current_state, clicked_button_id)
                if clicked_button:
                    self.graph.add_edge(self.current_state, similar_state, clicked_button)

            self.current_state = similar_state
            return True, similar_state

        
        was_added = self.graph.add_state(new_state)
        if was_added:
            self.metrics_manager.record_state_found()

            
            state_index = len(self.graph.nodes) - 1
            labeled_image_path = self.omniparser_client.get_last_labeled_image()
            if labeled_image_path:
                self.metrics_manager.save_state_image(state_index, labeled_image_path)

        
        if self.current_state and clicked_button_id is not None:
            clicked_button = self._find_button_by_id(self.current_state, clicked_button_id)
            if clicked_button:
                self.graph.add_edge(self.current_state, new_state, clicked_button)

        self.current_state = new_state
        return False, new_state

    def explore_state(self, state: State) -> None:
        
        self.metrics_manager.record_state_explored()

        button_count = 0
        while state.has_unexplored_buttons():
            iteration_start = time.time()
            button_count += 1

            
            if self.metrics_manager.is_timeout_reached():
                self.logger.info("Timeout reached during state exploration")
                return

            button = state.get_next_unexplored_button()
            if not button:
                break

            
            if self.graph.is_dead_button(state.state_id, button.id):
                self.logger.debug(f"Skipping dead button {button.id}")
                continue

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"🔘 Button {button_count}: Exploring '{button.content}' (ID: {button.id})")
            self.logger.info(f"{'='*60}")

            
            success = self._click_button(button)
            if not success:
                self.logger.warning(f"Failed to click button {button.id}")

                
                no_movement_count = self.mouse_controller.get_consecutive_no_movement()
                if no_movement_count >= self.config.exploration.max_no_movement_attempts:
                    self.logger.error(f"🚫 Button {button.id} is unreachable: Pointer stuck after {no_movement_count} attempts!")
                    self.logger.info(f"Marking button '{button.content}' as dead and continuing...")
                    
                    self.graph.add_dead_button(state.state_id, button.id)
                    
                    self.mouse_controller.reset_no_movement_counter()
                    continue

                continue

            
            try:
                check_state_start = time.time()
                is_known_state, new_state = self.check_current_state(button.id)
                check_state_time = time.time() - check_state_start

                if new_state is None:
                    continue

                iteration_time = time.time() - iteration_start
                self.logger.info(f"⏱️ TOTAL ITERATION TIME: {iteration_time:.2f}s")

                if is_known_state:
                    self.clicks_since_new_state += 1
                    self.logger.debug(f"Reached known state (clicks since new: {self.clicks_since_new_state})")

                    
                    if self.config.exploration.enable_home_detection and self._handle_home_return(new_state):
                        return

                    
                    if self.clicks_since_new_state >= self.config.exploration.max_clicks_without_new_state:
                        self.logger.info("Too many clicks without new state, restarting")
                        self._restart_app_and_resume()
                        return

                else:
                    
                    self.clicks_since_new_state = 0
                    self.last_trigger_button = (state, button)

                    self.logger.info(f"✨ New state discovered! Total states: {len(self.graph.nodes)}")
                    remaining_time = self.metrics_manager.get_remaining_time()
                    self.logger.info(f"⏱️ Time remaining: {remaining_time/60:.1f} minutes")

                    
                    self.metrics_manager.log_metrics()
                    self.logger.debug(self.graph.print_graph_structure())

                    
                    self.logger.info(f"🔍 Recursively exploring new state...")
                    self.explore_state(new_state)

            except TimeoutError:
                self.logger.info("Timeout reached during button exploration")
                return
            except Exception as e:
                self.logger.error(f"Error exploring button {button.id}: {e}")
                continue

    def explore_all_states(self) -> None:
        
        try:
            
            _, initial_state = self.check_current_state()
            if initial_state is None:
                self.logger.error("Could not capture initial app state")
                return

            
            if self.graph.is_home_state(initial_state):
                self.logger.error("❌ APP FAILED TO OPEN! Current state is still the home screen (state_0)")
                self.logger.error("The app did not launch successfully. Cannot explore home screen as app state.")
                raise Exception("App failed to open - still on home screen")

            self.logger.info("📱 Starting comprehensive state exploration from app initial state")
            self.explore_state(initial_state)

        except TimeoutError:
            self.logger.info("Exploration stopped due to timeout")
        except Exception as e:
            self.logger.error(f"Exploration failed with error: {e}")
        finally:
            self._finalize_exploration()

    def _click_button(self, button: Button) -> bool:
        
        try:
            click_start = time.time()
            
            
            self.click_counter += 1

            
            screen_width, screen_height = self.screenshot_manager.get_screen_dimensions()
            target_x, target_y = button.get_center(screen_width, screen_height)

            
            pre_click_screenshot = self.screenshot_manager.take_screenshot()
            if pre_click_screenshot.success and pre_click_screenshot.file_path:
                self.save_clicked_button_image(button, pre_click_screenshot.file_path)

            
            move_start = time.time()
            result = self.mouse_controller.move_to_target(
                target_x, target_y, self.screenshot_manager
            )
            move_time = time.time() - move_start
            self.logger.info(f"⏱️ Mouse movement took {move_time:.2f}s")

            if not result.success:
                self.logger.warning(f"Failed to move to button {button.id}: {result.error_message}")

                
                if result.password_detected:
                    self.logger.warning("🔐 Button led to password input - marking as dead and restarting app")
                    
                    self.graph.add_dead_button(self.current_state.state_id, button.id)
                    
                    self._restart_app_and_resume()

                return False

            
            if result.accuracy is not None:
                self.metrics_manager.record_pointer_move_success(result.accuracy)

            
            self.esp32.click_mouse(1)
            time.sleep(1)  

            total_click_time = time.time() - click_start
            self.logger.info(f"⏱️ Total click action took {total_click_time:.2f}s")

            return True

        except Exception as e:
            self.logger.error(f"Error clicking button {button.id}: {e}")
            self.metrics_manager.record_pointer_move_failure()
            return False

    def _handle_home_return(self, new_state: State) -> bool:
        
        if not self.graph.is_home_state(new_state):
            return False

        self.logger.warning(f"🏠 Returned to home state! This button exits the app.")

        
        if self.last_trigger_button:
            last_state, last_button = self.last_trigger_button
            self.graph.add_dead_button(last_state.state_id, last_button.id)
            self.logger.info(f"Marked button '{last_button.content}' as dead (exits to home screen)")

        
        self.logger.info("Restarting app to continue exploration inside the app")
        self._restart_app_and_resume()

        
        self.clicks_since_new_state = 0
        self.home_return_count = 0  
        return True  

    def _restart_app_and_resume(self):
        
        self.logger.info("🔄 Restarting app and resuming exploration")

        
        if self.last_trigger_button:
            last_state, last_button = self.last_trigger_button
            self.graph.add_dead_button(last_state.state_id, last_button.id)
            self.logger.info(f"Marked button '{last_button.content}' as dead")

        
        unexplored_states = self.graph.get_unexplored_states()
        if not unexplored_states:
            self.logger.info("🏁 NO UNEXPLORED BUTTONS REMAINING - Exploration complete!")
            self.logger.info("All reachable states have been explored. Ending exploration.")
            
            stats = self.graph.get_stats()
            self.logger.info(f"Final stats: {stats['total_states']} states, "
                           f"{stats['exploration_progress']:.1f}% explored")
            return

        self.logger.info(f"📊 States with unexplored buttons remaining: {len(unexplored_states)}")

        
        if self.app_manager:
            self.logger.info("Closing and reopening app...")
            if self.app_manager.restart_app():
                self.logger.info("✅ App restarted successfully")
                time.sleep(3)  
            else:
                self.logger.error("❌ Failed to restart app")
        else:
            self.logger.warning("No app_manager available, cannot restart app")

        
        self.clicks_since_new_state = 0
        self.last_trigger_button = None
        self.home_return_count = 0  
        self.mouse_controller.reset_no_movement_counter()  

    def _find_button_by_id(self, state: State, button_id: str) -> Optional[Button]:
        
        for button in state.buttons:
            if button.id == button_id:
                return button
        return None

    def _finalize_exploration(self):
        
        self.logger.info("Finalizing exploration session")

        
        stats = self.graph.get_stats()
        self.logger.info(f"Exploration completed:")
        self.logger.info(f"- Total states discovered: {stats['total_states']}")
        self.logger.info(f"- Total buttons found: {stats['total_buttons']}")
        self.logger.info(f"- Exploration progress: {stats['exploration_progress']:.1f}%")

        
        try:
            import json
            graph_data = self.graph.export_to_json()
            export_path = f"{self.metrics_manager.get_app_dir()}/state_graph.json"
            with open(export_path, 'w') as f:
                json.dump(graph_data, f, indent=2)
            self.logger.info(f"State graph exported to: {export_path}")
        except Exception as e:
            self.logger.error(f"Failed to export state graph: {e}")

        
        self.metrics_manager.finalize()
