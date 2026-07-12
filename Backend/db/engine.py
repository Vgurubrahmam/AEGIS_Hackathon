"""
AEGIS — SQLAlchemy Async Engine & Session Factory
Uses SQLite (aiosqlite) for zero-setup hackathon speed.
Switch to Postgres by changing DATABASE_URL in .env.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import get_settings


settings = get_settings()

# Dynamically rewrite PostgreSQL URL to use the asyncpg driver
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Configure connection arguments based on database type
if "sqlite" in db_url:
    connect_args = {"check_same_thread": False}
else:
    # Disable prepared statement caching for Supabase/PgBouncer connection pooler compatibility
    connect_args = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
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
