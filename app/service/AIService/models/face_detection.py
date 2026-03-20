from insightface.app import FaceAnalysis  # type: ignore
from typing import Optional
import numpy as np

BBox = tuple[int, int, int, int]

class FaceDetection:
    def __init__(self, model_name: str = "buffalo_l") -> None:
        self.model = model_name
        self.app: Optional[FaceAnalysis] = None

    def load_model(self) -> None:
        self.app = FaceAnalysis(name=self.model, allowed_modules=['detection'])
        print("[FaceDetection] model loaded successfully!")

    def init_model(self) -> None:
        if self.app is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        self.app.prepare(ctx_id=-1, det_size=(640, 640))  # type: ignore
        print("[FaceDetection] model initialized and ready.")

    def detect(self, image: np.ndarray) -> list[BBox]:
        if self.app is None:
            raise ValueError("Model not ready. Call load_model() first.")

        faces = self.app.get(image)
        return [(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in [f.bbox for f in faces]]
