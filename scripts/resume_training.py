from ultralytics import YOLO
import os

# Find latest training run
runs_dir = r"C:\Users\anasf\Documents\SmartFactory\runs\detect"
if not os.path.exists(runs_dir):
    print("No training runs found.")
    exit()

subdirs = [os.path.join(runs_dir, d) for d in os.listdir(runs_dir) if os.path.isdir(os.path.join(runs_dir, d))]
latest_run = max(subdirs, key=os.path.getmtime)

# Path to last checkpoint
last_ckpt = os.path.join(latest_run, "weights", "last.pt")

if os.path.exists(last_ckpt):
    print(f"Resuming from: {last_ckpt}")
    model = YOLO(last_ckpt)
    model.train(resume=True)
else:
    print(f"No checkpoint found in {latest_run}. Starting fresh.")
    model = YOLO("yolov8n.pt")
    model.train(data=r"C:\Users\anasf\Documents\SmartFactory\dataset\data.yaml", epochs=5, imgsz=640, plots=True)
