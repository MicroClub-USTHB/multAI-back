from insightface.app import FaceAnalysis  # type: ignore
from typing import Optional
import numpy as np

BBox = tuple[int, int, int, int]

class FaceDetection:
    def __init__(self, model_name: str = "buffalo_l") -> None:
        self.model = model_name
        self.app: Optional[FaceAnalysis] = None

    

    def detect(self, image: np.ndarray) -> list[BBox]:
        if self.app is None:
            raise ValueError("Model not ready. Call prepare() first.")

        faces = self.app.get(image)
        return [(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in [f.bbox for f in faces]]
