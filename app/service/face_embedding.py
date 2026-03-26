from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence, Tuple, TypedDict

import cv2 # type: ignore
import numpy as np
from insightface.app import FaceAnalysis  # type: ignore[import-untyped]
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger


class FaceImagePayload(TypedDict):
    filename: str
    content_type: str
    bytes: bytes


class FaceStub:
    bbox: Tuple[float, float, float, float]
    det_score: float
    keypoints: List[Tuple[float, float]]
    gender: Optional[Literal["F", "M"]] = None
    age: Optional[int] = None
    embedding: Optional[np.ndarray] = None


@dataclass(frozen=True)
class DetectedFace:
    embedding: list[float]
    bbox: Tuple[float, float, float, float]


class FaceEmbedding:
    """Thin wrapper around InsightFace to load, initialize, and embed faces."""
    def __init__(
        self,
        model_name: str | None = None,
        providers: Sequence[str] | None = None,
        ctx_id: int | None = None,
        det_size: Tuple[int, int] | None = None,
    ) -> None:
        self.model: FaceAnalysis | None = None
        self.model_name = model_name or settings.FACE_EMBEDDING_MODEL_NAME
        if providers is None:
            providers = tuple(
                p.strip()
                for p in settings.FACE_EMBEDDING_PROVIDERS.split(",")
                if p.strip()
            )
        self.providers = providers
        self.ctx_id = settings.FACE_EMBEDDING_CTX_ID if ctx_id is None else ctx_id
        if det_size is None:
            det_size = (
                settings.FACE_EMBEDDING_DET_WIDTH,
                settings.FACE_EMBEDDING_DET_HEIGHT,
            )
        self.det_size = det_size
        self._initialized = False

    def load_model(self) -> None:
        if self.model is not None:
            return

        self.model = FaceAnalysis(
            name=self.model_name,
            providers=list(self.providers),
        )
        logger.info("FaceEmbedding model loaded")

    def init_model(self) -> None:
        if self.model is None:
            raise ValueError("Model not loaded")

        if self._initialized:
            return

        self.model.prepare(ctx_id=self.ctx_id, det_size=self.det_size)  # type: ignore
        self._initialized = True
        logger.info("FaceEmbedding model initialized")

    def prepare(self) -> None:
        self.load_model()
        self.init_model()


class FaceEmbeddingService:
    """Service layer for face embedding workflows."""
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

        embeddings: list[np.ndarray] = []

        for payload in payloads:
            image = self._decode_image(payload)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Single detection pass — model.get() already returns embeddings
            faces: list[FaceStub] = await asyncio.to_thread( # type: ignore
                self.face_embedding.model.get, image_rgb  # type: ignore
            )

            if not faces:
                raise AppException.bad_request(
                    f"No faces detected in image {payload['filename']}"
                )

            face = faces[0]

            if face.embedding is None:
                raise AppException.bad_request(
                    f"Failed to generate embedding for {payload['filename']}"
                )

            embeddings.append(face.embedding.astype(np.float32))

        stacked = np.stack(embeddings, axis=0)
        averaged = np.mean(stacked, axis=0)

        return averaged.astype(float).tolist()

    async def detect_faces(
        self,
        payload: FaceImagePayload,
    ) -> list[DetectedFace]:
        image = self._decode_image(payload)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        faces: list[FaceStub] = await asyncio.to_thread( # type: ignore
            self.face_embedding.model.get, image_rgb  # type: ignore
        )

        detected: list[DetectedFace] = []
        for face in faces:
            if face.embedding is None:
                continue
            embedding = face.embedding.astype(float).flatten().tolist()
            detected.append(DetectedFace(embedding=embedding, bbox=face.bbox))

        return detected

    def _decode_image(self, payload: FaceImagePayload) -> np.ndarray:

        buffer = np.frombuffer(payload["bytes"], dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

        if image is None:
            raise AppException.bad_request(
                f"Cannot decode uploaded image {payload['filename']}"
            )

        return image
