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
    model = YOLO("yolo11m.pt")

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

    # Set environment variable to prevent memory fragmentation on Windows 8GB GPUs (commented out to prevent CUDA hangs)
    # os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    # ─── TRAIN ────────────────────────────────────────────────────────────────
    # Corrected Settings for RTX 3070 Ti (8GB VRAM):
    #   - imgsz=800  : A perfect sweet spot. 1024 forced the batch size too low.
    #   - batch=4    : Set to 4 to prevent VRAM paging/swapping with other open Windows apps.
    #   - optimizer='auto' : Defaults back to SGD with Momentum (more stable than AdamW for YOLO)
    #   - mixup/copy_paste : Enabled at soft rates (0.05) to help generalize without underfitting
    #   - cos_lr=True : Enable cosine learning rate decay
    #   - cls=1.0 : Increased classification loss weight to address class imbalance & low-recall classes
    results = model.train(
        data=yaml_path,
        epochs=150,
        imgsz=640,           # Set to 640 to match dataset native resolution and improve speed
        batch=8,             # Set to 8 now that imgsz is 640 (VRAM safe)
        device=device,
        amp=True,
        patience=30,
        plots=True,
        verbose=True,
        optimizer='auto',    # Revert to standard SGD
        cos_lr=True,         # Enable cosine LR scheduler
        mixup=0.05,          # Soft mixup augmentation
        copy_paste=0.05,     # Soft copy-paste augmentation
        cls=1.0,             # Focus more on correct class identification (imbalance/recall helper)
        workers=2,           # Set workers to 2 to enable parallel batch loading now that VRAM is safe
        project=os.path.join(script_dir, "runs", "detect"),
        name="sh17_train_fixed",  
    )

    # ─── DONE ─────────────────────────────────────────────────────────────────
    print("\n" + "─" * 60)
    print("✅ Training Complete!")
    save_dir = results.save_dir
    best_weights = os.path.join(save_dir, "weights", "best.pt")
    print(f"📦 Best model saved at:\n   {best_weights}")
    print("\nNext step: Copy best.pt to the backend/ folder:")
    print(f"   Copy-Item '{best_weights}' '{os.path.join(script_dir, 'backend', 'best.pt')}' -Force")

    # ─── EXPORT METRICS TO EXCEL ──────────────────────────────────────────────
    try:
        csv_path = os.path.join(save_dir, "results.csv")
        excel_path = os.path.join(script_dir, "SmartFactory_SH17_Metrics.xlsx")
        from scripts.export_metrics import export_training_results
        export_training_results(csv_path, excel_path)
    except Exception as e:
        print(f"\n⚠️ Could not export metrics to Excel: {e}")

if __name__ == '__main__':
    train_model()
