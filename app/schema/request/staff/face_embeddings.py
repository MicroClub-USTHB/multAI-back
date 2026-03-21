from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.service.batch_face_embedding import BatchImageInput


MAX_BATCH_SIZE = 200


class BatchFaceEmbeddingItemRequest(BaseModel):
    photo_id: UUID
    source_type: Literal["drive", "minio", "local"]
    source: str = Field(min_length=1, max_length=2048)

    def to_input(self) -> BatchImageInput:
        return BatchImageInput(
            photo_id=self.photo_id,
            source_type=self.source_type,
            source=self.source,
        )


class BatchFaceEmbeddingsRequest(BaseModel):
    items: list[BatchFaceEmbeddingItemRequest] = Field(
        min_length=1,
        max_length=MAX_BATCH_SIZE,
    )

    def to_inputs(self) -> list[BatchImageInput]:
        return [item.to_input() for item in self.items]
