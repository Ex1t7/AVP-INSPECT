"""
Password/PIN Input Pattern Detector for VisionOS
Detects the password input dialog with key icon and dots pattern
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class PasswordInputDetector:
    """Detects VisionOS password/PIN input dialog pattern"""

    def __init__(self):
        # Detection thresholds
        self.min_contour_area = 3000  # Minimum area for the white border box
        self.max_contour_area = 300000  # Maximum area
        self.aspect_ratio_range = (1.5, 6.0)  # Width/height ratio for the input box
        self.min_brightness_threshold = 180  # Minimum brightness for white border

    def detect(self, image_path: str) -> bool:
        """
        Detect if the password input pattern is present in the image

        Args:
            image_path: Path to the image file

        Returns:
            True if password input pattern is detected, False otherwise
        """
        img = cv2.imread(image_path)
        if img is None:
            return False

        return self.detect_from_array(img)

    def detect_from_array(self, img: np.ndarray) -> bool:
        """
        Detect if the password input pattern is present in the image array

        Args:
            img: Image as numpy array (BGR format)

        Returns:
            True if password input pattern is detected, False otherwise
        """
        if img is None or img.size == 0:
            return False

        # Method 1: White border detection with edge detection
        result1 = self._detect_by_edges(img)

        # Method 2: Direct brightness-based detection
        result2 = self._detect_by_brightness(img)

        # Return True if either method detects the pattern
        return result1 or result2

    def _detect_by_edges(self, img: np.ndarray) -> bool:
        """Detect password input by edge detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Detect edges using Canny
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Look for the characteristic white border box
        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by area
            if area < self.min_contour_area or area > self.max_contour_area:
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Check aspect ratio (width/height)
            if h == 0:
                continue
            aspect_ratio = w / h

            # The password input box should be wider than tall
            if not (self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]):
                continue

            # Check if the contour is roughly rectangular
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

            # Should have 4 corners (rectangle) or close to it
            if len(approx) < 4 or len(approx) > 8:
                continue

            # Extract the region of interest
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            # Additional check: look for circular patterns (dots) in the ROI
            if self._detect_circular_patterns(roi):
                return True

        return False

    def _detect_by_brightness(self, img: np.ndarray) -> bool:
        """Detect password input by looking for bright rectangular regions"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Threshold to find bright regions
        _, bright_mask = cv2.threshold(gray, self.min_brightness_threshold, 255, cv2.THRESH_BINARY)

        # Find contours in the bright regions
        contours, _ = cv2.findContours(bright_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < self.min_contour_area or area > self.max_contour_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)

            if h == 0:
                continue
            aspect_ratio = w / h

            if not (self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]):
                continue

            # Check if this bright region contains circular patterns
            roi = gray[y:y+h, x:x+w]
            if roi.size > 0 and self._detect_circular_patterns(roi):
                return True

        return False

    def _detect_circular_patterns(self, roi: np.ndarray) -> bool:
        """
        Detect circular patterns (password dots) in the ROI

        Args:
            roi: Region of interest (grayscale image)

        Returns:
            True if circular patterns are detected
        """
        # Use Hough Circle detection to find the dots
        circles = cv2.HoughCircles(
            roi,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,  # Minimum distance between circles
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=30
        )

        # If we detect 3-5 circles (typical for password dots), it's likely a password input
        if circles is not None:
            num_circles = len(circles[0])
            if 3 <= num_circles <= 6:
                return True

        return False

    def detect_with_visualization(self, image_path: str, output_path: Optional[str] = None) -> Tuple[bool, np.ndarray]:
        """
        Detect password input pattern and visualize the detection

        Args:
            image_path: Path to the image file
            output_path: Optional path to save the visualization

        Returns:
            Tuple of (detection_result, annotated_image)
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, None

        result = self.detect_from_array(img)

        # Draw the detection result on the image
        annotated = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_contour_area or area > self.max_contour_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if h == 0:
                continue
            aspect_ratio = w / h

            if not (self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]):
                continue

            roi = gray[y:y+h, x:x+w]
            if roi.size > 0 and self._detect_circular_patterns(roi):
                # Draw rectangle around detected password input
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 3)
                cv2.putText(annotated, "Password Input Detected", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if output_path:
            cv2.imwrite(output_path, annotated)

        return result, annotated


# Quick test function
def quick_test(image_path: str) -> bool:
    """
    Quick test function to detect password input pattern

    Args:
        image_path: Path to the screenshot image

    Returns:
        True if password input is detected, False otherwise
    """
    detector = PasswordInputDetector()
    return detector.detect(image_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python password_input_detector.py <image_path> [output_path]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    detector = PasswordInputDetector()

    if output_path:
        result, annotated = detector.detect_with_visualization(image_path, output_path)
        print(f"Password input detected: {result}")
        if annotated is not None:
            print(f"Visualization saved to: {output_path}")
    else:
        result = detector.detect(image_path)
        print(f"Password input detected: {result}")
