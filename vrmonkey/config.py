"""Configuration settings for the ESP32 Mouse State Explorer."""

import os
import time
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class NetworkConfig:
    """Network-related configuration."""
    lan_mode: bool = True
    omniparser_host: str = "10.193.124.191"
    omniparser_port: int = 7861
    remote_stream_host: str = "192.168.1.15"
    remote_stream_port: int = 5050
    gstreamer_host: str = "192.168.1.14"
    gstreamer_port: int = 5000

    @property
    def omniparser_url(self) -> str:
        host = self.omniparser_host if self.lan_mode else "localhost"
        return f"http://{host}:{self.omniparser_port}/"

    @property
    def remote_stream_url(self) -> str:
        return f"http://{self.remote_stream_host}:{self.remote_stream_port}/stream"


@dataclass
class MouseConfig:
    """Mouse movement and calibration configuration."""
    max_pixel: int = 9999
    move_step: int = 10
    step20: float = 30.28705877324809
    step10: float = 9.165820418219816
    bouncing_leg_step: int = 1
    tolerance: int = 15
    max_attempts: int = 10

    # Adaptive ratio learning
    ratio_learning_samples: int = 3
    ratio_learning_rate: float = 0.3
    min_ratio_samples: int = 3


@dataclass
class ScreenConfig:
    """Screen and display configuration."""
    width: int = 3024
    height: int = 1964
    monitor_number: int = 2  # For airplay source


@dataclass
class ExplorationConfig:
    """State exploration configuration."""
    timeout_minutes: int = 20  # Changed from 10 to 20 minutes
    max_consecutive_failures: int = 5
    max_clicks_without_new_state: int = 15
    max_lost_pointer_count: int = 5
    max_search_pages: int = 20
    enable_home_detection: bool = True  # Detect and handle returning to home state
    max_home_returns: int = 3  # Max times we can return to home before restarting app
    max_no_movement_attempts: int = 5  # Max consecutive no-movement attempts before declaring dead-end


@dataclass
class OmniParserConfig:
    """OmniParser API configuration."""
    box_threshold: float = 0.05
    iou_threshold: float = 0.1
    use_paddleocr: bool = False
    imgsz: int = 640
    timeout: float = 60.0


@dataclass
class PathConfig:
    """File and directory paths."""
    screenshot_dir: str = "/mnt/ssd2/VR_monkey/screenshots"
    exploration_results_dir: str = "exploration_results"
    app_cache_file: str = "app_cache.pkl"
    use_timestamp: bool = True  # Add timestamp to run directories to avoid overwriting

    def get_app_dir(self, app_name: str, run_timestamp: Optional[str] = None) -> str:
        """Get the directory for app exploration results.

        Args:
            app_name: Name of the application
            run_timestamp: Optional timestamp string. If not provided and use_timestamp is True,
                          will use 'latest' as a symlink to the most recent run

        Returns:
            Path to the app directory
        """
        if self.use_timestamp and run_timestamp:
            # Use timestamped subdirectory: exploration_results/{app_name}/run_{timestamp}/
            return os.path.join(self.exploration_results_dir, app_name, f"run_{run_timestamp}")
        else:
            # Use simple directory: exploration_results/{app_name}/
            return os.path.join(self.exploration_results_dir, app_name)

    def get_state_images_dir(self, app_name: str, run_timestamp: Optional[str] = None) -> str:
        return os.path.join(self.get_app_dir(app_name, run_timestamp), "state_images")

    def get_log_file(self, app_name: str, run_timestamp: Optional[str] = None) -> str:
        return os.path.join(self.get_app_dir(app_name, run_timestamp), f"{app_name}_metrics.log")


@dataclass
class VideoRecorderConfig:
    """Video recording service configuration."""
    enabled: bool = False  # Enable video recording during exploration
    service_host: str = "127.0.0.1"
    service_port: int = 8899


@dataclass
class AppConfig:
    """Application-specific configuration."""
    name: str = "Linkeeper"
    esp32_port: str = "/dev/serial/by-id/usb-Arduino_Nano_ESP32_DCDA0C20E178-if01"
    esp32_debug: bool = False
    enable_metrics: bool = True
    screenshot_source: str = "remote"  # Options: 'remote', 'airplay', 'gstreamer'


class Config:
    """Main configuration class that aggregates all config sections."""

    def __init__(self, app_name: Optional[str] = None):
        self.network = NetworkConfig()
        self.mouse = MouseConfig()
        self.screen = ScreenConfig()
        self.exploration = ExplorationConfig()
        self.omniparser = OmniParserConfig()
        self.paths = PathConfig()
        self.app = AppConfig()
        self.video_recorder = VideoRecorderConfig()

        if app_name:
            self.app.name = app_name

    def update_from_env(self):
        """Update configuration from environment variables."""
        if os.getenv("OMNIPARSER_HOST"):
            self.network.omniparser_host = os.getenv("OMNIPARSER_HOST")

        if os.getenv("ESP32_PORT"):
            self.app.esp32_port = os.getenv("ESP32_PORT")

        if os.getenv("SCREENSHOT_SOURCE"):
            self.app.screenshot_source = os.getenv("SCREENSHOT_SOURCE")

        if os.getenv("TIMEOUT_MINUTES"):
            self.exploration.timeout_minutes = int(os.getenv("TIMEOUT_MINUTES"))

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.app.name:
            raise ValueError("App name must be specified")

        if not os.path.exists(os.path.dirname(self.paths.screenshot_dir)):
            raise ValueError(f"Screenshot directory parent does not exist: {self.paths.screenshot_dir}")

        return True