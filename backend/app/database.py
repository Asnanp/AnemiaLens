"""
Async SQLAlchemy engine and session factory for AnemiaLens.

Supports SQLite (dev) and PostgreSQL (production) via DATABASE_URL.

Performance optimizations:
- Connection pooling with configurable pool size
- pool_pre_ping for stale connection detection
- pool_recycle for automatic connection refresh
- Query result caching for frequently-accessed data
- Indexed columns for common query patterns
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")

log = logging.getLogger("anemialens.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./anemialens.db").strip()

# For managed PostgreSQL providers, postgres:// must be normalized to postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ---------------------------------------------------------------------------
# Connection pooling configuration
# ---------------------------------------------------------------------------

# Environment variables for pool tuning (with sensible defaults)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # seconds
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args["check_same_thread"] = False
elif "postgres" in DATABASE_URL:
    connect_args["ssl"] = "require"


def _build_engine_kwargs() -> dict:
    """Build engine configuration based on database type."""
    base = {
        "echo": False,
        "pool_pre_ping": POOL_PRE_PING,
        "connect_args": connect_args,
    }

    if "sqlite" in DATABASE_URL:
        # SQLite: use OptimizedSQLiteMixin for better performance
        base["connect_args"] = {**connect_args, "timeout": 30}
        # SQLite doesn't use pool_size; use StaticPool for single-writer
        base["pool_size"] = 1
        base["max_overflow"] = 0
    elif "postgres" in DATABASE_URL:
        # PostgreSQL: use connection pooling
        base["pool_size"] = POOL_SIZE
        base["max_overflow"] = MAX_OVERFLOW
        base["pool_recycle"] = POOL_RECYCLE
        base["pool_timeout"] = POOL_TIMEOUT
        base["poolclass"] = AsyncAdaptedQueuePool

    return base


engine = create_async_engine(DATABASE_URL, **_build_engine_kwargs())


# Log slow queries (optional, enabled via SLOW_QUERY_THRESHOLD_MS env var)
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "0"))

if SLOW_QUERY_THRESHOLD_MS > 0:
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(__import__("time").time())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        start_times = conn.info.get("query_start_time", [])
        if start_times:
            start = start_times.pop()
            elapsed_ms = (__import__("time").time() - start) * 1000
            if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                log.warning(
                    "SLOW QUERY (%.1fms): %s",
                    elapsed_ms,
                    statement[:200],
                )


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


@asynccontextmanager
async def get_db_session():
    """
    Async context manager for database sessions.

    Preferred over the dependency version for service-layer code.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db():
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
    # For Supabase transaction pooler, use a separate direct engine for DDL
    ddl_url = DATABASE_URL
    if "pooler.supabase.com:6543" in ddl_url:
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
        log.error("Database table creation FAILED: %s", exc, exc_info=True)
        log.warning("Continuing startup despite table creation error.")


async def close_engine() -> None:
    """Dispose of the engine — called during app shutdown."""
    await engine.dispose()
    log.info("Database engine disposed.")


# ---------------------------------------------------------------------------
# Query optimization utilities
# ---------------------------------------------------------------------------


def paginated_query(query, page: int = 1, page_size: int = 20):
    """Apply pagination to a SQLAlchemy query."""
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size)


async def cached_count(session: AsyncSession, model, cache_key: str | None = None, ttl: int = 60):
    """
    Get cached row count for a model.
    For large tables, count(*) is expensive; this caches the result.
    """
    from app.services.cache import response_cache

    key = cache_key or f"count:{model.__tablename__}"
    cached = await response_cache.get(key)
    if cached is not None:
        return cached

    from sqlalchemy import func, select

    result = await session.execute(select(func.count()).select_from(model))
    count = result.scalar() or 0

    await response_cache.set(key, count, ttl_seconds=ttl)
    return count
