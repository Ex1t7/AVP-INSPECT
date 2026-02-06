


import sys
import time
import logging
import argparse
from typing import Optional


from config import Config
from screenshot_manager import ScreenshotManager
from mouse_controller import MouseController
from omniparser_client import OmniParserClient
from state_graph import StateGraph
from metrics_manager import MetricsManager
from app_manager import AppManager
from simple_state_explorer import StateExplorer
from esp32_mouse import ESP32Mouse
from video_recorder_client import VideoRecorderClient
import pointer_recognize


class StateExplorerApp:
    

    def __init__(self, app_name: str, timeout_minutes: int = 10):
        
        self.app_name = app_name
        self.timeout_minutes = timeout_minutes

        
        self.config = Config(app_name)
        self.config.exploration.timeout_minutes = timeout_minutes
        self.config.update_from_env()
        self.config.validate()

        
        self._setup_logging()

        
        self.esp32: Optional[ESP32Mouse] = None
        self.screenshot_manager: Optional[ScreenshotManager] = None
        self.mouse_controller: Optional[MouseController] = None
        self.omniparser_client: Optional[OmniParserClient] = None
        self.state_graph: Optional[StateGraph] = None
        self.metrics_manager: Optional[MetricsManager] = None
        self.app_manager: Optional[AppManager] = None
        self.state_explorer: Optional[StateExplorer] = None
        self.video_recorder: Optional[VideoRecorderClient] = None

        self.logger = logging.getLogger(__name__)

    def _setup_logging(self):
        
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

        
        logging.getLogger('gradio_client').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)

    def setup(self) -> bool:
        
        self.logger.info(f"Setting up State Explorer for app: {self.app_name}")

        try:
            
            self.logger.info("Initializing ESP32 connection...")
            self.esp32 = ESP32Mouse(
                port=self.config.app.esp32_port,
                debug=self.config.app.esp32_debug
            )

            
            self.logger.info("Initializing pointer recognition...")
            pointer_recognize.analyze_pointer_template()

            
            self.logger.info("Initializing screenshot manager...")
            self.screenshot_manager = ScreenshotManager(self.config)

            
            test_screenshot = self.screenshot_manager.take_screenshot()
            if not test_screenshot.success:
                raise Exception(f"Screenshot test failed: {test_screenshot.error_message}")

            
            self.logger.info("Initializing mouse controller...")
            self.mouse_controller = MouseController(self.config, self.esp32)

            
            self.logger.info("Initializing OmniParser client...")
            self.omniparser_client = OmniParserClient(self.config, self.screenshot_manager)

            
            if not self.omniparser_client.test_connection():
                raise Exception("OmniParser connection test failed")

            
            self.logger.info("Initializing state graph...")
            self.state_graph = StateGraph()

            
            self.logger.info("Initializing metrics manager...")
            self.metrics_manager = MetricsManager(self.config)
            if not self.metrics_manager.initialize(self.timeout_minutes):
                raise Exception("Metrics manager initialization failed")

            
            self.logger.info("Initializing app manager...")
            self.app_manager = AppManager(
                self.config, self.esp32,
                self.screenshot_manager, self.omniparser_client
            )

            
            self.logger.info("Initializing state explorer...")
            self.state_explorer = StateExplorer(
                self.config, self.state_graph, self.mouse_controller,
                self.screenshot_manager, self.omniparser_client,
                self.metrics_manager, self.esp32, self.app_manager
            )

            
            if self.config.video_recorder.enabled:
                self.logger.info("Initializing video recorder client...")
                self.video_recorder = VideoRecorderClient(
                    service_host=self.config.video_recorder.service_host,
                    service_port=self.config.video_recorder.service_port
                )
                if self.video_recorder.is_service_available():
                    self.logger.info("Video recording service is available")
                else:
                    self.logger.warning("Video recording service is not available - will proceed without recording")
            else:
                self.logger.info("Video recording is disabled")

            self.logger.info("All components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False

    def run(self) -> bool:
        
        try:
            self.logger.info(f"Starting exploration of {self.app_name} with {self.timeout_minutes}-minute timeout")

            
            if self.video_recorder and self.config.video_recorder.enabled:
                success, message = self.video_recorder.start_recording(self.app_name)
                if success:
                    self.logger.info(f"Video recording started: {message}")
                else:
                    self.logger.warning(f"Could not start video recording: {message}")

            
            

            
            if self.config.exploration.enable_home_detection:
                self.logger.info("📱 Capturing home screen state before opening app...")
                _, home_state = self.state_explorer.check_current_state()

                
                if home_state and len(home_state.buttons) == 0:
                    self.logger.info("🏠 Home menu not visible, opening it with FNH...")
                    self.esp32.keypress_action("FNH")  
                    time.sleep(2)  

                    
                    _, home_state = self.state_explorer.check_current_state()

                if home_state:
                    self.state_graph.set_home_state(home_state)
                    self.logger.info(f"🏠 Home screen state recorded for detection ({len(home_state.buttons)} buttons)")
                else:
                    self.logger.warning("Could not capture home screen state")

            
            self.logger.info(f"Opening application: {self.app_name}")
            app_success, app_position = self.app_manager.open_app()
            if not app_success:
                raise Exception(f"Failed to open {self.app_name}")

            self.logger.info(f"App opened successfully using Spotlight")

            
            self.logger.info("Calibrating mouse...")
            if not self._calibrate_mouse():
                raise Exception("Mouse calibration failed")

            
            
            time.sleep(3)  

            
            self.logger.info("Beginning state exploration...")
            self.state_explorer.explore_all_states()

            self.logger.info("Exploration completed successfully")
            return True

        except TimeoutError:
            self.logger.info("Exploration stopped due to timeout")
            return True  
        except Exception as e:
            self.logger.error(f"Exploration failed: {e}")
            return False
        finally:
            self._cleanup()

    def _calibrate_mouse(self) -> bool:
        
        try:
            
            self.logger.info("Testing mouse movement and pointer detection...")

            
            screenshot_result = self.screenshot_manager.take_screenshot()
            if not screenshot_result.success:
                return False

            
            initial_pointer = self.mouse_controller.find_pointer(screenshot_result.file_path)
            if initial_pointer is None:
                self.logger.warning("Cannot find initial pointer, attempting recovery...")
                
                max_pixel = self.config.mouse.max_pixel
                if not self.mouse_controller.move_pixel(-max_pixel, -max_pixel):
                    return False
                time.sleep(1)

                screenshot_result = self.screenshot_manager.take_screenshot()
                if not screenshot_result.success:
                    return False

                initial_pointer = self.mouse_controller.find_pointer(screenshot_result.file_path)
                if initial_pointer is None:
                    return False

            
            calibration_result = self.mouse_controller.calibrate_ratio(
                self.screenshot_manager, delta_x=300, delta_y=300
            )

            if calibration_result:
                self.logger.info("Mouse calibration completed successfully")
            else:
                self.logger.warning("Mouse calibration failed, using default ratio")

            return True

        except Exception as e:
            self.logger.error(f"Mouse calibration error: {e}")
            return False

    def _cleanup(self):
        
        self.logger.info("Cleaning up resources...")

        try:
            
            if self.video_recorder and self.config.video_recorder.enabled:
                if self.video_recorder.is_recording:
                    success, message, video_path = self.video_recorder.stop_recording()
                    if success:
                        self.logger.info(f"Video recording stopped: {video_path}")
                    else:
                        self.logger.warning(f"Error stopping video recording: {message}")

            
            self.logger.info("🧹 Closing all applications after exploration...")
            if self.app_manager:
                close_success = self.app_manager.close_all_apps(exclude_system_apps=True)
                if close_success:
                    self.logger.info("✅ All apps closed successfully")
                else:
                    self.logger.warning("⚠️ Some apps may not have been closed")
                time.sleep(2)  

            
            if self.esp32:
                self.esp32.close()

            
            if self.metrics_manager:
                self.metrics_manager.finalize()

            self.logger.info("Cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def close_all_apps(self, exclude_system_apps: bool = True) -> bool:
        
        if not self.app_manager:
            self.logger.error("App manager not initialized")
            return False

        return self.app_manager.close_all_apps(exclude_system_apps)

    def force_quit_all_apps(self) -> bool:
        
        if not self.app_manager:
            self.logger.error("App manager not initialized")
            return False

        return self.app_manager.force_quit_all_apps()

    def get_config_info(self) -> dict:
        
        return {
            'app_name': self.app_name,
            'timeout_minutes': self.timeout_minutes,
            'esp32_port': self.config.app.esp32_port,
            'screenshot_source': self.config.app.screenshot_source,
            'omniparser_url': self.config.network.omniparser_url,
            'metrics_enabled': self.config.app.enable_metrics
        }

    def print_system_info(self):
        
        info = self.get_config_info()
        print(f"\n=== State Explorer Configuration ===")
        for key, value in info.items():
            print(f"{key}: {value}")
        print("=" * 35)


def main():
    
    parser = argparse.ArgumentParser(
        description="ESP32 Mouse State Explorer - Automated UI Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal app exploration
  python state_explorer_refactored.py Linkeeper
  python state_explorer_refactored.py "My App" --timeout 15
  python state_explorer_refactored.py Calculator --debug

  # Task management operations
  python state_explorer_refactored.py dummy --close-all-apps
  python state_explorer_refactored.py dummy --force-quit-all
  python state_explorer_refactored.py dummy --config-info

  # For dedicated task management, use:
  python task_manager_utility.py --help
        """
    )

    parser.add_argument(
        'app_name',
        help='Name of the application to explore'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Exploration timeout in minutes (default: 10)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parser.add_argument(
        '--config-info',
        action='store_true',
        help='Show configuration information and exit'
    )

    parser.add_argument(
        '--close-all-apps',
        action='store_true',
        help='Close all applications and exit (excludes system apps)'
    )

    parser.add_argument(
        '--force-quit-all',
        action='store_true',
        help='Force quit ALL applications including system apps and exit'
    )

    parser.add_argument(
        '--enable-recording',
        action='store_true',
        help='Enable video recording during exploration (requires video_recorder_service.py to be running)'
    )

    args = parser.parse_args()

    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    
    app = StateExplorerApp(args.app_name, args.timeout)

    
    if args.enable_recording:
        app.config.video_recorder.enabled = True

    
    if args.config_info:
        app.print_system_info()
        return 0

    
    if args.close_all_apps or args.force_quit_all:
        if not app.setup():
            print("Failed to setup the application for task management.")
            return 1

        if args.close_all_apps:
            print("Closing all applications (excluding system apps)...")
            success = app.close_all_apps(exclude_system_apps=True)
            print(f"Close all apps: {'Success' if success else 'Failed'}")
            return 0 if success else 1

        if args.force_quit_all:
            print("⚠️  FORCE QUITTING ALL APPLICATIONS INCLUDING SYSTEM APPS!")
            print("This will close everything. Are you sure? (Press Ctrl+C to cancel)")
            time.sleep(3)  
            success = app.force_quit_all_apps()
            print(f"Force quit all: {'Success' if success else 'Failed'}")
            return 0 if success else 1

    
    if not app.setup():
        print("Failed to setup the application. Check logs for details.")
        return 1

    
    app.print_system_info()

    
    run_file = f"{args.app_name}_run.txt"
    try:
        with open(run_file, 'w') as f:
            f.write(f"{args.app_name} exploration started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception as e:
        print(f"Warning: Could not create run file: {e}")

    
    try:
        success = app.run()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\nExploration interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit_code = 1

    
    try:
        with open(run_file, 'a') as f:
            f.write(f"{args.app_name} exploration ended: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Exit code: {exit_code}\n")
    except Exception as e:
        print(f"Warning: Could not update run file: {e}")

    return exit_code



def state_explorer_metric(name: str, timeout_minutes: int = 10) -> bool:
    
    app = StateExplorerApp(name, timeout_minutes)
    if not app.setup():
        return False
    return app.run()


if __name__ == '__main__':
    sys.exit(main())