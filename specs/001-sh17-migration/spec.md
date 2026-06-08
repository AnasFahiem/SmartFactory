# Feature Specification: SH17 Dataset Migration

**Feature Branch**: `001-sh17-migration`

**Created**: 2026-06-08

**Status**: Draft

**Input**: User description: "Migrate the Smart Factory live PPE safety detection system to the SH17 dataset (8,099 images, 17 classes). Update train.py with GPU-optimized training settings (yolo11l, 100 epochs, batch=16, AMP). Rewrite backend/detector.py to fix 5 critical bugs: double-drawn bounding boxes, broken violation logic that relied on old NO-Hardhat class names, wrong confidence/aspect-ratio filters hardcoded to old class IDs, a broken yolov8n fallback model, and an unsafe relative path in train.py. Replace with SH17 class mappings, inference-level class filtering for Person/Helmet/Safety-vest/Gloves/Glasses/Head/Hands/Earmuffs, and spatial overlap-based violation detection."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic PPE Violation Detection (Priority: P1)

As a safety officer monitoring the factory floor, I want the system to automatically flag workers who are missing required PPE (Helmets and Safety Vests) using the new SH17 dataset model, so that I can ensure compliance without manual surveillance.

**Why this priority**: This is the core functionality of the Smart Factory system. Without accurate live violation detection, the system provides no safety value.

**Independent Test**: Can be fully tested by feeding an image of a person without a helmet to the backend and verifying that a "Helmet Violation" is triggered in the stats output.

**Acceptance Scenarios**:

1. **Given** a camera frame containing a person wearing a helmet, **When** processed by the detector, **Then** the person and helmet are bounded in green, and no violation is logged.
2. **Given** a camera frame containing a person *without* a helmet, **When** processed by the detector, **Then** the person's head is bounded in red, and a helmet violation is incremented.

---

### User Story 2 - Small PPE Detection Support (Priority: P2)

As a safety manager, I want the model to be capable of identifying smaller safety equipment like Gloves, Glasses, and Face-masks with reasonable confidence, so that we can expand our safety checks in the future.

**Why this priority**: While primary compliance is helmets and vests, tracking smaller PPE is a key advantage of upgrading to the SH17 dataset and higher resolution YOLOv11l model.

**Independent Test**: Can be tested by feeding close-up images of workers wearing gloves and glasses and confirming the bounding boxes appear with the correct labels.

**Acceptance Scenarios**:

1. **Given** a high-resolution frame of a worker's hands wearing safety gloves, **When** processed by the detector, **Then** the gloves are detected and labeled correctly.

### Edge Cases

- What happens when a worker is partially occluded behind machinery? (The spatial overlap logic should still evaluate whatever visible parts exist).
- How does system handle false positives (e.g., a hardhat resting on a table)? (The spatial logic ensures a violation is tied to a Person/Head detection, reducing standalone false alarms).
- What happens if the `best.pt` model file is missing? (The system should fail gracefully with an "AI disabled" warning rather than falling back to an incorrect COCO model).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST process camera frames using the custom-trained YOLOv11l model on the 17-class SH17 dataset.
- **FR-002**: System MUST map internal YOLO class IDs to the exact 17 SH17 class names (`Person`, `Ear`, `Earmuffs`, `Face`, `Face-guard`, `Face-mask`, `Foot`, `Tool`, `Glasses`, `Gloves`, `Helmet`, `Hands`, `Head`, `Medical-suit`, `Shoes`, `Safety-suit`, `Safety-vest`).
- **FR-003**: System MUST determine safety violations by calculating spatial overlap (IoU/Intersection over Area) between body parts and PPE (e.g., `Head` overlaps with `Helmet`, `Person` overlaps with `Safety-vest`).
- **FR-004**: System MUST NOT rely on negative classes (e.g., `NO-Hardhat`) for violation detection.
- **FR-005**: System MUST disable AI features and show a warning if the custom `best.pt` model fails to load, preventing the use of incompatible fallback models.
- **FR-006**: System MUST ensure bounding boxes are drawn exactly once per detected object to prevent visual ghosting.

### Key Entities

- **Bounding Box**: A set of coordinates (x1, y1, x2, y2) representing the location of a detected object.
- **Detection**: An instance containing a class ID, confidence score, bounding box, and label string.
- **Violation State**: A boolean/counter indicating if a required PPE item is missing from a detected person.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The detector correctly identifies a missing helmet or vest in at least 80% of clear, unobstructed test frames.
- **SC-002**: Bounding boxes are rendered without duplication (1 rendering pass per object).
- **SC-003**: The system successfully processes frames at >= 15 FPS on the target RTX 3070 Ti hardware.
- **SC-004**: The system logs 0 false positives triggered by the old hardcoded color/aspect-ratio filters.

## Assumptions

- Training on the RTX 3070 Ti will complete successfully and produce a viable `best.pt` model.
- The `yolo11l` model at `1280` image size can run inference fast enough for live video on the target hardware.
- The user's camera feed provides sufficient resolution to distinguish small PPE items like glasses.
