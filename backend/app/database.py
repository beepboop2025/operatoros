"""
Async SQLAlchemy engine, session factory, FastAPI dependency, and slow query logging.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

_slow_query_logger = logging.getLogger("operatoros.slow_queries")

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)


# ── Slow query logging (>500ms) ─────────────────────────────────────────────

_SLOW_QUERY_THRESHOLD_MS = 500


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.monotonic())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_ms = (time.monotonic() - conn.info["query_start_time"].pop()) * 1000
    if total_ms >= _SLOW_QUERY_THRESHOLD_MS:
        _slow_query_logger.warning(
            "SLOW QUERY (%.1fms): %s | params=%s",
            total_ms,
            statement[:500],
            str(parameters)[:200] if parameters else "None",
        )

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session, rolls back on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
