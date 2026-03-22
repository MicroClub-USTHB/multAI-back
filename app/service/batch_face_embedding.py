from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
import mimetypes
from pathlib import Path
import uuid
from typing import Literal
from urllib.parse import urlparse, parse_qs

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppException
from app.core.logger import logger
from app.core.constant import DEFAULT_CONTENT_TYPE, DRIVE_ALLOWED_HOSTS, MINIO_URL_PREFIX
from app.infra.google_drive import GoogleDriveClient, GoogleDriveFileDownload
from app.infra.minio import Bucket, IMAGES_BUCKET_NAME
from app.service.face_embedding import DetectedFace, FaceEmbeddingService, FaceImagePayload
from app.service.staff_drive import StaffDriveService
from db.generated import models
from db.generated import photo_faces as photo_face_queries


SourceType = Literal["drive", "minio", "local"]


@dataclass(frozen=True)
class BatchImageInput:
    photo_id: uuid.UUID
    source_type: SourceType
    source: str


@dataclass(frozen=True)
class BatchImageResult:
    photo_id: uuid.UUID
    source_type: SourceType
    source: str
    faces_detected: int
    faces_stored: int
    errors: list[str]


@dataclass(frozen=True)
class BatchFaceEmbeddingSummary:
    total_images: int
    total_faces_detected: int
    total_faces_stored: int
    failures: int
    results: list[BatchImageResult]


