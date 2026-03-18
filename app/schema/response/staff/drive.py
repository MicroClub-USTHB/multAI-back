from datetime import datetime

from pydantic import BaseModel, Field


class GoogleDriveConnectResponse(BaseModel):
    authorization_url: str
    state: str


class GoogleDriveConnectionStatusResponse(BaseModel):
    connected: bool
    google_email: str | None = None
    scopes: list[str] = Field(default_factory=list)
    connected_at: datetime | None = None
    token_expires_at: datetime | None = None


class GoogleDriveCallbackResponse(BaseModel):
    message: str
    google_email: str


class GoogleDriveDisconnectResponse(BaseModel):
    message: str


class GoogleDriveFileItem(BaseModel):
    id: str
    name: str
    mime_type: str | None = Field(default=None, alias="mimeType")
    thumbnail_link: str | None = Field(default=None, alias="thumbnailLink")
    icon_link: str | None = Field(default=None, alias="iconLink")


class GoogleDriveFileListResponse(BaseModel):
    files: list[GoogleDriveFileItem]
    next_page_token: str | None = Field(default=None, alias="nextPageToken")


class GoogleDriveImportFileResult(BaseModel):
    drive_file_id: str
    original_file_name: str
    minio_bucket: str
    minio_object_name: str
    minio_object_path: str


class GoogleDriveImportResponse(BaseModel):
    files: list[GoogleDriveImportFileResult]
