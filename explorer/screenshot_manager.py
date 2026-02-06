

import time
import socket
import logging
import requests
import cv2
import numpy as np
import mss
from typing import Optional, Tuple

from config import Config
from core_types import ScreenshotResult


class ScreenshotManager:
    

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def take_screenshot(self, source: Optional[str] = None) -> ScreenshotResult:
        
        if source is None:
            source = self.config.app.screenshot_source

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_path = f"{self.config.paths.screenshot_dir}/screenshot_{timestamp}.png"

        try:
            if source == 'airplay':
                return self._capture_airplay(file_path, timestamp)
            elif source == 'remote':
                return self._capture_remote_stream(file_path, timestamp)
            elif source == 'gstreamer':
                return self._capture_gstreamer(file_path, timestamp)
            else:
                error_msg = f"Unknown screenshot source: {source}"
                self.logger.error(error_msg)
                return ScreenshotResult(
                    success=False,
                    file_path=None,
                    timestamp=timestamp,
                    error_message=error_msg
                )
        except Exception as e:
            error_msg = f"Screenshot capture failed: {str(e)}"
            self.logger.error(error_msg)
            return ScreenshotResult(
                success=False,
                file_path=None,
                timestamp=timestamp,
                error_message=error_msg
            )

    def _capture_airplay(self, file_path: str, timestamp: str) -> ScreenshotResult:
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[self.config.screen.monitor_number]
                screenshot = sct.grab(monitor)
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                
                self.config.screen.height, self.config.screen.width = frame.shape[:2]

                cv2.imwrite(file_path, frame)
                self.logger.debug(f"Airplay screenshot saved: {file_path}")

                return ScreenshotResult(
                    success=True,
                    file_path=file_path,
                    timestamp=timestamp
                )
        except Exception as e:
            raise Exception(f"Airplay capture failed: {str(e)}")

    def _capture_remote_stream(self, file_path: str, timestamp: str) -> ScreenshotResult:
        
        try:
            url = self.config.network.remote_stream_url
            stream = requests.get(url, stream=True, timeout=10)
            bytes_buffer = b''

            for chunk in stream.iter_content(chunk_size=1024):
                bytes_buffer += chunk
                jpeg_start = bytes_buffer.find(b'\xff\xd8')  
                jpeg_end = bytes_buffer.find(b'\xff\xd9')    

                if jpeg_start != -1 and jpeg_end != -1:
                    jpg = bytes_buffer[jpeg_start:jpeg_end + 2]
                    bytes_buffer = bytes_buffer[jpeg_end + 2:]

                    img = cv2.imdecode(
                        np.frombuffer(jpg, dtype=np.uint8),
                        cv2.IMREAD_COLOR
                    )

                    if img is not None:
                        
                        self.config.screen.height, self.config.screen.width = img.shape[:2]

                        cv2.imwrite(file_path, img)
                        self.logger.debug(f"Remote stream screenshot saved: {file_path}")

                        return ScreenshotResult(
                            success=True,
                            file_path=file_path,
                            timestamp=timestamp
                        )

            raise Exception("No valid JPEG frame received from remote stream")

        except Exception as e:
            raise Exception(f"Remote stream capture failed: {str(e)}")

    def _capture_gstreamer(self, file_path: str, timestamp: str) -> ScreenshotResult:
        
        sock = None
        try:
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)

            self.logger.debug(f"Connecting to {self.config.network.gstreamer_host}:{self.config.network.gstreamer_port}")
            sock.connect((self.config.network.gstreamer_host, self.config.network.gstreamer_port))

            
            buffer = b''
            jpeg_start = b'\xff\xd8'
            jpeg_end = b'\xff\xd9'

            while True:
                data = sock.recv(4096)
                if not data:
                    break

                buffer += data

                
                start_idx = buffer.find(jpeg_start)
                if start_idx != -1:
                    end_idx = buffer.find(jpeg_end, start_idx)
                    if end_idx != -1:
                        
                        jpeg_data = buffer[start_idx:end_idx + 2]

                        
                        nparr = np.frombuffer(jpeg_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        if frame is not None:
                            
                            self.config.screen.height, self.config.screen.width = frame.shape[:2]

                            cv2.imwrite(file_path, frame)
                            self.logger.debug(f"GStreamer screenshot saved: {file_path}")

                            return ScreenshotResult(
                                success=True,
                                file_path=file_path,
                                timestamp=timestamp
                            )

                        
                        buffer = buffer[end_idx + 2:]
                        break

            raise Exception("No valid JPEG frame received from GStreamer")

        except socket.timeout:
            raise Exception("GStreamer connection timeout")
        except socket.error as e:
            raise Exception(f"GStreamer socket error: {e}")
        finally:
            if sock:
                sock.close()

    def get_screen_dimensions(self) -> Tuple[int, int]:
        
        return self.config.screen.width, self.config.screen.height