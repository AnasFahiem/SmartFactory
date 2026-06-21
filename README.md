# Smart Factory IoT Monitor 🏭

A comprehensive Real-time Industrial Surveillance and Safety Monitoring System using **YOLOv11** (Backend) and **Angular** (Frontend).

## Features 🚀
- **Real-time PPE Detection**: Detects Hardhats, Vests, Gloves, Masks, etc.
- **Safety Violation Alerts**: Instant visual feedback for compliance issues.
- **Live Video Streaming**: Low-latency video feed with AI overlay.
- **Dynamic Camera Control**: Switch between **Webcam** and **ESP32 IP Camera** on the fly.
- **Unified Dashboard**: Monitor sensor data (Person Count, Violations) and video in one place.

## Prerequisites
- **Python 3.8+**
- **Node.js & npm** (for Frontend)
- **NVIDIA GPU** with CUDA support (recommended for real-time detection)
- **ESP32-CAM** (Optional, for remote streaming)

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
python scripts/new_test_ui.py
```
Then open **http://localhost:8000** in your browser and click **Start Camera**.

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

## Model Training

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

### mAP Progression Over Training

| Epoch | mAP50 | mAP50-95 | Precision | Recall |
|-------|-------|----------|-----------|--------|
| 1     | 0.443 | 0.277    | 0.501     | 0.454  |
| 25    | 0.594 | 0.386    | 0.671     | 0.569  |
| 50    | 0.648 | 0.427    | 0.738     | 0.601  |
| 75    | 0.684 | 0.461    | 0.785     | 0.639  |
| 100   | 0.689 | 0.468    | 0.768     | 0.629  |
| 107   | 0.692 | 0.469    | 0.782     | 0.634  |

---

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
- In the **last 20 epochs**, train loss fell (−0.05) while val loss barely moved (+0.002).

**However**, this is **NOT severe overfitting** because:
- The validation loss is **flat/plateauing, not rising**.
- The mAP on validation data continued to improve slightly (0.684 → 0.692).
- Early stopping (patience=30) correctly detected the plateau and halted at epoch 107.

#### Is the Model Underfitting?

**No.** Training loss converged to low values (box=0.69, cls=0.42). If underfitting, both train AND val loss would be high.

---

### 2. Bias–Variance Tradeoff

| Indicator | Value | Interpretation |
|-----------|-------|----------------|
| Train box loss | 0.692 | Low — fits training data well |
| Val box loss | 0.922 | Higher — struggles on new data |
| Gap (val − train) | +0.230 | Moderate variance |
| Precision | 78.2% | High — predictions are usually correct |
| Recall | 63.4% | Lower — misses ~37% of objects |

- **Bias**: **Low** ✅ — The model has enough capacity (20M parameters) to learn complex patterns. Training loss converged to low values.
- **Variance**: **Moderate** 🟡 — The train-val gap indicates some training-specific patterns that don't generalize perfectly. This is typical for a medium-sized model on a complex 17-class detection task.

---

### 3. Normalization Technique

#### **Batch Normalization (BatchNorm2d)** ✅

| Property | Value |
|----------|-------|
| **Type** | `torch.nn.BatchNorm2d` |
| **Total layers** | **106** |
| **Epsilon (ε)** | 0.001 |
| **Momentum** | 0.03 |
| **Affine** | True (learnable γ and β) |
| **Track Running Stats** | True |

Every convolutional block follows the pattern: **Conv2d → BatchNorm2d → SiLU**.

BatchNorm normalizes each feature map across the batch dimension:

```
              x - μ_batch
  x̂ = ─────────────────────
        √(σ²_batch + ε)

  output = γ · x̂ + β
```

- **γ (gamma)** and **β (beta)** are learnable scale and shift parameters.
- **Momentum = 0.03** (lower than PyTorch default 0.1) provides more stable running statistics — a YOLO-specific tuning.
- During inference, **running mean/variance** are used instead of batch statistics.

---

### 4. Weight Initialization Technique

#### **Kaiming (He) Initialization** ✅

| Property | Value |
|----------|-------|
| **Method** | Kaiming Uniform (He Init) |
| **Designed for** | ReLU-family activations (SiLU) |

YOLOv11 initializes all Conv2d weights using **Kaiming Uniform**:

```
  W ~ Uniform(-bound, +bound)
  where bound = √(6 / fan_in)
```

- `fan_in` = `in_channels × kernel_h × kernel_w`
- Ensures the variance of activations is preserved through the forward pass, preventing **vanishing or exploding gradients**.
- Chosen over **Xavier/Glorot** because Xavier assumes linear/tanh activations, while Kaiming is designed for ReLU-family (SiLU).

**Special cases:**
- BatchNorm weights (γ) initialized to **1.0**, biases (β) to **0.0**.
- DFL (Distribution Focal Loss) conv uses fixed non-learnable weights.

---

### 5. Activation Functions

#### **SiLU (Sigmoid Linear Unit / Swish)** — Primary Activation ✅

| Property | Value |
|----------|-------|
| **Primary activation** | **SiLU** (Swish) |
| **Total instances** | **95** Conv blocks |
| **Identity (passthrough)** | **5** (Attention/SPPF) |

```
  SiLU(x) = x × sigmoid(x) = x × (1 / (1 + e⁻ˣ))
