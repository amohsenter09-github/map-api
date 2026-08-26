from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine():
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db() -> None:
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def ping_db() -> None:
    from sqlalchemy import text

    engine = _get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    _get_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
