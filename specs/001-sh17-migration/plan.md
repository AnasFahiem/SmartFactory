# Implementation Plan: SH17 Dataset Migration

**Branch**: `001-sh17-migration` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///F:/SmartFactory/specs/001-sh17-migration/spec.md)

**Input**: Feature specification from `/specs/001-sh17-migration/spec.md`

## Summary

Migrate the Smart Factory live PPE safety detection system from its current custom negative-class structure to the standardized 17-class SH17 dataset. This requires fixing 5 critical bugs in the backend inference logic (`detector.py`) and implementing spatial bounding-box overlap calculations to determine safety violations (e.g., checking if a detected `Head` has an overlapping `Helmet`), replacing the old hardcoded confidence filters and text-based negative logic.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: `ultralytics` (YOLOv11), `opencv-python` (`cv2`), `numpy`, `torch`
**Storage**: N/A (In-memory inference)
**Testing**: Manual live-camera verification
**Target Platform**: Windows 11 PC with NVIDIA RTX 3070 Ti (8GB VRAM)
**Project Type**: AI Inference Backend (`detector.py`) / Flask API
**Performance Goals**: >15 FPS real-time processing
**Constraints**: Requires accurate mapping of 17 specific SH17 classes
**Scale/Scope**: Live video streams from factory cameras

## Constitution Check

*Project principles not found - proceeding without constitution gates.*

## Project Structure

### Documentation (this feature)

```text
specs/001-sh17-migration/
├── plan.md              # This file
├── research.md          # Technical research and choices
├── data-model.md        # AI Class mapping structures
└── quickstart.md        # Run verification guide
```

### Source Code (repository root)

```text
backend/
├── app.py               # Main Flask entrypoint (no changes needed)
├── camera.py            # Video feed handler (no changes needed)
└── detector.py          # [MODIFY] AI Inference and overlap logic engine
```

**Structure Decision**: No structural changes. We are exclusively rewriting the internal logic of the existing `backend/detector.py` module.

## Technical Design: `detector.py` Rewrite

The `PPE_Detector.detect()` method currently contains legacy logic for a different dataset. We will rewrite it entirely.

1. **Remove the Double Box Bug**:
   Remove `annotated_frame = result.plot()`. We will only draw boxes via `cv2.rectangle` at the end of the pipeline.

2. **Remove Hardcoded Filter Bugs**:
   Remove `if cls_id == 0:` color/brightness/aspect-ratio filters. These were built for a dataset where `0=Hardhat`. In SH17, `0=Person`.

3. **Remove `yolov8n.pt` Fallback**:
   In `__init__`, if `best.pt` fails to load, set `self.model = None` and throw a visible red warning on the frame. Do NOT load `yolov8n.pt` as it is a COCO model.

4. **Implement New Class Map**:
   ```python
   CLASS_MAP = {
       0: 'Person', 1: 'Ear', 2: 'Earmuffs', 3: 'Face', 4: 'Face-guard', 
       5: 'Face-mask', 6: 'Foot', 7: 'Tool', 8: 'Glasses', 9: 'Gloves', 
       10: 'Helmet', 11: 'Hands', 12: 'Head', 13: 'Medical-suit', 
       14: 'Shoes', 15: 'Safety-suit', 16: 'Safety-vest'
   }
   ```

5. **Spatial Overlap Logic (IoA)**:
   Add a helper function to calculate Intersection over Area (IoA):
   ```python
   def _get_ioa(box_a, box_b):
       # Returns percentage of box_a covered by box_b
   ```
   Logic loop:
   - Identify all `Person` and `Head` boxes.
   - Identify all `Safety-vest` and `Helmet` boxes.
   - For each `Person`, check if any `Safety-vest` covers >15% of it. If not -> Vest Violation.
   - For each `Head`, check if any `Helmet` covers >30% of it. If not -> Helmet Violation.
