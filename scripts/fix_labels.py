import os
import hashlib
from glob import glob
from tqdm import tqdm
import numpy as np

DATASET_DIR = r"C:\Users\anasf\Documents\SmartFactory\dataset"

def get_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def compute_iou(box1, box2):
    # box: [class, x, y, w, h] (normalized)
    # Convert to x1, y1, x2, y2
    def to_coords(b):
        x, y, w, h = b[1], b[2], b[3], b[4]
        x1 = x - w/2
        y1 = y - h/2
        x2 = x + w/2
        y2 = y + h/2
        return x1, y1, x2, y2

    b1_x1, b1_y1, b1_x2, b1_y2 = to_coords(box1)
    b2_x1, b2_y1, b2_x2, b2_y2 = to_coords(box2)
    
    xi1 = max(b1_x1, b2_x1)
    yi1 = max(b1_y1, b2_y1)
    xi2 = min(b1_x2, b2_x2)
    yi2 = min(b1_y2, b2_y2)
    
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    
    b1_area = (b1_x2 - b1_x1) * (b1_y2 - b1_y1)
    b2_area = (b2_x2 - b2_x1) * (b2_y2 - b2_y1)
    
    union_area = b1_area + b2_area - inter_area
    
    if union_area == 0: return 0
    return inter_area / union_area

def clean_labels_in_file(label_path):
    if not os.path.exists(label_path): return
    
    with open(label_path, 'r') as f:
        lines = f.readlines()
        
    boxes = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 5:
            # cls, x, y, w, h
            boxes.append([int(parts[0])] + [float(x) for x in parts[1:]])
            
    # Deduplicate (NMS style)
    keep_indices = []
    
    # Sort by class then size (maybe?) - No, simple greedy NMS
    # Actually, we just want to remove SAME class duplicates.
    
    for i in range(len(boxes)):
        duplicate = False
        for j in keep_indices:
            # Check overlap
            iou = compute_iou(boxes[i], boxes[j])
            if iou > 0.9 and boxes[i][0] == boxes[j][0]: # Same class, exact same spot
                duplicate = True
                break
        
        if not duplicate:
            keep_indices.append(i)
            
    # Write back
    with open(label_path, 'w') as f:
        for i in keep_indices:
            b = boxes[i]
            line = f"{int(b[0])} {b[1]:.6f} {b[2]:.6f} {b[3]:.6f} {b[4]:.6f}\n"
            f.write(line)

def merge_duplicates_logic():
    print(f"Scanning for Image Overlaps in {DATASET_DIR}...")
    
    files_map = {} # hash -> list of {img_path, lbl_path}
    
    for split in ['train', 'valid', 'test']:
        img_dir = os.path.join(DATASET_DIR, split, 'images')
        lbl_dir = os.path.join(DATASET_DIR, split, 'labels')
        
        if not os.path.exists(img_dir): continue
        
        images = glob(os.path.join(img_dir, "*.*"))
        for img_path in tqdm(images, desc=f"Scanning {split}"):
            h = get_hash(img_path)
            
            base = os.path.splitext(os.path.basename(img_path))[0]
            lbl_path = os.path.join(lbl_dir, base + ".txt")
            
            if h not in files_map:
                files_map[h] = []
            files_map[h].append({'img': img_path, 'lbl': lbl_path})
            
    print("Processing Duplicates...")
    merged_count = 0
    
    for h, file_list in tqdm(files_map.items(), desc="Merging"):
        if len(file_list) > 1:
            # Merge all labels into the FIRST file
            master = file_list[0]
            all_lines = set()
            
            # Collect labels from master and all duplicates
            for f_obj in file_list:
                if os.path.exists(f_obj['lbl']):
                    with open(f_obj['lbl'], 'r') as f:
                        for line in f:
                            all_lines.add(line.strip())
                            
            # Write merged labels to Master
            if all_lines:
                with open(master['lbl'], 'w') as f:
                    for l in all_lines:
                        f.write(l + "\n")
            
            # Clean Master (NMS)
            clean_labels_in_file(master['lbl'])
            
            # Delete the others
            for i in range(1, len(file_list)):
                dup = file_list[i]
                if os.path.exists(dup['img']): os.remove(dup['img'])
                if os.path.exists(dup['lbl']): os.remove(dup['lbl'])
                
            merged_count += 1
        else:
            # Even unique files might have internal duplicates (double lines)
            clean_labels_in_file(file_list[0]['lbl'])

    print(f"Merged {merged_count} duplicate sets.")
    print("Dataset is now Unique and Clean.")

if __name__ == "__main__":
    merge_duplicates_logic()
