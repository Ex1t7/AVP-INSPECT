from pynput import keyboard
import pyautogui
import time
import os,cv2,requests
import subprocess
import json
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
from pointer_recognize import find_pointer_centers
from esp32_mouse import *
from gradio_client import Client, handle_file

mouse_ratio=1.0


def take_screenshot(remote = True):
    global screenshot_width, screenshot_height
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    local_path = f"/Users/{os.getlogin()}/Downloads/VR_monkey_hand/screenshots/screenshot_{timestamp}.png"
    
    if remote:
        url = 'http://192.168.1.188:5555/stream'
        stream = requests.get(url, stream=True)
        bytes_buffer = b''
        for chunk in stream.iter_content(chunk_size=1024):
            bytes_buffer += chunk
            a = bytes_buffer.find(b'\xff\xd8')  
            b = bytes_buffer.find(b'\xff\xd9')  
            if a != -1 and b != -1:
                jpg = bytes_buffer[a:b+2]
                bytes_buffer = bytes_buffer[b+2:]

                img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                screenshot_width, screenshot_height = img.shape[1::-1]
                cv2.imwrite(local_path, img)
                return local_path, timestamp
        
    
    
    

    screenshot = pyautogui.screenshot()
    
    
    
    
    screenshot.save(local_path)
    
    print(f"Screenshot saved to {local_path}")
    
    screenshot_width, screenshot_height = screenshot.size
    return local_path, timestamp





def run_OmniParser_on_server_and_get_masks(image_path):
    try:
        
        ssh_command = [
            'ssh', REMOTE_ALIAS,
            'zsh -l -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate base && cd /mnt/ssd2/VR_Monkey/OmniParser/ && python3 {0} --image {1}"'.format(OmniParserV2_SCRIPT_PATH, image_path)
        ]
        
        print(ssh_command)
        result = subprocess.run(ssh_command, capture_output=True, text=True)
        if result.returncode == 0:
            
            start  = result.stdout.index('[{')
            
            masks = json.loads(result.stdout[start:])
            return masks
        else:
            print("OmniParser Error:")
            print(result.stderr)
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing OmniParser on server: {e}")
        return None


def move_from_to_percentage(x,y,x_target,y_target):
    
    delta_x = x_target-x
    delta_y = y_target-y
    rightn = int(delta_x * screenshot_width/MOVE_STEP)
    downn = int(delta_y * screenshot_height/MOVE_STEP)
    stepr = MOVE_STEP*int(delta_x/abs(delta_x))
    stepd = MOVE_STEP*int(delta_y/abs(delta_y))
    print(rightn,downn,stepr,stepd)
    for i in range(abs(rightn)): esp32.move_mouse(stepr, 0)
    for i in range(abs(downn)): esp32.move_mouse(0, stepd)


def query_omniParser():
    local_path, timestamp = take_screenshot()
    
    
    result = client.predict(
        image_input=handle_file(local_path),
        box_threshold=0.05,
        iou_threshold=0.1,
        use_paddleocr=True,
        imgsz=640,
        api_name="/process"
    )
    
    icons = json.loads(result[1])
    
    labeled_img_path = result[0]
    pil_img = Image.open(labeled_img_path) 
    print(labeled_img_path)
    cv2.imshow('omniparser_result', np.array(pil_img))
    pointer = find_pointer_centers(local_path)
    
    
    return pointer,icons

def click_close_button():
    move_mouse_pixel(screenshot_width,screenshot_height)
    move_mouse_pixel(-1*screenshot_width,screenshot_height)
    
    
def click_back_button():
    move_mouse_pixel(-1*screenshot_width,-1*screenshot_height)
    

def check_same_state(icons_pre,icons_after):
    if abs(len(icons_after) - len(icons_pre)) < 3: return True
    else: return False
    
    
    
