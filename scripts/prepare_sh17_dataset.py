"""
prepare_sh17_dataset.py
-----------------------
Reorganizes the flat SH17 dataset into standard YOLO folder structure:

  dataset/
  ├── train/
  │   ├── images/
  │   └── labels/
  ├── val/
  │   ├── images/
  │   └── labels/
  └── data.yaml

Run from the SmartFactory root:
    python scripts/prepare_sh17_dataset.py
"""

import os
import shutil

# ─── PATHS ────────────────────────────────────────────────────────────────────
script_dir  = os.path.dirname(os.path.abspath(__file__))
root_dir    = os.path.dirname(script_dir)
dataset_dir = os.path.join(root_dir, "dataset")

src_images  = os.path.join(dataset_dir, "images")
src_labels  = os.path.join(dataset_dir, "labels")
train_txt   = os.path.join(dataset_dir, "train_files.txt")
val_txt     = os.path.join(dataset_dir, "val_files.txt")

# ─── SH17 CLASS NAMES (17 classes) ───────────────────────────────────────────
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

# ─── VALIDATE SOURCES ─────────────────────────────────────────────────────────
for p in [src_images, src_labels, train_txt, val_txt]:
    if not os.path.exists(p):
        print(f"❌ Missing: {p}")
        print("   Make sure you extracted the SH17 dataset into f:\\SmartFactory\\dataset\\")
        exit(1)

# ─── LOAD SPLIT LISTS ─────────────────────────────────────────────────────────
with open(train_txt) as f:
    train_files = [l.strip() for l in f if l.strip()]

with open(val_txt) as f:
    val_files = [l.strip() for l in f if l.strip()]

print(f"Train files: {len(train_files)}")
print(f"Val files:   {len(val_files)}")

# ─── CREATE OUTPUT DIRS ───────────────────────────────────────────────────────
for split in ["train", "val"]:
    os.makedirs(os.path.join(dataset_dir, split, "images"), exist_ok=True)
    os.makedirs(os.path.join(dataset_dir, split, "labels"), exist_ok=True)

# ─── COPY FILES ───────────────────────────────────────────────────────────────
def get_label_name(image_filename):
    """Strip image extension, return .txt label filename."""
    stem = os.path.splitext(image_filename)[0]
    return stem + ".txt"

def copy_split(file_list, split_name):
    copied_img   = 0
    copied_lbl   = 0
    missing_img  = 0
    missing_lbl  = 0

    out_img_dir = os.path.join(dataset_dir, split_name, "images")
    out_lbl_dir = os.path.join(dataset_dir, split_name, "labels")

    for img_file in file_list:
        src_img = os.path.join(src_images, img_file)
        if not os.path.exists(src_img):
            missing_img += 1
            continue

        dst_img = os.path.join(out_img_dir, img_file)
        shutil.copy2(src_img, dst_img)
        copied_img += 1

        lbl_file = get_label_name(img_file)
        src_lbl  = os.path.join(src_labels, lbl_file)
        if os.path.exists(src_lbl):
            dst_lbl = os.path.join(out_lbl_dir, lbl_file)
            shutil.copy2(src_lbl, dst_lbl)
            copied_lbl += 1
        else:
            missing_lbl += 1

    print(f"\n[{split_name}]")
    print(f"  Images copied:  {copied_img}")
    print(f"  Labels copied:  {copied_lbl}")
    if missing_img:
        print(f"  Warning: Images not found: {missing_img}")
    if missing_lbl:
        print(f"  Warning: Labels not found (images without annotations): {missing_lbl}")

print("\nCopying train split...")
copy_split(train_files, "train")

print("\nCopying val split...")
copy_split(val_files, "val")

# ─── WRITE data.yaml ──────────────────────────────────────────────────────────
yaml_path = os.path.join(dataset_dir, "data.yaml")
yaml_content = f"""# SH17 Dataset — PPE Detection (17 classes, 8099 images)
# Prepared by prepare_sh17_dataset.py

path: {dataset_dir.replace(os.sep, "/")}
train: train/images
val:   val/images

nc: {len(SH17_CLASSES)}
names: {SH17_CLASSES}
"""

with open(yaml_path, "w") as f:
    f.write(yaml_content)

print(f"\n✅ data.yaml written to: {yaml_path}")
print("\n" + "─" * 60)
print("✅ Dataset preparation complete!")
print("   You can now run:  python train.py")
print("─" * 60)
