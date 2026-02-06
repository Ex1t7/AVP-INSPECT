"""Metrics collection and logging functionality."""

import os
import time
import logging
import shutil
from typing import Optional

from config import Config
from core_types import MetricsData


class MetricsManager:
    """Manages exploration metrics collection and logging."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics: Optional[MetricsData] = None
        self.app_dir = ""
        self.state_images_dir = ""
        self.run_timestamp = time.strftime("%Y%m%d_%H%M%S")

    def initialize(self, timeout_minutes: int = 10) -> bool:
        """
        Initialize metrics collection for the current app.

        Args:
            timeout_minutes: Exploration timeout in minutes

        Returns:
            True if initialization was successful
        """
        if not self.config.app.enable_metrics:
            self.logger.info("Metrics collection is disabled")
            return True

        try:
            # Create app directory with timestamp
            self.app_dir = self.config.paths.get_app_dir(
                self.config.app.name,
                self.run_timestamp if self.config.paths.use_timestamp else None
            )
            os.makedirs(self.app_dir, exist_ok=True)

            # Create state images directory
            self.state_images_dir = self.config.paths.get_state_images_dir(
                self.config.app.name,
                self.run_timestamp if self.config.paths.use_timestamp else None
            )
            os.makedirs(self.state_images_dir, exist_ok=True)

            # Set up logging
            log_file = self.config.paths.get_log_file(
                self.config.app.name,
                self.run_timestamp if self.config.paths.use_timestamp else None
            )

            # Create a 'latest' symlink to this run (Unix-like systems only)
            if self.config.paths.use_timestamp:
                try:
                    latest_link = os.path.join(
                        self.config.paths.exploration_results_dir,
                        self.config.app.name,
                        "latest"
                    )
                    # Remove old symlink if it exists
                    if os.path.islink(latest_link):
                        os.unlink(latest_link)
                    # Create new symlink pointing to current run
                    os.symlink(f"run_{self.run_timestamp}", latest_link)
                except Exception as e:
                    self.logger.warning(f"Could not create 'latest' symlink: {e}")
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

            # Add handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)

            # Initialize metrics data
            self.metrics = MetricsData(
                start_time=time.time(),
                timeout_seconds=timeout_minutes * 60
            )

            self.logger.info(f"Metrics initialized for {self.config.app.name} "
                           f"with {timeout_minutes}-minute timeout")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize metrics: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self.config.app.enable_metrics and self.metrics is not None

    def is_timeout_reached(self) -> bool:
        """Check if the exploration timeout has been reached."""
        if not self.is_enabled():
            return False
        return self.metrics.is_timeout_reached()

    def get_remaining_time(self) -> float:
        """Get remaining exploration time in seconds."""
        if not self.is_enabled():
            return float('inf')
        return self.metrics.get_remaining_time()

    def record_state_found(self):
        """Record that a new state was found."""
        if self.is_enabled():
            self.metrics.states_found += 1

    def record_state_explored(self):
        """Record that a state was explored."""
        if self.is_enabled():
            self.metrics.states_explored += 1

    def record_button_found(self, count: int = 1):
        """Record that buttons were found."""
        if self.is_enabled():
            self.metrics.buttons_found += count

    def record_button_explored(self):
        """Record that a button was explored."""
        if self.is_enabled():
            self.metrics.buttons_explored += 1

    def record_pointer_move_success(self, accuracy: float):
        """Record a successful pointer movement."""
        if self.is_enabled():
            self.metrics.pointer_moves_success += 1
            self.metrics.pointer_move_accuracy.append(accuracy)

    def record_pointer_move_failure(self):
        """Record a failed pointer movement."""
        if self.is_enabled():
            self.metrics.pointer_moves_failed += 1

    def save_state_image(self, state_index: int, source_image_path: str) -> bool:
        """
        Save a state image to the metrics directory.

        Args:
            state_index: Index of the state in the graph
            source_image_path: Path to the source image file

        Returns:
            True if the image was saved successfully
        """
        if not self.is_enabled():
            return True

        try:
            state_image_filename = f"state_{state_index}_image.webp"
            state_image_path = os.path.join(self.state_images_dir, state_image_filename)
            shutil.copyfile(source_image_path, state_image_path)

            self.logger.info(f"Saved state image: {state_image_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save state image: {e}")
            return False

    def log_metrics(self, additional_info: Optional[str] = None):
        """Log current metrics summary."""
        if not self.is_enabled():
            return

        elapsed_time = self.metrics.get_elapsed_time()
        remaining_time = self.metrics.get_remaining_time()
        avg_accuracy = self.metrics.get_average_accuracy()

        metrics_summary = f"""
