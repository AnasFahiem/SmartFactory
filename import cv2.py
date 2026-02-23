import cv2
import requests
import time
import base64
from ultralytics import YOLO  # Import YOLO

# --- SETTINGS ---
CAMERA_URL = "http://192.168.1.35:8080/video" 
AZURE_URL = "https://smartest-factory-dcg4awhecvahcmgq.francecentral-01.azurewebsites.net/api/camera/upload"
MY_SECRET = "YourSuperSecretKey123" 

# 1. Load a pre-trained YOLO model (nano version is fastest for streaming)
# This will download 'yolov8n.pt' automatically on first run
model = YOLO('yolov8n.pt') 

session = requests.Session()
cap = cv2.VideoCapture(CAMERA_URL)

if not cap.isOpened():
    print("Error: Could not connect to IP Webcam.")
    exit()

while True:
    ret, frame = cap.read()
    if ret:
        # 2. RUN COMPUTER VISION DETECTION
        # We filter for 'person' (class 0 in COCO dataset)
        results = model.predict(frame, classes=[0], conf=0.5, verbose=False)
        
        # 3. ANNOTATE THE FRAME
        # This draws the red boxes and labels on the image
        annotated_frame = results[0].plot()
        
        # Count how many people are detected (potential violations if zone is restricted)
        person_count = len(results[0].boxes)

        # 4. PREPARE IMAGE FOR AZURE
        frame_resized = cv2.resize(annotated_frame, (640, 480))
        _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 30])
        base64_image = "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')
        
        try:
            # We send the violation count to the backend along with the image
            response = session.post(AZURE_URL, json={
                "image": base64_image, 
                "secretKey": MY_SECRET,
                "violationCount": person_count # New field for your backend
            }, timeout=1)
            
        except Exception as e:
            print(f"Connection error: {e}")

    time.sleep(0.05) # Increased frequency for smoother AI tracking