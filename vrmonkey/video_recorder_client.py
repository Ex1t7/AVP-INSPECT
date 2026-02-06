"""Client for controlling the video recording service."""

import logging
import requests
from typing import Optional, Tuple


class VideoRecorderClient:
    """Client for interacting with the video recording service."""

    def __init__(self, service_host: str = "127.0.0.1", service_port: int = 8899):
        """
        Initialize the video recorder client.

        Args:
            service_host: Host where the recording service is running
            service_port: Port where the recording service is running
        """
        self.service_host = service_host
        self.service_port = service_port
        self.base_url = f"http://{service_host}:{service_port}"
        self.logger = logging.getLogger(__name__)
        self.is_recording = False
        self.current_app_name: Optional[str] = None

    def start_recording(self, app_name: str, timeout: int = 5) -> Tuple[bool, str]:
        """
        Start recording for the given app.

        Args:
            app_name: Name of the app to record
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, message)
        """
        try:
            url = f"{self.base_url}/start_recording"
            response = requests.post(
                url,
                json={"app_name": app_name},
                timeout=timeout
            )

            if response.status_code == 200:
                self.is_recording = True
                self.current_app_name = app_name
                self.logger.info(f"Recording started for {app_name}")
                return True, f"Recording started for {app_name}"
            else:
                error_msg = response.json().get('message', 'Unknown error')
                self.logger.warning(f"Failed to start recording: {error_msg}")
                return False, error_msg

        except requests.exceptions.ConnectionError:
            msg = f"Cannot connect to video recording service at {self.base_url}"
            self.logger.warning(msg)
            return False, msg
        except requests.exceptions.Timeout:
            msg = f"Timeout connecting to video recording service"
            self.logger.warning(msg)
            return False, msg
        except Exception as e:
            msg = f"Error starting recording: {e}"
            self.logger.error(msg)
            return False, msg

    def stop_recording(self, timeout: int = 5) -> Tuple[bool, str, Optional[str]]:
        """
        Stop the current recording.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, message, video_path)
        """
        try:
            url = f"{self.base_url}/stop_recording"
            response = requests.post(url, timeout=timeout)

            if response.status_code == 200:
                data = response.json()
                video_path = data.get('video_path')
                message = data.get('message', 'Recording stopped')

                self.is_recording = False
                app_name = self.current_app_name
                self.current_app_name = None

                self.logger.info(f"Recording stopped for {app_name}: {video_path}")
                return True, message, video_path
            else:
                error_msg = response.json().get('message', 'Unknown error')
                self.logger.warning(f"Failed to stop recording: {error_msg}")
                return False, error_msg, None

        except requests.exceptions.ConnectionError:
            msg = f"Cannot connect to video recording service at {self.base_url}"
            self.logger.warning(msg)
            return False, msg, None
        except requests.exceptions.Timeout:
            msg = f"Timeout connecting to video recording service"
            self.logger.warning(msg)
            return False, msg, None
        except Exception as e:
            msg = f"Error stopping recording: {e}"
            self.logger.error(msg)
            return False, msg, None

    def get_status(self, timeout: int = 5) -> Tuple[bool, dict]:
        """
        Get the current recording status.

        Args:
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, status_dict)
        """
        try:
            url = f"{self.base_url}/status"
            response = requests.get(url, timeout=timeout)

            if response.status_code == 200:
                status = response.json()
                return True, status
            else:
                return False, {}

        except Exception as e:
            self.logger.debug(f"Error getting recording status: {e}")
            return False, {}

    def is_service_available(self, timeout: int = 2) -> bool:
        """
        Check if the video recording service is available.

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if service is available
        """
        success, _ = self.get_status(timeout=timeout)
        return success
