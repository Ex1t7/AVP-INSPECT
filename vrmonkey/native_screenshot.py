import os
import time
from datetime import datetime
import subprocess
import Quartz
from AppKit import NSWorkspace, NSScreen, NSImage
from Foundation import NSMakeRect
import pyautogui  # For fallback and supplementary functionality

def create_screenshots_dir():
    """Create screenshots directory if it doesn't exist"""
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
    return os.path.abspath("screenshots")

def get_timestamp():
    """Get current timestamp formatted for filenames"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def take_fullscreen_screenshot(filename=None):
    """
    Take a screenshot of the entire screen using macOS native screencapture
    
    Parameters:
    filename (str): Optional. Custom filename for the screenshot.
    
    Returns:
    str: Path to the saved screenshot file
    """
    screenshots_dir = create_screenshots_dir()
    
    if filename is None:
        filename = f"fullscreen_{get_timestamp()}.png"
    
    if not filename.endswith(".png"):
        filename += ".png"
    
    filepath = os.path.join(screenshots_dir, filename)
    
    # Use macOS built-in screencapture command
    subprocess.run(["screencapture", "-x", filepath])
    
    print(f"Full screen screenshot saved: {filepath}")
    return filepath

def get_active_window_info():
    """Get information about the currently active window in macOS"""
    # Get the frontmost application
    frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
    app_name = frontmost_app.localizedName()
    
    # Get window information using Quartz
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID
    )
    
    for window in window_list:
        if window.get('kCGWindowOwnerName') == app_name and window.get('kCGWindowIsOnscreen'):
            bounds = window.get('kCGWindowBounds')
            return {
                'app_name': app_name,
                'window_name': window.get('kCGWindowName', 'Unnamed Window'),
                'x': bounds['X'],
                'y': bounds['Y'],
                'width': bounds['Width'],
                'height': bounds['Height']
            }
    
    return None

def capture_active_window(filename=None):
    """
    Capture the currently active window in macOS
    
    Parameters:
    filename (str): Optional. Custom filename for the screenshot.
    
    Returns:
    str: Path to the saved screenshot file
    """
    screenshots_dir = create_screenshots_dir()
    
    # Get active window info
    window_info = get_active_window_info()
    
    if not window_info:
        print("Could not identify active window. Taking full screen screenshot instead.")
        return take_fullscreen_screenshot(filename)
    
    app_name = window_info['app_name']
    sanitized_app_name = ''.join(c if c.isalnum() else '_' for c in app_name)
    
    if filename is None:
        filename = f"{sanitized_app_name}_{get_timestamp()}.png"
    
    if not filename.endswith(".png"):
        filename += ".png"
    
    filepath = os.path.join(screenshots_dir, filename)
    
    # Use macOS built-in screencapture command with window bounds
    subprocess.run([
        "screencapture", 
        "-x",  # No sound
        "-R", f"{window_info['x']},{window_info['y']},{window_info['width']},{window_info['height']}",
        filepath
    ])
    
    print(f"Active window screenshot saved: {filepath}")
    print(f"Window: {window_info['window_name']} ({app_name})")
    return filepath

def list_all_windows():
    """List all visible windows on the system"""
    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID
    )
    
    print("\nVisible Windows:")
    print("-" * 60)
    print(f"{'Index':<6}{'Application':<20}{'Window Name':<30}{'Dimensions'}")
    print("-" * 60)
    
    windows = []
    index = 0
    
    for window in window_list:
        app_name = window.get('kCGWindowOwnerName', 'Unknown')
        window_name = window.get('kCGWindowName', 'Unnamed Window')
        
        # Skip windows without names or system windows
        if not window_name or app_name in ['Dock', 'Window Server']:
            continue
            
        bounds = window.get('kCGWindowBounds')
        if bounds:
            dimensions = f"{bounds['Width']}x{bounds['Height']}"
            windows.append({
                'app_name': app_name,
                'window_name': window_name,
                'bounds': bounds
            })
            print(f"{index:<6}{app_name[:19]:<20}{window_name[:29]:<30}{dimensions}")
            index += 1
    
    return windows

def capture_specific_window(filename=None):
    """
    Allow user to select a specific window to capture
    
    Parameters:
    filename (str): Optional. Custom filename for the screenshot.
    
    Returns:
    str: Path to the saved screenshot file
    """
    screenshots_dir = create_screenshots_dir()
    
    windows = list_all_windows()
    
    if not windows:
        print("No visible windows found. Taking full screen screenshot instead.")
        return take_fullscreen_screenshot(filename)
    
    try:
        index = int(input("\nEnter the index of the window to capture: "))
        if index < 0 or index >= len(windows):
            raise ValueError("Index out of range")
    except ValueError:
        print("Invalid input. Taking full screen screenshot instead.")
        return take_fullscreen_screenshot(filename)
    
    selected_window = windows[index]
    bounds = selected_window['bounds']
    app_name = selected_window['app_name']
    sanitized_app_name = ''.join(c if c.isalnum() else '_' for c in app_name)
    
    if filename is None:
        filename = f"{sanitized_app_name}_{get_timestamp()}.png"
    
    if not filename.endswith(".png"):
        filename += ".png"
    
    filepath = os.path.join(screenshots_dir, filename)
    
    # Use macOS built-in screencapture command with window bounds
    subprocess.run([
        "screencapture", 
        "-x",  # No sound
        "-R", f"{bounds['X']},{bounds['Y']},{bounds['Width']},{bounds['Height']}",
        filepath
    ])
    
    print(f"Window screenshot saved: {filepath}")
    print(f"Window: {selected_window['window_name']} ({app_name})")
    return filepath

def interactive_region_selection(filename=None):
    """
    Let user select a region for screenshot using macOS native selection
    
    Parameters:
    filename (str): Optional. Custom filename for the screenshot.
    
    Returns:
    str: Path to the saved screenshot file
    """
    screenshots_dir = create_screenshots_dir()
    
    if filename is None:
        filename = f"region_{get_timestamp()}.png"
    
    if not filename.endswith(".png"):
        filename += ".png"
    
    filepath = os.path.join(screenshots_dir, filename)
    
    print("Please select a region on your screen...")
    
    # Use macOS built-in screencapture command with interactive selection
    subprocess.run(["screencapture", "-i", "-x", filepath])
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"Region screenshot saved: {filepath}")
        return filepath
    else:
        print("Screenshot was cancelled or failed.")
        if os.path.exists(filepath):
            os.remove(filepath)
        return None

def timed_screenshots(interval=10, duration=60):
    """
    Take screenshots at regular intervals for a specified duration
    
    Parameters:
    interval (int): Time between screenshots in seconds
    duration (int): Total duration in seconds
    """
    screenshots_dir = create_screenshots_dir()
    num_screenshots = duration // interval
    
    print(f"Taking {num_screenshots} screenshots at {interval}-second intervals")
    print(f"Total duration: {duration} seconds")
    print(f"Screenshots will be saved to: {screenshots_dir}")
    print("Press Ctrl+C to stop")
    
    try:
        for i in range(num_screenshots):
            filename = f"timed_{i+1}_{get_timestamp()}.png"
            filepath = os.path.join(screenshots_dir, filename)
            
            # Use macOS built-in screencapture
            subprocess.run(["screencapture", "-x", filepath])
            
            print(f"Screenshot {i+1}/{num_screenshots} saved: {filename}")
            
            if i < num_screenshots - 1:
                time.sleep(interval)
        
        print("\nTimed screenshots completed!")
    
    except KeyboardInterrupt:
        print("\nTimed screenshots stopped by user")

def capture_all_screens(filename=None):
    """
    Capture all screens/displays connected to the Mac
    
    Parameters:
    filename (str): Optional. Base filename for the screenshots.
    
    Returns:
    list: Paths to the saved screenshot files
    """
    screenshots_dir = create_screenshots_dir()
    screens = NSScreen.screens()
    filepaths = []
    
    print(f"Found {len(screens)} display(s)")
    
    for i, screen in enumerate(screens):
        screen_number = i + 1
        
        if filename is None:
            screen_filename = f"display_{screen_number}_{get_timestamp()}.png"
        else:
            base, ext = os.path.splitext(filename)
            ext = ext if ext else ".png"
            screen_filename = f"{base}_display_{screen_number}{ext}"
        
        if not screen_filename.endswith(".png"):
            screen_filename += ".png"
        
        filepath = os.path.join(screenshots_dir, screen_filename)
        
        # Get screen frame
        frame = screen.frame()
        x, y = int(frame.origin.x), int(frame.origin.y)
        width, height = int(frame.size.width), int(frame.size.height)
        
        # Use macOS built-in screencapture command with screen bounds
        subprocess.run([
            "screencapture", 
            "-x",
            "-R", f"{x},{y},{width},{height}",
            filepath
        ])
        
        print(f"Display {screen_number} screenshot saved: {filepath}")
        filepaths.append(filepath)
    
    return filepaths

def main():
    """Main menu function"""
    print("\n🖼  macOS Screenshot Utility 🖼")
    
    while True:
        print("\nOptions:")
        print("1. Full Screen Screenshot")
        print("2. Active Window Screenshot")
        print("3. Select Specific Window")
        print("4. Interactive Region Selection")
        print("5. Timed Screenshots")
        print("6. Capture All Displays")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == "1":
            take_fullscreen_screenshot()
        
        elif choice == "2":
            print("Switching to active window in 3 seconds...")
            time.sleep(3)
            capture_active_window()
        
        elif choice == "3":
            capture_specific_window()
        
        elif choice == "4":
            interactive_region_selection()
        
        elif choice == "5":
            try:
                interval = int(input("Enter interval between screenshots (seconds, default 10): ") or 10)
                duration = int(input("Enter total duration (seconds, default 60): ") or 60)
                timed_screenshots(interval, duration)
            except ValueError:
                print("Invalid input. Using default values.")
                timed_screenshots()
        
        elif choice == "6":
            capture_all_screens()
        
        elif choice == "7":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice! Please try again.")

if __name__ == "__main__":
    main()