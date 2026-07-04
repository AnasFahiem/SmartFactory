import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    print("Warning: 'ultralytics' not found. AI features disabled.")


class PPE_Detector:
    """
    YOLOv11 PPE Compliance Detector for Industrial Safety.

    Detection Logic:
        1. Run YOLO inference to get raw detections (Person, Helmet, Vest, etc.)
        2. Build a list of "workers" from Person boxes OR from detected PPE if Person is missing
        3. Associate nearby PPE (Helmet, Vest, Safety-suit) to each worker using center-distance
        4. Check compliance: each worker needs (Helmet) AND (Vest OR Safety-suit)
        5. Draw results: Green = Compliant, Red = Violation
    """

    # SH17 Dataset: 17 Classes
    CLASS_MAP = {
        0: 'Person', 1: 'Ear', 2: 'Earmuffs', 3: 'Face', 4: 'Face-guard',
        5: 'Face-mask', 6: 'Foot', 7: 'Tool', 8: 'Glasses', 9: 'Gloves',
        10: 'Helmet', 11: 'Hands', 12: 'Head', 13: 'Medical-suit',
        14: 'Shoes', 15: 'Safety-suit', 16: 'Safety-vest'
    }

    # Classes we skip entirely (body parts that don't affect safety compliance)
    SKIP_CLASSES = {1, 3, 6, 11}  # Ear, Face, Foot, Hands

    # PPE classes we care about for compliance
    HELMET_ID = 10
    VEST_ID = 16
    SUIT_ID = 15
    PERSON_ID = 0

    def __init__(self, model_path='best.pt'):
        """Initialize the YOLOv11 model."""
        self.model = None

        if YOLO is not None:
            print(f"Loading YOLO model from {model_path}...")
            try:
                self.model = YOLO(model_path)
                print("Model loaded successfully.")
                print("Classes:", self.model.names)
            except Exception as e:
                print(f"Error loading model: {e}")
                print("WARNING: Custom best.pt model missing. AI features disabled.")
                self.model = None
        else:
            print("Running in Safe Mode (No AI). Install 'ultralytics' to fix.")

    # -------------------------------------------------------------------------
    # Geometry Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _box_center(box):
        """Return (cx, cy) of a bounding box."""
        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @staticmethod
    def _box_area(box):
        """Return area of a bounding box."""
        x1, y1, x2, y2 = box
        return max(0, x2 - x1) * max(0, y2 - y1)

    @staticmethod
    def _boxes_overlap(box_a, box_b):
        """Check if two boxes have ANY overlap."""
        x1_a, y1_a, x2_a, y2_a = box_a
        x1_b, y1_b, x2_b, y2_b = box_b
        return not (x2_a < x1_b or x2_b < x1_a or y2_a < y1_b or y2_b < y1_a)

    @staticmethod
    def _merge_boxes(boxes):
        """Merge a list of boxes into one bounding box that covers all of them."""
        if not boxes:
            return (0, 0, 0, 0)
        x1 = min(b[0] for b in boxes)
        y1 = min(b[1] for b in boxes)
        x2 = max(b[2] for b in boxes)
        y2 = max(b[3] for b in boxes)
        return (x1, y1, x2, y2)

    @staticmethod
    def _horizontal_overlap_ratio(box_a, box_b):
        """
        How much do two boxes overlap horizontally? Returns 0.0 to 1.0.
        Used to check if a helmet is roughly above a vest (same column).
        """
        x1_a, _, x2_a, _ = box_a
        x1_b, _, x2_b, _ = box_b

        overlap_left = max(x1_a, x1_b)
        overlap_right = min(x2_a, x2_b)
        overlap_w = max(0, overlap_right - overlap_left)

        min_w = min(x2_a - x1_a, x2_b - x1_b)
        if min_w <= 0:
            return 0
        return overlap_w / min_w

    @staticmethod
    def _vertical_distance(box_a, box_b):
        """
        Vertical gap between bottom of box_a and top of box_b (or vice versa).
        Returns 0 if they overlap vertically.
        """
        _, y1_a, _, y2_a = box_a
        _, y1_b, _, y2_b = box_b
        if y2_a < y1_b:
            return y1_b - y2_a
        if y2_b < y1_a:
            return y1_a - y2_b
        return 0  # They overlap vertically

    # -------------------------------------------------------------------------
    # Core Detection
    # -------------------------------------------------------------------------
    def detect(self, frame):
        """
        Run detection on a single frame.
        Returns: (annotated_frame, stats_dict)
        """
        # --- No model loaded ---
        if self.model is None:
            cv2.putText(frame, "AI DETECTION DISABLED", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, "Model best.pt not found or load failed", (50, 90),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame, {"total_people": 0, "violations": 0}

        # --- Run YOLO ---
        results = self.model(frame, verbose=False, conf=0.25)
        result = results[0]
        annotated_frame = frame.copy()
        frame_h, frame_w = frame.shape[:2]

        # --- Parse all raw detections ---
        all_detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            if cls_id not in self.CLASS_MAP:
                continue
            if cls_id in self.SKIP_CLASSES:
                continue

            all_detections.append({
                'id': cls_id,
                'conf': conf,
                'box': (x1, y1, x2, y2),
                'label': f"{self.CLASS_MAP[cls_id]} {conf:.2f}",
                'raw_label': self.CLASS_MAP[cls_id]
            })

        # DEBUG: Print what the model actually sees (remove after debugging)
        if all_detections:
            debug_info = [(d['raw_label'], round(d['conf'], 2)) for d in all_detections]
            print(f"[DEBUG] {debug_info}")
        else:
            print("[DEBUG] No detections in this frame.")

        # --- Separate detections by type ---
        people = [d for d in all_detections if d['id'] == self.PERSON_ID]
        helmets = [d for d in all_detections if d['id'] == self.HELMET_ID]
        vests = [d for d in all_detections if d['id'] == self.VEST_ID]
        suits = [d for d in all_detections if d['id'] == self.SUIT_ID]
        body_ppe = vests + suits  # Anything that covers the torso

        # =====================================================================
        # STEP 1: Build worker list
        # A "worker" is either a detected Person, or inferred from PPE clusters
        # =====================================================================
        workers = []  # Each worker: {'box': ..., 'label': ..., 'conf': ..., 'source': 'detected'|'inferred'}

        # Track which PPE items have been claimed by a detected Person
        claimed_helmets = set()
        claimed_body = set()

        # 1a. Use detected Person boxes first
        for person in people:
            workers.append({
                'box': person['box'],
                'label': person['label'],
                'conf': person['conf'],
                'source': 'detected'
            })

        # 1b. For any PPE that doesn't overlap with ANY detected person, create inferred workers
        # Group unclaimed vests/suits with nearby unclaimed helmets
        unclaimed_body = []
        for i, bp in enumerate(body_ppe):
            overlaps_person = False
            for person in people:
                if self._boxes_overlap(bp['box'], person['box']):
                    overlaps_person = True
                    break
            if not overlaps_person:
                unclaimed_body.append((i, bp))

        unclaimed_helmets = []
        for i, h in enumerate(helmets):
            overlaps_person = False
            for person in people:
                if self._boxes_overlap(h['box'], person['box']):
                    overlaps_person = True
                    break
            if not overlaps_person:
                unclaimed_helmets.append((i, h))

        # Match unclaimed helmets to unclaimed body PPE by horizontal alignment
        matched_helmet_indices = set()
        for bi, bp in unclaimed_body:
            best_helmet = None
            best_score = -1

            for hi, h in unclaimed_helmets:
                if hi in matched_helmet_indices:
                    continue
                # Helmet should be horizontally aligned with body PPE
                h_overlap = self._horizontal_overlap_ratio(h['box'], bp['box'])
                if h_overlap < 0.3:
                    continue
                # Helmet should be above or overlapping the body PPE
                v_dist = self._vertical_distance(h['box'], bp['box'])
                helmet_h = h['box'][3] - h['box'][1]
                if v_dist > helmet_h * 2:  # Too far apart vertically
                    continue
                score = h_overlap
                if score > best_score:
                    best_score = score
                    best_helmet = (hi, h)

            # Create inferred worker from this body PPE (+ helmet if found)
            boxes_to_merge = [bp['box']]
            if best_helmet is not None:
                boxes_to_merge.append(best_helmet[1]['box'])
                matched_helmet_indices.add(best_helmet[0])

            merged_box = self._merge_boxes(boxes_to_merge)
            # Expand slightly to be generous
            mx1, my1, mx2, my2 = merged_box
            pad_y = int((my2 - my1) * 0.1)
            pad_x = int((mx2 - mx1) * 0.05)
            merged_box = (
                max(0, mx1 - pad_x),
                max(0, my1 - pad_y),
                min(frame_w - 1, mx2 + pad_x),
                min(frame_h - 1, my2 + pad_y)
            )

            workers.append({
                'box': merged_box,
                'label': f"Person (Inferred) {bp['conf']:.2f}",
                'conf': bp['conf'],
                'source': 'inferred'
            })

        # Also create workers for fully unclaimed helmets (person with helmet but no vest detected)
        for hi, h in unclaimed_helmets:
            if hi in matched_helmet_indices:
                continue
            # Expand helmet box downward to approximate a person
            hx1, hy1, hx2, hy2 = h['box']
            h_height = hy2 - hy1
            person_box = (
                max(0, hx1 - int(h_height * 0.3)),
                hy1,
                min(frame_w - 1, hx2 + int(h_height * 0.3)),
                min(frame_h - 1, hy2 + int(h_height * 4))
            )
            workers.append({
                'box': person_box,
                'label': f"Person (Inferred) {h['conf']:.2f}",
                'conf': h['conf'],
                'source': 'inferred'
            })

        # =====================================================================
        # STEP 2: Check compliance for each worker
        # =====================================================================
        worker_results = []  # (worker, has_helmet, has_vest_or_suit)

        for worker in workers:
            wb = worker['box']

            # Check helmet: does any helmet overlap or sit near the top of this worker?
            has_helmet = False
            for h in helmets:
                if self._boxes_overlap(h['box'], wb):
                    has_helmet = True
                    break
                # Also check if helmet is just barely above the worker box
                if (self._horizontal_overlap_ratio(h['box'], wb) >= 0.3 and
                        self._vertical_distance(h['box'], wb) < (h['box'][3] - h['box'][1])):
                    has_helmet = True
                    break

            # Check vest/suit: does any vest or safety-suit overlap this worker?
            has_body_cover = False
            for bp in body_ppe:
                if self._boxes_overlap(bp['box'], wb):
                    has_body_cover = True
                    break

            worker_results.append((worker, has_helmet, has_body_cover))

        # =====================================================================
        # STEP 3: Draw everything
        # =====================================================================
        total_violations = 0

        for worker, has_helmet, has_body_cover in worker_results:
            x1, y1, x2, y2 = worker['box']

            no_helmet = not has_helmet
            no_vest = not has_body_cover

            if no_helmet and no_vest:
                color = (0, 0, 255)  # Red
                suffix = " [No Helmet & Vest]"
                total_violations += 2
            elif no_helmet:
                color = (0, 0, 255)  # Red
                suffix = " [No Helmet]"
                total_violations += 1
            elif no_vest:
                color = (0, 0, 255)  # Red
                suffix = " [No Vest]"
                total_violations += 1
            else:
                color = (0, 255, 0)  # Green
                suffix = " [Compliant]"

            # Draw person box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, f"{worker['label']}{suffix}",
                        (x1, max(y1 - 10, 15)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Draw all PPE items in cyan (thin) so user can see what was detected
        PPE_DRAW_IDS = {
            self.HELMET_ID, self.VEST_ID, self.SUIT_ID,
            2, 4, 5, 7, 8, 9, 13, 14  # Earmuffs, Face-guard, Face-mask, Tool, Glasses, Gloves, Medical-suit, Shoes
        }
        for det in all_detections:
            if det['id'] not in PPE_DRAW_IDS:
                continue
            x1, y1, x2, y2 = det['box']
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
            cv2.putText(annotated_frame, det['label'], (x1, max(y1 - 5, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        # --- Stats ---
        stats = {
            "total_people": len(workers),
            "violations": total_violations
        }

        return annotated_frame, stats
