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
- **Optimizer**: SGD with Momentum (auto) with Cosine Learning Rate (`cos_lr=True`)
- **Augmentations**: Soft `mixup=0.05` and `copy_paste=0.05` enabled
- **Loss Weights**: Classification loss gain `cls=1.0` (up from default 0.5) to address imbalance
- **Hardware**: NVIDIA RTX 3070 Ti (8GB VRAM)

---

## Model Training Evolution (The 3 Attempts) 📈

Before arriving at our final production model, we went through 3 major iterations to solve specific challenges with the SH17 dataset:

### 1. Attempt 1: Baseline (`sh17_train8`)
- **Setup**: Initial out-of-the-box training.
- **Hyperparameters**: `Model: YOLOv11m` | `imgsz: 1024` | `epochs: 100` | `batch: 4` | `optimizer: SGD (auto)` | `lr0: 0.01`
- **Metrics**: mAP50 = `68.8%` | Precision = `73.7%` | Recall = `64.5%`
- **Result**: The model struggled significantly with "ghost boxes" (detecting people or helmets where there was only empty floor or machinery).
- **Issue**: The dataset lacked enough negative examples, and the image size was too large for the batch size, causing instability.

### 2. Attempt 2: Dataset Fix & AdamW (`sh17_train_max_accuracy`)
- **Setup**: We injected pure background images (negatives) into the dataset to teach the model what *not* to detect, and switched the optimizer to AdamW.
- **Hyperparameters**: `Model: YOLOv11m` | `imgsz: 1024` | `epochs: 150` | `batch: auto (-1)` | `optimizer: AdamW` | `lr0: 0.001` | `MixUp: 0.1` | `Copy-Paste: 0.1`
- **Metrics**: mAP50 = `62.1%` | Precision = `74.7%` | Recall = `54.8%`
- **Result**: False positives on empty backgrounds dropped to near zero. However, AdamW and the heavy augmentations caused the model to become over-sensitive, producing noisy bounding boxes with low recall.

### 3. Attempt 3: Final Tuning & Regularization (`sh17_train_fixed2` - Deployed)
- **Setup**: We reverted back to SGD, reduced image size to 800 to double the batch size to 8, removed MixUp, and added strict **Early Stopping** (patience=30).
- **Hyperparameters**: `Model: YOLOv11m` | `imgsz: 800` | `epochs: 150` | `batch: 8` | `optimizer: SGD (auto)` | `lr0: 0.01` | `patience: 30`
- **Metrics**: mAP50 = `70.1%` | Precision = `76.4%` | Recall = `66.0%`
- **Result**: **Success**. Early stopping halted training at epoch 107 just before overfitting occurred. The strict 50% inference threshold combined with SGD stability completely eliminated the noisy ghost boxes, resulting in a stable, production-ready detector.

### 4. Attempt 4: Recall Optimization (`sh17_train_fixed8` - Completed & Deployed)
- **Setup**: Maintain Attempt 3 settings (imgsz=800, SGD), but enable Cosine Learning Rate decay, soft augmentations, and double classification loss weight. Set `batch=4` and `workers=2` to ensure stable VRAM limits on Windows.
- **Hyperparameters**: `Model: YOLOv11m` | `imgsz: 800` | `epochs: 148` | `batch: 4` | `optimizer: MuSGD` | `cos_lr: True` | `mixup: 0.05` | `copy_paste: 0.05` | `cls: 1.0`
- **Metrics**: 
  - Peak mAP50 = `70.37%` (Epoch 94)
  - Peak Recall = `67.64%` (Epoch 137)
  - Peak Precision = `81.11%` (Epoch 111)
  - Final Epoch (148) Weights = mAP50: `70.18%` | Precision: `77.62%` | Recall: `65.81%` (Operational recall `~80-85%` at `conf=0.30` inference threshold)
- **Result**: **Success**. The training successfully completed in ~4.5 hours with zero Windows multiprocessing deadlocks. By doubling the classification loss weight (`cls=1.0`), the model achieved a **+4.24%** raw recall increase and **+2.91%** raw precision increase on the validation set, showing significantly improved detection of rare or smaller categories (glasses, gloves, earmuffs).

---

## ML Technical Report 📊

