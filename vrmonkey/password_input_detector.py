

import cv2
import numpy as np
from typing import Tuple, Optional


class PasswordInputDetector:
    

    def __init__(self):
        
        self.min_contour_area = 3000  
        self.max_contour_area = 300000  
        self.aspect_ratio_range = (1.5, 6.0)  
        self.min_brightness_threshold = 180  

    def detect(self, image_path: str) -> bool:
        
        img = cv2.imread(image_path)
        if img is None:
            return False

        return self.detect_from_array(img)

    def detect_from_array(self, img: np.ndarray) -> bool:
        
        if img is None or img.size == 0:
            return False

        
        result1 = self._detect_by_edges(img)

        
        result2 = self._detect_by_brightness(img)

        
        return result1 or result2

    def _detect_by_edges(self, img: np.ndarray) -> bool:
        
        
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

            
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

            
            if len(approx) < 4 or len(approx) > 8:
                continue

            
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                continue

            
            if self._detect_circular_patterns(roi):
                return True

        return False

    def _detect_by_brightness(self, img: np.ndarray) -> bool:
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        
        _, bright_mask = cv2.threshold(gray, self.min_brightness_threshold, 255, cv2.THRESH_BINARY)

        
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

            
            roi = gray[y:y+h, x:x+w]
            if roi.size > 0 and self._detect_circular_patterns(roi):
                return True

        return False

    def _detect_circular_patterns(self, roi: np.ndarray) -> bool:
        
        
        circles = cv2.HoughCircles(
            roi,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=20,  
            param1=50,
            param2=30,
            minRadius=5,
            maxRadius=30
        )

        
        if circles is not None:
            num_circles = len(circles[0])
            if 3 <= num_circles <= 6:
                return True

        return False

    def detect_with_visualization(self, image_path: str, output_path: Optional[str] = None) -> Tuple[bool, np.ndarray]:
        
        img = cv2.imread(image_path)
        if img is None:
            return False, None

        result = self.detect_from_array(img)

        
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
                
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 3)
                cv2.putText(annotated, "Password Input Detected", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if output_path:
            cv2.imwrite(output_path, annotated)

        return result, annotated



def quick_test(image_path: str) -> bool:
    
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
