import asyncio
import io
import random
import string
import uuid
from typing import Awaitable, Callable, TypeVar
from fastapi import UploadFile
from miniopy_async.commonconfig import CopySource
from miniopy_async.error import S3Error
from miniopy_async.api import Minio

from app.core.config import settings
from app.core.logger import logger
from app.core.utils import check_extension
from app.core.exceptions import AppException
from app.core.constant import (
    DEFAULT_CONTENT_TYPE,
    DOCUMENTS_BUCKET_NAME as CORE_DOCUMENTS_BUCKET_NAME,
    IMAGES_BUCKET_NAME as CORE_IMAGES_BUCKET_NAME,
    WA_SIM_BUCKET_NAME as CORE_WA_SIM_BUCKET_NAME,
)


# Re-export bucket names for compatibility with existing imports.
IMAGES_BUCKET_NAME = CORE_IMAGES_BUCKET_NAME
DOCUMENTS_BUCKET_NAME = CORE_DOCUMENTS_BUCKET_NAME
WA_SIM_BUCKET_NAME = CORE_WA_SIM_BUCKET_NAME

T = TypeVar("T")


async def _with_retries(op_name: str, func: Callable[[], Awaitable[T]]) -> T:
    attempts = max(1, settings.MINIO_RETRY_ATTEMPTS)
    base_delay = settings.MINIO_RETRY_BASE_SECONDS
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchBucket"}:
                raise
            last_exc = exc
        except Exception as exc:
            last_exc = exc

        logger.warning(
            "MinIO %s failed (attempt %s/%s): %s",
            op_name,
            attempt,
            attempts,
            last_exc,
        )
        if attempt < attempts:
            await asyncio.sleep(base_delay * attempt)

    assert last_exc is not None
    raise last_exc

async def init_minio_client(
    minio_host: str, minio_port: int, minio_root_user: str, minio_root_password: str
) -> None:
    """Initialize MinIO client and ensure buckets exist."""
    Bucket.client = Minio(
        f"{minio_host}:{minio_port}",
        access_key=minio_root_user,
        secret_key=minio_root_password,
        secure=False,
    )

    for bucket_name in [IMAGES_BUCKET_NAME, DOCUMENTS_BUCKET_NAME, WA_SIM_BUCKET_NAME]:
        async def _ensure_bucket() -> None:
            if not await Bucket.client.bucket_exists(bucket_name):
                await Bucket.client.make_bucket(bucket_name)

        await _with_retries("ensure_bucket", _ensure_bucket)


class Bucket:
    """Bucket helper with retry-aware operations."""
    bucket_name: str
    file_prefix: str
    client: Minio

    def __init__(self, bucket_name: str, file_prefix: str):
        self.bucket_name = bucket_name
        self.file_prefix = file_prefix

    def _object_path(self, object_name: str) -> str:
        if self.file_prefix:
            return f"{self.file_prefix}/{object_name}"
        return object_name

    async def put(self, file: UploadFile, object_name: str | None = None) -> str:
        if object_name is None:
            object_name = str(uuid.uuid4())

        if file.content_type is None:
            file.content_type = DEFAULT_CONTENT_TYPE

        if file.filename is None:
            file.filename = object_name

        attempts = max(1, settings.MINIO_RETRY_ATTEMPTS)
        base_delay = settings.MINIO_RETRY_BASE_SECONDS
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                if hasattr(file.file, "seek"):
                    file.file.seek(0)
                await self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=self._object_path(object_name),
                    data=file.file,
                    length=-1,
                    part_size=settings.MINIO_PART_SIZE_BYTES,
                    content_type=file.content_type,
                    metadata={
                        "filename": file.filename,
                    },
                )
                return object_name
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "MinIO put failed for %s (attempt %s/%s): %s",
                    object_name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    await asyncio.sleep(base_delay * attempt)

        assert last_exc is not None
        raise last_exc

    async def get(self, object_name: str) -> tuple[bytes, str, str]:
        try:
            res = await _with_retries(
                "get_object",
                lambda: self.client.get_object(
                    bucket_name=self.bucket_name,
                    object_name=self._object_path(object_name),
                ),
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise AppException.not_found("File not found")
            else:
                raise e
        try:
            data = await res.read()
            content_type = (
                res.content_type if res.content_type else DEFAULT_CONTENT_TYPE
            )
            filename = res.headers.get("x-amz-meta-filename", f"{object_name}")
            return (data, filename, content_type)
        finally:
            res.close()

    async def delete(self, object_name: str) -> None:
        await _with_retries(
            "remove_object",
            lambda: self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=self._object_path(object_name),
            ),
        )

    async def put_bytes(
        self,
        *,
        data: bytes,
        object_name: str,
        content_type: str,
        filename: str | None = None,
    ) -> str:
        await _with_retries(
            "put_object_bytes",
            lambda: self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=self._object_path(object_name),
                data=io.BytesIO(data),
                length=len(data),
                part_size=settings.MINIO_PART_SIZE_BYTES,
                content_type=content_type,
                metadata={"filename": filename or object_name},
            ),
        )
        return object_name

    async def copy(self, *, source_object_name: str, target_object_name: str) -> str:
        await _with_retries(
            "copy_object",
            lambda: self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=self._object_path(target_object_name),
                source=CopySource(
                    self.bucket_name,
                    self._object_path(source_object_name),
                ),
            ),
        )
        return target_object_name

image_ext_content_type_map = {
    "apng": ["image/apng"],
    "avif": ["image/avif"],
    "gif": ["image/gif"],
    "jpeg": ["image/jpeg"],
    "jpg": ["image/jpeg"],
    "png": ["image/png", "image/x-citrix-png"],
    "svg": ["image/svg+xml"],
    "webp": ["image/webp"],
    "ico": ["image/x-icon", "image/vnd.microsoft.icon"],
}

class ImageBucket(Bucket):
    def __init__(self, file_prefix: str):
        super().__init__(IMAGES_BUCKET_NAME, file_prefix)

    async def put(self, file: UploadFile, object_name: str | None = None) -> str:
        check_extension(file, image_ext_content_type_map)
        return await super().put(file, object_name)

class DocumentBucket(Bucket):
    def __init__(self, file_prefix: str):
        super().__init__(DOCUMENTS_BUCKET_NAME, file_prefix)

class WaSimBucket(Bucket):
    def __init__(self) -> None:
        super().__init__(WA_SIM_BUCKET_NAME, "")

    async def put(self, file: UploadFile, object_name: str | None = None) -> str:
        if object_name is None:
            object_name = "".join(random.choice(string.digits) for _ in range(16))
        return await super().put(file, object_name)
