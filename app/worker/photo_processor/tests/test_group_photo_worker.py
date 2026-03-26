import sys
from unittest.mock import MagicMock

sys.modules['db.generated.photo_faces'] = MagicMock()
sys.modules['db.generated.photo_approvals'] = MagicMock()
sys.modules['db.generated.user'] = MagicMock()

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from app.worker.photo_processor.main import PhotoGroupProcessWorker
from app.worker.photo_processor.schema.event import PhotoGroupProcessEvent


@pytest.fixture
def worker():
    w = PhotoGroupProcessWorker()
    w._conn = MagicMock()
    w._face_service = MagicMock()
    w._bucket = MagicMock()
    return w


@pytest.fixture
def event():
    return PhotoGroupProcessEvent(
        photo_id=uuid.uuid4(),
        storage_key="photos/test.jpg",
        event_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_no_faces_detected(worker, event):
    """If no faces detected, worker should exit early without creating any records."""
    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg"))
    worker._face_service.compute_event_embedding = AsyncMock(return_value={"test.jpg": []})

    with patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        await worker.process(event)

        mock_face_q.AsyncQuerier.return_value.upsert_photo_face.assert_not_called()
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_not_called()


@pytest.mark.asyncio
async def test_creates_photo_face_and_approval_for_matched_user(worker, event):
    """For each matched user, a PhotoFace and PhotoApproval should be created."""
    face_embedding = [0.1] * 512
    user_id = uuid.uuid4()

    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg"))
    worker._face_service.compute_event_embedding = AsyncMock(
        return_value={"test.jpg": [face_embedding]}
    )

    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.face_embedding = [0.1] * 512  # identical → similarity = 1.0

    mock_photo_face = MagicMock()
    mock_photo_face.id = uuid.uuid4()

    with patch("app.worker.photo_processor.main.user_queries") as mock_user_q, \
         patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        async def mock_list_users_with_embedding():
            yield mock_user

        mock_user_q.AsyncQuerier.return_value.list_users_with_embedding = mock_list_users_with_embedding
        mock_face_q.AsyncQuerier.return_value.upsert_photo_face = AsyncMock(return_value=mock_photo_face)
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval = AsyncMock()

        await worker.process(event)

        mock_face_q.AsyncQuerier.return_value.upsert_photo_face.assert_called_once()
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_called_once()


@pytest.mark.asyncio
async def test_no_approval_for_unmatched_user(worker, event):
    """If similarity is below threshold, no PhotoApproval should be created."""
    face_embedding = [0.1] * 512

    worker._bucket.get = AsyncMock(return_value=(b"imagedata", "test.jpg", "image/jpeg"))
    worker._face_service.compute_event_embedding = AsyncMock(
        return_value={"test.jpg": [face_embedding]}
    )

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.face_embedding = [-0.1] * 512  # opposite → similarity < 0

    mock_photo_face = MagicMock()
    mock_photo_face.id = uuid.uuid4()

    with patch("app.worker.photo_processor.main.user_queries") as mock_user_q, \
         patch("app.worker.photo_processor.main.photo_face_queries") as mock_face_q, \
         patch("app.worker.photo_processor.main.photo_approval_queries") as mock_approval_q:

        async def mock_list_users_with_embedding():
            yield mock_user

        mock_user_q.AsyncQuerier.return_value.list_users_with_embedding = mock_list_users_with_embedding
        mock_face_q.AsyncQuerier.return_value.upsert_photo_face = AsyncMock(return_value=mock_photo_face)
        mock_approval_q.AsyncQuerier.return_value.create_photo_approval = AsyncMock()

        await worker.process(event)

        mock_approval_q.AsyncQuerier.return_value.create_photo_approval.assert_not_called()