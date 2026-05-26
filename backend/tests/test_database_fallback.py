from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import app.database as database_module


def test_create_tables_falls_back_to_sqlite_in_development(monkeypatch, tmp_path: Path) -> None:
    tracked_env = {
        "DATABASE_URL": os.environ.get("DATABASE_URL"),
        "ANEMIALENS_DEV_DATABASE_URL": os.environ.get("ANEMIALENS_DEV_DATABASE_URL"),
        "ANEMIALENS_ENABLE_DEV_DB_FALLBACK": os.environ.get("ANEMIALENS_ENABLE_DEV_DB_FALLBACK"),
        "ANEMIALENS_ENVIRONMENT": os.environ.get("ANEMIALENS_ENVIRONMENT"),
        "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
    }
    fallback_path = tmp_path / "fallback-dev.db"
    fallback_url = f"sqlite+aiosqlite:///{fallback_path.as_posix()}"
    db = database_module

    try:
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://postgres:secret@invalid.example.com:5432/postgres",
        )
        monkeypatch.setenv("ANEMIALENS_DEV_DATABASE_URL", fallback_url)
        monkeypatch.setenv("ANEMIALENS_ENABLE_DEV_DB_FALLBACK", "true")
        monkeypatch.setenv("ANEMIALENS_ENVIRONMENT", "development")
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        db = importlib.reload(database_module)
        calls: list[str] = []

        async def fake_create_all_tables_for_url(database_url: str) -> None:
            calls.append(database_url)
            if database_url.startswith("postgresql+asyncpg://"):
                raise OSError("host unreachable")

        monkeypatch.setattr(db, "_create_all_tables_for_url", fake_create_all_tables_for_url)

        asyncio.run(db.create_tables())

        assert calls == [
            "postgresql+asyncpg://postgres:secret@invalid.example.com:5432/postgres",
            fallback_url,
        ]
        assert db.DATABASE_URL == fallback_url
        assert str(db.engine.url) == fallback_url
    finally:
        asyncio.run(db.engine.dispose())
        for key, value in tracked_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        importlib.reload(database_module)
