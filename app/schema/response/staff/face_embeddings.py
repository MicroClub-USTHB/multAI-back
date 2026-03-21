from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BatchFaceEmbeddingEnqueueResponse(BaseModel):
    job_id: UUID
    queued: int
    submitted_at: datetime
