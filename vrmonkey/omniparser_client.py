"""OmniParser client for UI element detection."""

import json
import logging
from typing import List, Dict, Optional, Any
from gradio_client import Client, handle_file
from PIL import Image
import numpy as np

from config import Config
from fast_ui_detector import quick_detect_center_ui


class OmniParserClient:
    """Client for interacting with OmniParser service."""

    def __init__(self, config: Config, screenshot_manager):
        self.config = config
        self.screenshot_manager = screenshot_manager
        self.logger = logging.getLogger(__name__)
        self.client: Optional[Client] = None
        self.last_labeled_image: Optional[str] = None

        self._initialize_client()

    def _initialize_client(self) -> bool:
        """Initialize the Gradio client connection."""
        try:
            self.client = Client(
                self.config.network.omniparser_url,
                httpx_kwargs={"timeout": self.config.omniparser.timeout}
            )
            self.logger.info(f"OmniParser client initialized: {self.config.network.omniparser_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize OmniParser client: {e}")
            return False

    def get_ui_elements(self, retry: bool = True) -> Optional[List[Dict[str, Any]]]:
        """
        Get UI elements from the current screen using OmniParser.

        Args:
            retry: Whether to retry on failure

        Returns:
            List of UI elements or None if failed
        """
        if not self.client:
            if not self._initialize_client():
                return None

        # Take screenshot
        screenshot_result = self.screenshot_manager.take_screenshot()
        if not screenshot_result.success:
            self.logger.error("Failed to take screenshot for OmniParser")
            return []  # Return empty list instead of None

        try:
            # Call OmniParser API
            result = self.client.predict(
                image_input=handle_file(screenshot_result.file_path),
                box_threshold=self.config.omniparser.box_threshold,
                iou_threshold=self.config.omniparser.iou_threshold,
                use_paddleocr=self.config.omniparser.use_paddleocr,
                imgsz=self.config.omniparser.imgsz,
                api_name="/process",
            )

            # Store labeled image path
            self.last_labeled_image = result[0] if result and len(result) > 0 else None

            # Parse the JSON result
            if len(result) > 1:
                icons_raw = json.loads(result[1])

                # Handle empty or None results (e.g., plain background with no buttons)
                if icons_raw is None or not icons_raw:
                    self.logger.info("OmniParser returned empty result (no UI elements detected, possibly plain background)")
                    return []  # Return empty list instead of None

                icons = self._validate_and_filter_icons(icons_raw)
                self.logger.debug(f"OmniParser found {len(icons)} valid UI elements")
                return icons
            else:
                self.logger.warning("OmniParser returned incomplete result")
                return []  # Return empty list instead of None

        except Exception as e:
            # Check if it's the "NoneType is not iterable" error (empty result)
            if "'NoneType' object is not iterable" in str(e):
                self.logger.info("OmniParser returned empty result (no UI elements detected)")
                return []  # Return empty list for empty results

            self.logger.error(f"OmniParser prediction failed: {e}")

            # Handle specific error cases
            if 'could not execute a primitive' in str(e) and retry:
                self.logger.info("Retrying OmniParser call...")
                return self.get_ui_elements(retry=False)

            # Check for password UI
            if self._check_for_password_ui(screenshot_result.file_path):
                self.logger.warning("Password UI detected")
                return []  # Return empty list instead of None

            return []  # Return empty list instead of None for other errors

    def _validate_and_filter_icons(self, icons_raw: List[Any]) -> List[Dict[str, Any]]:
        """
        Validate and filter icon data from OmniParser.

        Args:
            icons_raw: Raw icon data from OmniParser

        Returns:
            List of validated icon dictionaries
        """
        # Handle None or empty input
        if not icons_raw:
            return []

        validated_icons = []

        for i, icon in enumerate(icons_raw):
            if not isinstance(icon, dict):
                self.logger.debug(f"Skipping non-dict icon {i}: {type(icon)}")
                continue

            # Check required fields
            required_fields = ['content', 'bbox', 'interactivity', 'source']
            if not all(field in icon for field in required_fields):
                self.logger.debug(f"Skipping icon {i} missing required fields")
                continue

            # Validate bbox
            bbox = icon['bbox']
            if not isinstance(bbox, list) or len(bbox) != 4:
                self.logger.debug(f"Skipping icon {i} with invalid bbox format: {bbox}")
                continue

            if not all(isinstance(x, (int, float)) for x in bbox):
                self.logger.debug(f"Skipping icon {i} with non-numeric bbox: {bbox}")
                continue

            # Validate bbox values are reasonable
            if any(x < 0 or x > 1 for x in bbox):
                self.logger.debug(f"Skipping icon {i} with out-of-range bbox: {bbox}")
                continue

            # Add validated icon
            validated_icons.append({
                'content': str(icon['content']),
                'bbox': [float(x) for x in bbox],
                'interactivity': bool(icon['interactivity']),
                'source': str(icon['source'])
            })

        return validated_icons

    def _check_for_password_ui(self, screenshot_path: str) -> bool:
        """
        Check if the current screen shows a password UI.

        Args:
            screenshot_path: Path to the screenshot

        Returns:
            True if password UI is detected
        """
        try:
            return quick_detect_center_ui(screenshot_path)
        except Exception as e:
            self.logger.error(f"Error checking for password UI: {e}")
            return False

    def get_last_labeled_image(self) -> Optional[str]:
        """Get the path to the last labeled image from OmniParser."""
        return self.last_labeled_image

    def test_connection(self) -> bool:
        """Test the connection to OmniParser service."""
        try:
            if not self.client:
                return self._initialize_client()

            # Try a simple health check if available
            # For now, just check if client is initialized
            return self.client is not None
        except Exception as e:
            self.logger.error(f"OmniParser connection test failed: {e}")
            return False

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the OmniParser service."""
        return {
            'url': self.config.network.omniparser_url,
            'timeout': self.config.omniparser.timeout,
            'box_threshold': self.config.omniparser.box_threshold,
            'iou_threshold': self.config.omniparser.iou_threshold,
            'use_paddleocr': self.config.omniparser.use_paddleocr,
            'imgsz': self.config.omniparser.imgsz,
            'connected': self.client is not None
        }