import os
import shutil
import random

dataset_dir = r"f:\SmartFactory\dataset"
val_img_dir = os.path.join(dataset_dir, "val", "images")
val_lbl_dir = os.path.join(dataset_dir, "val", "labels")

test_img_dir = os.path.join(dataset_dir, "test", "images")
test_lbl_dir = os.path.join(dataset_dir, "test", "labels")

# Create test directories
os.makedirs(test_img_dir, exist_ok=True)
os.makedirs(test_lbl_dir, exist_ok=True)

# List all validation images
val_images = [f for f in os.listdir(val_img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
total_val = len(val_images)

# We will take 50% of the validation set for the test set
num_test = total_val // 2

print(f"Total Validation Images: {total_val}")
print(f"Moving {num_test} images (50%) to the test set...")

# Set seed for reproducibility
random.seed(42)
test_candidates = random.sample(val_images, num_test)

moved_count = 0
for img_file in test_candidates:
    # Source paths
    src_img = os.path.join(val_img_dir, img_file)
    stem = os.path.splitext(img_file)[0]
    lbl_file = stem + ".txt"
    src_lbl = os.path.join(val_lbl_dir, lbl_file)

    # Destination paths
    dst_img = os.path.join(test_img_dir, img_file)
    dst_lbl = os.path.join(test_lbl_dir, lbl_file)

    # Move image
    if os.path.exists(src_img):
        shutil.move(src_img, dst_img)
        
        # Move label if exists
        if os.path.exists(src_lbl):
            shutil.move(src_lbl, dst_lbl)
        
        moved_count += 1

print(f"Successfully moved {moved_count} images and their labels to {test_img_dir}")

# Update data.yaml
yaml_path = os.path.join(dataset_dir, "data.yaml")

SH17_CLASSES = [
    'Person', 'Ear', 'Earmuffs', 'Face', 'Face-guard', 'Face-mask', 'Foot', 
    'Tool', 'Glasses', 'Gloves', 'Helmet', 'Hands', 'Head', 'Medical-suit', 
    'Shoes', 'Safety-suit', 'Safety-vest'
]

yaml_content = f"""# SH17 Dataset — PPE Detection (17 classes, 8099 images)
# Split: 80% Train, 10% Val, 10% Test

path: f:/SmartFactory/dataset
train: train/images
val:   val/images
test:  test/images

nc: {len(SH17_CLASSES)}
names: {SH17_CLASSES}
"""

with open(yaml_path, "w") as f:
    f.write(yaml_content)

print(f"Updated data.yaml at {yaml_path}")
