from __future__ import annotations

from collections.abc import Sequence
import json
from uuid import UUID

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logger import logger
from app.infra.nats import NatsClient, NatsSubjects
from app.schema.dto.face_embeddings import (
    BatchFaceEmbeddingItem,
    BatchFaceEmbeddingJob,
)


class BatchFaceEmbeddingQueueService:
    def __init__(self) -> None:
        self.stream_name = settings.NATS_FACE_EMBEDDING_STREAM

    async def enqueue(
        self,
        *,
        items: Sequence[BatchFaceEmbeddingItem],
        staff_user_id: UUID,
    ) -> BatchFaceEmbeddingJob:
        job = BatchFaceEmbeddingJob(
            staff_user_id=staff_user_id,
            items=list(items),
        )

        payload = job.model_dump(mode="json")
        try:
            await NatsClient.js_publish(
                subject=NatsSubjects.BATCH_FACE_EMBEDDINGS_REQUESTED,
                message=json.dumps(payload).encode("utf-8"),
                stream_name=self.stream_name,
            )
        except Exception as exc:
            logger.warning("Failed to enqueue batch face embedding job: %s", exc)
            raise AppException.internal_error("Failed to enqueue batch face embedding job") from exc

        return job
