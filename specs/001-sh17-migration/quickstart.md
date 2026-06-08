# Verification Guide: PPE Detection

This guide validates that the SH17 dataset logic is working on the camera stream.

## Setup
1. Ensure the camera is connected or a test video is available.
2. (After training) Ensure `best.pt` is located in `f:\SmartFactory\runs\detect\train\weights\best.pt`.
3. If not yet trained, the system will start in "AI Disabled" mode to prevent crashes.

## Verification Scenarios

### Scenario 1: AI Disabled Fallback
1. Start the app: `python app.py`
2. Open `http://localhost:5000`
3. Verify that a visible warning indicating "AI Disabled" appears on the camera feed if `best.pt` is missing.

### Scenario 2: Normal Detection (Post-training)
1. Start the app: `python app.py`
2. Open `http://localhost:5000`
3. Stand in front of the camera with a helmet and a high-vis vest.
4. Verify that bounding boxes named `Person`, `Helmet`, and `Safety-vest` appear exactly once.
5. Verify that the "Violations" counter on the UI does not increase.

### Scenario 3: Violation Detection (Post-training)
1. Take off the helmet.
2. Verify that the system bounding box for the Head or Person flashes red or specifically indicates a Helmet Violation.
3. Verify the "Violations" counter on the UI increases.
