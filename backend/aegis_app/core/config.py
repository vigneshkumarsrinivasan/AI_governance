"""
Application Configuration Settings.
Dual-database support: SQLite for instant zero-dependency local dev/tests,
PostgreSQL for production enterprise deployment.
"""

import json
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "AegisAI Governance OS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Deployment environment: development | test | staging | production
    # Controls demo-data seeding, error verbosity, and secret-key enforcement.
    ENVIRONMENT: str = "development"

    # Whether to auto-seed the "Acme Financial Services" demo tenant on startup.
    # Defaults to on for development convenience; must be explicitly enabled
    # (and is refused entirely in production) to avoid shipping a published
    # demo password to a real deployment.
    SEED_DEMO_DATA: bool = True

    # Security & Auth
    SECRET_KEY: str = "aegis-ai-enterprise-production-super-secret-key-change-in-prod-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database configuration
    # Default to sqlite for instant local execution without docker dependency.
    # Override via DATABASE_URL, e.g. postgresql+asyncpg://user:pass@host:5432/aegis
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/aegis_ai.db"

    # Evidence file storage: "local" (filesystem, dev-friendly) or "s3"
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_DIR: str = str(BASE_DIR / "evidence_storage")
    STORAGE_S3_BUCKET: Optional[str] = None
    STORAGE_S3_REGION: str = "us-east-1"
    EVIDENCE_MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024  # 25 MB
    EVIDENCE_DOWNLOAD_TOKEN_TTL_SECONDS: int = 300

    # AI Copilot provider abstraction. Defaults to "rules" (no external LLM call,
    # no data leaves the platform) so the platform never silently sends tenant
    # evidence/compliance data to a third-party model without explicit configuration.
    # Set to "anthropic" or "openai" and provide AI_API_KEY to enable generative answers.
    AI_PROVIDER: str = "rules"
    AI_API_KEY: Optional[str] = None
    AI_MODEL: Optional[str] = None

    # CORS - comma-separated list via env var CORS_ORIGINS, or defaults below.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3050",
        "http://127.0.0.1:3050",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Legal Disclaimer
    LEGAL_DISCLAIMER: str = (
        "This platform provides governance, risk, compliance, cybersecurity and evidence-management "
        "capabilities. It assists organizations in evaluating regulatory and framework readiness. "
        "It does not constitute legal advice, regulatory approval, certification or a guarantee of "
        "compliance. Compliance determinations may require review by qualified legal counsel, an "
        "independent auditor, or a certification body."
    )

    class Config:
        case_sensitive = True
        extra = "allow"
        env_file = ".env"

settings = Settings()

def validate_production_settings() -> None:
    """
    Fail-closed startup guard: refuses to boot with development defaults
    (default secret key, demo seeding) when ENVIRONMENT=production.
    """
    if settings.ENVIRONMENT != "production":
        return

    errors = []
    if settings.SECRET_KEY == Settings.model_fields["SECRET_KEY"].default:
        errors.append(
            "SECRET_KEY is still set to the development default. "
            "Set a unique, random SECRET_KEY via environment variable before running in production."
        )
    if settings.SEED_DEMO_DATA:
        errors.append(
            "SEED_DEMO_DATA must be false in production. The demo tenant ships with a published "
            "password and must never be created in a real customer environment."
        )
    if "sqlite" in settings.DATABASE_URL:
        errors.append(
            "DATABASE_URL points at SQLite. Production deployments must use PostgreSQL "
            "(postgresql+asyncpg://...) for concurrency, backup, and durability guarantees."
        )
    if errors:
        raise RuntimeError(
            "Refusing to start in production mode due to unsafe configuration:\n- "
            + "\n- ".join(errors)
        )
