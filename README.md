# Smart Factory IoT Monitor 🏭

A comprehensive Real-time Industrial Surveillance and Safety Monitoring System using **YOLOv11** (Backend) and **Angular** (Frontend).

## Features 🚀
- **Real-time PPE Detection**: Detects Hardhats, Vests, Gloves, Masks, etc.
- **Safety Violation Alerts**: Instant visual feedback for compliance issues.
- **Live Video Streaming**: Low-latency video feed.
- **Dynamic Camera Control**: Switch between **Webcam** and **ESP32 IP Camera** on the fly.
- **Unified Dashboard**: Monitor sensor data (Person Count, Violations) and video in one place.

## Prerequisites
- **Python 3.8+**
- **Node.js & npm** (for Frontend)
- **ESP32-CAM** (Optional, for remote streaming)

## Quick Start ⚡

### 1. Setup
1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd SmartFactory
    ```

2.  **Install Dependencies**:
    *   **Backend**:
        ```bash
        pip install -r requirements.txt
        ```
    *   **Frontend**:
        ```bash
        cd IoT-smart-factory/IoTFrontend
        npm install
        ```

### 2. Run the Application
You can start the entire system (Backend + Frontend) with a single script:

*   **Windows**: Double-click **`start_app.bat`**.

This script will:
1.  Start the Flask Backend (port 5000).
2.  Start the Angular Frontend (port 4200).
3.  Automatically open your browser to the dashboard.

*(Logs are saved to `backend_log.txt` and `frontend_log.txt`)*

---

## Manual Execution (Dev Mode)
If you prefer running components separately:

**Backend**:
```bash
cd backend
python app.py
```

**Frontend**:
```bash
cd IoT-smart-factory/IoTFrontend
npm start
```

## Usage
- **Dashboard**: View real-time sensor metrics (Personnel, Violations, Temperature, etc.).
- **Live Stream**: Click the top tab to view the video feed.
    -   **Toggle**: Start/Stop the stream.
    -   **Source**: Select "ESP32" and enter your camera's IP (e.g., `http://192.168.1.50/stream`) or use a local Webcam.ss printed in the Serial Monitor (e.g., `192.168.1.105`).
3. Open `backend/app.py` and modify the camera initialization:
   ```python
   # In app.py
   # Change '0' to your ESP32 stream URL
   ```
4. Restart the Flask app.

## Features
- **Real-time Video**: Low latency MJPEG streaming.
- **PPE Detection**: Uses YOLOv8 to detect people (and PPE classes if custom/fine-tuned).
- **Compliance Status**: Visual indicators for safety compliance.
- **Stats Dashboard**: Live counters for detected personnel and violations.
