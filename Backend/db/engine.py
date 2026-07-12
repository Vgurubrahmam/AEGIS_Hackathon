"""
AEGIS — SQLAlchemy Async Engine & Session Factory
Uses SQLite (aiosqlite) for zero-setup hackathon speed.
Switch to Postgres by changing DATABASE_URL in .env.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import get_settings


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # SQLite-specific: allow concurrent reads
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from db.models import Base as _  # noqa: ensure models are imported
        await conn.run_sync(Base.metadata.create_all)
