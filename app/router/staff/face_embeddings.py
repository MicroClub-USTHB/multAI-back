from fastapi import APIRouter, Depends

from app.container import Container, get_container
from app.deps.cookie_auth import get_current_staff_user
from app.schema.request.staff.face_embeddings import BatchFaceEmbeddingsRequest
from app.schema.response.staff.face_embeddings import BatchFaceEmbeddingResponse
from db.generated.models import StaffUser


router = APIRouter(prefix="/batch")


@router.post("/face-embeddings", response_model=BatchFaceEmbeddingResponse)
async def batch_face_embeddings(
    req: BatchFaceEmbeddingsRequest,
    current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> BatchFaceEmbeddingResponse:
    summary = await container.batch_face_embedding_service.process_batch(
        items=req.to_inputs(),
        staff_user_id=current_staff_user.id,
    )
    return BatchFaceEmbeddingResponse.from_summary(summary)
