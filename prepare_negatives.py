import os

def create_negative_labels(images_dir):
    """
    Scans a directory of images and creates empty .txt label files 
    for each image found.
    
    In YOLOv8:
    - An image WITH a corresponding .txt file that is EMPTY implies:
      "There are NO objects of interest in this image."
    - This is a 'Negative Sample'.
    - The model learns: "Even though this looks like a head/background, it is NOT a hardhat."
    """
    
    print(f"Scanning for images in: {images_dir}")
    
    if not os.path.exists(images_dir):
        print(f"Error: Directory not found: {images_dir}")
        return

    count = 0
    supported_ext = ['.jpg', '.jpeg', '.png', '.bmp']
    
    # Ensure a 'labels' folder exists? 
    # Usually YOLO structure is images/ and labels/ parallel.
    # But if users dump images in one folder, labels usually go next to them 
    # OR in a parallel labels/ folder.
    # Let's assume standard Roboflow/YOLO structure: ../images/ -> ../labels/
    
    # We will try to find the parallel 'labels' folder
    parent_dir = os.path.dirname(images_dir)
    dir_name = os.path.basename(images_dir)
    
    # Try to find sibling 'labels' folder
    labels_dir = os.path.join(parent_dir, 'labels')
    
    if not os.path.exists(labels_dir):
        # Fallback: Create labels in the same folder if no parallel structure
        print(f"Note: Parallel 'labels' folder not found at {labels_dir}")
        print("Creating labels in the SAME directory as images (Simple Mode).")
        labels_dir = images_dir
    else:
        print(f"Found 'labels' directory: {labels_dir}")

    for filename in os.listdir(images_dir):
        base, ext = os.path.splitext(filename)
        
        if ext.lower() in supported_ext:
            label_file = os.path.join(labels_dir, base + ".txt")
            
            # Create empty file if it doesn't exist
            if not os.path.exists(label_file):
                open(label_file, 'w').close()
                count += 1
                # print(f"Created negative label: {label_file}")
            else:
                # If file exists, check if empty? No, safer to leave existing labels alone 
                # in case user mixed positive/negative samples.
                pass
                
    print(f"Done! Created {count} empty label files.")
    print("These images are now 'Negative Samples'. Re-train your model to apply this fix.")

if __name__ == "__main__":
    # USER: Set this path to your folder of "Background Images" (No PPE, just people/hair)
    target_dir = r"C:\Users\anasf\OneDrive\Desktop\negatives"
    create_negative_labels(target_dir.strip())
