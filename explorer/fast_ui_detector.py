import cv2
import numpy as np

def quick_detect_center_ui(image_path, template_path="/mnt/ssd2/VR_monkey/templates/center_ui_template.png", 
                          threshold=0.85, roi_scale=0.5):
    
    
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    
    if img is None or template is None:
        return False
    
    h, w = img.shape[:2]
    
    
    rw, rh = int(w * roi_scale), int(h * roi_scale)
    x0, y0 = (w - rw) // 2, (h - rh) // 2
    roi = img[y0:y0+rh, x0:x0+rw]
    
    
    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hsv_template = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    
    
    lower = np.array([0, 0, 203])
    upper = np.array([179, 30, 253])
    
    mask_roi = cv2.inRange(hsv_roi, lower, upper)
    mask_template = cv2.inRange(hsv_template, lower, upper)
    
    
    result = cv2.matchTemplate(mask_roi, mask_template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    
    return max_val > threshold

def batch_detect(image_list, template_path="/mnt/ssd2/VR_monkey/templates/center_ui_template.png"):
    
    results = []
    template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    
    if template is None:
        return [False] * len(image_list)
    
    
    hsv_template = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, 203])
    upper = np.array([179, 30, 253])
    mask_template = cv2.inRange(hsv_template, lower, upper)
    
    for img_path in image_list:
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)
        if img is None:
            results.append(False)
            continue
            
        h, w = img.shape[:2]
        rw, rh = int(w * 0.5), int(h * 0.5)
        x0, y0 = (w - rw) // 2, (h - rh) // 2
        roi = img[y0:y0+rh, x0:x0+rw]
        
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask_roi = cv2.inRange(hsv_roi, lower, upper)
        
        result = cv2.matchTemplate(mask_roi, mask_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        results.append(max_val > 0.85)
    
    return results


if __name__ == "__main__":
    
    test_image = "/mnt/ssd2/VR_monkey/screenshots/screenshot_20250820-051759.png"
    detected = quick_detect_center_ui(test_image)
    print(f"快速检测结果: {detected}")
    
    
    image_list = [
        "/mnt/ssd2/VR_monkey/screenshots/screenshot_20250820-051759.png",
        
    ]
    results = batch_detect(image_list)
    print(f"批量检测结果: {results}")