Metrics Summary:
- Time elapsed: {elapsed_time:.2f} seconds
- Time remaining: {remaining_time:.2f} seconds
- Timeout reached: {self.metrics.is_timeout_reached()}
- States found: {self.metrics.states_found}
- States explored: {self.metrics.states_explored}
- Buttons found: {self.metrics.buttons_found}
- Buttons explored: {self.metrics.buttons_explored}
- Pointer moves successful: {self.metrics.pointer_moves_success}
- Pointer moves failed: {self.metrics.pointer_moves_failed}
- Average pointer move accuracy: {avg_accuracy:.2f}%
"""

        if additional_info:
            metrics_summary += f"- Additional info: {additional_info}\n"

        self.logger.info(metrics_summary)

        # Also print to console
        print(f"=== Metrics Update ===")
        print(f"Time remaining: {remaining_time/60:.1f} minutes")
        print(f"States found: {self.metrics.states_found}")
        print(f"States explored: {self.metrics.states_explored}")
        print(f"Buttons explored: {self.metrics.buttons_explored}")
        print(f"Average accuracy: {avg_accuracy:.1f}%")
        print("=====================")

    def get_metrics_data(self) -> Optional[MetricsData]:
        """Get the current metrics data."""
        return self.metrics

    def finalize(self):
        """Finalize metrics collection and log final summary."""
        if not self.is_enabled():
            return

        self.log_metrics("Final metrics summary")

        # Create final report
        try:
            report_path = os.path.join(self.app_dir, "final_report.txt")
            with open(report_path, 'w') as f:
                f.write(f"Exploration Report for {self.config.app.name}\n")
                f.write("=" * 50 + "\n\n")

                f.write(f"App: {self.config.app.name}\n")
                f.write(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.metrics.start_time))}\n")
                f.write(f"Duration: {self.metrics.get_elapsed_time():.2f} seconds\n")
                f.write(f"Timeout: {self.metrics.timeout_seconds/60:.1f} minutes\n")
                f.write(f"Completed: {'Yes' if self.metrics.is_timeout_reached() else 'No'}\n\n")

                f.write("Statistics:\n")
                f.write(f"- States discovered: {self.metrics.states_found}\n")
                f.write(f"- States explored: {self.metrics.states_explored}\n")
                f.write(f"- Buttons found: {self.metrics.buttons_found}\n")
                f.write(f"- Buttons explored: {self.metrics.buttons_explored}\n")
                f.write(f"- Successful pointer moves: {self.metrics.pointer_moves_success}\n")
                f.write(f"- Failed pointer moves: {self.metrics.pointer_moves_failed}\n")
                f.write(f"- Average move accuracy: {self.metrics.get_average_accuracy():.2f}%\n")

                if self.metrics.pointer_moves_success > 0:
                    success_rate = (self.metrics.pointer_moves_success /
                                  (self.metrics.pointer_moves_success + self.metrics.pointer_moves_failed)) * 100
                    f.write(f"- Pointer move success rate: {success_rate:.2f}%\n")

            self.logger.info(f"Final report saved: {report_path}")

        except Exception as e:
            self.logger.error(f"Failed to create final report: {e}")

    def get_app_dir(self) -> str:
        """Get the app directory path."""
        return self.app_dir

    def get_state_images_dir(self) -> str:
        """Get the state images directory path."""
        return self.state_images_dir