```

**Properties:**
- **Smooth & non-monotonic** — unlike ReLU's sharp corner at 0
- **Self-gated** — the input multiplies its own sigmoid
- **No dead neurons** — unlike ReLU which kills negative activations, SiLU allows small gradient flow
- **Output range** — approximately [-0.28, +∞)

| Feature | ReLU | SiLU (Swish) |
|---------|------|-------------|
| Formula | max(0, x) | x · σ(x) |
| Smooth | ❌ No | ✅ Yes |
| Dead neurons | ❌ Yes | ✅ No |
| Accuracy | Good | **Better** (+1-2%) |

---

### 6. Full Architecture Summary

| Component | Layer Type | Count | Purpose |
|-----------|-----------|-------|---------|
| Convolution | Conv2d | 113 | Feature extraction |
| Normalization | BatchNorm2d | 106 | Normalize activations |
| Activation | SiLU | 95 | Non-linear transformation |
| Residual Blocks | Bottleneck | 16 | Skip connections |
| Feature Aggregation | C3k2 | 8 | Cross-stage partial connections |
| Feature Aggregation | C3k | 8 | 3-kernel convolution blocks |
| Depthwise Conv | DWConv | 6 | Efficient spatial filtering |
| Skip Connections | Identity | 5 | Residual bypass paths |
| Feature Fusion | Concat | 4 | Multi-scale feature merging |
| Upsampling | Upsample | 2 | Increase spatial resolution |
| Spatial Pooling | SPPF | 1 | Multi-scale spatial pyramid |
| Self-Attention | C2PSA + Attention | 1 | Global context modeling |
| Detection Head | Detect + DFL | 1 | Final predictions |

#### Architecture Flow
```
Input (800×800×3)
       │
       ▼
  ┌──────────────────┐
  │  BACKBONE         │
  │  CSPDarknet       │  Conv → C3k2 blocks (5 stages)
  │  + SPPF           │  Spatial Pyramid Pooling
  │  + C2PSA          │  Self-Attention
  └──────────────────┘
       │
       ▼
  ┌──────────────────┐
  │  NECK (PAN-FPN)   │  Multi-scale feature fusion
  │  Upsample+Concat  │  Top-down + bottom-up paths
  │  + C3k2 blocks    │
  └──────────────────┘
       │
       ▼
  ┌──────────────────┐
  │  HEAD (Detect)    │  3 detection scales:
  │  ├─ P3 (Small)    │    100×100 for small objects
  │  ├─ P4 (Medium)   │    50×50 for medium objects
  │  └─ P5 (Large)    │    25×25 for large objects
  │  + DFL regression │  Distribution Focal Loss
  └──────────────────┘
       │
       ▼
  17 class predictions + bounding boxes
```

#### Model Statistics

| Metric | Value |
|--------|-------|
| **Total Parameters** | **20,066,115** (~20M) |
| **Model Size** | ~120 MB |
| **Input Resolution** | 800 × 800 |
| **Output Classes** | 17 (PPE classes) |
| **Detection Scales** | 3 (small, medium, large) |
| **Loss Function** | BCE (cls) + CIoU (box) + DFL (distribution) |

---

### 7. Regularization Techniques

| Technique | Status | Details |
|-----------|--------|---------|
| Batch Normalization | ✅ Used | 106 layers — implicit regularizer |
| Data Augmentation | ✅ Used | Mosaic, HSV jitter, flip, scale, translate, erasing |
| Weight Decay (L2) | ✅ Used | 0.0005 — penalizes large weights |
| Early Stopping | ✅ Used | patience=30 — stopped at epoch 107/150 |
| Dropout | ❌ Not used | 0 dropout layers |
| Label Smoothing | ❌ Not used | Not configured |
| MixUp | ❌ Not used | mixup=0.0 |
| Copy-Paste | ❌ Not used | copy_paste=0.0 |

---

### 8. Summary Verdict

| Question | Answer |
|----------|--------|
| **Overfitting?** | 🟡 Mildly. Train loss drops while val loss plateaus. Gap = +0.23. Not severe. |
| **Underfitting?** | ✅ No. Training loss converged to low values. |
| **High Bias?** | ✅ No (Low bias). Model fits training data well. |
| **High Variance?** | 🟡 Moderate. Noticeable train-val gap. |
| **Normalization** | BatchNorm2d — 106 layers, ε=0.001, momentum=0.03 |
| **Weight Init** | Kaiming (He) Uniform — for SiLU activations |
| **Activation** | SiLU (Swish) — 95 instances, x · sigmoid(x) |
| **Regularization** | BatchNorm + Weight Decay + Augmentation + Early Stopping |

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
│   ├── new_test_ui.py       # Standalone test UI with live webcam
│   ├── export_metrics.py    # Export training results to Excel
│   └── ai_dashboard_monitor.py
├── train.py           # Model training script
├── requirements.txt   # Python dependencies
└── start_app.bat      # One-click launcher (Windows)
```

## License
MIT
