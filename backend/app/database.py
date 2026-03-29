"""
Async SQLAlchemy engine and session factory for AnemiaLens.

Supports SQLite (dev) and PostgreSQL (production) via DATABASE_URL.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./anemialens.db").strip()

# For managed PostgreSQL providers, postgres:// must be normalized to postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgres" in DATABASE_URL:
    connect_args["ssl"] = "require"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all ORM tables — called once during app startup."""
    import logging
    log = logging.getLogger("anemialens")

    # For Supabase transaction pooler, use a separate direct engine for DDL
    # Transaction pooler doesn't support multi-statement DDL well
    ddl_url = DATABASE_URL
    if "pooler.supabase.com:6543" in ddl_url:
        # Switch to session pooler port 5432 for DDL operations
        ddl_url = ddl_url.replace(":6543/", ":5432/")
        log.info("Using session pooler (port 5432) for DDL operations.")

    try:
        # Ensure all ORM models are imported so Base.metadata knows about them
        import app.models  # noqa: F401

        from sqlalchemy.ext.asyncio import create_async_engine as _make_engine
        ddl_connect_args: dict = {}
        if "postgres" in ddl_url:
            ddl_connect_args["ssl"] = "require"
        elif "sqlite" in ddl_url:
            ddl_connect_args["check_same_thread"] = False
        ddl_engine = _make_engine(
            ddl_url,
            echo=False,
            pool_pre_ping=True,
            connect_args=ddl_connect_args,
        )
        async with ddl_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ddl_engine.dispose()
        log.info("Database tables created/verified successfully.")
    except Exception as exc:
        log.error(f"Database table creation FAILED: {exc}", exc_info=True)
        # Non-fatal — tables may already exist
        log.warning("Continuing startup despite table creation error.")
