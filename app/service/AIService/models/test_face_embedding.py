# test_face_embedding.py
import cv2
import os
from face_detection import FaceDetection
from face_embedding import FaceEmbedding

image_path = r"C:\Users\Lenovo\OneDrive\Desktop\MultiAI\multAI-back\app\images\BNADEM.JPG"
if not os.path.exists(image_path):
    raise ValueError(f"Image not found: {image_path}")

image = cv2.imread(image_path)
if image is None:
    raise ValueError("Failed to read image")

detector = FaceDetection()
detector.load_model()
detector.init_model()
bboxes = detector.detect(image)
print("Faces detected:", len(bboxes))

if len(bboxes) == 0:
    raise ValueError("No faces detected in image")

embedder = FaceEmbedding()
embedder.load_model()
embedder.init_model()
user_embedding = embedder.embed(image, bboxes)

print("Embedding length:", len(user_embedding))
print("first ten values:", user_embedding[:10])

# Save image with rectangle (cast to int in case bbox values are floats)
x1, y1, x2, y2 = [int(v) for v in bboxes[0]]
cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
output_path = r"C:\Users\Lenovo\OneDrive\Desktop\MultiAI\multAI-back\app\images\BNADEM_detected.JPG"
cv2.imwrite(output_path, image)
print("Saved detected image at:", output_path)