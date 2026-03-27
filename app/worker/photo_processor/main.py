import asyncio
import json
from typing import Any

import numpy as np
import sqlalchemy.ext.asyncio

from app.core.logger import logger
from app.infra.database import engine
from app.infra.nats import NatsClient, NatsSubjects
from app.infra.minio import ImageBucket
from app.service.face_embedding import FaceEmbeddingService, FaceImagePayload
from app.worker.photo_processor.schema.event import PhotoGroupProcessEvent
from db.generated import user as user_queries
from db.generated import photo_faces as photo_face_queries
from db.generated import photo_approvals as photo_approval_queries


SIMILARITY_THRESHOLD = 0.5
STREAM_NAME = "photos"
DURABLE_NAME = "photo-group-processor"

def cosine_similarity(a: list[float], b: Any) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))

class PhotoGroupProcessWorker:
    def __init__(self) -> None:
        self._conn: sqlalchemy.ext.asyncio.AsyncConnection | None = None
        self._face_service: FaceEmbeddingService | None = None
        self._bucket: ImageBucket | None = None

    async def start(self) -> None:
        if self._conn is not None:
            return
        self._conn = await engine.connect()
        self._face_service = FaceEmbeddingService()
        self._bucket = ImageBucket(file_prefix="photos")

    async def stop(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            self._face_service = None
            self._bucket = None

    async def process(self, event: PhotoGroupProcessEvent) -> None:
        if self._conn is None or self._face_service is None or self._bucket is None:
            raise RuntimeError("Worker not started")

        # 1. fetch photo from MinIO
        image_bytes, filename, content_type = await self._bucket.get(event.storage_key)

        payload: FaceImagePayload = {
            "filename": filename,
            "content_type": content_type,
            "bytes": image_bytes,
        }

        # 2. get embeddings for all faces in the photo
        results = await self._face_service.compute_event_embedding([payload])
        face_embeddings = results.get(filename, [])

        if not face_embeddings:
            logger.info("No faces detected in photo %s", event.photo_id)
            return

        # 3. fetch all enrolled users
        user_querier = user_queries.AsyncQuerier(self._conn)
        face_querier = photo_face_queries.AsyncQuerier(self._conn)
        approval_querier = photo_approval_queries.AsyncQuerier(self._conn)

        # 4. process each detected face
        for face_index, face_embedding in enumerate(face_embeddings):

            # create PhotoFace record
            photo_face = await face_querier.upsert_photo_face(
              photo_id=event.photo_id,
              face_index=face_index,
              dollar_3=face_embedding,
              bbox=None,
            )

            if photo_face is None:
                logger.warning("Failed to create photo face %s for photo %s", face_index, event.photo_id)
                continue

            # 5. compare against all enrolled users
            async for user in user_querier.list_users_with_embedding():
                if user.face_embedding is None:
                    continue

                similarity = cosine_similarity(face_embedding, user.face_embedding)

                if similarity >= SIMILARITY_THRESHOLD:
                    logger.info(
                        "Face %s matched user %s with similarity %.4f",
                        face_index, user.id, similarity
                    )
                    # 6. create PhotoApproval
                    await approval_querier.create_photo_approval(
                            photo_id=event.photo_id,
                            user_id=user.id,
                            decision=None,
                    )


def _parse_payload(raw_data: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw_data.decode("utf-8"))
        if not isinstance(parsed, dict):
            logger.warning("Photo group process payload must be an object, got %s", type(parsed))
            return None
        return parsed
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.error("Cannot parse photo group process payload: %s", exc)
        return None


async def _handle_event(worker: PhotoGroupProcessWorker, raw_data: bytes) -> None:
    parsed = _parse_payload(raw_data)
    if parsed is None:
        return
    try:
        event = PhotoGroupProcessEvent.model_validate(parsed)
    except Exception as exc:
        logger.warning("Photo group process payload validation failed: %s", exc)
        return
    try:
        await worker.process(event)
    except Exception:
        logger.exception("Failed to process photo group event for photo %s", parsed.get("photo_id"))


async def listen_nats_event(worker: PhotoGroupProcessWorker) -> None:
    await NatsClient.js_subscribe(
        subject=NatsSubjects.PHOTO_GROUP_PROCESS,
        callback=lambda data: _handle_event(worker, data),
        stream_name=STREAM_NAME,
        durable_name=DURABLE_NAME,
    )
    logger.info("Listening for photo group process events on %s", NatsSubjects.PHOTO_GROUP_PROCESS.value)


async def main() -> None:
    worker = PhotoGroupProcessWorker()
    await worker.start()
    await NatsClient.connect()
    try:
        await listen_nats_event(worker)
        await asyncio.Event().wait()
    finally:
        await worker.stop()
        await NatsClient.close()


if __name__ == "__main__":
    asyncio.run(main())