def explore_all_icons(pointer=None,icons=None):
    if not icons: icons = [{'type': 'text', 'bbox': [0.5558862686157227, 0.47148674726486206, 0.6190476417541504, 0.503564178943634], 'interactivity': False, 'content': ' Sleep Focus', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.5760582089424133, 0.5096741318702698, 0.5958994626998901, 0.5295315384864807], 'interactivity': False, 'content': 'Edit', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.4722222089767456, 0.5442973375320435, 0.528769850730896, 0.5728105902671814], 'interactivity': False, 'content': ' Allowed People', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.4728836119174957, 0.587067186832428, 0.5228174328804016, 0.6099796295166016], 'interactivity': False, 'content': 'Allowed Apps', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.47189152240753174, 0.6563136577606201, 0.4990079402923584, 0.6741344332695007], 'interactivity': False, 'content': 'Schedule', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.48578041791915894, 0.6787168979644775, 0.6838624477386475, 0.7209776043891907], 'interactivity': False, 'content': "Sleep Focs ollows the slee schedule you've set on iPho", 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.48379629850387573, 0.7118126153945923, 0.567460298538208, 0.7403258681297302], 'interactivity': False, 'content': 'tap Browse, then Sleep.', 'source': 'box_ocr_content_ocr'}, {'type': 'text', 'bbox': [0.4682539701461792, 0.7774949073791504, 0.5109127163887024, 0.7998981475830078], 'interactivity': False, 'content': 'Delete Focu', 'source': 'box_ocr_content_ocr'}, {'type': 'icon', 'bbox': [0.30601203441619873, 0.39558279514312744, 0.4430326521396637, 0.43665969371795654], 'interactivity': True, 'content': 'Focus ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.30316680669784546, 0.48781347274780273, 0.44307005405426025, 0.5328643918037415], 'interactivity': True, 'content': 'FaceTime ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.30100953578948975, 0.5317357778549194, 0.4425356090068817, 0.5739173889160156], 'interactivity': True, 'content': 'ersona ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.2999460697174072, 0.5723088383674622, 0.44178178906440735, 0.6149234771728516], 'interactivity': True, 'content': 'Eyes &Hands ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.30423954129219055, 0.4343486428260803, 0.44375357031822205, 0.47766855359077454], 'interactivity': True, 'content': 'Screen Time ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.2993154227733612, 0.7120394110679626, 0.438029944896698, 0.7523024082183838], 'interactivity': True, 'content': 'Control Center ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.2988433837890625, 0.7514626979827881, 0.43711042404174805, 0.7933204770088196], 'interactivity': True, 'content': 'Digital Crown ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.29936152696609497, 0.6676687598228455, 0.4394797384738922, 0.7132314443588257], 'interactivity': True, 'content': 'Accessibility ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.0, 0.8644243478775024, 0.0685061439871788, 0.9151952266693115], 'interactivity': True, 'content': 'nnect ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.2983003556728363, 0.7936040163040161, 0.4372548758983612, 0.8310602307319641], 'interactivity': True, 'content': 'Siri & Search ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.30079180002212524, 0.6132668256759644, 0.44085076451301575, 0.6592692732810974], 'interactivity': True, 'content': 'warenes & Safety ', 'source': 'box_yolo_content_ocr'}, {'type': 'icon', 'bbox': [0.47787365317344666, 0.45976313948631287, 0.544006884098053, 0.551574170589447], 'interactivity': True, 'content': 'Lime', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.454436331987381, 0.3686181604862213, 0.4759344756603241, 0.40364667773246765], 'interactivity': True, 'content': 'Back', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.30710697174072266, 0.35613930225372314, 0.4404589533805847, 0.3967898190021515], 'interactivity': True, 'content': 'a video player.', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.6836060881614685, 0.5997493267059326, 0.701525092124939, 0.6328127384185791], 'interactivity': True, 'content': 'Forward', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.47776326537132263, 0.8450061678886414, 0.542012095451355, 0.8727951645851135], 'interactivity': True, 'content': 'a battery level indicator.', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.5726659297943115, 0.4286532998085022, 0.6050760746002197, 0.4713205099105835], 'interactivity': True, 'content': '3D modeling or 3D modeling software.', 'source': 'box_yolo_content_yolo'}, {'type': 'icon', 'bbox': [0.6859914660453796, 0.5626347064971924, 0.6999591588973999, 0.5890843868255615], 'interactivity': True, 'content': 'Next', 'source': 'box_yolo_content_yolo'}]
    if not pointer: x_now,y_now = 0.5,0.5
    else:
        x_now = pointer[0]
        y_now = pointer[1]
    for idx, icon in enumerate(icons):
        if not icon['interactivity']: continue
        x_min,y_min,x_max,y_max = icon['bbox']
        print('[+]',idx,icon['content'])
        x_target = int((x_min+x_max)/2 * screenshot_width)
        y_target = int((y_min+y_max)/2 * screenshot_height)
        delta_x = x_target- x_now
        delta_y = y_target- y_now
        print((x_now,y_now),(x_target,y_target))
        move_mouse_pixel(delta_x,delta_y)
        x_now,y_now = x_target,y_target
        p,icons = query_omniParser()
        
        print("\n".join(f"{i}: {x}" for i, x in enumerate(icons)))
        esp32.click_mouse(1)
        time.sleep(2)
        local_path, timestamp = take_screenshot()
        p_after = find_pointer_centers(local_path)
        if p != None and p_after == None:
            esp32.move_mouse(-1,0)
            esp32.move_mouse(1,0)
        p_after,icons_after = query_omniParser()
        if check_same_state(icons,icons_after): continue
        else:
            explore_all_icons(p_after,icons_after)
    click_back_button()
    
