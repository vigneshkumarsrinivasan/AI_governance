"""Synchronous DB session for the ingestion pipeline / CLI.

The web app uses async SQLAlchemy; batch ingestion is simpler and safer as a
synchronous script, so we derive a sync engine from the same DATABASE_URL.
"""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aegis_app.core.config import settings
from aegis_app.core.database import Base
from aegis_app.models import models, regulatory  # noqa: F401  (register tables)


def _sync_url(url: str) -> str:
    return (
        url.replace("+aiosqlite", "")
        .replace("+asyncpg", "+psycopg2")
        .replace("postgresql+psycopg2", "postgresql")
    )


engine = create_engine(_sync_url(settings.DATABASE_URL), future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_all() -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
