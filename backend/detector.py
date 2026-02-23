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
        Initialize the YOLOv8 model.
        """
        self.model = None
        
        if YOLO is not None:
            print(f"Loading YOLO model from {model_path}...")
            try:
                # ---------------------------------------------------------
                # NOTE: To use the Roboflow model 'orbit-xboi4/safety-sbfwr'
                # Download 'best.pt' and place it in the backend folder.
                # ---------------------------------------------------------
                self.model = YOLO(model_path)
                print("Model loaded successfully.")
                print("Classes:", self.model.names) # Print classes to console
            except Exception as e:
                print(f"Error loading model: {e}")
                print("Trying default yolov8n.pt as fallback...")
                try:
                    self.model = YOLO('yolov8n.pt')
                except:
                    pass
        else:
            print("Running in Safe Mode (No AI). Install 'ultralytics' to fix.")

    def detect(self, frame):
        """
        Run detection on a single frame.
        """
        # --- NO LIBRARY INSTALLED ---
        if self.model is None:
            # Just display a warning on the frame
            cv2.putText(frame, "AI LIBRARIES MISSING", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, "Please install requirements.txt", (50, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame, {"total_people": 0, "violations": 0}
        # -----------------------------

        results = self.model(frame, verbose=False, conf=0.10)
        result = results[0]

        total_people = 0
        violations = 0
        
        # Draw detections
        annotated_frame = result.plot()
        
        # DEBUG: Print detected classes to terminal to verify what the model sees
        if len(result.boxes) > 0:
            print(f"Detections: {[int(b.cls[0]) for b in result.boxes]}")

        
        # Count statistics based on class names
        # We check result.names for the actual class labels
        names = result.names
        # Custom Mapping for Safety Model (Orbit-xboi4)
        # Since the model only returns IDs 0-4, we map them to standard safety classes.
        # This is a best-guess based on standard PPE datasets.
        # Adjust if labels are swapped (e.g. if 0 shows as 'No-Helmet' but is actually 'Helmet').
        CLASS_MAP = {
            0: 'Hardhat',
            1: 'NO-Hardhat',
            2: 'NO-Safety Vest',
            3: 'Person',
            4: 'Safety Vest',
            5: 'Safety Gloves',
            6: 'Safety Boot',
            7: 'Safety Glasses',
            8: 'Mask'
        }

        # Debug: Print what we found to console periodically
        # print(names) 
        
        # Store valid detections to handle conflicts later
        valid_detections = [] # list of (cls_id, conf, box, label, color)
        
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # --- 1. HARDHAT COLOR FILTER ---
            # If detecting "Hardhat" (0), verify it is NOT hair (Black/Brown)
            if cls_id == 0:
                # Extract ROI
                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    # Convert to HSV
                    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                    # Check Brightness (Value)
                    mean_val = np.mean(hsv[:, :, 2])
                    # Hair is usually dark (Value < 60-80). Hardhats (White/Yellow) are bright (>100).
                    # Red/Blue hardhats might be darker but still > hair.
                    
                    print(f"Hardhat Candidate Conf:{conf:.2f} Brightness:{mean_val:.1f}")
                    
                    if mean_val < 70: # Threshold for "Dark Object" (Hair)
                        print("-> Rejected (Too Dark/Hair)")
                        continue
            
            # --- 2. GEOMETRIC & CONFIDENCE FILTERS ---
            if cls_id == 0:
                 # Aspect Ratio Check: Hardhats are "Squarish" or "Wide". 
                 # Human Heads/Faces are "Tall" (Rectangular).
                 # If Height > 1.25 * Width, it's likely a Face/Head, not a Hat.
                 width = x2 - x1
                 height = y2 - y1
                 aspect_ratio = height / width
                 
                 if aspect_ratio > 1.25:
                     print(f"-> Rejected (Too Tall: AR {aspect_ratio:.2f})")
                     continue

                 if conf < 0.80: continue # Strict Confidence for Hardhat
            
            if cls_id in [5, 7, 8]:
                print(f"Small PPE Candidate {cls_id}: {conf:.2f}") # Debug Gloves/Glasses/Masks
                if conf < 0.10: continue # Lenient for Small PPE
            
            # Get Label name
            if cls_id in CLASS_MAP:
                raw_label = CLASS_MAP[cls_id]
            else:
                raw_label = names[cls_id]
                
            label = f"{raw_label} {conf:.2f}"
            
            # Determine Color
            color = (0, 0, 255) if 'no-' in label.lower() else (0, 255, 0)
            if 'person' in label.lower(): color = (255, 255, 0)
            if 'boot' in label.lower(): color = (255, 0, 255) # Magenta for boots
            
            valid_detections.append({
                'id': cls_id,
                'conf': conf,
                'box': (x1, y1, x2, y2),
                'label': label,
                'color': color,
                'raw_label': raw_label.lower()
            })

        # --- 3. CONFLICT RESOLUTION (Vest vs No-Vest) ---
        # If we have conflicting classes overlapping, pick the higher confidence one.
        indices_to_remove = set()
        
        for i in range(len(valid_detections)):
            if i in indices_to_remove: continue
            
            det_a = valid_detections[i]
            box_a = det_a['box']
            label_a = det_a['raw_label']
            
            for j in range(i + 1, len(valid_detections)):
                if j in indices_to_remove: continue
                
                det_b = valid_detections[j]
                box_b = det_b['box']
                label_b = det_b['raw_label']
                
                # Check conflict: Vest vs No-Vest
                conflict = False
                if ('vest' in label_a and 'no-safety vest' in label_b) or \
                   ('vest' in label_b and 'no-safety vest' in label_a):
                     conflict = True
                     
                if conflict:
                    # Calculate IoU (Intersection over Union) or simple overlap
                    # Simple overlap: do the boxes intersect significantly?
                    xA = max(box_a[0], box_b[0])
                    yA = max(box_a[1], box_b[1])
                    xB = min(box_a[2], box_b[2])
                    yB = min(box_a[3], box_b[3])
                    
                    interArea = max(0, xB - xA) * max(0, yB - yA)
                    if interArea > 0: # They overlap
                         # Remove lower confidence
                         if det_a['conf'] >= det_b['conf']:
                             indices_to_remove.add(j)
                             print(f"Resolved Conflict: Kept {label_a}, Removed {label_b}")
                         else:
                             indices_to_remove.add(i)
                             print(f"Resolved Conflict: Kept {label_b}, Removed {label_a}")
                             break # Stop checking i, it's gone
        
        # --- DRAW FINAL DETECTIONS ---
        detected_class_names = []
        
        for i, det in enumerate(valid_detections):
            if i in indices_to_remove: continue
            
            x1, y1, x2, y2 = det['box']
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), det['color'], 2)
            cv2.putText(annotated_frame, det['label'], (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, det['color'], 2)
            
            detected_class_names.append(det['raw_label'])
        
        # --- STATS LOGIC ---
        
        has_person = any('person' in l for l in detected_class_names)
        
        # Check Explicit Violations
        for l in detected_class_names:
            is_violation = False
            if 'no-' in l or 'missing' in l: is_violation = True
            # Unprotected parts checks
            if 'head' in l and 'hardhat' not in l: is_violation = True 
            
            if is_violation:
                # print(f"Explicit Violation: {l}")
                violations += 1
                
        # Check Implicit Violations (Person but missing items)
        # Requirement: Hardhat AND Vest
        has_hardhat = any('hardhat' in l and 'no-' not in l for l in detected_class_names)
        has_vest = any('vest' in l and 'no-' not in l for l in detected_class_names)
        
        if has_person and (not has_hardhat or not has_vest):
             if not has_hardhat and not any('no-hardhat' in l for l in detected_class_names):
                 print("Implicit Violation: Missing Hardhat")
                 violations += 1
                 
             if not has_vest and not any('no-safety vest' in l for l in detected_class_names):
                 print("Implicit Violation: Missing Vest")
                 violations += 1
        
        # Normalize violations (boolean status usually preferred for UI)
        if violations > 0:
             # Ensure at least 1 count
             pass

        # Calculate actual count of people
        total_people = sum(1 for l in detected_class_names if 'person' in l)

        stats = {
            "total_people": total_people,
            "violations": violations
        }

        return annotated_frame, stats
