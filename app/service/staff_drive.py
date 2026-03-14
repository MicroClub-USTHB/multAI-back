import base64
import hashlib
import json
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import AppException
from app.infra.google_drive import GoogleDriveClient
from app.infra.minio import ImageBucket
from app.infra.redis import RedisClient
from db.generated import staff_drive_connections as drive_queries
from db.generated import stuff_user as staff_queries
from db.generated.models import StaffDriveConnection, StaffUser


DRIVE_BUCKET_PREFIX = "staff-drive"
TOKEN_REFRESH_MARGIN = timedelta(minutes=5)


@dataclass
class DriveFilePreview:
    id: str
    name: str
    mime_type: str | None
    thumbnail_link: str | None
    icon_link: str | None


@dataclass
class SelectedDriveFile:
    id: str
    name: str
    mime_type: str | None


@dataclass
class DriveImportResult:
    drive_file_id: str
    original_file_name: str
    minio_bucket: str
    minio_object_name: str
    minio_object_path: str


class StaffDriveService:
    STATE_PREFIX = "google_drive_oauth_state:{state}"
    STATE_TTL_SECONDS = 600
    PROVIDER = "google_drive"

    def __init__(
        self,
        staff_user_querier: staff_queries.AsyncQuerier,
        drive_connection_querier: drive_queries.AsyncQuerier,
        redis: RedisClient,
    ):
        self.staff_user_querier = staff_user_querier
        self.drive_connection_querier = drive_connection_querier
        self.redis = redis

    async def create_connect_url(self, staff_user: StaffUser) -> tuple[str, str]:
        state = secrets.token_urlsafe(32)
        await self.redis.set(
            self.STATE_PREFIX.format(state=state),
            json.dumps({"staff_user_id": str(staff_user.id)}),
            expire=self.STATE_TTL_SECONDS,
            nx=True,
        )
        return GoogleDriveClient.build_consent_url(state), state

    async def handle_callback(self, code: str, state: str) -> StaffDriveConnection:
        state_key = self.STATE_PREFIX.format(state=state)
        state_payload = await self.redis.get(state_key)
        if state_payload is None:
            raise AppException.bad_request("OAuth state is missing or expired")

        await self.redis.delete(state_key)

        try:
            staff_user_id = uuid.UUID(json.loads(state_payload)["staff_user_id"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise AppException.bad_request("Invalid OAuth state payload") from exc

        staff_user = await self.staff_user_querier.get_staff_user_by_id(id=staff_user_id)
        if staff_user is None:
            raise AppException.not_found("Staff user not found")

        token = await GoogleDriveClient.exchange_code(code)
        user_info = await GoogleDriveClient.get_user_info(token.access_token)

        encrypted_access_token = self._encrypt(token.access_token)
        encrypted_refresh_token = (
            self._encrypt(token.refresh_token) if token.refresh_token else None
        )

        connection = await self.drive_connection_querier.upsert_staff_drive_connection(
            arg=drive_queries.UpsertStaffDriveConnectionParams(
                staff_user_id=staff_user.id,
                provider=self.PROVIDER,
                google_email=user_info.email,
                google_account_id=user_info.id,
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                token_expires_at=token.expires_at,
                scopes=token.scope,
            )
        )
        if connection is None:
            raise AppException.internal_error("Failed to save Google Drive connection")

        return connection

    async def list_drive_files(
        self,
        staff_user: StaffUser,
        folder_id: str | None,
        page_token: str | None,
        page_size: int = 30,
    ) -> dict[str, object]:
        connection = await self.get_status(staff_user.id)
        if connection is None:
            raise AppException.not_found("Google Drive is not connected")

        access_token, _ = await self._ensure_valid_access_token(connection)
        query = self._build_folder_query(folder_id)
        response = await GoogleDriveClient.list_files(
            access_token=access_token,
            query=query,
            page_size=page_size,
            page_token=page_token,
        )

        raw_files = response.get("files")
        files: list[dict[str, object]] = []
        if isinstance(raw_files, list):
            for entry in raw_files:
                if not isinstance(entry, dict):
                    continue
                file_id = entry.get("id")
                name = entry.get("name")
                if not isinstance(file_id, str) or not file_id:
                    continue
                if not isinstance(name, str) or not name:
                    continue
                preview = DriveFilePreview(
                    id=file_id,
                    name=name,
                    mime_type=self._optional_str(entry, "mimeType"),
                    thumbnail_link=self._optional_str(entry, "thumbnailLink"),
                    icon_link=self._optional_str(entry, "iconLink"),
                )
                files.append(asdict(preview))

        return {
            "files": files,
            "nextPageToken": self._optional_str(response, "nextPageToken"),
        }

    async def import_images_from_drive(
        self,
        staff_user: StaffUser,
        selected_files: list[SelectedDriveFile],
    ) -> list[dict[str, object]]:
        if not selected_files:
            return []

        connection = await self.get_status(staff_user.id)
        if connection is None:
            raise AppException.not_found("Google Drive is not connected")

        access_token, _ = await self._ensure_valid_access_token(connection)
        bucket = ImageBucket(f"{DRIVE_BUCKET_PREFIX}/{staff_user.id}")
        results: list[dict[str, object]] = []

        for selected in selected_files:
            drive_stream = await GoogleDriveClient.download_file(
                access_token=access_token,
                file_id=selected.id,
            )
            object_name = self._generate_object_name(selected.name)
            prefixed_object_name = self._prefixed_object_name(bucket.file_prefix, object_name)
            content_type = selected.mime_type or "application/octet-stream"
            try:
                await bucket.client.put_object(
                    bucket_name=bucket.bucket_name,
                    object_name=prefixed_object_name,
                    data=drive_stream,
                    length=-1,
                    part_size=10 * 1024 * 1024,
                    content_type=content_type,
                    metadata={"filename": selected.name},
                )
            finally:
                drive_stream.close()

            result = DriveImportResult(
                drive_file_id=selected.id,
                original_file_name=selected.name,
                minio_bucket=bucket.bucket_name,
                minio_object_name=object_name,
                minio_object_path=prefixed_object_name,
            )
            results.append(asdict(result))

        return results

    async def get_status(self, staff_user_id: uuid.UUID) -> StaffDriveConnection | None:
        return await self.drive_connection_querier.get_active_staff_drive_connection_by_staff_user_id(
            staff_user_id=staff_user_id,
            provider=self.PROVIDER,
        )

    async def disconnect(self, staff_user_id: uuid.UUID) -> None:
        connection = await self.get_status(staff_user_id)
        if connection is None:
            raise AppException.not_found("No Google Drive connection found")

        await self.drive_connection_querier.revoke_staff_drive_connection_by_staff_user_id(
            staff_user_id=staff_user_id,
            provider=self.PROVIDER,
        )

    def _encrypt(self, raw_value: str) -> str:
        return self._fernet().encrypt(raw_value.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_value: str) -> str:
        try:
            return self._fernet().decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise AppException.internal_error("Stored Google Drive token cannot be decrypted") from exc

    async def _ensure_valid_access_token(
        self,
        connection: StaffDriveConnection,
    ) -> tuple[str, StaffDriveConnection]:
        expires_at = connection.token_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if (
            expires_at is not None
            and expires_at - TOKEN_REFRESH_MARGIN > datetime.now(timezone.utc)
        ):
            return self.decrypt(connection.access_token), connection

        return await self._refresh_connection(tokens=connection)

    async def _refresh_connection(
        self,
        tokens: StaffDriveConnection,
    ) -> tuple[str, StaffDriveConnection]:
        if tokens.refresh_token is None:
            raise AppException.bad_request(
                "Google Drive refresh token is missing; reconnect to continue"
            )

        refresh_token = self.decrypt(tokens.refresh_token)
        fresh_token = await GoogleDriveClient.refresh_token(refresh_token)
        encrypted_access_token = self._encrypt(fresh_token.access_token)
        encrypted_refresh_token = (
            self._encrypt(fresh_token.refresh_token)
            if fresh_token.refresh_token
            else tokens.refresh_token
        )

        updated_connection = (
            await self.drive_connection_querier.update_staff_drive_connection_tokens(
                arg=drive_queries.UpdateStaffDriveConnectionTokensParams(
                    staff_user_id=tokens.staff_user_id,
                    provider=self.PROVIDER,
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token,
                    token_expires_at=fresh_token.expires_at,
                )
            )
        )
        if updated_connection is None:
            raise AppException.internal_error(
                "Unable to refresh Google Drive connection tokens"
            )

        return self.decrypt(encrypted_access_token), updated_connection

    @staticmethod
    def _optional_str(data: dict[str, object], key: str) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        return value

    @staticmethod
    def _build_folder_query(folder_id: str | None) -> str:
        if folder_id:
            return f"'{folder_id}' in parents and trashed=false"
        return "'root' in parents and trashed=false"

    @staticmethod
    def _generate_object_name(filename: str) -> str:
        if "." in filename:
            suffix = filename[filename.rfind(".") :]
        else:
            suffix = ""
        return f"{uuid.uuid4()}{suffix}"

    @staticmethod
    def _prefixed_object_name(prefix: str, object_name: str) -> str:
        if prefix:
            return f"{prefix}/{object_name}"
        return object_name

    def _fernet(self) -> Fernet:
        digest = hashlib.sha256(settings.encryption_key.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
