import os
import hashlib
from glob import glob
from tqdm import tqdm

DATASET_DIR = r"C:\Users\anasf\Documents\SmartFactory\dataset"

def get_hash(filepath):
    """Returns MD5 hash of file content."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def clean_duplicates():
    print(f"Scanning for duplicates in {DATASET_DIR}...")
    
    duplicates_found = 0
    total_files = 0
    unique_hashes = set()
    
    for split in ['train', 'valid', 'test']:
        img_dir = os.path.join(DATASET_DIR, split, 'images')
        lbl_dir = os.path.join(DATASET_DIR, split, 'labels')
        
        if not os.path.exists(img_dir): continue
        
        # Get all images
        image_files = sorted(glob(os.path.join(img_dir, "*.*")))
        
        for img_path in tqdm(image_files, desc=f"Cleaning {split}"):
            file_hash = get_hash(img_path)
            
            if file_hash in unique_hashes:
                # DUPLICATE FOUND
                duplicates_found += 1
                
                # Delete Image
                os.remove(img_path)
                
                # Delete Label
                base_name = os.path.splitext(os.path.basename(img_path))[0]
                lbl_path = os.path.join(lbl_dir, base_name + ".txt")
                if os.path.exists(lbl_path):
                    os.remove(lbl_path)
                    
                # print(f"Removed Duplicate: {os.path.basename(img_path)}")
            else:
                unique_hashes.add(file_hash)
                total_files += 1

    print(f"\n--- Cleanup Complete ---")
    print(f"Total Unique Images: {total_files}")
    print(f"Duplicates Removed: {duplicates_found}")

if __name__ == "__main__":
    clean_duplicates()