class BatchFaceEmbeddingService:
    def __init__(
        self,
        face_embedding_service: FaceEmbeddingService,
        staff_drive_service: StaffDriveService,
        photo_face_querier: photo_face_queries.AsyncQuerier,
    ) -> None:
        self.face_embedding_service = face_embedding_service
        self.staff_drive_service = staff_drive_service
        self.photo_face_querier = photo_face_querier
        self.default_bucket = Bucket(IMAGES_BUCKET_NAME, "")

    async def process_batch(
        self,
        *,
        items: Sequence[BatchImageInput],
        staff_user_id: uuid.UUID | None,
    ) -> BatchFaceEmbeddingSummary:
        if not items:
            raise AppException.bad_request("At least one image is required")

        access_token = await self._get_access_token(items, staff_user_id)
        results: list[BatchImageResult] = []
        total_faces_detected = 0
        total_faces_stored = 0

        for item in items:
            result, faces_detected, faces_stored = await self._process_item(
                item,
                access_token,
            )
            total_faces_detected += faces_detected
            total_faces_stored += faces_stored
            results.append(result)

        failures = sum(1 for result in results if result.errors)
        return BatchFaceEmbeddingSummary(
            total_images=len(items),
            total_faces_detected=total_faces_detected,
            total_faces_stored=total_faces_stored,
            failures=failures,
            results=results,
        )

    async def _get_access_token(
        self,
        items: Sequence[BatchImageInput],
        staff_user_id: uuid.UUID | None,
    ) -> str | None:
        if not any(item.source_type == "drive" for item in items):
            return None
        if staff_user_id is None:
            raise AppException.bad_request("staff_user_id is required for drive sources")
        return await self.staff_drive_service.get_access_token_for_staff_user(
            staff_user_id
        )

    async def _process_item(
        self,
        item: BatchImageInput,
        access_token: str | None,
    ) -> tuple[BatchImageResult, int, int]:
        errors: list[str] = []
        try:
            payload = await self._load_payload(item, access_token)
        except Exception as exc:
            logger.warning(
                "Failed to load image for photo %s (%s): %s",
                item.photo_id,
                item.source,
                exc,
            )
            errors.append(str(exc))
            return self._build_result(item, 0, 0, errors), 0, 0

        try:
            faces = await self.face_embedding_service.detect_faces(payload)
        except Exception as exc:
            logger.warning(
                "Face detection failed for photo %s: %s",
                item.photo_id,
                exc,
            )
            errors.append(str(exc))
            return self._build_result(item, 0, 0, errors), 0, 0

        faces_detected = len(faces)
        if not faces:
            errors.append("No faces detected")

        faces_stored = await self._store_faces(item.photo_id, faces, errors)
        return (
            self._build_result(item, faces_detected, faces_stored, errors),
            faces_detected,
            faces_stored,
        )

    async def _store_faces(
        self,
        photo_id: uuid.UUID,
        faces: Sequence[DetectedFace],
        errors: list[str],
    ) -> int:
        faces_stored = 0
        for face_index, face in enumerate(faces):
            try:
                stored = await self._store_face(
                    photo_id=photo_id,
                    face_index=face_index,
                    face=face,
                )
                if stored is None:
                    raise AppException.internal_error("Failed to store face embedding")
                await self._commit_best_effort()
                faces_stored += 1
            except IntegrityError as exc:
                await self._rollback_best_effort()
                logger.warning(
                    "Failed to store face %s for photo %s: %s",
                    face_index,
                    photo_id,
                    exc,
                )
                errors.append(f"face {face_index}: {exc}")
            except Exception as exc:
                await self._rollback_best_effort()
                logger.warning(
                    "Failed to store face %s for photo %s: %s",
                    face_index,
                    photo_id,
                    exc,
                )
                errors.append(f"face {face_index}: {exc}")
        return faces_stored

    @staticmethod
    def _build_result(
        item: BatchImageInput,
        faces_detected: int,
        faces_stored: int,
        errors: list[str],
    ) -> BatchImageResult:
        return BatchImageResult(
            photo_id=item.photo_id,
            source_type=item.source_type,
            source=item.source,
            faces_detected=faces_detected,
            faces_stored=faces_stored,
            errors=errors,
        )

    async def _load_payload(
        self,
        item: BatchImageInput,
        access_token: str | None,
    ) -> FaceImagePayload:
        if item.source_type == "drive":
            if access_token is None:
                raise AppException.bad_request("Missing Google Drive access token")
            return await self._load_from_drive(item.source, access_token)
        if item.source_type == "minio":
            return await self._load_from_minio(item.source)
        if item.source_type == "local":
            return self._load_from_local(item.source)
        raise AppException.bad_request("Unsupported source type")

    async def _load_from_drive(
        self,
        source: str,
        access_token: str,
    ) -> FaceImagePayload:
        file_id = self._extract_drive_file_id(source)
        downloaded = await GoogleDriveClient.download_file(
            access_token=access_token,
            file_id=file_id,
        )
        return self._payload_from_drive(downloaded)

    async def _load_from_minio(self, source: str) -> FaceImagePayload:
        bucket_name, object_name = self._parse_minio_source(source)
        bucket = self.default_bucket
        if bucket_name != IMAGES_BUCKET_NAME:
            bucket = Bucket(bucket_name, "")
        data, filename, content_type = await bucket.get(object_name)
        return FaceImagePayload(
            filename=filename,
            content_type=content_type,
            bytes=data,
        )

    def _load_from_local(self, source: str) -> FaceImagePayload:
        path = self._normalize_local_path(source)
        if not path.exists() or not path.is_file():
            raise AppException.not_found(f"Local file not found: {path}")
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or DEFAULT_CONTENT_TYPE
        return FaceImagePayload(
            filename=path.name,
            content_type=content_type,
            bytes=data,
        )

    async def _store_face(
        self,
        *,
        photo_id: uuid.UUID,
        face_index: int,
        face: DetectedFace,
    ) -> models.PhotoFace | None:
        bbox_payload = {
            "x1": float(face.bbox[0]),
            "y1": float(face.bbox[1]),
            "x2": float(face.bbox[2]),
            "y2": float(face.bbox[3]),
        }
        embedding_literal = self._vector_literal(face.embedding)
        return await self.photo_face_querier.upsert_photo_face(
            photo_id=photo_id,
            face_index=face_index,
            dollar_3=embedding_literal,
            bbox=json.dumps(bbox_payload),
        )

    async def _rollback_best_effort(self) -> None:
        conn = getattr(self.photo_face_querier, "_conn", None)
        if conn is None:
            return
        try:
            await conn.rollback()
        except Exception:
            pass

    async def _commit_best_effort(self) -> None:
        conn = getattr(self.photo_face_querier, "_conn", None)
        if conn is None:
            return
        try:
            await conn.commit()
        except Exception:
            pass

    @staticmethod
    def _vector_literal(embedding: Sequence[float]) -> str:
        return "[" + ", ".join(str(x) for x in embedding) + "]"

    @staticmethod
    def _payload_from_drive(downloaded: GoogleDriveFileDownload) -> FaceImagePayload:
        metadata = downloaded.metadata
        return FaceImagePayload(
            filename=metadata.name,
            content_type=metadata.mime_type,
            bytes=downloaded.content,
        )

    @staticmethod
    def _extract_drive_file_id(source: str) -> str:
        if source.startswith("http://") or source.startswith("https://"):
            parsed = urlparse(source)
            if not any(host in parsed.netloc for host in DRIVE_ALLOWED_HOSTS):
                raise AppException.bad_request("Invalid Google Drive URL")
            query_id = parse_qs(parsed.query).get("id")
            if query_id and query_id[0]:
                return query_id[0]
            parts = [part for part in parsed.path.split("/") if part]
            if "d" in parts:
                d_index = parts.index("d")
                if d_index + 1 < len(parts):
                    return parts[d_index + 1]
            raise AppException.bad_request("Google Drive file id not found in URL")
        return source

    @staticmethod
    def _parse_minio_source(source: str) -> tuple[str, str]:
        if source.startswith(MINIO_URL_PREFIX):
            raw = source[len(MINIO_URL_PREFIX) :]
            parts = raw.split("/", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise AppException.bad_request("Invalid MinIO source format")
            return parts[0], parts[1]
        return IMAGES_BUCKET_NAME, source

    @staticmethod
    def _normalize_local_path(source: str) -> Path:
        normalized = source
        if source.startswith("file://"):
            normalized = source[len("file://") :]
        return Path(normalized)
