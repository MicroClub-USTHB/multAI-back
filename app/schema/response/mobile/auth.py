from datetime import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class DeviceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_name: str
    device_type: str
    totp_secret: str | None

class SessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: uuid.UUID
    device_id: uuid.UUID
    last_active: datetime
    expires_at: datetime

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str

class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserSchema
    devices: List[DeviceSchema]
    sessions: Optional[SessionSchema]

class MobileAuthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    session_id: str
    expires_in: int
