from ultralytics import YOLO
import os
import torch

def train_model():
    # ─── GPU CHECK ────────────────────────────────────────────────────────────
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb  = round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)
        print(f"✅ GPU Detected: {gpu_name} ({vram_gb} GB VRAM)")
        if vram_gb >= 8:
            print("   High-VRAM GPU detected. Using optimal high-accuracy settings.")
        elif vram_gb >= 4:
            print("   Mid-VRAM GPU detected. Using memory-safe settings.")
        device = 0
    else:
        print("⚠️  No CUDA GPU found. Training will run on CPU (very slow).")
        print("    If you have an NVIDIA GPU, reinstall PyTorch with CUDA support.")
        device = "cpu"

    # ─── MODEL ────────────────────────────────────────────────────────────────
    # Optimized for RTX 3070 Ti (8GB VRAM)
    # yolo11l.pt = Large model — high accuracy, comfortably fits in 8GB VRAM
    # ─────────────────────────────────────────────────────────────────────────
    # If using RTX 2050 (4GB), change to: model=yolo11m.pt, batch=4, imgsz=640
    # ─────────────────────────────────────────────────────────────────────────
    model = YOLO("yolo11l.pt")

    # ─── DATASET PATH ─────────────────────────────────────────────────────────
    # FIX: Resolve path relative to this script file, not the terminal CWD.
    # This ensures training works regardless of which folder you open the terminal in.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    yaml_path  = os.path.join(script_dir, "dataset", "data.yaml")

    if not os.path.exists(yaml_path):
        print(f"\n❌ Error: Could not find dataset at:\n   {yaml_path}")
        print("   Please make sure you extracted the SH17 dataset into 'SmartFactory/dataset'")
        print("   The folder must contain: dataset/train/, dataset/val/, and dataset/data.yaml")
        return

    print(f"\nDataset found at: {yaml_path}")
    print("Starting training on the SH17 dataset (17 PPE classes, 8,099 images)...")
    print("─" * 60)

    # Set environment variable to prevent memory fragmentation on Windows 8GB GPUs
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # ─── TRAIN ────────────────────────────────────────────────────────────────
    # Settings optimized for RTX 3070 Ti (8GB VRAM):
    #   - imgsz=1280 : Captures small objects (gloves, earmuffs, glasses)
    #   - batch=8    : Reduced from 16 to fit comfortably in 8GB VRAM without Out of Memory (OOM) errors
    #   - epochs=100 : Enough for the model to fully converge on SH17
    #   - patience=20: Stop early if validation mAP doesn't improve for 20 epochs
    #   - device=0   : Use GPU (the NVIDIA card)
    #   - amp=True   : Automatic Mixed Precision — halves VRAM usage, speeds training
    results = model.train(
        data=yaml_path,
        epochs=100,
        imgsz=1280,         # Higher res: SH17 images are up to 8192px — 1280 catches small objects
        batch=8,            # Lowered to 8 to prevent CUDA OOM
        device=device,
        amp=True,           # Mixed precision (FP16) — halves VRAM usage, speeds training
        patience=20,        # Stop early if no improvement for 20 epochs
        plots=True,
        verbose=True,
        project=os.path.join(script_dir, "runs", "detect"),
        name="sh17_train",  # Results saved to runs/detect/sh17_train/
    )

    # ─── DONE ─────────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("✅ Training Complete!")
    best_weights = os.path.join(script_dir, "runs", "detect", "sh17_train", "weights", "best.pt")
    print(f"📦 Best model saved at:\n   {best_weights}")
    print("\nNext step: Copy best.pt to the backend/ folder:")
    print(f"   Copy-Item '{best_weights}' '{os.path.join(script_dir, 'backend', 'best.pt')}' -Force")

    # ─── EXPORT METRICS TO EXCEL ──────────────────────────────────────────────
    try:
        csv_path = os.path.join(script_dir, "runs", "detect", "sh17_train", "results.csv")
        excel_path = os.path.join(script_dir, "SmartFactory_SH17_Metrics.xlsx")
        from scripts.export_metrics import export_training_results
        export_training_results(csv_path, excel_path)
    except Exception as e:
        print(f"\n⚠️ Could not export metrics to Excel: {e}")

if __name__ == '__main__':
    train_model()