def start_explorer():
    calc_mouse_ratio(delta=500)
    
    
    pointer,icons = query_omniParser()
    explore_all_icons(pointer,icons)
    
      
def on_keypress(key):
    
    try:
        if key.char:
            if key.char.lower() == 't' or key.char.lower() == 'j':
                if key.char.lower() == 't':
                    local_path, timestamp = '/Users/ex1t/Downloads/VR_monkey_hand/screenshots/screenshot_20250304-130734.png', '20250304-130734'
                elif key.char.lower() == 'j':
                    start_explorer()
                    
            elif key.char.lower() == 'i':
                move_mouse_pixel(450,192)
            elif key.char.lower() == 'k':
                move_mouse_pixel(500,500)
            elif key.char.lower() == 'w':
                esp32.move_mouse(0, -1*MOVE_STEP)  
            elif key.char.lower() == 'a':
                esp32.move_mouse(-1*MOVE_STEP, 0)  
            elif key.char.lower() == 't':
                esp32.move_mouse(MOVE_STEP, MOVE_STEP)
                esp32.move_mouse(1,1)
            elif key.char.lower() == 's':
                esp32.move_mouse(0, MOVE_STEP)  
            elif key.char.lower() == 'd':
                esp32.move_mouse(MOVE_STEP, 0)  
            elif key.char.lower() == 'e':
                explore_all_icons()    
            elif key.char.lower() == 'l':
                esp32.move_mouse(0, -1 * MOVE_STEP)
                esp32.move_mouse(0, MOVE_STEP)
                local_path, timestamp = take_screenshot()
                pointer0 = find_pointer_centers(local_path)
                for i in range(20): esp32.move_mouse(MOVE_STEP, 0)
                time.sleep(1)
                local_path, timestamp = take_screenshot()
                pointer1 = find_pointer_centers(local_path)
                for i in range(20): esp32.move_mouse(0, MOVE_STEP)
                time.sleep(1)
                local_path, timestamp = take_screenshot()
                pointer2 = find_pointer_centers(local_path)
                pointers = [pointer0,pointer1,pointer2]
                print(pointers)
                
                
            elif key.char.lower() == 'q':
                print("Exiting...")
                return False  
    except AttributeError:
        
        pass


