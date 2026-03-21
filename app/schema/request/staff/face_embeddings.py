from pydantic import BaseModel, Field

from app.schema.dto.face_embeddings import BatchFaceEmbeddingItem


MAX_BATCH_SIZE = 200


class BatchFaceEmbeddingsRequest(BaseModel):
    items: list[BatchFaceEmbeddingItem] = Field(
        min_length=1,
        max_length=MAX_BATCH_SIZE,
    )

    def to_inputs(self) -> list[BatchFaceEmbeddingItem]:
        return self.items
