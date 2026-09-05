"""
Security utilities: password hashing, JWT generation, and token verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
import bcrypt
from aegis_app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


def create_download_token(evidence_id: str, tenant_id: str) -> str:
    """
    Short-lived, tenant-bound token authorizing exactly one evidence file
    download (spec #51: "short-lived download links, authorization before
    issuance"). Separate from the login access token so a leaked download
    link can't be used to authenticate as the user.
    """
    return create_access_token(
        data={"purpose": "evidence_download", "evidence_id": evidence_id, "tenant_id": tenant_id},
        expires_delta=timedelta(seconds=settings.EVIDENCE_DOWNLOAD_TOKEN_TTL_SECONDS),
    )


def decode_download_token(token: str, evidence_id: str, tenant_id: str) -> bool:
    payload = decode_access_token(token)
    if not payload or payload.get("purpose") != "evidence_download":
        return False
    return payload.get("evidence_id") == evidence_id and payload.get("tenant_id") == tenant_id