def calc_mouse_ratio(delta=500):
    local_path, timestamp = take_screenshot()
    pointer = find_pointer_centers(local_path)
    while(not pointer):
        move_mouse_pixel(20,20)
        local_path, timestamp = take_screenshot()
        pointer = find_pointer_centers(local_path)
    move_mouse_pixel(-3000,-3000)

    local_path, timestamp = take_screenshot()
    pointer = find_pointer_centers(local_path)
    while(not pointer):
        move_mouse_pixel(10,10)
        local_path, timestamp = take_screenshot()
        pointer = find_pointer_centers(local_path)
    time.sleep(1)
    x_now, y_now  = pointer
    delta_x,delta_y = delta,delta
    move_mouse_pixel(delta_x,delta_y)
    local_path, timestamp = take_screenshot()
    x_target, y_target  = find_pointer_centers(local_path)
    global mouse_ratio
    print("pre",x_now,y_now)
    print("target", x_target, y_target)
    ratio_x = abs(x_target-x_now)/delta_x
    ratio_y = abs(y_target-y_now)/delta_y
    if abs(ratio_x - 1 )< abs(ratio_y-1):
        mouse_ratio = ratio_x
        print('mouse_ratio by x: ',mouse_ratio)
    else:
        mouse_ratio = ratio_y
        print('mouse_ratio by y: ',mouse_ratio)
    
    print('mouse_ratio: ',mouse_ratio)
    
    
def move_mouse_pixel(x,y,mouse_ratio=1.0):
    if x != 0:
        x_sign = int(abs(x)/x)
    else:
        x_sign = 1
    if y!=0:
        y_sign = int(abs(y)/y)
    else:
        y_sign = 1
    x = int(x * mouse_ratio)
    y = int(y * mouse_ratio)
    move_x_20_times = int(abs(x)/step20)
    move_x_10_times = int((abs(x) % step20)/step10)
    move_y_20_times = int(abs(y)/step20)
    move_y_10_times = int((abs(y) % step20)/step10)
    while move_x_20_times>0 or move_y_20_times>0:
        esp32.move_mouse( x_sign* 20 * min(1,max(move_x_20_times,0)) ,y_sign*20*min(1,max(move_y_20_times,0)) )
        move_x_20_times-=1
        move_y_20_times-=1
    
    while move_x_10_times>0 or move_y_10_times>0:
        esp32.move_mouse( x_sign* 10 * min(1,max(move_x_10_times,0)) ,y_sign*10*min(1,max(move_y_10_times,0)) )
        move_x_10_times-=1
        move_y_10_times-=1
    time.sleep(0.1)
    esp32.move_mouse(-1,0)
    esp32.move_mouse(-1,0)
    esp32.move_mouse(1,0)
    esp32.move_mouse(1,0)

def main():
    print("Press 'j' to take a screenshot and send it to the server. Press 'esc' to exit.")
    listener = keyboard.Listener(on_press=on_keypress)
    listener.start()  
    listener.join()   




client = Client("http://localhost:7861/")


REMOTE_ALIAS = 'gpu_rustdesk'
USERNAME = 'ex1t'
SSH_KEY_PATH = '～/.ssh/id_rsa'  
screenshot_width, screenshot_height = 3024,1964

REMOTE_PATH = '/mnt/ssd2/VR_Monkey/avp_images/test/'  
OmniParserV2_SCRIPT_PATH = '/mnt/ssd2/VR_Monkey/OmniParser/parse_image.py'  
local_path = ''
MOVE_STEP = 10
step20 = 30.28705877324809
step10 = 9.165820418219816

if __name__ == '__main__':
    esp32 = ESP32Mouse(port="/dev/cu.usbmodemDCDA0C20E1782")
    
    main()     

