import sys
import pytest
import uuid
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

sys.modules['db.generated.user'] = MagicMock()

from app.worker.photo_processor.main import PhotoGroupProcessWorker  # noqa: E402
from app.worker.photo_processor.schema.event import PhotoGroupProcessEvent  # noqa: E402


@pytest.fixture
def worker() -> Generator[PhotoGroupProcessWorker, None, None]:
    from unittest.mock import create_autospec
    from app.infra.minio import ImageBucket
    from app.service.face_embedding import FaceEmbeddingService

    w = PhotoGroupProcessWorker()
    w._conn = MagicMock()
    w._bucket = create_autospec(ImageBucket, instance=True)
    w._face_service = create_autospec(FaceEmbeddingService, instance=True)
    yield w


@pytest.fixture
def event() -> Generator[PhotoGroupProcessEvent, None, None]:
    yield PhotoGroupProcessEvent(
        photo_id=uuid.uuid4(),
        storage_key="photos/test.jpg",
        event_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_no_faces_detected(worker: PhotoGroupProcessWorker, event: PhotoGroupProcessEvent) -> None:
    """If no faces detected, worker should exit early without creating any records."""
    assert worker._bucket is not None
    assert worker._face_service is not None
    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg")) # type: ignore
    worker._face_service.compute_event_embedding = AsyncMock(return_value={"test.jpg": []}) # type: ignore

    with patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        await worker.process(event)

        mock_face_q.AsyncQuerier.return_value.upsert_photo_face.assert_not_called()
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_not_called()


@pytest.mark.asyncio
async def test_creates_photo_face_and_approval_for_matched_user(worker: PhotoGroupProcessWorker, event: PhotoGroupProcessEvent) -> None:
    """For each matched user, a PhotoFace and PhotoApproval should be created."""
    face_embedding = [0.1] * 512
    user_id = uuid.uuid4()

    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg")) # type: ignore
    worker._face_service.compute_event_embedding = AsyncMock( # type: ignore
        return_value={"test.jpg": [face_embedding]}
    ) # type: ignore

    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.face_embedding = [0.1] * 512

    mock_photo_face = MagicMock()
    mock_photo_face.id = uuid.uuid4()

    with patch("app.worker.photo_processor.main.user_queries") as mock_user_q, \
         patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        async def mock_list_users_with_embedding() -> AsyncGenerator[MagicMock, None]:
            yield mock_user

        mock_user_q.AsyncQuerier.return_value.list_users_with_embedding = mock_list_users_with_embedding
        mock_face_q.AsyncQuerier.return_value.upsert_photo_face = AsyncMock(return_value=mock_photo_face)
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval = AsyncMock()

        await worker.process(event)

        mock_face_q.AsyncQuerier.return_value.upsert_photo_face.assert_called_once()
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_called_once()


@pytest.mark.asyncio
async def test_no_approval_for_unmatched_user(worker: PhotoGroupProcessWorker, event: PhotoGroupProcessEvent) -> None:
    """If similarity is below threshold, no PhotoApproval should be created."""
    face_embedding = [0.1] * 512

    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg")) # type: ignore
    worker._face_service.compute_event_embedding = AsyncMock( # type: ignore
        return_value={"test.jpg": [face_embedding]}
    ) # type: ignore

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.face_embedding = [-0.1] * 512

    mock_photo_face = MagicMock()
    mock_photo_face.id = uuid.uuid4()

    with patch("app.worker.photo_processor.main.user_queries") as mock_user_q, \
         patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        async def mock_list_users_with_embedding() -> AsyncGenerator[MagicMock, None]:
            yield mock_user

        mock_user_q.AsyncQuerier.return_value.list_users_with_embedding = mock_list_users_with_embedding
        mock_face_q.AsyncQuerier.return_value.upsert_photo_face = AsyncMock(return_value=mock_photo_face)
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval = AsyncMock()

        await worker.process(event)

        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_not_called()
