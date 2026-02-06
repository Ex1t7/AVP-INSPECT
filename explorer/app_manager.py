

import os
import time
import pickle
import logging
from typing import Optional, Tuple, Dict, Any, List

from config import Config
from core_types import AppCacheEntry
from state_graph import StateGraph
import pointer_recognize


class AppManager:
    

    def __init__(self, config: Config, esp32, screenshot_manager=None, omniparser_client=None):
        self.config = config
        self.esp32 = esp32
        self.screenshot_manager = screenshot_manager
        self.omniparser_client = omniparser_client
        self.logger = logging.getLogger(__name__)
        self.app_cache: Dict[str, AppCacheEntry] = {}
        self._load_app_cache()

        
        from mouse_controller import MouseController
        self.mouse_controller = MouseController(self.config, self.esp32)

        
        self._initialize_mouse_system()

    def _initialize_mouse_system(self):
        
        try:
            self.logger.info("Initializing mouse system...")

            
            pointer_recognize.analyze_pointer_template()
            self.logger.info("Pointer template analyzed")

            
            if self.screenshot_manager:
                if self._align_mouse():
                    self.logger.info("Mouse alignment completed successfully")
                else:
                    self.logger.warning("Mouse alignment failed, but continuing...")
            else:
                self.logger.warning("No screenshot manager available, skipping mouse alignment")

        except Exception as e:
            self.logger.error(f"Mouse system initialization failed: {e}")

    def open_app(self, app_name: Optional[str] = None) -> Tuple[bool, Optional[Tuple[int, int]]]:
        
        if app_name is None:
            app_name = self.config.app.name

        self.logger.info(f"Opening app: {app_name}")

        try:
            
            self.esp32.keypress_action("SPOTLIGHT")
            time.sleep(1)  

            
            max_chunk_size = 16
            if len(app_name) > max_chunk_size:
                self.logger.info(f"App name is too long, sending in chunks")
                self.esp32.print_text(app_name[:max_chunk_size])
                time.sleep(0.5)
                self.esp32.print_text(app_name[max_chunk_size:])
            else:
                self.esp32.print_text(app_name)
            time.sleep(1)  

            
            self.esp32.write_key("ENTER")
            time.sleep(2)  

            
            self.esp32.keypress_action("SPOTLIGHT")
            time.sleep(1)  
            time.sleep(15)  

            self.logger.info(f"Successfully opened {app_name}")
            
            return True, None

        except Exception as e:
            self.logger.error(f"Error opening app {app_name}: {e}")
            return False, None

    def close_all_apps(self, exclude_system_apps: bool = True) -> bool:
        
        self.logger.info("Closing all applications...")

        try:
            
            max_pixel = self.config.mouse.max_pixel
            self._move_mouse_pixel(-max_pixel, -max_pixel)
            time.sleep(1)

            
            self.esp32.keypress_action("FNH")
            time.sleep(1)
            self.esp32.open_task_manager()
            time.sleep(4)  

            
            self.esp32.recenter_view()
            time.sleep(1) 

            
            self._move_mouse_pixel(max_pixel, -max_pixel)
            self._bounce_leg()

            close_button_pos = (1245, 500)

            app_1_pos = (close_button_pos[0]+250, close_button_pos[1] +250)
            print(f"Calculated app_1_pos: {app_1_pos}")

            for i in range(5):
                app_pos = (app_1_pos[0], app_1_pos[1] + i*80)
                self._move_mouse_to_target(app_pos[0], app_pos[1])
                self._bounce_leg()
                self.esp32.click_mouse(1)
                time.sleep(0.5)

            force_quit_pos = (close_button_pos[0]+250, close_button_pos[1] +650)

            self._move_mouse_to_target(force_quit_pos[0], force_quit_pos[1])
            self._bounce_leg()
            self.esp32.click_mouse(1)
            time.sleep(0.5)

            apps_closed = 0

            
            self._move_mouse_to_target(force_quit_pos[0], force_quit_pos[1] - 225)
            self.esp32.click_mouse(1)
            time.sleep(1)

            apps_closed += 1
            self.logger.info(f"Closed app #{apps_closed}")

            self.esp32.recenter_view()
            time.sleep(1)
            
            self._move_mouse_to_target(force_quit_pos[0] - 255, force_quit_pos[1] - 650)
            self.esp32.click_mouse(1)
            time.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"Error closing all apps: {e}")
            return False

    def force_quit_all_apps(self) -> bool:
        
        self.logger.warning("Force quitting ALL applications...")
        return self.close_all_apps(exclude_system_apps=False)

    def close_app(self, app_name: Optional[str] = None) -> bool:
        
        if app_name is None:
            app_name = self.config.app.name

        self.logger.info(f"Closing all apps (triggered by request to close {app_name})")

        
        return self.close_all_apps(exclude_system_apps=True)

    def restart_app(self, app_name: Optional[str] = None) -> bool:
        
        if app_name is None:
            app_name = self.config.app.name

        self.logger.info(f"Restarting app: {app_name}")

        if self.close_app(app_name):
            time.sleep(2)  
            success, _ = self.open_app(app_name)
            return success
        else:
            self.logger.error(f"Failed to close app {app_name} for restart")
            return False

    def _find_app_on_cached_page(self, app_name: str, page: int) -> Tuple[bool, Optional[Tuple[int, int]]]:
        
        
        self._navigate_to_page(page)

        
        if not self.omniparser_client:
            return False, None

        ui_elements = self.omniparser_client.get_ui_elements()
        if not ui_elements:
            return False, None

        
        for element in ui_elements:
            if 'ocr' not in element.get('source', ''):
                continue

            similarity = StateGraph.text_similarity(element.get('content', ''), app_name)
            if similarity > 0.8:
                position = self._get_element_center(element)
                self.logger.info(f"Found cached app {app_name} at {position}")
                return True, position

        return False, None

    def _search_app_through_pages(self, app_name: str) -> Tuple[bool, Optional[Tuple[int, int]]]:
        
        max_pages = self.config.exploration.max_search_pages
        current_page = 0
        previous_elements = []

        for page in range(max_pages):
            if not self.omniparser_client:
                return False, None

            ui_elements = self.omniparser_client.get_ui_elements()
            if not ui_elements:
                continue

            
            if self._is_same_page_content(ui_elements, previous_elements):
                self.logger.info("Reached end of app pages")
                break

            
            for element in ui_elements:
                if 'ocr' in element.get('source', ''):
                    self._update_app_cache(element.get('content', ''), current_page)

            
            for element in ui_elements:
                if 'ocr' not in element.get('source', ''):
                    continue

                similarity = StateGraph.text_similarity(element.get('content', ''), app_name)
                if similarity > 0.8:
                    position = self._get_element_center(element)
                    self.logger.info(f"Found app {app_name} on page {current_page} at {position}")
                    self._update_app_cache(app_name, current_page)
                    return True, position

            
            previous_elements = ui_elements
            self._next_page()
            current_page += 1
            time.sleep(1)

        self.logger.warning(f"App {app_name} not found after searching {max_pages} pages")
        return False, None

    def _navigate_to_first_page(self):
        
        for _ in range(20):
            self._prev_page()

    def _navigate_to_page(self, target_page: int, current_page: int = 0):
        
        if target_page == current_page:
            return

        pages_to_scroll = target_page - current_page
        self.logger.debug(f"Navigating from page {current_page} to page {target_page}")

        for _ in range(abs(pages_to_scroll)):
            if pages_to_scroll > 0:
                self._next_page()
            else:
                self._prev_page()
            time.sleep(1)

    def _next_page(self):
        
        self.esp32.scroll_mouse(0, 80)
        self.esp32.scroll_mouse(0, 80)

    def _prev_page(self):
        
        self.esp32.scroll_mouse(0, -80)
        self.esp32.scroll_mouse(0, -80)

    def _is_same_page_content(self, current_elements: List[Dict], previous_elements: List[Dict]) -> bool:
        
        if not previous_elements:
            return False

        current_content = ''.join(sorted([elem.get('content', '') for elem in current_elements]))
        previous_content = ''.join(sorted([elem.get('content', '') for elem in previous_elements]))

        similarity = StateGraph.text_similarity(current_content, previous_content)
        return similarity > 0.8

    def _get_element_center(self, element: Dict) -> Tuple[int, int]:
        
        bbox = element.get('bbox', [0, 0, 0, 0])
        screen_width, screen_height = self.screenshot_manager.get_screen_dimensions()

        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2 * screen_width)
        center_y = int((y1 + y2) / 2 * screen_height)
        return center_x, center_y

    def _load_app_cache(self):
        
        try:
            cache_path = self.config.paths.app_cache_file
            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    
                    for app_name, data in cache_data.items():
                        if isinstance(data, dict) and 'page' in data and 'timestamp' in data:
                            self.app_cache[app_name] = AppCacheEntry(
                                page=data['page'],
                                timestamp=data['timestamp']
                            )
                self.logger.info(f"Loaded app cache with {len(self.app_cache)} entries")
            else:
                self.logger.info("No existing app cache found")
        except Exception as e:
            self.logger.error(f"Error loading app cache: {e}")
            self.app_cache = {}

    def _save_app_cache(self):
        
        try:
            cache_path = self.config.paths.app_cache_file
            cache_data = {}
            for app_name, entry in self.app_cache.items():
                cache_data[app_name] = {
                    'page': entry.page,
                    'timestamp': entry.timestamp
                }
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            self.logger.debug(f"Saved app cache with {len(cache_data)} entries")
        except Exception as e:
            self.logger.error(f"Error saving app cache: {e}")

    def _get_cached_app_info(self, app_name: str) -> Optional[AppCacheEntry]:
        
        for cached_name, entry in self.app_cache.items():
            similarity = StateGraph.text_similarity(app_name, cached_name)
            if similarity > 0.8:
                return entry
        return None

    def _update_app_cache(self, app_name: str, page: int):
        
        
        for cached_name in list(self.app_cache.keys()):
            similarity = StateGraph.text_similarity(app_name, cached_name)
            if similarity > 0.8:
                if cached_name != app_name:
                    
                    entry = self.app_cache.pop(cached_name)
                    self.app_cache[app_name] = AppCacheEntry(page=page, timestamp=time.time())
                else:
                    self.app_cache[app_name] = AppCacheEntry(page=page, timestamp=time.time())
                self._save_app_cache()
                return

        
        self.app_cache[app_name] = AppCacheEntry(page=page, timestamp=time.time())
        self._save_app_cache()

    def _move_mouse_pixel(self, x: int, y: int) -> bool:
        
        
        
        return self.esp32.move_mouse(x, y)

    def _move_mouse_to_target(self, x: int, y: int) -> bool:
        
        
        if hasattr(self, 'mouse_controller') and self.mouse_controller:
            result = self.mouse_controller.move_to_target(x, y, self.screenshot_manager)
            return result.success
        else:
            print("No mouse controller available, using fallback implementation")
            
            return True

    def _find_current_pointer(self) -> Optional[Tuple[int, int]]:
        
        try:
            if self.screenshot_manager:
                screenshot_result = self.screenshot_manager.take_screenshot()
                
                if hasattr(screenshot_result, 'file_path'):
                    screenshot_path = screenshot_result.file_path
                else:
                    
                    screenshot_path = screenshot_result

                if screenshot_path:
                    pointer = pointer_recognize.find_pointer_centers(screenshot_path)
                    return pointer
        except Exception as e:
            self.logger.warning(f"Pointer detection failed: {e}")
        return None

    def _align_mouse(self) -> bool:
        
        try:
            self.logger.info("Starting mouse alignment...")
            max_pixel = self.config.mouse.max_pixel

            
            if not self._move_mouse_pixel(-max_pixel, -max_pixel):
                self.logger.error("Failed to move to top-left corner during alignment")
                return False

            if not self._move_mouse_pixel(10, -max_pixel):
                self.logger.error("Failed to move to top-left corner during alignment")
                return False

            time.sleep(0.5)
            left_top = self._find_current_pointer()

            
            if not self._move_mouse_pixel(max_pixel, max_pixel):
                self.logger.error("Failed to move to bottom-right corner during alignment")
                return False

            time.sleep(0.5)
            right_bottom = self._find_current_pointer()

            
            if not self._move_mouse_pixel(-max_pixel, max_pixel):
                self.logger.error("Failed to move to bottom-left corner during alignment")
                return False

            time.sleep(0.5)
            left_bottom = self._find_current_pointer()

            
            if not self._move_mouse_pixel(max_pixel, -max_pixel):
                self.logger.error("Failed to move to top-right corner during alignment")
                return False

            if not self._move_mouse_pixel(-10, -max_pixel):
                self.logger.error("Failed to move to top-right corner during alignment")
                return False

            time.sleep(0.5)
            right_top = self._find_current_pointer()

            self.logger.info(f"Corner positions: left_top={left_top}, right_top={right_top}, left_bottom={left_bottom}, right_bottom={right_bottom}")

            
            if all(pos is not None for pos in [left_top, right_top, left_bottom, right_bottom]):
                window_w = right_top[0] - left_top[0]
                window_h = left_bottom[1] - left_top[1]
                self.logger.info(f"Detected screen dimensions: {window_w}x{window_h}")

                
                if not self._move_mouse_pixel(-max_pixel, -max_pixel):
                    self.logger.error("Failed to move to top-left corner after alignment")
                    return False

                
                self._calc_mouse_ratio(window_w/2, window_h/2)

            self.logger.info("Mouse alignment completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Mouse alignment failed: {e}")
            return False

    def _calc_mouse_ratio(self, delta_x=500, delta_y=500):
        
        try:
            time.sleep(2)
            current_pos = self._find_current_pointer()

            if current_pos and self._move_mouse_pixel(delta_x, delta_y):
                time.sleep(2)
                target_pos = self._find_current_pointer()

                if target_pos:
                    ratio_x = abs(target_pos[0] - current_pos[0]) / delta_x
                    ratio_y = abs(target_pos[1] - current_pos[1]) / delta_y
                    self.logger.info(f"Mouse ratio calculated: x={ratio_x:.3f}, y={ratio_y:.3f}")

        except Exception as e:
            self.logger.warning(f"Mouse ratio calculation failed: {e}")

    def _is_task_manager_closed(self) -> bool:
        
        if not self.omniparser_client:
            self.logger.warning("OmniParser not available, assuming task manager closed")
            return True

        try:
            ui_elements = self.omniparser_client.get_ui_elements()
            if not ui_elements:
                return True

            
            for element in ui_elements:
                content = element.get('content', '').lower()
                if 'force quit' in content or 'force_quit' in content:
                    self.logger.debug(f"Task manager still open - found: {element.get('content', '')}")
                    return False

            self.logger.info("Task manager closed successfully - no 'Force Quit' text found")
            return True

        except Exception as e:
            self.logger.warning(f"Error checking task manager status: {e}")
            return True  

    def _bounce_leg(self):
        
        for _ in range(2):
            self.esp32.move_mouse(self.config.mouse.bouncing_leg_step, 0)
            time.sleep(0.1)
        self.config.mouse.bouncing_leg_step *= -1

    def display_app_cache(self):
        
        if not self.app_cache:
            print("App cache is empty")
            return

        print(f"\n=== App Cache ({len(self.app_cache)} entries) ===")
        for app_name, entry in self.app_cache.items():
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
            print(f"{app_name}:")
            print(f"  Page: {entry.page}")
            print(f"  Last updated: {timestamp_str}")
            print(f"  Stale: {entry.is_stale()}")
        print("=" * 40)
