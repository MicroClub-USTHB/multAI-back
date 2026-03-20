from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence, Tuple, TypedDict

import cv2  # type: ignore
import numpy as np
from insightface.app import FaceAnalysis  # type: ignore[import-untyped]
from app.core.exceptions import AppException

from app.core.exceptions import AppException

BBox = Tuple[int, int, int, int]


class FaceImagePayload(TypedDict):
    filename: str
    content_type: str
    bytes: bytes


@dataclass                                   # ① proper dataclass
class FaceStub:
    bbox: Tuple[float, float, float, float]
    det_score: float
    keypoints: List[Tuple[float, float]]
    gender: Optional[Literal["F", "M"]] = None
    age: Optional[int] = None
    embedding: Optional[np.ndarray] = None


class FaceEmbedding:
    def __init__(
        self,
        model_name: str = "buffalo_l",
        providers: Sequence[str] = ("CPUExecutionProvider",),
        ctx_id: int = -1,
        det_size: Tuple[int, int] = (640, 640),
    ) -> None:
        self.model: FaceAnalysis | None = None
        self.model_name = model_name
        self.providers = providers
        self.ctx_id = ctx_id
        self.det_size = det_size
        self._initialized = False

    # ② single centralized readiness guard
    def _ensure_ready(self) -> None:
        if self.model is None or not self._initialized:
            raise RuntimeError("Model not ready. Call `prepare()` first.")

    def load_model(self) -> None:
        if self.model is not None:
            return
        self.model = FaceAnalysis(
            name=self.model_name, providers=list(self.providers))

    def init_model(self) -> None:
        if self.model is None:
            raise ValueError("Model not loaded. Call `load_model()` first.")
        if self._initialized:
            return
        self.model.prepare(ctx_id=self.ctx_id,
                           det_size=self.det_size)  # type: ignore
        self._initialized = True

    def prepare(self) -> None:
        self.load_model()
        self.init_model()

    # ③ explicit detect() method — fixes the abstraction leak in the service layer
    def detect(self, image_bgr: np.ndarray) -> list[FaceStub]:
        """Run detection + embedding on a BGR image (OpenCV native format)."""
        self._ensure_ready()
        return self.model.get(image_bgr)  # type: ignore

    def embed(self, image_bgr: np.ndarray, bbox_hint: BBox | None = None) -> list[float]:
        """
        Extract embedding of the face closest to bbox_hint (centroid match).
        Falls back to highest-confidence face when bbox_hint is None.
        """
        self._ensure_ready()
        faces: list[FaceStub] = self.model.get(image_bgr)  # type: ignore

        if not faces:
            raise ValueError("No faces detected in image")

        face = (
            self._pick_by_bbox(faces, bbox_hint)
            if bbox_hint is not None
            else max(faces, key=lambda f: f.det_score)  # ④ best score fallback
        )

        if face.embedding is None:
            raise ValueError("No embedding produced for the selected face")

        return face.embedding.flatten().tolist()

    @staticmethod
    def _pick_by_bbox(faces: list[FaceStub], bbox: BBox) -> FaceStub:
        """⑤ Concise centroid matching with np.hypot instead of manual sqrt."""
        tx = (bbox[0] + bbox[2]) / 2
        ty = (bbox[1] + bbox[3]) / 2
        return min(
            faces,
            key=lambda f: np.hypot(
                (f.bbox[0] + f.bbox[2]) / 2 - tx,
                (f.bbox[1] + f.bbox[3]) / 2 - ty,
            ),
        )


class FaceEmbeddingService:
    def __init__(self, face_embedding: FaceEmbedding | None = None) -> None:
        self.face_embedding = face_embedding or FaceEmbedding()
        self.face_embedding.prepare()

    async def compute_average_embedding(
        self,
        payloads: Sequence[FaceImagePayload],
    ) -> list[float]:
        if not payloads:
            raise AppException.bad_request(
                "At least one image is required for enrollment"
            )

        # ⑥ parallel processing — all images are embedded concurrently
        embeddings: list[np.ndarray] = await asyncio.gather(
            *[self._embed_payload(p) for p in payloads]
        )

        averaged = np.mean(np.stack(embeddings, axis=0), axis=0)
        return averaged.astype(float).tolist()

    async def _embed_payload(self, payload: FaceImagePayload) -> np.ndarray:
        """⑦ Extracted per-image logic into its own async method."""
        image = self._decode_image(payload)

        faces: list[FaceStub] = await asyncio.to_thread(
            self.face_embedding.detect, image   # ③ uses detect(), not model.get()
        )

        if not faces:
            raise AppException.bad_request(
                f"No faces detected in image '{payload['filename']}'"
            )

        face = max(faces, key=lambda f: f.det_score)

        if face.embedding is None:
            raise AppException.bad_request(
                f"Failed to generate embedding for '{payload['filename']}'"
            )

        return face.embedding.astype(np.float32)

    @staticmethod
    def _decode_image(payload: FaceImagePayload) -> np.ndarray:
        buffer = np.frombuffer(payload["bytes"], dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise AppException.bad_request(
                f"Cannot decode uploaded image '{payload['filename']}'"
            )
        return image
