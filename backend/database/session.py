"""
Database session management — async SQLAlchemy engine and session factory.

Pattern: one engine, one session factory, sessions are request-scoped.
FastAPI dependency get_db() yields a session per request and closes it after.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from backend.config import settings
from backend.database.models import Base


# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO_SQL,
    poolclass=NullPool,
    future=True,
)

# ── Session factory ───────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ── Initialization ────────────────────────────────────────────────────────────

async def init_db() -> None:
    """
    Create all tables on startup if they don't exist.
    In production you would use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all tables — useful for testing. Never call in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """
    Yields a database session per request and closes it after.

    Usage in a route:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()