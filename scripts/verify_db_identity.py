"""Verify the configured database is HookForge before migrations.

Usage (from backend/ with venv active):
  python ../scripts/verify_db_identity.py

Exits 0 only when current_database() == hookforge and current_user == hookforge_app.
Never prints passwords.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import clear_settings_cache, get_settings  # noqa: E402

EXPECTED_DB = "hookforge"
EXPECTED_USER = "hookforge_app"


async def main() -> int:
    clear_settings_cache()
    settings = get_settings()
    parsed = urlparse(settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))
    print(f"config_host={parsed.hostname}:{parsed.port or 5432}")
    print(f"config_db={parsed.path.lstrip('/')}")
    print(f"config_user={parsed.username}")

    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(text("SELECT current_database(), current_user"))
            ).one()
    except Exception as exc:
        print(f"CONNECT_FAILED error={type(exc).__name__}")
        print(
            "Update DATABASE_URL in .env to "
            "postgresql+asyncpg://hookforge_app:<password>@localhost:5432/hookforge"
        )
        return 1
    finally:
        await engine.dispose()

    db_name, db_user = row[0], row[1]
    print(f"connected_db={db_name}")
    print(f"connected_user={db_user}")

    if db_name != EXPECTED_DB or db_user != EXPECTED_USER:
        print("IDENTITY_MISMATCH")
        print(f"expected_db={EXPECTED_DB} expected_user={EXPECTED_USER}")
        return 2

    print("IDENTITY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
