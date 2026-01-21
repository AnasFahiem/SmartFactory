from ultralytics import YOLO
import os

def train_model():
    # 1. Load the model (YOLOv11 nano version)
    model = YOLO("yolo11n.pt") 

    # 2. Define path to data.yaml
    # Assuming user extracted the folder to 'dataset' inside SmartFactory
    yaml_path = os.path.abspath("dataset/data.yaml")

    if not os.path.exists(yaml_path):
        print(f"Error: Could not find {yaml_path}")
        print("Please make sure you extracted the downloaded folder into 'SmartFactory/dataset'")
        return

    print("Starting training... (This may take a while depending on your PC)")
    
    # 3. Train
    # epochs=20 is a good start for a demo
    # imgsz=640 is standard
    results = model.train(data=yaml_path, epochs=5, imgsz=640, plots=True)
    
    # 4. Export the best model
    # It usually saves to runs/detect/train/weights/best.pt
    print("Training Complete!")
    print("Your new model is at: runs/detect/train/weights/best.pt")
    print("Move that file to the backend folder to use it.")

if __name__ == '__main__':
    train_model()
