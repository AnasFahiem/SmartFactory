#!/usr/bin/env python3
"""
merge_datasets.py
------------------
Filters, maps, and merges a downloaded Roboflow dataset into the SH17 dataset.

How to use:
  1. Download the 'ppe-dataset-original' from Roboflow in YOLO format.
  2. Extract it into your project folder (e.g., f:\\SmartFactory\\ppe-dataset-original).
  3. Run this script:
     python scripts/merge_datasets.py --src f:\\SmartFactory\\ppe-dataset-original
"""

import os
import argparse
import shutil
import yaml

# SH17 class names and IDs for reference
SH17_CLASSES = [
    "Person",        # 0
    "Ear",           # 1
    "Earmuffs",      # 2
    "Face",          # 3
    "Face-guard",    # 4
    "Face-mask",     # 5
    "Foot",          # 6
    "Tool",          # 7
    "Glasses",       # 8
    "Gloves",        # 9
    "Helmet",        # 10
    "Hands",         # 11
    "Head",          # 12
    "Medical-suit",  # 13
    "Shoes",         # 14
    "Safety-suit",   # 15
    "Safety-vest",   # 16
]

# Normalized mapping table (roboflow class name lowercase -> SH17 class ID)
NORM_MAPPING = {
    'coverall': 15,
    'safetysuit': 15,
    'safety-suit': 15,
    'gloves': 9,
    'glove': 9,
    'helmet': 10,
    'hardhat': 10,
    'vest': 16,
    'safetyvest': 16,
    'safety-vest': 16,
    'goggles': 8,
    'glasses': 8,
    'mask': 5,
    'facemask': 5,
    'face-mask': 5,
    'safetyshoe': 14,
    'safety-shoe': 14,
    'shoes': 14,
    'shoe': 14,
    'person': 0,
    'head': 12,
}

def normalize_name(name):
    return name.lower().replace("-", "").replace("_", "").replace(" ", "")

def merge_datasets(src_dir, dst_dir, filter_only_4_classes=True):
    print(f"\n=== Merging dataset from {src_dir} to {dst_dir} ===")
    
    # 1. Read source data.yaml
    src_yaml_path = os.path.join(src_dir, "data.yaml")
    if not os.path.exists(src_yaml_path):
        # Check if the folder contains data.yaml directly
        print(f"[ERROR] Could not find data.yaml at {src_yaml_path}")
        return
        
    with open(src_yaml_path, 'r') as f:
        try:
            src_yaml = yaml.safe_load(f)
        except Exception as e:
            print(f"[ERROR] parsing source data.yaml: {e}")
            return

    src_classes = src_yaml.get("names", [])
    if isinstance(src_classes, dict):
        # Convert dictionary to list if names is a dict
        max_idx = max(src_classes.keys())
        src_classes_list = ["" for _ in range(max_idx + 1)]
        for k, v in src_classes.items():
            src_classes_list[k] = v
        src_classes = src_classes_list

    print(f"Found source classes: {src_classes}")
    
    # Build mapping from source class index to target SH17 class index
    class_mapping = {}
    for idx, name in enumerate(src_classes):
        norm = normalize_name(name)
        if norm in NORM_MAPPING:
            target_id = NORM_MAPPING[norm]
            # If we only want the 4 core classes (9, 10, 15, 16)
            if filter_only_4_classes and target_id not in [9, 10, 15, 16]:
                print(f"[WARN] Skipping mapping for '{name}' -> SH17 ID {target_id} (not in the core 4 classes)")
                continue
            class_mapping[idx] = target_id
            print(f"[OK] Mapping source class '{name}' (ID {idx}) -> SH17 class '{SH17_CLASSES[target_id]}' (ID {target_id})")
        else:
            print(f"[ERROR] No mapping found for source class '{name}' (ID {idx}) - will be filtered out")

    # 2. Iterate through splits (train, val/valid, test)
    splits = [
        ("train", "train"),
        ("valid", "val"),  # Roboflow uses 'valid', SH17 uses 'val'
        ("val", "val"),    # Just in case
        ("test", "test")
    ]
    
    stats = {i: 0 for i in class_mapping.values()}
    total_images_copied = 0
    total_annotations_mapped = 0
    
    for src_split, dst_split in splits:
        src_images_dir = os.path.join(src_dir, src_split, "images")
        src_labels_dir = os.path.join(src_dir, src_split, "labels")
        
        dst_images_dir = os.path.join(dst_dir, dst_split, "images")
        dst_labels_dir = os.path.join(dst_dir, dst_split, "labels")
        
        if not os.path.exists(src_images_dir):
            continue
            
        os.makedirs(dst_images_dir, exist_ok=True)
        os.makedirs(dst_labels_dir, exist_ok=True)
        
        print(f"\nProcessing split: {src_split} -> {dst_split}")
        
        image_files = [f for f in os.listdir(src_images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
        split_images_copied = 0
        
        for img_file in image_files:
            src_img_path = os.path.join(src_images_dir, img_file)
            
            # Formulate label filename
            lbl_file = os.path.splitext(img_file)[0] + ".txt"
            src_lbl_path = os.path.join(src_labels_dir, lbl_file)
            
            # Destination filenames (prefixed to avoid collisions)
            dst_img_name = f"rf_{img_file}"
            dst_lbl_name = f"rf_{lbl_file}"
            dst_img_path = os.path.join(dst_images_dir, dst_img_name)
            dst_lbl_path = os.path.join(dst_labels_dir, dst_lbl_name)
            
            mapped_lines = []
            
            if os.path.exists(src_lbl_path):
                with open(src_lbl_path, 'r') as lf:
                    lines = lf.readlines()
                    
                for line in lines:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    try:
                        cls_idx = int(parts[0])
                        if cls_idx in class_mapping:
                            target_id = class_mapping[cls_idx]
                            parts[0] = str(target_id)
                            mapped_lines.append(" ".join(parts) + "\n")
                            stats[target_id] += 1
                            total_annotations_mapped += 1
                    except ValueError:
                        continue
            
            # Copy image
            shutil.copy2(src_img_path, dst_img_path)
            
            # Write mapped label file (even if empty, to serve as negative background image)
            with open(dst_lbl_path, 'w') as lf:
                lf.writelines(mapped_lines)
                
            split_images_copied += 1
            total_images_copied += 1
            
        print(f"  Copied {split_images_copied} images to {dst_split}")

    print("\n" + "="*40)
    print("--- Merging Complete Summary:")
    print(f"Total Images Added: {total_images_copied}")
    print(f"Total Bounding Boxes Mapped: {total_annotations_mapped}")
    print("Breakdown by Class:")
    for cid, count in stats.items():
        print(f"  - {SH17_CLASSES[cid]} (ID {cid}): {count} boxes")
    print("="*40)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge Roboflow dataset into SH17")
    parser.add_argument("--src", required=True, help="Path to extracted Roboflow dataset directory")
    parser.add_argument("--dst", default="dataset", help="Path to SH17 target dataset directory (default: 'dataset')")
    parser.add_argument("--all-classes", action="store_true", help="Map all matching classes instead of just the core 4 (Helmet, Vest, Safety-suit, Gloves)")
    
    args = parser.parse_args()
    
    # Resolve paths relative to workspace root if they are relative
    src_dir = os.path.abspath(args.src)
    dst_dir = os.path.abspath(args.dst)
    
    filter_only_4 = not args.all_classes
    merge_datasets(src_dir, dst_dir, filter_only_4_classes=filter_only_4)
