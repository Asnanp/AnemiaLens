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
DEFAULT_SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./anemialens.db"

# ---------------------------------------------------------------------------
# Connection pooling configuration
# ---------------------------------------------------------------------------

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "0"))


def _normalize_database_url(database_url: str) -> str:
    url = database_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _resolve_database_url() -> str:
    return _normalize_database_url(
        os.getenv("DATABASE_URL", DEFAULT_SQLITE_DATABASE_URL)
    )


def _runtime_environment() -> str:
    return (
        os.getenv("ANEMIALENS_ENVIRONMENT")
        or os.getenv("ENVIRONMENT")
        or "development"
    ).strip().lower()


def _truthy_env(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _development_database_fallback_enabled() -> bool:
    explicit = _truthy_env(os.getenv("ANEMIALENS_ENABLE_DEV_DB_FALLBACK"))
    if explicit is not None:
        return explicit
    return _runtime_environment() != "production"


def _development_fallback_database_url() -> str:
    return _normalize_database_url(
        os.getenv("ANEMIALENS_DEV_DATABASE_URL", DEFAULT_SQLITE_DATABASE_URL)
    )


def _build_connect_args(database_url: str) -> dict[str, object]:
    connect_args: dict[str, object] = {}
    if "sqlite" in database_url:
        connect_args["check_same_thread"] = False
    elif "postgres" in database_url:
        connect_args["ssl"] = "require"
    return connect_args


def _build_engine_kwargs(database_url: str) -> dict[str, object]:
    """Build engine configuration based on database type."""
    connect_args = _build_connect_args(database_url)
    base: dict[str, object] = {
        "echo": False,
        "pool_pre_ping": POOL_PRE_PING,
        "connect_args": connect_args,
    }

    if "sqlite" in database_url:
        base["connect_args"] = {**connect_args, "timeout": 30}
        base["pool_size"] = 1
        base["max_overflow"] = 0
    elif "postgres" in database_url:
        base["pool_size"] = POOL_SIZE
        base["max_overflow"] = MAX_OVERFLOW
        base["pool_recycle"] = POOL_RECYCLE
        base["pool_timeout"] = POOL_TIMEOUT
        base["poolclass"] = AsyncAdaptedQueuePool

    return base


def _attach_slow_query_logging(target_engine) -> None:
    if SLOW_QUERY_THRESHOLD_MS <= 0:
        return

    @event.listens_for(target_engine.sync_engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(__import__("time").time())

    @event.listens_for(target_engine.sync_engine, "after_cursor_execute")
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


def _build_engine_and_session(database_url: str):
    current_engine = create_async_engine(
        database_url,
        **_build_engine_kwargs(database_url),
    )
    _attach_slow_query_logging(current_engine)
    session_factory = async_sessionmaker(
        current_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return current_engine, session_factory


DATABASE_URL = _resolve_database_url()
_configured_database_url = DATABASE_URL
engine, async_session_factory = _build_engine_and_session(DATABASE_URL)


async def _rebind_engine(database_url: str) -> None:
    global DATABASE_URL, _configured_database_url, engine, async_session_factory

    current_engine = engine
    DATABASE_URL = database_url
    _configured_database_url = database_url
    engine, async_session_factory = _build_engine_and_session(database_url)
    os.environ["DATABASE_URL"] = database_url

    if current_engine is not engine:
        await current_engine.dispose()

    database_kind = "sqlite" if "sqlite" in database_url else "postgresql"
    log.info("Database engine rebound for %s runtime.", database_kind)


def _ensure_engine_current() -> None:
    current_database_url = _resolve_database_url()
    if current_database_url == _configured_database_url:
        return

    globals()["DATABASE_URL"] = current_database_url
    globals()["_configured_database_url"] = current_database_url
    globals()["engine"], globals()["async_session_factory"] = _build_engine_and_session(
        current_database_url
    )

    database_kind = "sqlite" if "sqlite" in current_database_url else "postgresql"
    log.info("Database engine rebound for %s runtime.", database_kind)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


@asynccontextmanager
async def get_db_session():
    """
    Async context manager for database sessions.

    Preferred over the dependency version for service-layer code.
    """
    _ensure_engine_current()
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
    _ensure_engine_current()
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
    """Create all ORM tables - called once during app startup."""
    _ensure_engine_current()
    primary_database_url = DATABASE_URL

    try:
        await _create_all_tables_for_url(primary_database_url)
        log.info("Database tables created/verified successfully.")
    except Exception as exc:
        log.error("Database table creation FAILED: %s", exc, exc_info=True)
        fallback_url = await _activate_development_database_fallback(exc)
        if fallback_url is not None:
            await _create_all_tables_for_url(fallback_url)
            log.info("Database tables created/verified successfully using SQLite fallback.")
            return
        log.warning("Continuing startup despite table creation error.")


async def close_engine() -> None:
    """Dispose of the engine - called during app shutdown."""
    _ensure_engine_current()
    await engine.dispose()
    log.info("Database engine disposed.")


async def _create_all_tables_for_url(database_url: str) -> None:
    ddl_url = database_url
    if "pooler.supabase.com:6543" in ddl_url:
        ddl_url = ddl_url.replace(":6543/", ":5432/")
        log.info("Using session pooler (port 5432) for DDL operations.")

    ddl_engine = create_async_engine(
        ddl_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"ssl": "require"} if "postgres" in ddl_url else {},
    )
    try:
        async with ddl_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await ddl_engine.dispose()


async def _activate_development_database_fallback(exc: Exception) -> str | None:
    if "sqlite" in DATABASE_URL:
        return None
    if not _development_database_fallback_enabled():
        return None

    fallback_url = _development_fallback_database_url()
    if fallback_url == DATABASE_URL:
        return None

    log.warning(
        "Primary database unavailable in %s mode; falling back to local SQLite runtime. "
        "Original error: %s",
        _runtime_environment(),
        exc,
    )
    await _rebind_engine(fallback_url)
    return fallback_url


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
    from sqlalchemy import func, select

    key = cache_key or f"count:{model.__tablename__}"
    cached = await response_cache.get(key)
    if cached is not None:
        return cached

    result = await session.execute(select(func.count()).select_from(model))
    count = result.scalar() or 0

    await response_cache.set(key, count, ttl_seconds=ttl)
    return count
