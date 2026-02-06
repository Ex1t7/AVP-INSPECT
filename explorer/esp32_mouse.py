import serial
import time
import threading
import subprocess
import os
DEUBG=False

class ESP32Mouse:
    def __init__(self, port, baud_rate=115200, timeout=1, debug=True):
        
        self.port = port
        self.baud_rate = baud_rate
        self.debug = debug
        self.command_timeout = 15  
        self.last_command_time = 0
        self.command_lock = threading.Lock()
        try:
            self.connection = serial.Serial(port, baud_rate, timeout=timeout)
            print(f"Connected to ESP32 on {port}")
        except Exception as e:
            print(f"Error connecting to ESP32: {e}")
            self.connection = None

    def reset_arduino_device(self):
        
        try:
            print("ESP32 timeout detected, attempting device reset...")
            script_path = os.path.join(os.path.dirname(__file__), 'reset_arduino.py')
            if os.path.exists(script_path):
                result = subprocess.run(['python3', script_path], 
                                      capture_output=True, text=True, timeout=30)
                print(f"Reset result: {result.stdout}")
                if result.returncode == 0:
                    print("Device reset successful, reconnecting...")
                    
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
        
        if self.connection is None:
            print("Not connected to ESP32.")
            return False

        with self.command_lock:
            try:
                
                current_time = time.time()
                if current_time - self.last_command_time > self.command_timeout:
                    print("Previous command may have timed out, resetting device...")
                    if not self.reset_arduino_device():
                        return False
                
                self.last_command_time = current_time
                
                
                self.connection.write((command + '\n').encode('utf-8'))
                
                
                start_time = time.time()
                response = None
                
                while time.time() - start_time < self.command_timeout:
                    if self.connection.in_waiting:
                        response = self.connection.readline().decode('utf-8').strip()
                        break
                    time.sleep(0.01)  
                
                if response and self.debug:
                    print(f"ESP32 Response: {response}")
                
                
                if time.time() - start_time >= self.command_timeout:
                    print(f"Command '{command}' timed out after {self.command_timeout} seconds")
                    print("Attempting device reset...")
                    if self.reset_arduino_device():
                        
                        print("Retrying command after reset...")
                        return self.send_command_with_timeout(command)
                    else:
                        return False
                
                return True
                
            except Exception as e:
                print(f"Error sending command '{command}': {e}")
                print("Attempting device reset...")
                if self.reset_arduino_device():
                    
                    print("Retrying command after reset...")
                    return self.send_command_with_timeout(command)
                else:
                    return False

    def send_command(self, command):
        
        return self.send_command_with_timeout(command)

    def move_mouse(self, x, y):
        
        command = f"MOVE {x} {y}"
        return self.send_command(command)

    def scroll_mouse(self, x, y):
        
        command = f"SCROLL {x} {y}"
        return self.send_command(command)

    def click_mouse(self, button):
        
        command = f"CLICK {button}"
        return self.send_command(command)

    def print_text(self, text):
        
        command = f"PRINT {text}"
        return self.send_command(command)
         
    def write_key(self, key_name):
        
        command = f"WRITE {key_name}"
        return self.send_command(command)

    def keypress_action(self, action):
        
        command = f"KEYPRESS {action}"
        return self.send_command(command)

    def open_task_manager(self):
        
        command = "TASKMGR"
        return self.send_command(command)
        
    def recenter_view(self):
        
        command = "HoldHome"
        return self.send_command(command)
        
    def close(self):
        
        if self.connection:
            self.connection.close()
            print("Disconnected from ESP32.")
