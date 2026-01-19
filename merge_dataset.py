import os
import shutil
import yaml
from glob import glob
from tqdm import tqdm

# --- CONFIGURATION ---
TARGET_DIR = r"C:\Users\anasf\Documents\SmartFactory\dataset"

# NEW 9-CLASS SCHEMA:
# 0: Hardhat
# 1: NO-Hardhat
# 2: NO-Safety Vest
# 3: Person
# 4: Safety Vest
# 5: Safety Gloves   <-- Split
# 6: Safety Boot
# 7: Safety Glasses  <-- New
# 8: Mask            <-- New

SOURCES = [
    {
        "path": r"C:\Users\anasf\Downloads\Safety.v2i.yolov8",
        # Source IDs:
        # 0:Boots, 2:Glass, 3:Glove, 4:Helmet, 5:Mask, 10:No-Helmet, 12:No-Vest, 13:Person, 14:Vest
        "map": {
            0: 6,   # Boots -> Boot
            2: 7,   # Glass -> Glasses (NEW ID 7)
            3: 5,   # Glove -> Gloves (ID 5)
            4: 0,   # Helmet -> Hardhat
            5: 8,   # Mask -> Mask (NEW ID 8)
            10: 1,  # No-Helmet -> NO-Hardhat
            12: 2,  # No-Vest -> NO-Safety Vest
            13: 3,  # Person -> Person
            14: 4   # Vest -> Safety Vest
        }
    },
    {
        "path": r"C:\Users\anasf\Downloads\SafetyHazardDetection.v2i.yolov8",
        # Source IDs:
        # 0:boots, 1:gloves, 2:goggles, 3:helmet, 7:no-helmet, 8:no-vest, 9:vest
        "map": {
            0: 6,  # boots -> Boot
            1: 5,  # gloves -> Gloves (ID 5)
            2: 7,  # goggles -> Glasses (NEW ID 7)
            3: 0,  # helmet -> Hardhat
            7: 1,  # no-helmet -> NO-Hardhat
            8: 2,  # no-vest -> NO-Safety Vest
            9: 4   # vest -> Safety Vest
        }
    }
]

def clean_legacy_labels():
    """
    The original dataset used ID 5 for 'Combined'.
    Now ID 5 is 'Gloves'.
    We must remove ID 5 from OLD files so they don't pollute the 'Gloves' class 
    with Glasses/Masks that are mislabeled.
    """
    print("Sanitizing Legacy Data (Removing old ID 5)...")
    for split in ['train', 'valid', 'test']:
        lbl_dir = os.path.join(TARGET_DIR, split, 'labels')
        if not os.path.exists(lbl_dir): continue
        
        for lbl_file in os.listdir(lbl_dir):
            # Skip files we are about to re-generate (starts with new_)
            # But wait, we are about to delete 'new_' files next.
            # So 'legacy' files are ones NOT starting with 'new_'.
            if lbl_file.startswith("new_"): continue
            
            path = os.path.join(lbl_dir, lbl_file)
            with open(path, 'r') as f:
                lines = f.readlines()
            
            kept_lines = []
            modified = False
            for line in lines:
                parts = line.split()
                if not parts: continue
                cls_id = int(parts[0])
                if cls_id == 5:
                    modified = True # Dropping ID 5 (Combined)
                else:
                    kept_lines.append(line)
            
            if modified:
                with open(path, 'w') as f:
                    f.writelines(kept_lines)
    print("Legacy sanitization complete.")

def merge_datasets():
    print(f"Target Dataset: {TARGET_DIR}")
    
    # 1. Clean previous merge ("new_*" files) to strictly avoid duplicates
    print("Cleaning up previous merge artifacts...")
    for split in ['train', 'valid', 'test']:
        for sub in ['images', 'labels']:
            d = os.path.join(TARGET_DIR, split, sub)
            if os.path.exists(d):
                files = glob(os.path.join(d, "new_*"))
                for f in files:
                    os.remove(f)
                    
    # 2. Sanitize Legacy Data
    clean_legacy_labels()

    # 3. Merge New Data
    global_img_count = 0

    for source in SOURCES:
        src_path = source['path']
        class_map = source['map']
        
        print(f"\nProcessing Source: {src_path}")
        if not os.path.exists(src_path):
            print(f"Skipping (Not Found): {src_path}")
            continue

        for split in ['train', 'valid', 'test']:
            src_split_dir = os.path.join(src_path, split)
            if split == 'valid' and not os.path.exists(src_split_dir):
                src_split_dir = os.path.join(src_path, 'val')
            
            if not os.path.exists(src_split_dir):
                continue
                
            print(f"  Merging '{split}' set...")
            
            src_images = glob(os.path.join(src_split_dir, 'images', '*.*'))
            
            for img_path in tqdm(src_images):
                filename = os.path.basename(img_path)
                new_filename = f"new_{global_img_count}_{filename}"
                
                target_img_path = os.path.join(TARGET_DIR, split, 'images', new_filename)
                shutil.copy2(img_path, target_img_path)
                
                label_name = os.path.splitext(filename)[0] + '.txt'
                src_label_path = os.path.join(src_split_dir, 'labels', label_name)
                target_label_path = os.path.join(TARGET_DIR, split, 'labels', os.path.splitext(new_filename)[0] + '.txt')
                
                new_lines = []
                if os.path.exists(src_label_path):
                    with open(src_label_path, 'r') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        parts = line.strip().split()
                        if not parts: continue
                        
                        cls_id = int(parts[0])
                        
                        if cls_id in class_map:
                            new_id = class_map[cls_id]
                            new_line = f"{new_id} {' '.join(parts[1:])}\n"
                            new_lines.append(new_line)
                    
                    if new_lines:
                        with open(target_label_path, 'w') as f:
                            f.writelines(new_lines)
                    else:
                        open(target_label_path, 'w').close() 
                else:
                    open(target_label_path, 'w').close()
                
                global_img_count += 1
                
    # 4. UPDATE data.yaml
    yaml_path = os.path.join(TARGET_DIR, 'data.yaml')
    new_config = {
        'train': '../train/images',
        'val': '../valid/images',
        'test': '../test/images',
        'nc': 9,
        'names': ['Hardhat', 'NO-Hardhat', 'NO-Safety Vest', 'Person', 'Safety Vest', 'Safety Gloves', 'Safety Boot', 'Safety Glasses', 'Mask']
    }
    
    with open(yaml_path, 'w') as f:
        yaml.safe_dump(new_config, f)

    print("\nMerge Complete!")
    print(f"Total processed images: {global_img_count}")
    print("Schema updated to 9 classes. Ready to train.")

if __name__ == "__main__":
    merge_datasets()
