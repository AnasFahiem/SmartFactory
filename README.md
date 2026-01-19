# Smart Factory Safety Monitoring System 🏭

A real-time computer vision dashboard for monitoring PPE compliance in industrial environments.

## Project Structure
```
SmartFactory/
├── backend/
│   ├── app.py          # Flask application server
│   ├── camera.py       # Camera stream handling (ESP32/Webcam)
│   └── detector.py     # YOLOv8 Object Detection Logic
├── static/
│   ├── css/
│   │   └── style.css   # Modern industrial theme styling
│   └── js/
│       └── script.js   # Real-time stats polling
├── templates/
│   └── index.html      # Main dashboard interface
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Setup & Installation

1. **Install Python 3.8+**
   Ensure Python is installed on your system.

2. **Install Dependencies**
   Run the following command in the terminal:
   ```sh
   pip install -r requirements.txt
   ```
   *Note: This installs Flask, OpenCV, and Ultralytics (YOLO).*

3. **Run the Application**
   Navigate to the `backend` folder and run `app.py`:
   ```sh
   cd backend
   python app.py
   ```

4. **Access the Dashboard**
   Open your browser and verify the address: `http://localhost:5000`

## ESP32 Camera Integration

To use an ESP32-CAM instead of your local webcam:

1. Flash your ESP32-CAM with the standard "CameraWebServer" example from the Arduino IDE.
2. Note the IP address printed in the Serial Monitor (e.g., `192.168.1.105`).
3. Open `backend/app.py` and modify the camera initialization:
   ```python
   # In app.py
   # Change '0' to your ESP32 stream URL
   camera_source = "http://192.168.1.105:81/stream" 
   camera = VideoCamera(source=camera_source)
   ```
4. Restart the Flask app.

## Features
- **Real-time Video**: Low latency MJPEG streaming.
- **PPE Detection**: Uses YOLOv8 to detect people (and PPE classes if custom/fine-tuned).
- **Compliance Status**: Visual indicators for safety compliance.
- **Stats Dashboard**: Live counters for detected personnel and violations.
