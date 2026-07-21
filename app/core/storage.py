"""Object storage abstraction: MinIO (S3 API) or local filesystem.

Local-only by design (PRD air-gap): no external CDN. ``STORAGE_PROVIDER`` picks
the backend; callers use ``get_storage().put(key, data)`` / ``.get(key)``.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str: ...
    def get(self, key: str) -> bytes: ...


class LocalStorage:
    def __init__(self, base_path: str) -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = self.base / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._path(key).write_bytes(data)
        return f"local://{key}"

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


class MinioStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        import boto3

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            existing = {b["Name"] for b in self.client.list_buckets().get("Buckets", [])}
            if self.bucket not in existing:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info("Created MinIO bucket %s", self.bucket)
        except Exception as exc:  # noqa: BLE001
            logger.warning("MinIO bucket check failed: %s", exc)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return f"s3://{self.bucket}/{key}"

    def get(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    provider = (settings.STORAGE_PROVIDER or "local").lower()
    if provider == "minio":
        try:
            return MinioStorage(
                endpoint=settings.MINIO_ENDPOINT_URL,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket=settings.MINIO_BUCKET,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("MinIO unavailable (%s) — falling back to local storage", exc)
    return LocalStorage(os.path.abspath(settings.LOCAL_STORAGE_PATH))
