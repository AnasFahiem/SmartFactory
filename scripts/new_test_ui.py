import os
import sys
import cv2
import numpy as np
import base64
from flask import Flask, render_template_string, request, jsonify

# Add project root to path so we can import the backend module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.detector import PPE_Detector

app = Flask(__name__)

# Load the AI model once on startup
print("Loading YOLO model from best.pt...")
try:
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "best.pt")
    detector = PPE_Detector(model_path)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model: {e}")
    detector = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SmartFactory AI - Live Camera</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { margin-bottom: 1.5rem; }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 1.5rem;
            width: 100%;
            max-width: 1100px;
            box-shadow: 0 10px 25px -3px rgba(0,0,0,0.6);
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        #live-view {
            width: 100%;
            border-radius: 10px;
            background: #000;
            min-height: 400px;
            object-fit: contain;
        }
        .controls {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-top: 1rem;
        }
        button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.8rem 2rem;
            font-size: 1.1rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
        }
        button:hover { background: #2563eb; }
        button.stop { background: #ef4444; }
        button.stop:hover { background: #dc2626; }
        .badge {
            background: #334155;
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.9rem;
            color: #94a3b8;
        }
        .badge.live {
            background: #dc2626;
            color: white;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .hidden { display: none !important; }
    </style>
</head>
<body>
    <h1>🤖 SmartFactory AI - Live Detection</h1>
    <div class="card">
        <!-- Single view: shows annotated AI frame -->
        <img id="live-view" src="" alt="Click Start to begin live detection">

        <div class="controls">
            <button id="start-btn">🔴 Start Camera</button>
            <button id="stop-btn" class="stop hidden">⏹ Stop Camera</button>
            <span id="live-badge" class="badge hidden live">● LIVE</span>
            <span id="fps-counter" class="badge"></span>
        </div>
    </div>

    <!-- Hidden elements for capturing -->
    <video id="webcam" autoplay playsinline style="display:none;"></video>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        const video = document.getElementById('webcam');
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const liveView = document.getElementById('live-view');
        const startBtn = document.getElementById('start-btn');
        const stopBtn = document.getElementById('stop-btn');
        const liveBadge = document.getElementById('live-badge');
        const fpsCounter = document.getElementById('fps-counter');

        let stream = null;
        let isDetecting = false;
        let frameCount = 0;
        let lastTime = Date.now();

        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } } });
                video.srcObject = stream;

                startBtn.classList.add('hidden');
                stopBtn.classList.remove('hidden');
                liveBadge.classList.remove('hidden');
                isDetecting = true;

                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    captureAndSend();
                };
            } catch (err) {
                alert("Error accessing webcam: " + err.message);
            }
        }

        function stopCamera() {
            isDetecting = false;
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            video.srcObject = null;
            startBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            liveBadge.classList.add('hidden');
            liveView.src = "";
            fpsCounter.innerText = "";
        }

        async function captureAndSend() {
            if (!isDetecting) return;

            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const base64Image = canvas.toDataURL('image/jpeg', 0.92);

            try {
                const response = await fetch('/detect_live', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64Image })
                });

                if (response.ok) {
                    const result = await response.json();
                    liveView.src = result.annotated_image;

                    frameCount++;
                    const now = Date.now();
                    if (now - lastTime >= 1000) {
                        fpsCounter.innerText = 'FPS: ' + frameCount;
                        frameCount = 0;
                        lastTime = now;
                    }
                }
            } catch (err) {
                console.error("Detection error:", err);
            }

            requestAnimationFrame(captureAndSend);
        }

        startBtn.addEventListener('click', startCamera);
        stopBtn.addEventListener('click', stopCamera);
    </script>
</body>
</html>
"""

from flask import Response

@app.route('/')
def index():
    response = Response(render_template_string(HTML_TEMPLATE))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/detect_live', methods=['POST'])
def detect_live():
    if not detector:
        return jsonify({"error": "Model not loaded"}), 500

    try:
        data = request.json
        img_b64 = data.get('image', '')

        # Decode base64 to OpenCV image
        if img_b64.startswith('data:image'):
            img_b64 = img_b64.split(',')[1]
            
        img_bytes = base64.b64decode(img_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image format"}), 400

        # Run AI detection
        annotated_frame, stats = detector.detect(frame)

        # Encode back to base64 (quality 92 for crisp output)
        ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if not ret:
            return jsonify({"error": "Failed to encode result"}), 500

        out_b64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "annotated_image": f"data:image/jpeg;base64,{out_b64}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("====================================================")
    print("🚀 NEW SmartFactory AI UI launching...")
    print("👉 Open http://localhost:8000 in your browser to try!")
    print("====================================================")
    # Use host=0.0.0.0 to allow access from local network if needed
    app.run(host='0.0.0.0', port=8000, debug=False)
