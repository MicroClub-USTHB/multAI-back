from insightface.app import FaceAnalysis
from typing import List, Tuple


class FaceDetection:
    def __init__(self, model_name: str = "buffalo_l"):
        self.model = model_name
        self.app = None
    

    
 
 
    
    def detect(self, image)->list[tuple[int,int,int,int]]:
        if self.app is None:
            raise ValueError("model not loaded. call load_model() and init_model() first.")
       
        faces = self.app.get(image)
        bboxes: List[Tuple[int, int, int, int]] = []
        for face in faces:
            x1, y1, x2, y2 = face.bbox.astype(int)
            bboxes.append((x1, y1, x2, y2))
        return bboxes
    
