"""Shared pytest fixtures for HookForge backend tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import clear_settings_cache


def _load_dotenv_files() -> None:
    """Minimal .env loader (no extra dependency) for test bootstrap."""
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _derive_test_database_url(base_url: str) -> str:
    """Use dedicated hookforge_test DB — never the development hookforge DB."""
    override = os.getenv("TEST_DATABASE_URL")
    if override:
        return override
    normalized = base_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    rebuilt = parsed._replace(path="/hookforge_test")
    return urlunparse(rebuilt).replace("postgresql://", "postgresql+asyncpg://", 1)


_load_dotenv_files()
_BASE_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://hookforge_app:CHANGE_ME@localhost:5432/hookforge",
)
TEST_DATABASE_URL = _derive_test_database_url(_BASE_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

_SCHEMA_READY = False


@pytest.fixture(autouse=True)
def configure_test_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-16chars-min")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/15")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/14")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/13")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("REDIS_REQUIRED", "false")
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "true")
    monkeypatch.setenv("RATE_LIMIT_ENABLED_IN_TEST", "false")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_MINUTES", "60")
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Function-scoped session against hookforge_test with outer rollback."""
    global _SCHEMA_READY

    clear_settings_cache()
    import app.models  # noqa: F401
    from app.db.base import Base

    parsed = urlparse(TEST_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    db_name = parsed.path.lstrip("/")
    if db_name != "hookforge_test":
        pytest.fail(
            f"Refusing to run DB tests against '{db_name}'. "
            "Expected dedicated database 'hookforge_test'."
        )

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text("SELECT current_database(), current_user"))).one()
            if row[0] != "hookforge_test":
                pytest.fail(f"Connected to unexpected database: {row[0]}")
            if row[1] != "hookforge_app":
                pytest.fail(f"Connected as unexpected user: {row[1]}")

        if not _SCHEMA_READY:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            _SCHEMA_READY = True

        connection = await engine.connect()
        outer = await connection.begin()
        session = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
            join_transaction_mode="create_savepoint",
        )()
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()
            await connection.close()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client with DB session override and mocked Redis lifecycle."""
    from app.db.session import get_db
    from app.main import create_app

    clear_settings_cache()

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield db_session
        except Exception:
            await db_session.rollback()
            raise
        else:
            await db_session.commit()

    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        application = create_app()
        application.dependency_overrides[get_db] = _override_get_db
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_db() -> AsyncIterator[AsyncClient]:
    """Lightweight client for tests that do not need the database."""
    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        clear_settings_cache()
        from app.main import create_app

        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
