from insightface.app import FaceAnalysis
import numpy as np


class FaceEmbedding:
    def __init__(self):
        self.model = None

    def load_model(self):
        self.model = FaceAnalysis(name='buffalo_l')

    def init_model(self):
        if self.model is None:
            raise ValueError("Model not loaded")

        self.model.prepare(ctx_id=0, det_size=(640, 640))
    
    def embed(self, image)->list[float]:
        if self.model is None:
            raise ValueError("Model not initialized")

        faces = self.model.get(image)

        if len(faces) == 0:
            return None

        embedding = faces[0].embedding

        return embedding.tolist()