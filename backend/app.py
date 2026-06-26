from flask import Flask, jsonify
from camera import VideoCamera
from detector import PPE_Detector
import cv2
import threading
import time
import requests
import base64
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# The URL of the .NET Backend where the camera frames are pushed.
# Use localhost for local testing via start_app.bat, or the Azure URL for cloud deployment.
# Local: http://localhost:5005/api/camera/upload
# Cloud: https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net/api/camera/upload
API_URL = os.getenv("API_URL", "http://localhost:5005/api/camera/upload")
# TODO: SECURITY RISK - Move this to an environment variable (.env) before production
MY_SECRET = "YourSuperSecretKey123"
CAMERA_SOURCE = "" # Leave empty (0) for default webcam, or put an IP camera URL here

# Global stats
current_stats = {"total_people": 0, "violations": 0}

# Initialize Hardware
camera = VideoCamera(source=CAMERA_SOURCE)
detector = PPE_Detector()
session = requests.Session() # Use session for better performance (Keep-Alive)

def azure_push_loop():
    """Background thread to process frames and push to Azure."""
    global current_stats
    print("Azure Push Loop Started...")
    
    while True:
        try:
            if not camera.is_running:
                time.sleep(1)
                continue

            frame = camera.get_frame()
            if frame is None:
                continue

            # 1. Run AI Detection
            annotated_frame, stats = detector.detect(frame)
            current_stats = stats

            # 2. Resize and Compress (Reduces latency to France)
            small_frame = cv2.resize(annotated_frame, (640, 480))
            _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 35])
            
            # 3. Convert to Base64
            b64_img = base64.b64encode(buffer).decode('utf-8')
            full_b64 = f"data:image/jpeg;base64,{b64_img}"

            # 4. Push to .NET Backend
            payload = {
                "image": full_b64,
                "secretKey": MY_SECRET,
                "violationCount": stats['violations']
            }
            
            # Non-blocking post (short timeout)
            session.post(API_URL, json=payload, timeout=0.5)

        except Exception as e:
            print(f"Push Error: {e}")
            time.sleep(1)

        # Control Frame Rate (e.g., 5-10 FPS is good for factory monitoring)
        time.sleep(0.1)

# Start the background thread
threading.Thread(target=azure_push_loop, daemon=True).start()

@app.route('/api/camera/status')
def get_status():
    return jsonify({
        "is_running": camera.is_running,
        "stats": current_stats
    })

@app.route('/api/camera/toggle', methods=['POST'])
def toggle_camera():
    from flask import request
    req_data = request.get_json(silent=True) or {}
    action = req_data.get("action", "start")
    if action == "stop":
        camera.stop()
    else:
        camera.start()
    return jsonify({"is_running": camera.is_running})

if __name__ == '__main__':
    # No need for video_feed route anymore; SignalR handles the display
    app.run(host='0.0.0.0', port=5000, use_reloader=False)