import sys
sys.path.insert(0, r"C:\Users\Lenovo\OneDrive\Desktop\MultiAI\multAI-back")


import asyncio
from app.service.face_embedding import FaceEmbeddingService, FaceImagePayload

image_path = r"C:\Users\Lenovo\OneDrive\Desktop\MultiAI\multAI-back\app\images\image1.png"

with open(image_path, "rb") as f:
    payload: FaceImagePayload = {
        "filename": "image1.png",
        "content_type": "image/jpeg",
        "bytes": f.read()
    }

service = FaceEmbeddingService()

results = asyncio.run(service.compute_event_embedding([payload]))

for filename, embeddings in results.items():
    print(f"{filename}: {len(embeddings)} face(s) found")
    for i, emb in enumerate(embeddings):
       # print(f"  Face {i+1}: embedding length {len(emb)}")
        print(f"  Face {i+1} first 10 values: {emb[:10]}")
