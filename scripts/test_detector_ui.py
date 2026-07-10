import os
import sys
import cv2
import base64
import numpy as np
import time
import threading
from flask import Flask, render_template_string, request, jsonify, Response

# Add root folder to path to import detector safely
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

# Try loading detector
try:
    from backend.detector import PPE_Detector
    from backend.camera import VideoCamera
    # Check both root and backend folders for best.pt
    best_path = os.path.join(root_dir, "best.pt")
    if not os.path.exists(best_path):
        best_path = os.path.join(root_dir, "backend", "best.pt")
    detector = PPE_Detector(model_path=best_path)
except Exception as e:
    print(f"Error loading detector or camera: {e}")
    detector = None

app = Flask(__name__)

# Standalone Webcam handler
camera = VideoCamera()

# IP Camera state
ip_camera_thread = None
ip_cam_running = False
ip_cam_url = ""

class ThreadedIPCamera:
    def __init__(self, url):
        self.url = url
        
        # Extremely aggressive FFMPEG flags for zero-latency RTSP
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|flags2;fast"
        
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.ret = False
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.new_frame_ready = threading.Event()
        
        # Start background thread immediately if opened
        if self.cap.isOpened():
            grabbed = self.cap.grab()
            if grabbed:
                self.ret, self.frame = self.cap.retrieve()
            self.thread = threading.Thread(target=self.update, args=())
            self.thread.daemon = True
            self.thread.start()

    def update(self):
        while self.running:
            if self.cap.isOpened():
                grabbed = self.cap.grab()
                if grabbed:
                    ret, frame = self.cap.retrieve()
                    if ret:
                        with self.lock:
                            self.ret = ret
                            self.frame = frame
                        self.new_frame_ready.set()
            else:
                time.sleep(0.01)

    def read(self):
        self.new_frame_ready.wait(timeout=0.1)
        self.new_frame_ready.clear()
        with self.lock:
            return self.ret, self.frame
        
    def isOpened(self):
        return self.cap.isOpened() if self.cap else False

    def release(self):
        self.running = False
        self.new_frame_ready.set()
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()

