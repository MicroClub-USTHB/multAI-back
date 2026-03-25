import dataclasses
import uuid
import sqlalchemy
import sqlalchemy.ext.asyncio
from db.generated import models

CREATE_PHOTO_APPROVAL = """-- name: create_photo_approval \\:one
INSERT INTO photo_approvals (
    photo_id, user_id, decision
) VALUES (
    :p1, :p2, :p3
)
RETURNING id, photo_id, user_id, decision, decided_at
"""
@dataclasses.dataclass()
class CreatePhotoApprovalParams:
    photo_id: uuid.UUID
    user_id: uuid.UUID
    decision: str = "pending"

class AsyncQuerier:
    def __init__(self, conn: sqlalchemy.ext.asyncio.AsyncConnection):
        self._conn = conn

    async def create_photo_approval(self, arg: CreatePhotoApprovalParams) -> models.PhotoApproval | None:
        row = (await self._conn.execute(sqlalchemy.text(CREATE_PHOTO_APPROVAL), {
            "p1": arg.photo_id,
            "p2": arg.user_id,
            "p3": arg.decision,
        })).first()
        if row is None:
            return None
        return models.PhotoApproval(
            id=row[0],
            photo_id=row[1],
            user_id=row[2],
            decision=row[3],
            decided_at=row[4],
        )