from fastapi import APIRouter, Depends, Query

from app.container import Container, get_container
from app.core.exceptions import AppException
from app.deps.staff_auth import get_current_staff_user
from app.schema.request.staff.drive import GoogleDriveImportRequest
from app.schema.response.staff.drive import (
    GoogleDriveCallbackResponse,
    GoogleDriveConnectResponse,
    GoogleDriveConnectionStatusResponse,
    GoogleDriveDisconnectResponse,
    GoogleDriveFileListResponse,
    GoogleDriveImportResponse,
)
from app.service.staff_drive import SelectedDriveFile
from db.generated.models import StaffUser


router = APIRouter(prefix="/drive")


@router.get("/connect", response_model=GoogleDriveConnectResponse)
async def connect_google_drive(
    current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> GoogleDriveConnectResponse:
    authorization_url, state = await container.staff_drive_service.create_connect_url(
        current_staff_user
    )
    return GoogleDriveConnectResponse(authorization_url=authorization_url, state=state)


@router.get("/callback", response_model=GoogleDriveCallbackResponse)
async def google_drive_callback(
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
    container: Container = Depends(get_container),
) -> GoogleDriveCallbackResponse:
    if error is not None:
        raise AppException.bad_request(f"Google OAuth error: {error}")

    connection = await container.staff_drive_service.handle_callback(code, state)
    return GoogleDriveCallbackResponse(
        message="Google Drive connected successfully",
        google_email=connection.google_email,
    )


@router.get("/status", response_model=GoogleDriveConnectionStatusResponse)
async def google_drive_status(
    current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> GoogleDriveConnectionStatusResponse:
    connection = await container.staff_drive_service.get_status(current_staff_user.id)
    if connection is None:
        return GoogleDriveConnectionStatusResponse(connected=False)

    return GoogleDriveConnectionStatusResponse(
        connected=True,
        google_email=connection.google_email,
        scopes=[scope for scope in connection.scopes.split(" ") if scope],
        connected_at=connection.connected_at,
        token_expires_at=connection.token_expires_at,
    )


@router.get("/files", response_model=GoogleDriveFileListResponse)
async def list_google_drive_files(
    folder_id: str | None = Query(default=None, alias="folderId"),
    page_token: str | None = Query(default=None, alias="pageToken"),
    page_size: int = Query(default=30, alias="pageSize", ge=1, le=1000),
    # current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> GoogleDriveFileListResponse:
    payload = await container.staff_drive_service.list_drive_files(
        staff_user=current_staff_user,
        folder_id=folder_id,
        page_token=page_token,
        page_size=page_size,
    )
    return GoogleDriveFileListResponse(**payload)


@router.post("/disconnect", response_model=GoogleDriveDisconnectResponse)
async def disconnect_google_drive(
    # current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> GoogleDriveDisconnectResponse:
    await container.staff_drive_service.disconnect(current_staff_user.id)
    return GoogleDriveDisconnectResponse(message="Google Drive disconnected successfully")


@router.post("/files/import", response_model=GoogleDriveImportResponse)
async def import_drive_files(
    request: GoogleDriveImportRequest,
    # current_staff_user: StaffUser = Depends(get_current_staff_user),
    container: Container = Depends(get_container),
) -> GoogleDriveImportResponse:
    selections = [
        SelectedDriveFile(
            id=file.id,
            name=file.name,
            mime_type=file.mime_type,
        )
        for file in request.files
    ]

    result = await container.staff_drive_service.import_images_from_drive(
        staff_user=current_staff_user,
        selected_files=selections,
    )
    return GoogleDriveImportResponse(files=result)
