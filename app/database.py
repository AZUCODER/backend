"""
Database configuration and session management.

This module contains the database engine setup, session management,
and database utilities using SQLModel.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

# Sync engine for Alembic and testing
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Async engine for main application
async_database_url = settings.DATABASE_URL_ASYNC or settings.DATABASE_URL.replace(
    "sqlite://", "sqlite+aiosqlite://"
)

if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace(
        "postgresql://", "postgresql+psycopg://"
    )

async_engine = create_async_engine(
    async_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Session makers
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def create_db_and_tables():
    """
    Create database and tables.
    Used for initialization and testing.
    """
    SQLModel.metadata.create_all(sync_engine)


async def create_db_and_tables_async():
    """
    Create database and tables asynchronously.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
