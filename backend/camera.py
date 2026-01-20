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
        self.video = None
        
        # Try to open the source provided
        print(f"[Camera] Attempting to open source: {source}")
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            success, _ = cap.read()
            if success:
                self.video = cap
                print(f"[Camera] Success connecting to {source}")
            else:
                cap.release()
                print(f"[Camera] Source {source} opened but failed to read frame.")
        
        # Fallback: Try other indices if source failed or if source was just '0'
        if self.video is None:
            print("[Camera] Main source failed. Searching for other cameras...")
            for i in [0, 1, 2, 3]:
                if i == source: continue
                print(f"[Camera] Trying Webcam Index {i}...")
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    success, _ = cap.read()
                    if success:
                        self.video = cap
                        print(f"[Camera] Found working webcam at Index {i}!")
                        break
                    else:
                        cap.release()
        
        if self.video is None:
             print("[Camera] CRITICAL FAILURE: No camera could be opened.")
             # We will handle None in get_frame but this explains the black screen

    def __del__(self):
        if self.video and self.video.isOpened():
            self.video.release()

    def get_frame(self):
        if self.video is None:
            # Camera failed to init, try to reconnect or return blank
            # print("Warning: Camera source is None.") 
            return np.zeros((480, 640, 3), dtype=np.uint8)

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
