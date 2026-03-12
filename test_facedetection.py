import cv2
from insightface import FaceDetection
import os

# Folder with images to test
IMAGE_FOLDER = "images"
image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(('.jpg', '.png'))]

# Initialize detector
detector = FaceDetection()
print("[STEP] Loading model...")
detector.load_model()

print("[STEP] Initializing model...")
detector.init_model()

# Process each image
for img_file in image_files:
    print(f"\n[STEP] Processing image: {img_file}")
    img_path = os.path.join(IMAGE_FOLDER, img_file)
    
    # Load image
    image = cv2.imread(img_path)
    print("[STEP] Image loaded.")

    # Detect faces
    print("[STEP] Detecting faces...")
    bboxes = detector.detect(image)
    print(f"[STEP] Detected {len(bboxes)} face(s): {bboxes}")

    # Draw bounding boxes
    for (x1, y1, x2, y2) in bboxes:
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Optional: show each step visually
    cv2.imshow(f"Face Detection - {img_file}", image)
    print("[STEP] Displaying image with bounding boxes. Press any key to continue...")
    cv2.waitKey(0)  # Wait until a key is pressed
    cv2.destroyAllWindows()