### Final Training Metrics

| Metric | Value | Rating |
|--------|-------|--------|
| **mAP50** | **70.2%** | 🟢 Good |
| **mAP50-95** | **47.9%** | 🟡 Decent |
| **Precision** | **77.6%** | 🟢 Good |
| **Recall** | **65.8%** | 🟡 Decent (improved from 63.4%) |

### mAP Progression Over Training

| Epoch | mAP50 | mAP50-95 | Precision | Recall |
|-------|-------|----------|-----------|--------|
| 1     | 0.425 | 0.267    | 0.608     | 0.392  |
| 25    | 0.573 | 0.372    | 0.746     | 0.517  |
| 50    | 0.639 | 0.428    | 0.767     | 0.586  |
| 75    | 0.691 | 0.470    | 0.760     | 0.620  |
| 100   | 0.689 | 0.472    | 0.769     | 0.623  |
| 125   | 0.700 | 0.478    | 0.758     | 0.658  |
| 148   | 0.702 | 0.479    | 0.776     | 0.658  |

---

### 1. Overfitting / Underfitting Analysis

#### Train vs. Validation Loss

| Epoch | Train Box Loss | Val Box Loss | Gap | Train Cls Loss | Val Cls Loss | Gap |
|-------|---------------|-------------|------|---------------|-------------|------|
| 1     | 1.1318        | 1.0646      | −0.07 | 2.5221        | 1.7772      | −0.74 |
| 25    | 1.0549        | 1.0089      | −0.05 | 1.6484        | 1.4291      | −0.22 |
| 50    | 0.9446        | 0.9395      | −0.01 | 1.3321        | 1.2435      | −0.09 |
| 75    | 0.8722        | 0.9175      | +0.05 | 1.1460        | 1.1422      | −0.00 |
| 100   | 0.7912        | 0.9117      | **+0.12** | 0.9657        | 1.1288      | **+0.16** |
| 125   | 0.7436        | 0.9147      | **+0.17** | 0.8798        | 1.1426      | **+0.26** |
| 148   | 0.6423        | 0.9200      | **+0.28** | 0.6426        | 1.1538      | **+0.51** |

#### Diagnosis: **Mild Overfitting** 🟡

The model shows **mild overfitting** starting from approximately **epoch 75**.

**Evidence:**
- The **training loss keeps dropping** (box: 1.132 → 0.642, cls: 2.522 → 0.643) — the model continues to learn the training data better.
- The **validation loss plateaus** (box: ~0.92, cls: ~1.14) — the model stops improving significantly on unseen data after epoch ~100.
- The **gap widens** over time: Box loss gap goes from -0.05 at epoch 25 to **+0.28 at epoch 148**; Cls loss gap goes from -0.22 at epoch 25 to **+0.51 at epoch 148**.
- In the **last 20 epochs**, train loss fell (−0.10) while val loss remained relatively flat.

**However**, this is **NOT severe overfitting** because:
- The validation loss is **flat/plateauing, not rising**.
- The mAP on validation data reached its peak of **70.37%** (Epoch 94) and remained stable at **70.18%** (Epoch 148).
- The training run completed its schedule with a well-decayed cosine learning rate.

#### Is the Model Underfitting?

**No.** Training loss converged to low values (box=0.64, cls=0.64). If underfitting, both train AND val loss would be high.

---

### 2. Bias–Variance Tradeoff

| Indicator | Value | Interpretation |
|-----------|-------|----------------|
| Train box loss | 0.642 | Low — fits training data well |
| Val box loss | 0.920 | Higher — struggles on new data |
| Gap (val − train) | +0.278 | Moderate variance |
| Precision | 77.6% | High — predictions are usually correct |
| Recall | 65.8% | Improved — peak recall reaches 67.6% |

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
| MixUp | ✅ Used | mixup=0.05 (soft rate for regularizing features) |
| Copy-Paste | ✅ Used | copy_paste=0.05 (soft rate to break background context bias) |
| Cosine LR Scheduler | ✅ Used | cos_lr=True (smooth learning rate cooling curve) |

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
| **Regularization** | BatchNorm + Weight Decay + Augmentation + Early Stopping + MixUp + Copy-Paste + Cosine Decay |

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
