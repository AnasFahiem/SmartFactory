import cv2
import time
import requests
import numpy as np

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
        self.connect()

    def connect(self):
        """Attempts to connect to the current source."""
        if self.video is not None:
            self.video.release()
            
        print(f"[Camera] Connecting to source: {self.source}")
        # If source is a digit string, convert to int (webcam index)
        if isinstance(self.source, str) and self.source.isdigit():
             self.source = int(self.source)

        self.video = cv2.VideoCapture(self.source)
        
        if self.video.isOpened():
            print(f"[Camera] Connected to {self.source}")
        else:
            print(f"[Camera] Failed to connect to {self.source}")
            # Don't fallback automatically to webcam to ensure user knows their IP failed
            # self.video = None (keeps the failed object which isOpened() == False)

    def set_source(self, new_source):
        self.source = new_source
        self.connect()

    def start(self):
        self.is_running = True
        if not self.video or not self.video.isOpened():
             self.connect()

    def stop(self):
        self.is_running = False
        if self.video and self.video.isOpened():
            self.video.release()
        self.video = None

    def __del__(self):
        if self.video and self.video.isOpened():
            self.video.release()

    def get_frame(self):
        if not self.is_running:
             # Return black frame if stopped
             return np.zeros((480, 640, 3), dtype=np.uint8)

        if self.video is None or not self.video.isOpened():
            # Try to reconnect implicitly? Or just return black
            # For now, return black to indicate failure
            return np.zeros((480, 640, 3), dtype=np.uint8)

        success, frame = self.video.read()
        if not success:
            # If reading fails (e.g. stream disconnected), return black
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        return frame
        
        # Resize for performance and standard UI size if needed
        # frame = cv2.resize(frame, (640, 480))
        return frame

    def get_jpg_bytes(self, frame):
        """Convert a frame to jpg bytes for streaming"""
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
