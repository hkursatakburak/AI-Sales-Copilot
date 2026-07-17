"""Async SQLite veritabanı bağlantısı ve oturum yönetimi."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def _get_engine(database_url: str):
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(database_url, echo=False)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db(database_url: str) -> None:
    """Tabloları oluşturur (yoksa). Uygulama başlangıcında çağrılır."""
    from app.infrastructure.db.user_model import UserORM  # noqa: F401 — model kayıtlı olsun

    engine = _get_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db(database_url: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI bağımlılığı: her istek için temiz bir oturum açar, ardından kapatır."""
    from app.core.config import get_settings

    url = database_url or get_settings().database_url
    _get_engine(url)
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
