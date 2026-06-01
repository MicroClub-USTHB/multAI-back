import cv2
from face_detection import FaceDetection
import os

# Folder with images to test (relative to project root)
IMAGE_FOLDER = "../../../../images"
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

    # Save the image with bounding boxes instead of showing window
    output_filename = f"detected_{img_file}"
    output_path = os.path.join(IMAGE_FOLDER, output_filename)
    cv2.imwrite(output_path, image)
    print(f"[STEP] Saved processed image to: {output_path}")
    print(f"[STEP] Image processed with {len(bboxes)} face(s). Bounding boxes: {bboxes}")

    # Optional: try to show window (will fail gracefully if GUI not available)
    try:
        cv2.imshow(f"Face Detection - {img_file}", image)
        print("[STEP] Press any key in the image window to continue...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error as e:
        print(f"[INFO] GUI display not available: {e}")
        print(f"[INFO] Image saved to {output_path} - open it manually to see results")
