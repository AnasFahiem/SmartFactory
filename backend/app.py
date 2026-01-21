from flask import Flask, render_template, Response, jsonify
from camera import VideoCamera
from detector import PPE_Detector
import cv2
import threading
import time

app = Flask(__name__, template_folder='../templates', static_folder='../static')
from flask_cors import CORS
CORS(app)

# Global variables to hold latest stats
current_stats = {
    "total_people": 0,
    "violations": 0
}

# Initialize Camera and Detector
# NOTE: Replace '0' with your ESP32 stream URL, e.g., 'http://192.168.1.X:81/stream'
camera_source = 0 
camera = VideoCamera(source=camera_source)
detector = PPE_Detector()

def gen_frames():
    """Generator function for video streaming."""
    global current_stats
    print("Starting video stream loop...")
    frame_count = 0
    while True:
        try:
            # If camera is stopped, pause the loop to avoid burning CPU and sending frames
            if not camera.is_running:
                time.sleep(0.3)
                continue

            frame = camera.get_frame()
            if frame is None:
                print("Error: Camera returned None frame.")
                continue

            # Run Detection
            annotated_frame, stats = detector.detect(frame)
            
            # Update global stats
            current_stats = stats
            
            # Encode to JPEG
            frame_bytes = camera.get_jpg_bytes(annotated_frame)
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Stream is alive! Processed {frame_count} frames.")
                
        except Exception as e:
            print(f"CRITICAL ERROR in gen_frames: {e}")
            time.sleep(1) # Prevent spamming loop on error

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera/status', methods=['GET'])
def get_camera_status():
    status = {
        "source": camera.source,
        "is_running": camera.is_running,
        "stats": current_stats
    }
    return jsonify(status)

@app.route('/api/camera/config', methods=['POST'])
def set_camera_config():
    """Set camera source (0, 1, or URL)"""
    from flask import request
    data = request.json
    new_source = data.get("source", 0)
    
    # Simple validation: if it looks like an int, cast it
    if str(new_source).isdigit():
        new_source = int(new_source)
        
    camera.set_source(new_source)
    return jsonify({"message": f"Camera source set to {new_source}", "success": True})

@app.route('/api/camera/toggle', methods=['POST'])
def toggle_camera():
    """Start or Stop the camera stream"""
    from flask import request
    data = request.json
    action = data.get("action", "start") # "start" or "stop"
    
    if action == "stop":
        camera.stop()
        return jsonify({"message": "Camera stopped", "is_running": False})
    else:
        camera.start()
        return jsonify({"message": "Camera started", "is_running": True})

@app.route('/api/status')
def api_status():
    return jsonify(current_stats)

if __name__ == '__main__':
    # Threaded=True is important for streaming multiple clients (if needed)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
