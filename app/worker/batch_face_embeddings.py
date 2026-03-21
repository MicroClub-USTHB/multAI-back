from __future__ import annotations

import asyncio

from app.container import Container
from app.core.config import settings
from app.core.logger import logger
from app.infra.database import engine
from app.infra.minio import init_minio_client
from app.infra.nats import NatsClient, NatsSubjects
from app.infra.redis import RedisClient
from app.schema.dto.face_embeddings import BatchFaceEmbeddingJob


class BatchFaceEmbeddingWorker:
    def __init__(self, container: Container) -> None:
        self.container = container

    async def handle_message(self, data: bytes) -> None:
        job = BatchFaceEmbeddingJob.model_validate_json(data)
        await self.container.batch_face_embedding_service.process_batch(
            items=job.to_inputs(),
            staff_user_id=job.staff_user_id,
        )


async def run_worker() -> None:
    await init_minio_client(
        minio_host=settings.MINIO_HOST,
        minio_port=settings.MINIO_API_PORT,
        minio_root_user=settings.MINIO_ROOT_USER,
        minio_root_password=settings.MINIO_ROOT_PASSWORD,
    )
    RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
    async with engine.connect() as conn:
        container = Container(conn)
        worker = BatchFaceEmbeddingWorker(container)

        await NatsClient.js_subscribe(
            subject=NatsSubjects.BATCH_FACE_EMBEDDINGS_REQUESTED,
            callback=worker.handle_message,
            stream_name=settings.NATS_FACE_EMBEDDING_STREAM,
            durable_name=settings.NATS_FACE_EMBEDDING_DURABLE,
        )

        logger.info("BatchFaceEmbeddingWorker subscribed; waiting for jobs")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(run_worker())
