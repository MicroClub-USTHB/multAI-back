from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GoogleDriveConnectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    authorization_url: str
    state: str


class GoogleDriveConnectionStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connected: bool
    google_email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    token_expires_at: datetime | None = None


class GoogleDriveCallbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    google_email: str


class GoogleDriveDisconnectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
