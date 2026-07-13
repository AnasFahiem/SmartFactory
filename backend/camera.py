import cv2
import time
import requests
import numpy as np
import threading
import os

class VideoCamera:
    def __init__(self, source=0):
        """
        Initialize video camera.
        source: 
          - Integer (0, 1) for local webcam.
          - String (URL) for IP camera / ESP32 stream.
        """
        self.source = source
        self.video = None
        self.is_running = True
        
        self.frame = None
        self.ret = False
        self.frame_requested = True
        self.thread = None
        
        self.connect()

    def connect(self):
        """Attempts to connect to the current source."""
        if self.video is not None:
            self.video.release()
            
        print(f"[Camera] Connecting to source: {self.source}")
        
        # If source is a digit string, convert to int (webcam index)
        if isinstance(self.source, str) and self.source.isdigit():
             self.source = int(self.source)

        if isinstance(self.source, str) and (self.source.startswith("rtsp://") or self.source.startswith("http://")):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|flags2;fast"
            self.video = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            self.video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.video.set(cv2.CAP_PROP_FPS, 15)
        else:
            self.video = cv2.VideoCapture(self.source)
        
        if self.video.isOpened():
            print(f"[Camera] Connected to {self.source}")
            # Start background thread for zero-latency reading
            self.video.grab()
            self.ret, self.frame = self.video.retrieve()
            
            self.is_running = True
            self.thread = threading.Thread(target=self.update, args=())
            self.thread.daemon = True
            self.thread.start()
        else:
            print(f"[Camera] Failed to connect to {self.source}")
            # Don't fallback automatically to webcam to ensure user knows their IP failed
            # self.video = None (keeps the failed object which isOpened() == False)

    def update(self):
        while self.is_running:
            if self.video and self.video.isOpened():
                grabbed = self.video.grab()
                if grabbed and self.frame_requested:
                    self.ret, self.frame = self.video.retrieve()
                    self.frame_requested = False
            else:
                time.sleep(0.01)

    def set_source(self, new_source):
        self.source = new_source
        self.connect()

    def start(self):
        if not self.video or not self.video.isOpened():
             self.connect()

    def stop(self):
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.video and self.video.isOpened():
            self.video.release()
        self.video = None

    def __del__(self):
        self.stop()

    def get_frame(self):
        if not self.is_running or self.video is None or not self.video.isOpened():
             # Return black frame if stopped
             return np.zeros((480, 640, 3), dtype=np.uint8)

        self.frame_requested = True
        
        # Wait very briefly if the frame isn't ready, but usually we just return the latest
        if not self.ret or self.frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
            
        return self.frame.copy()

    def get_jpg_bytes(self, frame):
        """Convert a frame to jpg bytes for streaming"""
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
