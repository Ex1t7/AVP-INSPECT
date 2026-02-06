import cv2
import numpy as np

# Global variable for custom center
custom_center = None

# Global variables
pointer_template = {
    'circle_radius': None,
    'circle_boldness': None,
    'center_boldness': None,
    'hsv_range': {
        'lower': np.array([36, 25, 25]),
        'upper': np.array([86, 255, 255])
    }
}

def update_custom_center(main_image, threshold=0.3, temp_save_path='temp_filtered_image.png', show_visualization=False):
    """
    Update the global custom_center variable by finding the circle closest to the default image center.
    
    Parameters:
        main_image (numpy.ndarray or str): The main image or its file path in which to search for the pointer.
        threshold (float): Threshold for circle detection (default is 0.3).
        temp_save_path (str): File path to temporarily save the filtered image.
        show_visualization (bool): Whether to show visualization windows (default is False).
    
    Returns:
        Tuple[int, int] or None: The updated custom center coordinates, or None if no valid circle is found.
    """
    global custom_center
    
    # Load main image if provided as a file path
    if isinstance(main_image, str):
        main_image = cv2.imread(main_image)
    if main_image is None or main_image.size == 0:
        raise ValueError("Main image is empty or not loaded correctly.")
    
    # Define the HSV range for green
    lower_green = np.array([36, 25, 25])
    upper_green = np.array([86, 255, 255])
    
    # Filter the main image for green
    hsv_main = cv2.cvtColor(main_image, cv2.COLOR_BGR2HSV)
    mask_main = cv2.inRange(hsv_main, lower_green, upper_green)
    filtered_main = cv2.bitwise_and(main_image, main_image, mask=mask_main)
    cv2.imwrite(temp_save_path, filtered_main)
    
    # Show the filtered image if visualization is enabled
    if show_visualization:
        cv2.imshow('Filtered Image (Green)', filtered_main)
        cv2.waitKey(1)  # Wait for 1ms to update the window
    
    # Convert to grayscale for circle detection
    gray = cv2.cvtColor(filtered_main, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Detect circles using HoughCircles
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=20,
        maxRadius=100
    )
    
    # Create a copy of the filtered image for visualization
    visualization = filtered_main.copy()
    
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for circle in circles[0, :]:
            x, y, r = circle
            # Draw the circle
            cv2.circle(visualization, (x, y), r, (0, 255, 0), 2)
            # Draw the center point
            cv2.circle(visualization, (x, y), 2, (0, 0, 255), 3)
    
    # Show the visualization with detected circles if enabled
    if show_visualization:
        cv2.imshow('Detected Circles', visualization)
        cv2.waitKey(1)  # Wait for 1ms to update the window
    
    if circles is None:
        if show_visualization:
            cv2.waitKey(0)  # Wait for key press before closing windows
            cv2.destroyAllWindows()
        return None
    
    circles = np.uint16(np.around(circles))
    
    # Determine the default center of the main image
    img_h, img_w = main_image.shape[:2]
    default_center_x, default_center_y = img_w // 2, img_h // 2
    
    # Find the circle closest to the default center
    closest_circle = None
    min_distance = float('inf')
    
    for circle in circles[0, :]:
        x, y, r = circle
        
        # Extract ROI around the circle center
        roi_size = 10
        roi_x1 = max(0, x - roi_size)
        roi_y1 = max(0, y - roi_size)
        roi_x2 = min(img_w, x + roi_size)
        roi_y2 = min(img_h, y + roi_size)
        
        roi = gray[roi_y1:roi_y2, roi_x1:roi_x2]
        
        # Check if there's a dot in the center (same green color as the circle)
        center_intensity = roi[roi.shape[0]//2, roi.shape[1]//2]
        surrounding_intensity = np.mean(roi)
        
        if center_intensity > surrounding_intensity:
            # Calculate distance from the default center
            distance = np.sqrt((x - default_center_x)**2 + (y - default_center_y)**2)
            
            if distance < min_distance:
                min_distance = distance
                closest_circle = (x, y)
    
    if closest_circle is None:
        if show_visualization:
            cv2.waitKey(0)  # Wait for key press before closing windows
            cv2.destroyAllWindows()
        return None
    
    # Update the global custom_center
    custom_center = closest_circle
    
    # Draw the selected circle in a different color
    cv2.circle(visualization, closest_circle, 5, (255, 0, 0), -1)  # Blue dot for selected center
    
    # Show the final selection if visualization is enabled
    if show_visualization:
        cv2.imshow('Final Selection', visualization)
        cv2.waitKey(0)  # Wait for key press before closing windows
        cv2.destroyAllWindows()
    
    return closest_circle

def find_pointer_centers(main_image, threshold=0.3, temp_save_path='temp_filtered_image.png', show_visualization=False):
    """
    Detect the pointer centers in the main image by filtering for green color and detecting circles.
    The function looks for circular shapes with a dot in the center, using template characteristics
    for improved detection. If no matches are found with strict conditions, it progressively
    loosens the matching criteria.
    
    Parameters:
        main_image (numpy.ndarray or str): The main image or its file path in which to search for the pointer.
        threshold (float): Threshold for circle detection (default is 0.3).
        temp_save_path (str): File path to temporarily save the filtered image.
        show_visualization (bool): Whether to show visualization windows (default is False).
    
    Returns:
        Tuple[int, int] or None: A tuple of (x, y) coordinates representing the center 
                                 point of the pointer that is furthest from the image center, or
                                 None if no valid match is found.
    """
    global custom_center, pointer_template
    
    # Check if template has been analyzed
    if pointer_template['circle_radius'] is None:
        raise ValueError("Pointer template has not been analyzed. Call analyze_pointer_template first.")
    
    # Load main image if provided as a file path
    if isinstance(main_image, str):
        main_image = cv2.imread(main_image)
    if main_image is None or main_image.size == 0:
        raise ValueError("Main image is empty or not loaded correctly.")
    
    # Filter the main image for green using template HSV range
    hsv_main = cv2.cvtColor(main_image, cv2.COLOR_BGR2HSV)
    mask_main = cv2.inRange(hsv_main, pointer_template['hsv_range']['lower'], pointer_template['hsv_range']['upper'])
    filtered_main = cv2.bitwise_and(main_image, main_image, mask=mask_main)
    cv2.imwrite(temp_save_path, filtered_main)
    
    # Show the filtered image if visualization is enabled
    if show_visualization:
        cv2.imshow('Filtered Image (Green)', filtered_main)
        cv2.waitKey(1)  # Wait for 1ms to update the window
    
    # Convert to grayscale for circle detection
    gray = cv2.cvtColor(filtered_main, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Define progressive radius ranges
    radius_ranges = [
        (0.8, 1.2),  # First try: strict range (±20%)
        (0.6, 1.4),  # Second try: wider range (±40%)
        (0.4, 1.6),  # Third try: even wider range (±60%)
        (0.2, 1.8)   # Last resort: very wide range (±80%)
    ]
    
    # Define progressive boldness tolerances
    boldness_tolerances = [
        0.2,  # First try: 20% tolerance
        0.3,  # Second try: 30% tolerance
        0.4,  # Third try: 40% tolerance
        0.5   # Last resort: 50% tolerance
    ]
    
    # Try each progressively looser set of conditions
    for radius_range, boldness_tolerance in zip(radius_ranges, boldness_tolerances):
        # Detect circles using HoughCircles with current radius range
        template_radius = pointer_template['circle_radius']
        min_radius = max(20, int(template_radius * radius_range[0]))
        max_radius = min(100, int(template_radius * radius_range[1]))
        
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=min_radius,
            maxRadius=max_radius
        )
        
        if circles is None:
            continue
        
        circles = np.uint16(np.around(circles))
        
        # Determine the center of the main image
        img_h, img_w = main_image.shape[:2]
        if custom_center is not None:
            center_x, center_y = custom_center
        else:
            center_x, center_y = img_w // 2, img_h // 2
        
        # Create a copy of the filtered image for visualization
        visualization = filtered_main.copy()
        
        # Find the circle with the center dot, using current tolerance
        valid_circles = []
        for circle in circles[0, :]:
            x, y, r = circle
            
            # Calculate circle boldness
            circle_mask = np.zeros_like(gray)
            cv2.circle(circle_mask, (x, y), r, 255, 1)
            circle_pixels = gray[circle_mask > 0]
            circle_boldness = np.mean(circle_pixels) / 255.0
            
            # Calculate center point boldness
            center_roi_size = 5
            center_roi = gray[
                max(0, y - center_roi_size):min(gray.shape[0], y + center_roi_size),
                max(0, x - center_roi_size):min(gray.shape[1], x + center_roi_size)
            ]
            center_boldness = np.mean(center_roi) / 255.0
            
            # Check if circle and center boldness match template with current tolerance
            circle_boldness_match = abs(circle_boldness - pointer_template['circle_boldness']) <= boldness_tolerance
            center_boldness_match = abs(center_boldness - pointer_template['center_boldness']) <= boldness_tolerance
            
            if circle_boldness_match and center_boldness_match:
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                valid_circles.append(((x, y), distance))
                
                if show_visualization:
                    # Draw the circle
                    cv2.circle(visualization, (x, y), r, (0, 255, 0), 2)
                    # Draw the center point
                    cv2.circle(visualization, (x, y), 2, (0, 0, 255), 3)
        print(valid_circles)
        if valid_circles:
            # Select the circle furthest from the image center
            selected = max(valid_circles, key=lambda x: x[1])
            selected_center = selected[0]
            
            # Draw the selected circle in a different color
            cv2.circle(visualization, selected_center, 5, (255, 0, 0), -1)  # Blue dot for selected center
            cv2.imwrite('temp_filtered_image.png',visualization)
            # Show the final selection if visualization is enabled
            if show_visualization:
                cv2.imshow('Final Selection', visualization)
                cv2.waitKey(0)  # Wait for key press before closing windows
                cv2.destroyAllWindows()
            
            return (int(selected_center[0]), int(selected_center[1]))
    
    # If we get here, no valid circles were found with any tolerance level
    if show_visualization:
        cv2.waitKey(0)  # Wait for key press before closing windows
        cv2.destroyAllWindows()
    return None

def analyze_pointer_template(template_image_path='../screenshots/pointer_template_main.png', show_visualization=False):
    """
    Analyze a pointer template image to extract its characteristics.
    
    Parameters:
        template_image_path (str): Path to the template image file.
        show_visualization (bool): Whether to show visualization windows.
    
    Returns:
        dict: Dictionary containing the extracted characteristics.
    """
    global pointer_template
    
    # Load template image
    template = cv2.imread(template_image_path)
    if template is None:
        raise ValueError(f"Could not load template image from {template_image_path}")
    
    # Convert to HSV and filter for green
    hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, pointer_template['hsv_range']['lower'], pointer_template['hsv_range']['upper'])
    filtered = cv2.bitwise_and(template, template, mask=mask)
    
    # Convert to grayscale for analysis
    gray = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # Detect circles
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=20,
        maxRadius=100
    )
    
    if circles is None:
        raise ValueError("No circles detected in the template image")
    
    circles = np.uint16(np.around(circles))
    
    # Create visualization if needed
    if show_visualization:
        visualization = template.copy()
    
    # Analyze the first circle found (assuming template has only one circle)
    x, y, r = circles[0, 0]
    
    # Calculate circle boldness (average intensity along the circle perimeter)
    circle_mask = np.zeros_like(gray)
    cv2.circle(circle_mask, (x, y), r, 255, 1)  # Draw circle with thickness 1
    circle_pixels = gray[circle_mask > 0]
    circle_boldness = np.mean(circle_pixels) / 255.0
    
    # Calculate center point boldness
    center_roi_size = 5
    center_roi = gray[
        max(0, y - center_roi_size):min(gray.shape[0], y + center_roi_size),
        max(0, x - center_roi_size):min(gray.shape[1], x + center_roi_size)
    ]
    center_boldness = np.mean(center_roi) / 255.0
    
    # Update global template characteristics
    pointer_template.update({
        'circle_radius': int(r),
        'circle_boldness': float(circle_boldness),
        'center_boldness': float(center_boldness)
    })
    
    if show_visualization:
        # Draw the detected circle
        cv2.circle(visualization, (x, y), r, (0, 255, 0), 2)
        # Draw the center point
        cv2.circle(visualization, (x, y), 2, (0, 0, 255), 3)
        
        # Show the visualization
        cv2.imshow('Template Analysis', visualization)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return pointer_template

def main():
    # Path to the template image
    template_image_path = '/Users/ex1t/Downloads/VR_monkey_hand/screenshots/pointer_template.png'
    
    # Path to the main image
    main_image_path = '/Users/ex1t/Downloads/VR_monkey_hand/screenshots/screenshot_20250325-144558.png'
    
    # First, analyze the pointer template
    print("Analyzing pointer template...")
    template_characteristics = analyze_pointer_template(template_image_path, show_visualization=True)
    print("Template characteristics:", template_characteristics)
    
    # Then, update the custom center
    print("\nUpdating custom center...")
    new_center = update_custom_center(main_image_path, show_visualization=True)
    print("Updated custom center to:", new_center)
    
    # Finally, find the pointer center using the template characteristics
    print("\nFinding pointer center...")
    pointer_center = find_pointer_centers(main_image_path, show_visualization=True)
    print("Pointer center found at:", pointer_center)

if __name__ == '__main__':
    main()
