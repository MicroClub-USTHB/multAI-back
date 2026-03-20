from insightface.app import FaceAnalysis
from typing import List, Tuple

BBox = Tuple[int, int, int, int]

class FaceDetection:
    def __init__(self, model_name: str = "buffalo_l"):
        self.model = model_name
        self.app = None
    
    def prepare(self):
        self.app = FaceAnalysis(name=self.model, allowed_modules=['detection'])
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        print("[FaceDetection] model loaded and ready!")

    
    def detect(self, image)->List[BBox]:
        if self.app is None:
            raise ValueError("model not loaded. call load_model() and init_model() first.")
       
        faces = self.app.get(image)
        return [(int(x1), int(y1), int(x2), int(y2)) for x1, y1, x2, y2 in [f.bbox for f in faces]]
    
