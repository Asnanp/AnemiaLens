"""
Async SQLAlchemy engine and session factory for AnemiaLens.

Supports SQLite (dev) and PostgreSQL (production) via DATABASE_URL.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./anemialens.db").strip()

# For PostgreSQL on Render, the URL starts with postgres:// but SQLAlchemy needs postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgres" in DATABASE_URL:
    connect_args["ssl"] = "require"
    connect_args["statement_timeout"] = "8000"  # 8s query timeout

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_timeout=10,
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
        from sqlalchemy.ext.asyncio import create_async_engine as _make_engine
        ddl_engine = _make_engine(
            ddl_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"ssl": "require"} if "postgres" in ddl_url else {},
        )
        async with ddl_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await ddl_engine.dispose()
        log.info("Database tables created/verified successfully.")
    except Exception as exc:
        log.error(f"Database table creation FAILED: {exc}", exc_info=True)
        # Non-fatal — tables may already exist
        log.warning("Continuing startup despite table creation error.")
