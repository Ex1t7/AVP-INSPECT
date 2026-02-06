import serial
import time
import threading
import subprocess
import os
DEUBG=False

class ESP32Mouse:
    def __init__(self, port, baud_rate=115200, timeout=1, debug=True):
        """
        Initialize the connection to the ESP32.

        :param port: Serial port (e.g., 'COM3' or '/dev/ttyUSB0').
        :param baud_rate: Baud rate for the serial communication (default 115200).
        :param timeout: Read timeout for the serial connection (default 1 second).
        """
        self.port = port
        self.baud_rate = baud_rate
        self.debug = debug
        self.command_timeout = 15  # 15 seconds timeout for commands
        self.last_command_time = 0
        self.command_lock = threading.Lock()
        try:
            self.connection = serial.Serial(port, baud_rate, timeout=timeout)
            print(f"Connected to ESP32 on {port}")
        except Exception as e:
            print(f"Error connecting to ESP32: {e}")
            self.connection = None

    def reset_arduino_device(self):
        """
        Reset Arduino device using the reset script.
        """
        try:
            print("ESP32 timeout detected, attempting device reset...")
            script_path = os.path.join(os.path.dirname(__file__), 'reset_arduino.py')
            if os.path.exists(script_path):
                result = subprocess.run(['python3', script_path], 
                                      capture_output=True, text=True, timeout=30)
                print(f"Reset result: {result.stdout}")
                if result.returncode == 0:
                    print("Device reset successful, reconnecting...")
                    # Reconnect after reset
                    if self.connection:
                        try:
                            self.connection.close()
                        except:
                            pass
                    time.sleep(2)
                    try:
                        self.connection = serial.Serial(self.port, self.baud_rate, timeout=1)
                        print(f"Reconnected to ESP32 on {self.port}")
                        return True
                    except Exception as e:
                        print(f"Failed to reconnect: {e}")
                        self.connection = None
                        return False
                else:
                    print(f"Reset failed: {result.stderr}")
                    return False
            else:
                print("Reset script not found")
                return False
        except Exception as e:
            print(f"Error during reset: {e}")
            return False

    def send_command_with_timeout(self, command):
        """
        Send a command to the ESP32 with timeout detection.
        """
        if self.connection is None:
            print("Not connected to ESP32.")
            return False

        with self.command_lock:
            try:
                # Check if we're stuck on a previous command
                current_time = time.time()
                if current_time - self.last_command_time > self.command_timeout:
                    print("Previous command may have timed out, resetting device...")
                    if not self.reset_arduino_device():
                        return False
                
                self.last_command_time = current_time
                
                # Send command with timeout
                self.connection.write((command + '\n').encode('utf-8'))
                
                # Wait for response with timeout
                start_time = time.time()
                response = None
                
                while time.time() - start_time < self.command_timeout:
                    if self.connection.in_waiting:
                        response = self.connection.readline().decode('utf-8').strip()
                        break
                    time.sleep(0.01)  # Small delay to prevent busy waiting
                
                if response and self.debug:
                    print(f"ESP32 Response: {response}")
                
                # Check if we got a response within timeout
                if time.time() - start_time >= self.command_timeout:
                    print(f"Command '{command}' timed out after {self.command_timeout} seconds")
                    print("Attempting device reset...")
                    if self.reset_arduino_device():
                        # Retry the command once after reset
                        print("Retrying command after reset...")
                        return self.send_command_with_timeout(command)
                    else:
                        return False
                
                return True
                
            except Exception as e:
                print(f"Error sending command '{command}': {e}")
                print("Attempting device reset...")
                if self.reset_arduino_device():
                    # Retry the command once after reset
                    print("Retrying command after reset...")
                    return self.send_command_with_timeout(command)
                else:
                    return False

    def send_command(self, command):
        """
        Send a command to the ESP32 (legacy method, now uses timeout detection).
        """
        return self.send_command_with_timeout(command)

    def move_mouse(self, x, y):
        """
        Move the mouse pointer.

        :param x: Horizontal movement.
        :param y: Vertical movement.
        """
        command = f"MOVE {x} {y}"
        return self.send_command(command)

    def scroll_mouse(self, x, y):
        """
        Scroll the mouse.

        :param x: Horizontal scroll.
        :param y: Vertical scroll.
        """
        command = f"SCROLL {x} {y}"
        return self.send_command(command)

    def click_mouse(self, button):
        """
        Click a mouse button.

        :param button: Button code (e.g., 1 for left click, 2 for right click).
        """
        command = f"CLICK {button}"
        return self.send_command(command)

    def print_text(self, text):
        """
        Send a text string followed by an Enter key.

        :param text: Text to send.
        """
        command = f"PRINT {text}"
        return self.send_command(command)
         
    def write_key(self, key_name):
        """
        Send a predefined special key.

        :param key_name: Name of the key (e.g., ENTER, PLAYPAUSE).
        """
        command = f"WRITE {key_name}"
        return self.send_command(command)

    def keypress_action(self, action):
        """
        Send a key combination or specific action.

        :param action: Action name (e.g., CTRLALTDELETE, ENTER, PLAYPAUSE).
        """
        command = f"KEYPRESS {action}"
        return self.send_command(command)

    def open_task_manager(self):
        """
        Open the Windows Task Manager by sending the TASKMGR command.
        """
        command = "TASKMGR"
        return self.send_command(command)
        
    def recenter_view(self):
        """
        Recenter the view.
        """
        command = "HoldHome"
        return self.send_command(command)
        
    def close(self):
        """
        Close the connection to the ESP32.
        """
        if self.connection:
            self.connection.close()
            print("Disconnected from ESP32.")
