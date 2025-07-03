"""
Database configuration and session management.

This module contains the database engine setup, session management,
and database utilities using SQLModel with enhanced connection management.
"""

import asyncio
import sys
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine

from app.config import get_settings

# Import enhanced database components
from app.database.connection import db_manager, get_db as get_enhanced_db

# Fix for Windows event loop policy with psycopg
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

settings = get_settings()

# Sync engine for Alembic and testing
sync_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# For backward compatibility - use enhanced database manager for async operations
async_engine = db_manager.engine
AsyncSessionLocal = db_manager.session_factory

# Legacy session maker for backward compatibility
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)


# Enhanced session function with monitoring
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Enhanced dependency function to get database session.

    Now uses the enhanced database manager with monitoring and retry logic.

    Yields:
        AsyncSession: Database session with enhanced features
    """
    async for session in get_enhanced_db():
        yield session


# Legacy function for backward compatibility
async def get_session_legacy() -> AsyncGenerator[AsyncSession, None]:
    """
    Legacy dependency function for backward compatibility.

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


# Health check function
async def get_database_health():
    """Get database health status"""
    return await db_manager.health_check()


# Pool status function
async def get_database_pool_status():
    """Get database connection pool status"""
    return await db_manager.get_pool_status()
