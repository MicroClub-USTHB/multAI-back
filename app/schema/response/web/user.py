from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
<<<<<<< HEAD
from db.generated.models import User
=======
>>>>>>> 8ce7e61 (Add admin user CRUD and block/unblock endpoints)


class AdminUserSchema(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    blocked: bool
    created_at: datetime
    updated_at: datetime
<<<<<<< HEAD


def to_admin_user_schema(user: User) -> AdminUserSchema:
    return AdminUserSchema(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        blocked=user.blocked,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
=======
>>>>>>> 8ce7e61 (Add admin user CRUD and block/unblock endpoints)
