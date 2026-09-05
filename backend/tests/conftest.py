"""
Pytest configuration shared by the whole test suite.

Critical: this file MUST set DATABASE_URL (and other test-safe env vars)
BEFORE any `aegis_app.*` module is imported anywhere in the test session,
because aegis_app.core.database creates its SQLAlchemy engine at import time
from aegis_app.core.config.settings. Pytest guarantees conftest.py in a
directory is imported before the test modules in that directory, so this
works as long as no test file (or fixture) imports aegis_app at collection
time before conftest.py has run - which is why the env vars are set here,
at module scope, before the `from aegis_app...` imports below.

Without this, running pytest would silently read/write the real development
database (backend/aegis_ai.db) - which is exactly what the previous test
suite did.
"""

import os
import pathlib

_TEST_DB_PATH = pathlib.Path(__file__).parent / "test_aegis.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ["ENVIRONMENT"] = "test"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["SECRET_KEY"] = "test-only-secret-key-do-not-use-in-production"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_DIR"] = str(pathlib.Path(__file__).parent / "test_evidence_storage")

import pytest
import pytest_asyncio
import httpx

from aegis_app.main import app
from aegis_app.core.database import engine, Base


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_test_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
