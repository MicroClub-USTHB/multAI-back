from uuid import UUID

from pydantic import BaseModel

from app.service.batch_face_embedding import BatchFaceEmbeddingSummary, BatchImageResult


class BatchFaceEmbeddingResultSchema(BaseModel):
    photo_id: UUID
    source_type: str
    source: str
    faces_detected: int
    faces_stored: int
    errors: list[str]

    @classmethod
    def from_result(cls, result: BatchImageResult) -> "BatchFaceEmbeddingResultSchema":
        return cls(
            photo_id=result.photo_id,
            source_type=result.source_type,
            source=result.source,
            faces_detected=result.faces_detected,
            faces_stored=result.faces_stored,
            errors=result.errors,
        )


class BatchFaceEmbeddingResponse(BaseModel):
    total_images: int
    total_faces_detected: int
    total_faces_stored: int
    failures: int
    results: list[BatchFaceEmbeddingResultSchema]

    @classmethod
    def from_summary(cls, summary: BatchFaceEmbeddingSummary) -> "BatchFaceEmbeddingResponse":
        return cls(
            total_images=summary.total_images,
            total_faces_detected=summary.total_faces_detected,
            total_faces_stored=summary.total_faces_stored,
            failures=summary.failures,
            results=[
                BatchFaceEmbeddingResultSchema.from_result(result)
                for result in summary.results
            ],
        )
