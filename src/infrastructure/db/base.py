"""Async SQLAlchemy engine + session factory with Postgres primary, SQLite fallback."""

from __future__ import annotations

import os
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url
    # Fallback to sync-style or local postgres, then sqlite
    sync_url = os.getenv("DATABASE_SYNC_URL", "")
    if sync_url:
        return sync_url.replace("postgresql://", "postgresql+asyncpg://").replace("sqlite://", "sqlite+aiosqlite://")
    return "sqlite+aiosqlite:///./data/app.db"


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = _resolve_database_url()
        # SQLite needs check_same_thread=False handling via connect_args
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            # Ensure data directory exists for file-based sqlite
            if ":///" in url:
                try:
                    import pathlib

                    db_path = url.split(":///")[-1].split("?")[0]
                    if db_path and db_path != ":memory:":
                        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
        _engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        logger.info("DB engine created: %s", url.split("@")[-1] if "@" in url else url)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency — yields an AsyncSession."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables if not exists (fallback when alembic not run)."""
    from infrastructure.db.models.user import User  # noqa: F401 — ensure model imported

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB init: tables ensured")


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("DB engine disposed")


def reset_engine_for_tests() -> None:
    """Reset globals — used in tests to switch DATABASE_URL."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
