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
          - String (URL) for IP camera / ESP32 stream (e.g. 'http://192.168.1.100/stream').
        """
        self.source = source
        self.video = cv2.VideoCapture(self.source)
        
        # If simulation mode (no camera), we could generate blank frames or valid noise
        # But we assume at least a webcam is available for the demo if ESP32 isn't.
        
        if not self.video.isOpened():
            print(f"Warning: Could not open video source {self.source}. Trying default webcam 0.")
            self.video = cv2.VideoCapture(0)

    def __del__(self):
        if self.video.isOpened():
            self.video.release()

    def get_frame(self):
        success, frame = self.video.read()
        if not success:
            # Return a blank black frame if camera fails
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Resize for performance and standard UI size if needed
        # frame = cv2.resize(frame, (640, 480))
        return frame

    def get_jpg_bytes(self, frame):
        """Convert a frame to jpg bytes for streaming"""
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
