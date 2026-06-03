from insightface.app import FaceAnalysis  
from typing import Any


class FaceDetection:
    def __init__(self, model_name: str = "buffalo_l")-> None:
        self.model = model_name
        self.app = None

    def load_model(self)-> None:
        self.app = FaceAnalysis(name=self.model, allowed_modules=['detection'])
        print("[FaceDetection] model loaded successfully!")


    def init_model(self)-> None:
        if self.app is None:
            raise ValueError("model not loaded. call load_model() first.")
        self.app.prepare(ctx_id=0, det_size=(640, 640))  
        print("[INFO] Model initialized and ready.")

    def detect(self, image: Any)->list[tuple[int,int,int,int]]:
        if self.app is None:
            raise ValueError("model not loaded. call load_model() and init_model() first.")

        faces = self.app.get(image)
        bboxes: list[tuple[int, int, int, int]] = []
        for face in faces:
            x1, y1, x2, y2 = face.bbox.astype(int)
            bboxes.append((x1, y1, x2, y2))
        return bboxes
