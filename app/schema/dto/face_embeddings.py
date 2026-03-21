from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.service.batch_face_embedding import BatchImageInput


class BatchFaceEmbeddingItem(BaseModel):
    photo_id: UUID
    source_type: Literal["drive", "minio", "local"]
    source: str = Field(min_length=1, max_length=2048)

    def to_input(self) -> BatchImageInput:
        return BatchImageInput(
            photo_id=self.photo_id,
            source_type=self.source_type,
            source=self.source,
        )


class BatchFaceEmbeddingJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    staff_user_id: UUID
    items: list[BatchFaceEmbeddingItem]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_inputs(self) -> list[BatchImageInput]:
        return [item.to_input() for item in self.items]
