from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.deps.cookie_auth import get_current_staff_user
from app.schema.request.staff.face_embeddings import BatchFaceEmbeddingsRequest
from app.schema.response.staff.face_embeddings import BatchFaceEmbeddingEnqueueResponse
from db.generated.models import StaffUser


router = APIRouter(prefix="/batch")


@router.post(
    "/face-embeddings",
    response_model=BatchFaceEmbeddingEnqueueResponse,
    status_code=202,
)
async def batch_face_embeddings(
    req: BatchFaceEmbeddingsRequest,
    current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> BatchFaceEmbeddingEnqueueResponse:
    job = await container.batch_face_embedding_queue_service.enqueue(
        items=req.to_inputs(),
        staff_user_id=current_staff_user.id,
    )
    return BatchFaceEmbeddingEnqueueResponse(
        job_id=job.job_id,
        queued=len(job.items),
        submitted_at=job.submitted_at,
    )
