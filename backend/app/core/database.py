"""
app/core/database.py
====================
Async SQLAlchemy engine, session factory, and FastAPI dependency helpers.

Design decisions:
* ``pool_size=20`` with ``max_overflow=0`` to cap concurrent DB connections.
* ``expire_on_commit=False`` prevents lazy-load errors after a commit inside
  an async context (attributes remain accessible without an open session).
* The ``get_db`` dependency uses an ``async with`` block so the session is
  always properly closed, even on exceptions.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {
    "echo": (settings.ENVIRONMENT == "development"),
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 0,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Declarative base – all ORM models inherit from this
# ---------------------------------------------------------------------------
Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session, then close it on completion.

    Usage::

        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...

    The session is rolled back automatically if an unhandled exception
    propagates out of the endpoint (SQLAlchemy does this in ``__aexit__``
    when an exception is present).
    """
    async with AsyncSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# Schema initialisation (dev / test helper)
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all ORM-mapped tables if they do not already exist.

    This is called once at application startup via the lifespan context
    manager.  In production, Alembic migrations should be preferred for
    schema changes; ``init_db`` is primarily useful during development and
    integration testing with ephemeral SQLite databases.
    """
    # Import all models so SQLAlchemy's metadata is fully populated before
    # calling ``create_all``.
    import app.models  # noqa: F401 – side-effect import

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
