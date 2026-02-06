/**
 * ESP32 BLE Mouse and Keyboard Control via Serial Commands
 */
#include "BleCombo.h" // Ensure you have the BleCombo library installed
#include <ESP32Servo.h>

#define rotation_angle 15
#define servo2_rotation_angle 25
#define default_angle 90
#define delay_time 2500

Servo servo1;
Servo servo2;

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE Mouse and Keyboard...");
  
  // Initialize Keyboard and Mouse
  Keyboard.begin();
  Mouse.begin();
  servo1.attach(12); // D2 -> GPIO5
  servo2.attach(13); // D3 -> GPIO6

  servo1.write(default_angle);
  servo2.write(default_angle);
}


void loop() {
  if (Keyboard.isConnected()) { // Check if BLE Mouse is connected
    if (Serial.available() > 0) {
      String command = Serial.readStringUntil('\n'); // Read a command from Serial
      command.trim(); // Remove leading and trailing whitespace

      if (command.startsWith("MOVE")) {
        // Format: MOVE x y
        int x, y;
        sscanf(command.c_str(), "MOVE %d %d", &x, &y);
        moveMouse(x, y);
      }
      else if (command.startsWith("SCROLL")) {
        // Format: SCROLL x y
        int scrollX, scrollY;
        sscanf(command.c_str(), "SCROLL %d %d", &scrollX, &scrollY);
        scrollMouse(scrollX, scrollY);
      }
      else if (command.startsWith("TASKMGR")) {
        Serial.println("Using Servo to open Task Manager");
        servo1.write(default_angle - rotation_angle);
        servo2.write(default_angle + servo2_rotation_angle);
        delay(delay_time);
        servo1.write(default_angle);
        servo2.write(default_angle);
      }
      else if (command.startsWith("HoldHome")) {
        Serial.println("Using Servo to hold Home button");
        servo1.write(default_angle - rotation_angle);
        delay(1500);
        servo1.write(default_angle);
      }
      else if (command.startsWith("CLICK")) {
        // Format: CLICK button
        int button;
        sscanf(command.c_str(), "CLICK %d", &button);
        clickMouse(button);
      }
      else if (command.startsWith("PRINT")) {
        // Format: PRINT Your text here
        String text = command.substring(5); // Extract text after "PRINT"
        text.trim(); // Remove leading and trailing whitespace
        if (text.length() > 0) {
          Serial.println("Sending text with ENTER: " + text);
          Keyboard.println(text); // Sends the text followed by an Enter key
          delay(50);
          Keyboard.releaseAll();
        }
        else {
          Serial.println("PRINT command requires text. Usage: PRINT Your text here");
        }
      }
      else if (command.startsWith("WRITE")) {
        // Format: WRITE KEY_NAME
        String keyName = command.substring(5); // Extract key name after "WRITE"
        keyName.trim(); // Remove leading and trailing whitespace
        if (keyName.length() > 0) {
          uint16_t keyCode = getSpecialKeyCode(keyName);
          if (keyCode != 0) {
            Serial.println("Writing special key: " + keyName);
            Keyboard.write(keyCode); // Sends the special key
          }
          else {
            Serial.println("Unknown WRITE key. Use predefined special keys like ENTER, PLAYPAUSE.");
          }
        }
        else {
          Serial.println("WRITE command requires a key name. Usage: WRITE KEY_NAME");
        }
      }
      else if (command.startsWith("KEYPRESS")) {
        // Format: KEYPRESS ACTION
        String action = command.substring(9); // Extract action after "KEYPRESS"
        action.trim(); // Remove leading and trailing whitespace

        if (action.equalsIgnoreCase("ENTER")) {
          Serial.println("Sending Enter key...");
          Keyboard.write(KEY_RETURN);
        }
        else if (action.equalsIgnoreCase("PLAYPAUSE")) {
          Serial.println("Sending Play/Pause media key...");
          Keyboard.write(KEY_MEDIA_PLAY_PAUSE);
        }
        else if (action.equalsIgnoreCase("CTRLALTDELETE")) {
          Serial.println("Sending Ctrl+Alt+Delete...");
          Keyboard.press(KEY_LEFT_CTRL);
          Keyboard.press(KEY_LEFT_ALT);
          Keyboard.press(KEY_DELETE);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("TAB")) {
          Serial.println("Sending TAB (Go to next item)...");
          Keyboard.press(KEY_TAB);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("SHIFTTAB")) {
          Serial.println("Sending Shift-TAB (Go to previous item)...");
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press(KEY_TAB);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (command.equalsIgnoreCase("PING")) {
        // Health check command
        Serial.println("PONG");
      }
        else if (action.equalsIgnoreCase("SPACE")) {
          Serial.println("Sending Space (Activate selected item)...");
          Keyboard.press(' ');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("FNH")) {
          Serial.println("Sending Cmd+H (Go to Home View)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('h');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("FNC")) {
          Serial.println("Sending Cmd+C (Open Control Centre)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('c');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("FNN")) {
          Serial.println("Sending Cmd+N (Open Notification Centre)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('n');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("TABH")) {
          Serial.println("Sending Tab+H (Show Help)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press('h');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("GOBACK")) {
          Serial.println("Sending Go Back command...");
          Keyboard.press(KEY_ESC);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("CONTEXTMENU")) {
          Serial.println("Opening Contextual Menu (Tab+M)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press('m');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ACTIONS")) {
          Serial.println("Opening Actions Menu (Tab+Z)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press('z');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ANALYTICS")) {
          Serial.println("Opening Analytics...(Cmd+Shift+.)");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press('.');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("PASSTHROUGH")) {
          Serial.println("Toggling Pass-Through Mode...(Cmd+Shift+P)");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press('p');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("GESTURES")) {
          Serial.println("Opening Keyboard Gestures (Tab+G)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press('g');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("MOVETOBEGIN")) {
          Serial.println("Moving to beginning (Tab+Left Arrow)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press(KEY_LEFT_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("MOVETOEND")) {
          Serial.println("Moving to end (Tab+Right Arrow)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press(KEY_RIGHT_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("MOVETONEXT")) {
          Serial.println("Moving to next item (Ctrl+Tab)...");
          Keyboard.press(KEY_LEFT_CTRL);
          Keyboard.press(KEY_TAB);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("MOVETOPREV")) {
          Serial.println("Moving to previous item (Ctrl+Shift+Tab)...");
          Keyboard.press(KEY_LEFT_CTRL);
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press(KEY_TAB);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("RESTART")) {
          Serial.println("Restarting (Shift+Ctrl+Cmd+R)...");
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press(KEY_LEFT_CTRL);
          Keyboard.press(KEY_LEFT_GUI);
          Keyboard.press('r');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("SIRI")) {
          Serial.println("Opening Siri (Cmd+S)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('s');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ACCESSIBILITY")) {
          Serial.println("Opening Accessibility Shortcut (Tab+X)...");
          Keyboard.press(KEY_TAB);
          Keyboard.press('x');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("TOUCH")) {
          Serial.println("Sending Touch command (Cmd+T)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('t');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("UP")) {
          Serial.println("Sending Up Arrow key...");
          Keyboard.press(KEY_UP_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("DOWN")) {
          Serial.println("Sending Down Arrow key...");
          Keyboard.press(KEY_DOWN_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("LEFT")) {
          Serial.println("Sending Left Arrow key...");
          Keyboard.press(KEY_LEFT_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("RIGHT")) {
          Serial.println("Sending Right Arrow key...");
          Keyboard.press(KEY_RIGHT_ARROW);
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ZOOMIN")) {
          Serial.println("Sending Zoom In (Cmd+=)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(KEY_LEFT_SHIFT);
          Keyboard.press('=');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ZOOMOUT")) {
          Serial.println("Sending Zoom Out (Cmd+-)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('-');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ROTATELEFT")) {
          Serial.println("Sending Rotate Left (Cmd+[)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press('[');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("ROTATERIGHT")) {
          Serial.println("Sending Rotate Right (Cmd+])...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(']');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("SPOTLIGHT")) {
          Serial.println("Opening Spotlight (Cmd+Space)...");
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(' ');
          delay(100);
          Keyboard.releaseAll();
        }
        else if (action.equalsIgnoreCase("FORCEQUIT")) {
          Serial.println("Opening Force Quit (Option+Command+Esc)...");
          Keyboard.press(KEY_LEFT_ALT);
          Keyboard.press(KEY_RIGHT_GUI);
          Keyboard.press(27);  // ASCII ESC
          delay(100);
          Keyboard.releaseAll();
        }
        else {
          Serial.println("Unknown KEYPRESS action. Use: ENTER, PLAYPAUSE, CTRLALTDELETE, TAB, SHIFTTAB, SPACE, FNH, FNC, FNN, TABH, GOBACK, CONTEXTMENU, ACTIONS, ANALYTICS, PASSTHROUGH, GESTURES, UP, DOWN, LEFT, RIGHT, ZOOMIN, ZOOMOUT, ROTATELEFT, ROTATERIGHT, SPOTLIGHT, FORCEQUIT, MOVETOBEGIN, MOVETOEND, MOVETONEXT, MOVETOPREV, RESTART, SIRI, or ACCESSIBILITY.");
        }
      }
      else {
        Serial.println("Unknown command. Use: MOVE, SCROLL, CLICK, PRINT, WRITE, KEYPRESS, or TOUCH.");
      }
    }
  }
}

// Function to move the mouse
void moveMouse(int x, int y) {
  Serial.printf("Moving mouse: x=%d, y=%d\n", x, y);
  Mouse.move(x, y);
}

// Function to scroll the mouse
void scrollMouse(int scrollX, int scrollY) {
  Serial.printf("Scrolling mouse: scrollX=%d, scrollY=%d\n", scrollX, scrollY);
  Mouse.move(0, 0, scrollY, scrollX);
}

// Function to click the mouse
void clickMouse(int button) {
  Serial.printf("Clicking mouse button: %d\n", button);
  Mouse.click(button);
}

// Function to map special key names to key codes
uint16_t getSpecialKeyCode(String keyName) {
  keyName.toUpperCase();
  if (keyName == "ENTER") {
    return KEY_RETURN;
  }
  else if (keyName == "ESCAPE") {
    return KEY_ESC;
  }
  else if (keyName == "TAB") {
    return KEY_TAB;
  }
  else if (keyName == "BACKSPACE") {
    return KEY_BACKSPACE;
  }
  // Add more special keys as needed
  else {
    return 0; // Unknown key
  }
}
