import os
import threading
import time
from flask import Flask, request, jsonify
import cv2
import requests
import numpy as np

app = Flask(__name__)

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), 'recordings')
os.makedirs(RECORDINGS_DIR, exist_ok=True)


recording_thread = None
recording_active = False
current_app_name = None
current_video_path = None
recording_stop_event = None

STREAM_URL = 'http://192.168.1.15:5050/stream'


def mjpeg_stream_reader(stream_url):
    
    print(f"Connecting to MJPEG stream at {stream_url}")
    try:
        stream = requests.get(stream_url, stream=True, timeout=10)
        print(f"Stream connected, status code: {stream.status_code}")
    except Exception as e:
        print(f"ERROR: Failed to connect to stream: {e}")
        return

    bytes_buffer = b''
    frame_num = 0
    for chunk in stream.iter_content(chunk_size=1024):
        if not chunk:
            continue
        bytes_buffer += chunk
        a = bytes_buffer.find(b'\xff\xd8')  
        b = bytes_buffer.find(b'\xff\xd9')  
        if a != -1 and b != -1 and b > a:
            jpg = bytes_buffer[a:b+2]
            bytes_buffer = bytes_buffer[b+2:]
            
            if len(jpg) > 2:
                try:
                    img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        frame_num += 1
                        if frame_num == 1:
                            print(f"First frame decoded successfully: {img.shape}")
                        yield img
                except Exception as e:
                    print(f"Warning: Failed to decode frame: {e}")
                    continue


def record_stream(app_name, stop_event):
    global current_video_path
    timestamp = time.strftime('%Y%m%d-%H%M')  
    filename = f"{app_name}_{timestamp}.mp4"
    video_path = os.path.join(RECORDINGS_DIR, filename)
    current_video_path = video_path
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')  
    out = None
    fps = 15
    frame_count = 0

    print(f"Starting recording for {app_name} to {video_path}")

    try:
        for frame in mjpeg_stream_reader(STREAM_URL):
            if stop_event.is_set():
                print(f"Stop event received after {frame_count} frames")
                break
            if out is None:
                h, w = frame.shape[:2]
                out = cv2.VideoWriter(video_path, fourcc, fps, (w, h))
                if not out.isOpened():
                    print(f"ERROR: Failed to open VideoWriter for {video_path}")
                    return
                print(f"VideoWriter initialized: {w}x{h} @ {fps}fps")
            out.write(frame)
            frame_count += 1
            if frame_count % 50 == 0:
                print(f"Recorded {frame_count} frames...")
    except Exception as e:
        print(f"Error during recording: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if out is not None:
            out.release()
            print(f"Recording stopped. {frame_count} frames written to {video_path}")
        else:
            print(f"Recording stopped. No frames were recorded (VideoWriter was never initialized)")

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_thread, recording_active, current_app_name, recording_stop_event
    if recording_active:
        return jsonify({'status': 'error', 'message': 'Recording already in progress', 'app_name': current_app_name}), 400
    data = request.get_json() or {}
    app_name = data.get('app_name')
    if not app_name:
        return jsonify({'status': 'error', 'message': 'Missing app_name'}), 400
    recording_stop_event = threading.Event()
    recording_thread = threading.Thread(target=record_stream, args=(app_name, recording_stop_event), daemon=True)
    recording_active = True
    current_app_name = app_name
    recording_thread.start()
    return jsonify({'status': 'success', 'message': f'Recording started for {app_name}'})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_thread, recording_active, current_app_name, current_video_path, recording_stop_event
    if not recording_active or recording_thread is None:
        return jsonify({'status': 'error', 'message': 'No recording in progress'}), 400
    
    if recording_stop_event:
        recording_stop_event.set()
    recording_thread.join(timeout=5)
    recording_active = False
    app_name = current_app_name
    video_path = current_video_path
    current_app_name = None
    current_video_path = None
    recording_thread = None
    recording_stop_event = None
    return jsonify({'status': 'success', 'message': f'Recording stopped for {app_name}', 'video_path': video_path})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'recording': recording_active,
        'app_name': current_app_name,
        'video_path': current_video_path
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8899, debug=False) 