# Beautiful single-page dashboard HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartFactory AI Playground</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.4);
            --success: #10b981;
            --error: #ef4444;
            --text: #f8fafc;
            --text-muted: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem;
            overflow-x: hidden;
        }

        header {
            text-align: center;
            margin-bottom: 2rem;
            animation: fadeInDown 0.6s ease-out;
        }

        header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.05em;
            background: linear-gradient(to right, #a5b4fc, #818cf8, #6366f1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        header p {
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        .playground-container {
            width: 100%;
            max-width: 1200px;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 2rem;
            animation: fadeInUp 0.8s ease-out;
        }

        .panel {
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(12px);
            border-radius: 24px;
            padding: 2rem;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        }

        .controls-panel {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .control-group h3 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text);
            border-bottom: 1px solid var(--glass-border);
            padding-bottom: 0.5rem;
        }

        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 1rem;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 14px 0 var(--primary-glow);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px 0 var(--primary-glow);
            filter: brightness(1.1);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            box-shadow: none;
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            box-shadow: none;
        }

        .btn-danger {
            background: var(--error);
            box-shadow: 0 4px 14px 0 rgba(239, 68, 68, 0.4);
        }

        .btn-danger:hover {
            box-shadow: 0 6px 20px 0 rgba(239, 68, 68, 0.4);
        }

        .file-upload-wrapper {
            position: relative;
            width: 100%;
            height: 120px;
            border: 2px dashed var(--glass-border);
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .file-upload-wrapper:hover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.05);
        }

        .file-upload-wrapper input[type="file"] {
            position: absolute;
            width: 100%;
            height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .file-upload-wrapper span {
            color: var(--text-muted);
            font-size: 0.9rem;
            text-align: center;
            padding: 0 1rem;
        }

        .display-panel {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            align-items: center;
            justify-content: center;
            min-height: 500px;
            position: relative;
        }

        .image-container {
            width: 100%;
            max-height: 600px;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--glass-border);
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.2);
            position: relative;
        }

        .image-container img {
            max-width: 100%;
            max-height: 600px;
            object-fit: contain;
        }

        .placeholder-text {
            color: var(--text-muted);
            font-size: 1.2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
            width: 100%;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 1rem;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
        }

        .stat-card .label {
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stat-card.violations .value {
            color: var(--error);
        }

        .stat-card.people .value {
            color: var(--success);
        }

        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

    <header>
        <h1>SmartFactory AI Playground</h1>
        <p>Standalone model testing sandbox &bull; YOLOv11m</p>
    </header>

    <div class="playground-container">
        <!-- Controls Panel -->
        <div class="panel controls-panel">
            <div class="control-group">
                <h3>Image Upload</h3>
                <div class="file-upload-wrapper">
                    <span>Drag & drop or click to upload image</span>
                    <input type="file" id="imageInput" accept="image/*">
                </div>
            </div>

            <div class="control-group">
                <h3>Webcam Stream</h3>
                <button class="btn" id="startCamBtn">Start Live Webcam</button>
                <button class="btn btn-danger" id="stopCamBtn" style="display: none;">Stop Webcam</button>
            </div>

            <div class="control-group">
                <h3>IP Camera Stream</h3>
                <input type="text" id="ipCamInput" placeholder="rtsp://user:pass@IP:port/stream"
                    style="width: 100%; padding: 0.75rem; border-radius: 12px; border: 1px solid var(--glass-border);
                    background: rgba(255,255,255,0.05); color: var(--text); font-family: 'Outfit', sans-serif;
                    font-size: 0.9rem; outline: none;">
                <button class="btn btn-secondary" id="startIpCamBtn">Connect IP Camera</button>
                <button class="btn btn-danger" id="stopIpCamBtn" style="display: none;">Disconnect IP Camera</button>
            </div>
            
            <div class="control-group" id="statsPanel" style="display: none;">
                <h3>Detection Stats</h3>
                <div class="stats-grid">
                    <div class="stat-card people">
                        <span class="value" id="valPeople">0</span>
                        <span class="label">People Found</span>
                    </div>
                    <div class="stat-card violations">
                        <span class="value" id="valViolations">0</span>
                        <span class="label">Violations</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Display Panel -->
        <div class="panel display-panel">
            <div class="image-container" id="displayContainer">
                <div class="placeholder-text" id="placeholder">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="opacity: 0.3;">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                    </svg>
                    <span>Upload an image or start the webcam to begin testing</span>
                </div>
                <img id="displayImg" style="display: none;">
            </div>
        </div>
    </div>

    <script>
        const imageInput = document.getElementById('imageInput');
        const startCamBtn = document.getElementById('startCamBtn');
        const stopCamBtn = document.getElementById('stopCamBtn');
        const displayContainer = document.getElementById('displayContainer');
        const displayImg = document.getElementById('displayImg');
        const placeholder = document.getElementById('placeholder');
        const statsPanel = document.getElementById('statsPanel');
        const valPeople = document.getElementById('valPeople');
        const valViolations = document.getElementById('valViolations');

        let isWebcamActive = false;
        let isIpCamActive = false;

        const ipCamInput = document.getElementById('ipCamInput');
        const startIpCamBtn = document.getElementById('startIpCamBtn');
        const stopIpCamBtn = document.getElementById('stopIpCamBtn');

        // Image upload handler
        imageInput.addEventListener('change', async (e) => {
            if (isWebcamActive) stopWebcam();
            
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('image', file);

            try {
                const response = await fetch('/api/detect', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (data.success) {
                    // Update UI
                    displayImg.src = 'data:image/jpeg;base64,' + data.image;
                    displayImg.style.display = 'block';
                    placeholder.style.display = 'none';

                    // Update stats
                    statsPanel.style.display = 'block';
                    valPeople.innerText = data.stats.total_people;
                    valViolations.innerText = data.stats.violations;
                }
            } catch (err) {
                console.error("Upload error:", err);
            }
        });

        // Webcam functions
        startCamBtn.addEventListener('click', () => {
            isWebcamActive = true;
            startCamBtn.style.display = 'none';
            stopCamBtn.style.display = 'block';
            placeholder.style.display = 'none';

            // Show webcam stream direct route
            displayImg.src = '/api/video_feed';
            displayImg.style.display = 'block';

            // Poll stats from backend
            statsPanel.style.display = 'block';
            startStatsPolling();
        });

        stopCamBtn.addEventListener('click', stopWebcam);

        function stopWebcam() {
            isWebcamActive = false;
            startCamBtn.style.display = 'block';
            stopCamBtn.style.display = 'none';
            displayImg.style.display = 'none';
            placeholder.style.display = 'flex';
            statsPanel.style.display = 'none';
            fetch('/api/stop_webcam', { method: 'POST' });
        }

        // IP Camera handlers
        startIpCamBtn.addEventListener('click', async () => {
            const url = ipCamInput.value.trim();
            if (!url) { alert('Please enter an IP camera URL'); return; }

            if (isWebcamActive) stopWebcam();
            if (isIpCamActive) await stopIpCam();

            try {
                const res = await fetch('/api/start_ipcam', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await res.json();
                if (!data.success) { alert('Failed to connect: ' + (data.error || 'Unknown error')); return; }

                isIpCamActive = true;
                startIpCamBtn.style.display = 'none';
                stopIpCamBtn.style.display = 'block';
                placeholder.style.display = 'none';
                displayImg.src = '/api/ipcam_feed';
                displayImg.style.display = 'block';
                statsPanel.style.display = 'block';
                startStatsPolling();
            } catch (err) {
                console.error('IP cam error:', err);
                alert('Connection failed. Check the URL and try again.');
            }
        });

        stopIpCamBtn.addEventListener('click', stopIpCam);

        async function stopIpCam() {
            isIpCamActive = false;
            startIpCamBtn.style.display = 'block';
            stopIpCamBtn.style.display = 'none';
            displayImg.style.display = 'none';
            placeholder.style.display = 'flex';
            statsPanel.style.display = 'none';
            await fetch('/api/stop_ipcam', { method: 'POST' });
        }

        let pollInterval;
        function startStatsPolling() {
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(async () => {
                if (!isWebcamActive) {
                    clearInterval(pollInterval);
                    return;
                }
                try {
                    const response = await fetch('/api/stats');
                    const data = await response.json();
                    valPeople.innerText = data.total_people;
                    valViolations.innerText = data.violations;
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 300);
        }
    </script>
</body>
</html>
"""

# API 1: Detect from uploaded image file
@app.route('/api/detect', methods=['POST'])
def detect_image():
    if detector is None:
        return jsonify({"success": False, "error": "Detector not loaded"})

    file = request.files.get('image')
    if not file:
        return jsonify({"success": False, "error": "No image uploaded"})

    try:
        # Convert file to OpenCV image
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Run detection
        annotated_img, stats = detector.detect(img)

        # Encode back to base64
        _, buffer = cv2.imencode('.jpg', annotated_img)
        b64_img = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "success": True,
            "image": b64_img,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API 2: Video Stream loop
latest_webcam_stats = {"total_people": 0, "violations": 0}

def gen_frames():
    global latest_webcam_stats
    camera.start()
    while camera.is_running:
        frame = camera.get_frame()
        if frame is None:
            time.sleep(0.03)
            continue

        if detector:
            # Run detection
            annotated_frame, stats = detector.detect(frame)
            latest_webcam_stats = stats
        else:
            annotated_frame = frame
            
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/api/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stop_webcam', methods=['POST'])
def stop_webcam():
    camera.stop()
    return jsonify({"success": True})

# API 3: IP Camera Stream
@app.route('/api/start_ipcam', methods=['POST'])
def start_ipcam():
    global ip_camera_thread, ip_cam_running, ip_cam_url
    data = request.get_json()
    url = data.get('url', '')
    if not url:
        return jsonify({"success": False, "error": "No URL provided"})

    # Release any existing IP cam
    if ip_camera_thread is not None:
        ip_camera_thread.release()

    ip_camera_thread = ThreadedIPCamera(url)
    if not ip_camera_thread.isOpened():
        ip_camera_thread = None
        return jsonify({"success": False, "error": "Could not connect to IP camera. Check URL/credentials."})

    ip_cam_running = True
    ip_cam_url = url
    print(f"[IP CAM] Connected to: {url}")
    return jsonify({"success": True})

@app.route('/api/stop_ipcam', methods=['POST'])
def stop_ipcam():
    global ip_camera_thread, ip_cam_running
    ip_cam_running = False
    if ip_camera_thread is not None:
        ip_camera_thread.release()
        ip_camera_thread = None
    print("[IP CAM] Disconnected.")
    return jsonify({"success": True})

def gen_ipcam_frames():
    global latest_webcam_stats, ip_camera_thread, ip_cam_running
    while ip_cam_running and ip_camera_thread is not None:
        ret, frame = ip_camera_thread.read()
        if not ret or frame is None:
            time.sleep(0.03)
            continue

        # We copy the frame to avoid the background thread overwriting it during inference
        current_frame = frame.copy()

        if detector:
            annotated_frame, stats = detector.detect(current_frame)
            latest_webcam_stats = stats
        else:
            annotated_frame = current_frame

        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/api/ipcam_feed')
def ipcam_feed():
    return Response(gen_ipcam_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats')
def get_stats():
    return jsonify(latest_webcam_stats)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    print("====================================================")
    print("🚀 Standalone SmartFactory AI Playground launching...")
    print("👉 Open http://localhost:8000 in your browser to try!")
    print("====================================================")
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)
