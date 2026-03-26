import uuid

from pydantic import BaseModel, ConfigDict


class WebAuthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    access_token: str
    user_id: uuid.UUID
    role: str
    model_config = ConfigDict(frozen=True, from_attributes=True)



