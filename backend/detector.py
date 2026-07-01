import cv2
import numpy as np
import time

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    print("Warning: 'ultralytics' not found. AI features disabled.")

class PPE_Detector:
    def __init__(self, model_path='best.pt'):
        """
        Initialize the YOLOv11 model.
        """
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

    def detect(self, frame):
        """
        Run detection on a single frame.
        """
        # --- NO LIBRARY/MODEL INSTALLED ---
        if self.model is None:
            # Just display a warning on the frame
            cv2.putText(frame, "AI DETECTION DISABLED", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, "Model best.pt not found or load failed", (50, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame, {"total_people": 0, "violations": 0}
        # -----------------------------

        results = self.model(frame, verbose=False, conf=0.30)
        result = results[0]

        # Draw detections on a copy to prevent double drawing
        annotated_frame = frame.copy()
        
        # 17 SH17 Dataset Classes
        CLASS_MAP = {
            0: 'Person', 1: 'Ear', 2: 'Earmuffs', 3: 'Face', 4: 'Face-guard', 
            5: 'Face-mask', 6: 'Foot', 7: 'Tool', 8: 'Glasses', 9: 'Gloves', 
            10: 'Helmet', 11: 'Hands', 12: 'Head', 13: 'Medical-suit', 
            14: 'Shoes', 15: 'Safety-suit', 16: 'Safety-vest'
        }

        # Detections list
        detections = []
        
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Skip if invalid class ID
            if cls_id not in CLASS_MAP:
                continue
                
            # Ignore non-safety classes requested by user (Ear, Face, Foot, Hands)
            if cls_id in [1, 3, 6, 11]:
                continue
                
            raw_label = CLASS_MAP[cls_id]
            
            # Confidence filtering:
            # Require 50% confidence for all classes to avoid floating ghost boxes
            if conf < 0.30:
                continue
                
            detections.append({
                'id': cls_id,
                'conf': conf,
                'box': (x1, y1, x2, y2),
                'label': f"{raw_label} {conf:.2f}",
                'raw_label': raw_label
            })

        # Helper to compute Intersection over Area (IoA): Area(A ∩ B) / Area(A)
        def get_ioa(box_a, box_b):
            x1_a, y1_a, x2_a, y2_a = box_a
            x1_b, y1_b, x2_b, y2_b = box_b
            
            xA = max(x1_a, x1_b)
            yA = max(y1_a, y1_b)
            xB = min(x2_a, x2_b)
            yB = min(y2_a, y2_b)
            
            inter_area = max(0, xB - xA) * max(0, yB - yA)
            area_a = (x2_a - x1_a) * (y2_a - y1_a)
            
            if area_a == 0:
                return 0
            return inter_area / area_a

        # Extract specific classes for spatial overlap violation analysis
        people = [d for d in detections if d['id'] == 0]
        heads = [d for d in detections if d['id'] == 12]
        helmets = [d for d in detections if d['id'] == 10]
        vests = [d for d in detections if d['id'] == 16]

        # Tracking violations
        helmet_violations = set() # indices of heads or people violating helmet rule
        vest_violations = set()   # indices of people violating vest rule

        # 1. Helmet Check (Primary: on detected Heads)
        for idx, head in enumerate(heads):
            # Check if any helmet overlaps this head >= 30%
            has_helmet = False
            for helmet in helmets:
                if get_ioa(head['box'], helmet['box']) >= 0.30:
                    has_helmet = True
                    break
            if not has_helmet:
                helmet_violations.add(('head', idx))

        # 2. Helmet Check (Secondary fallback: on People where no Head is detected nearby)
        for idx, person in enumerate(people):
            # Find if there are any heads inside this person
            has_associated_head = False
            for head in heads:
                if get_ioa(head['box'], person['box']) >= 0.70:
                    has_associated_head = True
                    break
            
            if not has_associated_head:
                # No separate Head detected, check if there's any Helmet overlapping the person box
                # Helmet box should be mostly inside the person box
                has_helmet = False
                for helmet in helmets:
                    if get_ioa(helmet['box'], person['box']) >= 0.70:
                        has_helmet = True
                        break
                if not has_helmet:
                    helmet_violations.add(('person', idx))

        # 3. Vest Check (On all People)
        for idx, person in enumerate(people):
            # Check if any vest is worn by this person (vest should be mostly inside person box)
            has_vest = False
            for vest in vests:
                if get_ioa(vest['box'], person['box']) >= 0.50:
                    has_vest = True
                    break
            if not has_vest:
                vest_violations.add(idx)

        # Draw boxes and labels
        # Colors: Green for compliant PPE/Person, Red for violations, Cyan for neutrals
        for idx, person in enumerate(people):
            x1, y1, x2, y2 = person['box']
            has_person_viol = (idx in vest_violations) or (('person', idx) in helmet_violations)
            color = (0, 0, 255) if has_person_viol else (0, 255, 0)
            
            label_suffix = ""
            if idx in vest_violations and ('person', idx) in helmet_violations:
                label_suffix = " (No Helmet & Vest)"
            elif idx in vest_violations:
                label_suffix = " (No Vest)"
            elif ('person', idx) in helmet_violations:
                label_suffix = " (No Helmet)"
                
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, f"{person['label']}{label_suffix}", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for idx, head in enumerate(heads):
            x1, y1, x2, y2 = head['box']
            has_head_viol = ('head', idx) in helmet_violations
            color = (0, 0, 255) if has_head_viol else (0, 255, 0)
            
            label_suffix = " (No Helmet)" if has_head_viol else ""
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 1)
            cv2.putText(annotated_frame, f"{head['label']}{label_suffix}", (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Draw other compliant objects/neutral items
        # Exclude: Person(0), Ear(1), Face(3), Foot(6), Hands(11), Head(12)
        IGNORE_DRAW_CLASSES = [0, 1, 3, 6, 11, 12]
        other_detections = [d for d in detections if d['id'] not in IGNORE_DRAW_CLASSES]
        for det in other_detections:
            x1, y1, x2, y2 = det['box']
            color = (255, 255, 0) # Cyan for small items or other clothes
            if det['id'] in [10, 16]: # Helmet/Vest
                color = (0, 255, 0)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, det['label'], (x1, y1-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Calculate final stats
        total_people = len(people)
        violations = len(helmet_violations) + len(vest_violations)

        stats = {
            "total_people": total_people,
            "violations": violations
        }

        return annotated_frame, stats
