# Smart Factory IoT Monitor 🏭

A comprehensive Real-time Industrial Surveillance and Safety Monitoring System integrating **Computer Vision (YOLOv11)**, **IoT Sensors**, and **Anomaly Detection AI**.

## 📑 Table of Contents
- [Overview 🚀](#overview-)
- [Hardware Components & Sensors 🛠️](#hardware-components--sensors-%EF%B8%8F)
- [Cloud & Database Architecture ☁️](#cloud--database-architecture-%E2%98%81%EF%B8%8F)
- [AI Models 🧠](#ai-models-)
  - [1. Computer Vision (PPE Detection)](#1-computer-vision-ppe-detection)
  - [2. Anomaly Detection (Sensor Data)](#2-anomaly-detection-sensor-data)
- [Prerequisites](#prerequisites)
- [Quick Start ⚡](#quick-start-)
- [Manual Execution (Dev Mode)](#manual-execution-dev-mode)
- [Model Training (YOLOv11)](#model-training-yolov11)
- [ML Technical Report 📊](#ml-technical-report-)
- [Dataset: SH17](#dataset-sh17-safety-helmet-17-class)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview 🚀
SmartFactory is a dual-layered AI monitoring system for industrial environments:
1. **Vision-based Safety**: Real-time PPE (Personal Protective Equipment) compliance checking.
2. **Sensor-based Environmental Safety**: Real-time monitoring of gas leaks, temperature, humidity, and weight anomalies.

---

## Hardware Components & Sensors 🛠️
The project integrates multiple microcontrollers and sensors to gather physical data from the factory floor:

### Microcontrollers
- **ESP32-S3**: The main brain for processing sensor data and communicating with the cloud.
- **ESP32-CAM**: Dedicated wireless IP camera used to read QR codes on products.

### Sensors & Actuators
- **MQ-2 Gas Sensor**: Detects smoke, methane, and LPG gas leaks to trigger fire/gas alarms.
- **DHT11**: Monitors ambient temperature and humidity for environmental safety.
- **HX711 & Load Cell**: High-precision weight measurement for monitoring industrial loads or inventory.
- **L298N Motor Driver**: Controls actuators, conveyor belts, or factory machinery based on automated AI decisions.

---

## Cloud & Database Architecture ☁️
- **MQTT Broker**: **HiveMQ Cloud** is used for robust, low-latency telemetry communication between the ESP32 hardware, the AI anomaly detection script, and the backend.
- **Database**: The system uses a centralized database to log sensor telemetry, record PPE violations, and store historical AI predictions for long-term analytics.

---

## AI Models 🧠

### 1. Computer Vision (PPE Detection)
- **Model**: YOLOv11m
- **Purpose**: Detects 17 classes of Personal Protective Equipment (Hardhats, Vests, Gloves, Masks, etc.) and flags violations (e.g., person without a helmet).
- **Inference**: Runs locally on a GPU (via the Flask Backend) or can be tested via the standalone UI playgrounds.

### 2. Anomaly Detection (Sensor Data)
- **Model**: Isolation Forest (Machine Learning)
- **Purpose**: A dedicated script (`ai_dashboard_monitor.py`) listens to the `factory/#` MQTT topics. It takes real-time readings of Temperature, Humidity, and Gas states and predicts anomalies.
- **Action**: If an anomaly is detected, it automatically sends an **emergency email alert** to the factory administrator and publishes a warning back to the dashboard.

---

## Prerequisites
- **Python 3.8+**
- **Node.js & npm** (for Frontend)
- **NVIDIA GPU** with CUDA support (recommended for real-time detection)

---

## Quick Start ⚡

### 1. Setup
1.  **Clone the repository**:
    ```bash
    git clone https://github.com/AnasFahiem/SmartFactory.git
    cd SmartFactory
    ```

2.  **Install Dependencies**:
    *   **Backend**:
        ```bash
        pip install -r requirements.txt
        ```
    *   **Frontend**:
        ```bash
        cd frontend
        npm install
        ```

### 2. Run the Application
You can start the entire system (Backend + Frontend) with a single script:

*   **Windows**: Double-click **`start_app.bat`**.

This script will:
1.  Start the Flask Backend (port 5000).
2.  Start the Angular Frontend (port 4200).
3.  Automatically open your browser to the dashboard.

### 3. Test the AI Model Locally
To test the trained PPE detection model with your webcam:
```bash
python scripts/test_detector_ui.py
```
Then open **http://localhost:8000** in your browser and click **Start Live Webcam**.

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
cd frontend
npm start
```

---

## Model Training (YOLOv11)

To retrain the model on the SH17 dataset:
```bash
python train.py
```

Training configuration:
- **Model**: YOLOv11m (Medium)
- **Dataset**: SH17 PPE Detection (17 classes, 8,099 images)
- **Image Size**: 800×800
- **Batch Size**: 8
- **Epochs**: 150 (with early stopping, patience=30)
- **Optimizer**: SGD with Momentum (auto)
- **Hardware**: NVIDIA RTX 3070 Ti (8GB VRAM)

---

## ML Technical Report 📊

### Final Training Metrics

| Metric | Value | Rating |
|--------|-------|--------|
| **mAP50** | **69.5%** | 🟡 Decent |
| **mAP50-95** | **46.9%** | 🟡 Decent |
| **Precision** | **78.2%** | 🟢 Good |
| **Recall** | **63.4%** | 🟠 Needs work |

### 1. Overfitting / Underfitting Analysis

#### Train vs. Validation Loss

| Epoch | Train Box Loss | Val Box Loss | Gap | Train Cls Loss | Val Cls Loss | Gap |
|-------|---------------|-------------|------|---------------|-------------|------|
| 1     | 1.0889        | 1.0673      | −0.02 | 1.2534        | 0.9048      | −0.35 |
| 25    | 0.9796        | 0.9803      | +0.00 | 0.7388        | 0.6885      | −0.05 |
| 50    | 0.8681        | 0.9351      | **+0.07** | 0.5875        | 0.6108      | **+0.02** |
| 75    | 0.7836        | 0.9131      | **+0.13** | 0.5016        | 0.5735      | **+0.07** |
| 100   | 0.7091        | 0.9205      | **+0.21** | 0.4340        | 0.5719      | **+0.14** |
| 107   | 0.6923        | 0.9220      | **+0.23** | 0.4224        | 0.5709      | **+0.15** |

#### Diagnosis: **Mild Overfitting** 🟡

The model shows **mild overfitting** starting from approximately **epoch 50**.

**Evidence:**
- The **training loss keeps dropping** (box: 1.089 → 0.692, cls: 1.253 → 0.422) — the model continues to learn the training data better.
- The **validation loss plateaus** (box: ~0.92, cls: ~0.57) — the model stops improving on unseen data after epoch ~75.
- The **gap widens** over time: Box loss gap goes from 0.00 at epoch 25 to **+0.23 at epoch 107**.

**However**, this is **NOT severe overfitting** because:
- The validation loss is **flat/plateauing, not rising**.
- The mAP on validation data continued to improve slightly (0.684 → 0.692).
- Early stopping (patience=30) correctly detected the plateau and halted at epoch 107.

#### Is the Model Underfitting?
**No.** Training loss converged to low values (box=0.69, cls=0.42). If underfitting, both train AND val loss would be high.

---

## Dataset: SH17 (Safety Helmet 17-Class)

The model detects 17 PPE-related classes:

| ID | Class | ID | Class |
|----|-------|----|-------|
| 0 | Person | 9 | Gloves |
| 1 | Ear | 10 | Helmet |
| 2 | Earmuffs | 11 | Hands |
| 3 | Face | 12 | Head |
| 4 | Face-guard | 13 | Medical-suit |
| 5 | Face-mask | 14 | Shoes |
| 6 | Foot | 15 | Safety-suit |
| 7 | Tool | 16 | Safety-vest |
| 8 | Glasses | | |

---

## Project Structure

```
SmartFactory/
├── backend/           # Flask API + YOLO detector
│   ├── app.py         # Main Flask server
│   ├── detector.py    # PPE_Detector class (YOLOv11)
│   ├── camera.py      # Camera management
│   └── best.pt        # Trained YOLO model weights
├── frontend/          # Angular dashboard
│   └── src/
├── IoTBackend/        # .NET IoT backend (SignalR + MQTT)
├── scripts/
│   ├── test_detector_ui.py  # Standalone test UI with live webcam
│   ├── export_metrics.py    # Export training results to Excel
│   └── ai_dashboard_monitor.py # Anomaly detection & email alerts
├── train.py           # Model training script
├── requirements.txt   # Python dependencies
└── start_app.bat      # One-click launcher (Windows)
```

## License
MIT
