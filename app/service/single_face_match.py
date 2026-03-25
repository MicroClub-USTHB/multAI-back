from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

import sqlalchemy
import sqlalchemy.ext.asyncio

from app.core.logger import logger
from app.service.face_embedding import FaceEmbeddingService, FaceImagePayload
from app.schema.dto.single_face_match import BBoxPayload, SingleFaceMatchJob
from db.generated import photo_faces as photo_face_queries
from db.generated import models


@dataclass(frozen=True)
class ClosestUserMatch:
    user_id: UUID
    distance: float


PHOTO_EXISTS = """
SELECT 1
FROM photos
WHERE id = :photo_id
"""

GET_CLOSEST_USER = """
SELECT id, (face_embedding <=> :embedding::vector) AS distance
FROM users
WHERE face_embedding IS NOT NULL
ORDER BY distance ASC
LIMIT 1
"""

INSERT_FACE_MATCH = """
INSERT INTO face_matches (photo_face_id, user_id, confidence)
VALUES (:photo_face_id, :user_id, :confidence)
RETURNING id
"""


class SingleFaceMatchService:
    def __init__(
        self,
        *,
        conn: sqlalchemy.ext.asyncio.AsyncConnection,
        face_embedding_service: FaceEmbeddingService,
        photo_face_querier: photo_face_queries.AsyncQuerier,
    ) -> None:
        self.conn = conn
        self.face_embedding_service = face_embedding_service
        self.photo_face_querier = photo_face_querier

    async def process_job(self, job: SingleFaceMatchJob) -> None:
        if job.faces_detected is not None and job.faces_detected != 1:
            logger.info(
                "Skipping photo %s: faces_detected=%s (single-face worker)",
                job.photo_id,
                job.faces_detected,
            )
            return

        if not await self._photo_exists(job.photo_id):
            logger.warning("Photo not found: %s", job.photo_id)
            return

        embedding, bbox = await self._resolve_embedding(job)
        if embedding is None:
            return

        photo_face = await self._upsert_photo_face(
            photo_id=job.photo_id,
            face_index=job.face_index,
            embedding=embedding,
            bbox=bbox,
        )
        if photo_face is None:
            logger.warning("Failed to upsert photo_face for photo %s", job.photo_id)
            return
        await self._commit_best_effort()

        match = await self._find_closest_user(embedding)
        if match is None:
            logger.info("No user embeddings available for matching")
            return

        await self._insert_face_match(
            photo_face_id=photo_face.id,
            user_id=match.user_id,
            confidence=match.distance,
        )
        await self._commit_best_effort()

    async def _photo_exists(self, photo_id: UUID) -> bool:
        row = (await self.conn.execute(
            sqlalchemy.text(PHOTO_EXISTS),
            {"photo_id": photo_id},
        )).first()
        return row is not None

    async def _resolve_embedding(
        self,
        job: SingleFaceMatchJob,
    ) -> tuple[list[float] | None, BBoxPayload | None]:
        try:
            payload = self._load_payload(job)
        except Exception as exc:
            logger.warning("Failed to load image payload for photo %s: %s", job.photo_id, exc)
            return None, None

        try:
            faces = await self.face_embedding_service.detect_faces(payload)
        except Exception as exc:
            logger.warning("Face detection failed for photo %s: %s", job.photo_id, exc)
            return None, None

        if len(faces) != 1:
            logger.info(
                "Skipping photo %s: detected %s faces (single-face worker)",
                job.photo_id,
                len(faces),
            )
            return None, None

        face = faces[0]
        bbox = BBoxPayload(
            x1=float(face.bbox[0]),
            y1=float(face.bbox[1]),
            x2=float(face.bbox[2]),
            y2=float(face.bbox[3]),
        )
        return face.embedding, bbox

    def _load_payload(self, job: SingleFaceMatchJob) -> FaceImagePayload:
        if job.image_ref:
            raise NotImplementedError(
                "MinIO image loading not implemented. TODO: fetch bytes from image_ref."
            )

        raise ValueError("Missing image_ref in event payload")

    async def _upsert_photo_face(
        self,
        *,
        photo_id: UUID,
        face_index: int,
        embedding: list[float],
        bbox: BBoxPayload | None,
    ) -> models.PhotoFace | None:
        embedding_literal = self._vector_literal(embedding)
        bbox_payload = None
        if bbox is not None:
            bbox_payload = json.dumps(
                {"x1": bbox.x1, "y1": bbox.y1, "x2": bbox.x2, "y2": bbox.y2}
            )
        return await self.photo_face_querier.upsert_photo_face(
            photo_id=photo_id,
            face_index=face_index,
            dollar_3=embedding_literal,
            bbox=bbox_payload,
        )

    async def _find_closest_user(
        self,
        embedding: list[float],
    ) -> ClosestUserMatch | None:
        embedding_literal = self._vector_literal(embedding)
        row = (await self.conn.execute(
            sqlalchemy.text(GET_CLOSEST_USER),
            {"embedding": embedding_literal},
        )).first()
        if row is None:
            return None
        return ClosestUserMatch(user_id=row[0], distance=float(row[1]))

    async def _insert_face_match(
        self,
        *,
        photo_face_id: UUID,
        user_id: UUID,
        confidence: float,
    ) -> None:
        await self.conn.execute(
            sqlalchemy.text(INSERT_FACE_MATCH),
            {
                "photo_face_id": photo_face_id,
                "user_id": user_id,
                "confidence": confidence,
            },
        )

    async def _commit_best_effort(self) -> None:
        try:
            await self.conn.commit()
        except Exception:
            pass

    @staticmethod
    def _vector_literal(embedding: list[float]) -> str:
        return "[" + ", ".join(str(x) for x in embedding) + "]"
