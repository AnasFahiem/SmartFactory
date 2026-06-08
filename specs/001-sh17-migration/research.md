# Technical Research: SH17 Migration

## Decision: Spatial Violation Detection
**Rationale**: In the previous system, the model was trained with classes like `NO-Hardhat`, offloading the "violation check" logic to the AI model itself. In the new SH17 dataset, the model simply detects what is visibly present (`Person`, `Helmet`). The easiest way to determine if a `Person` is wearing a `Helmet` in 2D bounding-box space is to check the intersection of their coordinates. 
**Alternatives**: Using pose-estimation (YOLO-pose) to detect head/shoulder keypoints and binding the helmet box to the head keypoint. Rejected because the SH17 dataset does not contain keypoint annotations, only bounding boxes.

## Decision: Fallback Model
**Rationale**: Previously, if `best.pt` wasn't found, the system loaded `yolov8n.pt`. However, YOLOv8n uses the COCO dataset where `class 0` is `Person` but `class 10` is `Fire hydrant`. The SH17 class map would mislabel a fire hydrant as a helmet, causing confusing false positives. We will fail gracefully instead.
