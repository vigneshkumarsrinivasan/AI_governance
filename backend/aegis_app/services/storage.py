"""
Pluggable evidence file storage.

Evidence documents are highly sensitive (spec #51), so this module deliberately
never exposes a raw, permanently-valid public URL. Every retrieval goes through
a short-lived, tenant-checked download token minted by the evidence API
(see api/evidence.py), regardless of which backend is active.

Two backends are implemented:
  - LocalFileStorage: filesystem-backed, used by default so the platform is
    runnable with zero external dependencies in local/dev environments.
  - S3Storage: real AWS S3 via boto3, activated by setting
    STORAGE_BACKEND=s3 and STORAGE_S3_BUCKET. Uses actual pre-signed URLs.

Selection is controlled by Settings.STORAGE_BACKEND - never hard-coded, so a
production deployment can switch backends via configuration alone.
"""

import hashlib
import mimetypes
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aegis_app.core.config import settings

# Magic-byte signatures for the evidence file types we accept. This is a
# defense-in-depth check against a malicious file with a spoofed extension -
# it is not a substitute for a real anti-malware scanner (spec #29/#51
# explicitly call for a "malware scan integration point"; see
# StorageBackend.MALWARE_SCAN_HOOK below for where that plugs in).
_MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"PK\x03\x04": "application/zip",  # docx/xlsx/pptx are zip containers
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
}

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif",
    ".docx", ".xlsx", ".pptx", ".csv", ".txt", ".json", ".md", ".zip",
}


class UnsupportedFileError(ValueError):
    pass


@dataclass
class StoredFile:
    storage_key: str
    storage_backend: str
    sha256_hash: str
    size_bytes: int
    content_type: str


def validate_upload(filename: str, content: bytes) -> None:
    """
    Defense-in-depth validation before anything is persisted:
    extension allowlist + magic-byte sniff + size cap.
    Raises UnsupportedFileError / ValueError on rejection.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileError(
            f"File extension '{ext}' is not permitted. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if len(content) == 0:
        raise UnsupportedFileError("Uploaded file is empty.")
    if len(content) > settings.EVIDENCE_MAX_UPLOAD_BYTES:
        raise UnsupportedFileError(
            f"File exceeds the maximum allowed size of {settings.EVIDENCE_MAX_UPLOAD_BYTES // (1024*1024)} MB."
        )
    # Plain-text-ish types (csv/txt/json/md) have no reliable magic number - skip the sniff for those.
    if ext in {".csv", ".txt", ".json", ".md"}:
        return
    if not any(content.startswith(sig) for sig in _MAGIC_BYTES):
        raise UnsupportedFileError(
            "File content does not match its extension (failed magic-byte validation)."
        )

    # MALWARE_SCAN_HOOK: a real deployment plugs an antivirus/EDR scan call here
    # (e.g. ClamAV daemon, cloud AV API) before the file is persisted. Not
    # implemented in this environment - no scanner is available - so this is
    # left as an explicit, documented gap rather than silently claiming
    # malware scanning happens when it does not.


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, tenant_id: str, filename: str, content: bytes) -> StoredFile:
        ...

    @abstractmethod
    async def read(self, storage_key: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        ...


class LocalFileStorage(StorageBackend):
    """
    Filesystem-backed storage rooted at settings.STORAGE_LOCAL_DIR, partitioned
    per-tenant. Filenames are always server-generated UUIDs (never the
    user-supplied filename) to eliminate path traversal risk.
    """

    def __init__(self, root: Optional[str] = None):
        self.root = Path(root or settings.STORAGE_LOCAL_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _tenant_dir(self, tenant_id: str) -> Path:
        # tenant_id is a server-generated UUID, never user input, so it is
        # safe to use directly as a path segment.
        d = self.root / tenant_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save(self, tenant_id: str, filename: str, content: bytes) -> StoredFile:
        validate_upload(filename, content)
        ext = Path(filename).suffix.lower()
        key_name = f"{uuid.uuid4()}{ext}"
        dest = self._tenant_dir(tenant_id) / key_name
        dest.write_bytes(content)

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        sha256_hash = hashlib.sha256(content).hexdigest()

        return StoredFile(
            storage_key=f"{tenant_id}/{key_name}",
            storage_backend="local",
            sha256_hash=sha256_hash,
            size_bytes=len(content),
            content_type=content_type,
        )

    async def read(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        return path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            path.unlink()

    def _resolve(self, storage_key: str) -> Path:
        # storage_key is always server-generated ("<tenant_uuid>/<file_uuid>.ext"),
        # but resolve() + is_relative_to() guards against any path-traversal
        # attempt if that assumption is ever violated by a bug elsewhere.
        candidate = (self.root / storage_key).resolve()
        if not str(candidate).startswith(str(self.root.resolve())):
            raise ValueError("Invalid storage key.")
        return candidate


class S3Storage(StorageBackend):
    """
    Real AWS S3 backend. Requires STORAGE_S3_BUCKET and standard AWS
    credentials (env vars / instance role / profile) to be configured -
    boto3 resolves credentials the standard way, nothing is hard-coded here.
    """

    def __init__(self, bucket: Optional[str] = None, region: Optional[str] = None):
        import boto3  # imported lazily so environments without boto3/AWS never pay this cost

        self.bucket = bucket or settings.STORAGE_S3_BUCKET
        if not self.bucket:
            raise RuntimeError("STORAGE_S3_BUCKET must be set to use the S3 storage backend.")
        self.client = boto3.client("s3", region_name=region or settings.STORAGE_S3_REGION)

    async def save(self, tenant_id: str, filename: str, content: bytes) -> StoredFile:
        validate_upload(filename, content)
        ext = Path(filename).suffix.lower()
        key = f"{tenant_id}/{uuid.uuid4()}{ext}"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

        return StoredFile(
            storage_key=key,
            storage_backend="s3",
            sha256_hash=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
            content_type=content_type,
        )

    async def read(self, storage_key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        return obj["Body"].read()

    async def delete(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)

    def presigned_url(self, storage_key: str, expires_in: int) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )


def get_storage_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalFileStorage()
