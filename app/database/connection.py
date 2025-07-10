"""
Enhanced database connection management.

This module provides improved database connection management with
advanced pooling, monitoring, and health checking capabilities.
"""

import asyncio
import logging
import sys
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
import inspect

from app.config import get_settings

# Fix for Windows event loop policy with psycopg
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseConfig:
    """Enhanced database configuration"""

    def __init__(self):
        # Connection pool settings
        self.pool_size = getattr(settings, "DB_POOL_SIZE", 20)
        self.max_overflow = getattr(settings, "DB_MAX_OVERFLOW", 30)
        self.pool_timeout = getattr(settings, "DB_POOL_TIMEOUT", 30)
        self.pool_recycle = getattr(settings, "DB_POOL_RECYCLE", 3600)
        self.pool_pre_ping = getattr(settings, "DB_POOL_PRE_PING", True)

        # Query settings
        self.query_timeout = getattr(settings, "DB_QUERY_TIMEOUT", 30)
        self.echo = settings.DEBUG

        # Health check settings
        self.health_check_interval = getattr(
            settings, "DB_HEALTH_CHECK_INTERVAL", 300
        )  # 5 minutes

    def get_engine_kwargs(self) -> Dict[str, Any]:
        """Get engine configuration kwargs"""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
        }

    def get_postgresql_config(self) -> Dict[str, Any]:
        """Get PostgreSQL-specific configuration"""
        option_str = (
            f"-c application_name=fastapi_backend "
            f"-c jit=off "
            f"-c statement_timeout={self.query_timeout}s"
        )

        return {
            "options": option_str,
        }


class DatabaseManager:
    """
    Enhanced database manager with monitoring and health checks.

    Provides advanced connection pooling, monitoring, and health checking
    for reliable database operations.
    """

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._config = DatabaseConfig()
        self._connection_count = 0
        self._health_status = True
        self._last_health_check = None

    def _get_database_url(self) -> str:
        """Get the appropriate database URL for async operations"""
        if hasattr(settings, "DATABASE_URL_ASYNC") and settings.DATABASE_URL_ASYNC:
            return settings.DATABASE_URL_ASYNC
        return settings.DATABASE_URL

    def _create_engine(self) -> AsyncEngine:
        """Create database engine with optimized configuration"""
        db_url = self._get_database_url()
        engine_kwargs = self._config.get_engine_kwargs()

        # Add PostgreSQL-specific configuration
        if db_url.startswith("postgresql"):
            if "+psycopg" in db_url or "+psycopg2" in db_url:
                engine_kwargs["connect_args"] = self._config.get_postgresql_config()

        logger.info(f"Creating database engine with URL: {db_url[:50]}...")

        return create_async_engine(db_url, **engine_kwargs)

    @property
    def engine(self) -> AsyncEngine:
        """Get or create database engine"""
        if self._engine is None:
            self._engine = self._create_engine()
            self._setup_event_listeners()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker:
        """Get or create session factory"""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
        return self._session_factory

    def _setup_event_listeners(self):
        """Setup database event listeners for monitoring"""

        @event.listens_for(self.engine.sync_engine, "connect")
        def set_connection_timeout(dbapi_connection, connection_record):
            self._connection_count += 1
            logger.debug(
                f"New database connection established (total: {self._connection_count})"
            )

        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

        @event.listens_for(self.engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            logger.warning(f"Connection invalidated: {exception}")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        session = None
        try:
            session = self.session_factory()
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}")
            if isinstance(session, AsyncSession):
                try:
                    rollback = getattr(session, "rollback", None)
                    if rollback is not None and callable(rollback):
                        await rollback()
                except Exception as rollback_exc:
                    logger.error(f"Error during rollback: {rollback_exc}")
            raise
        finally:
            if isinstance(session, AsyncSession):
                try:
                    close = getattr(session, "close", None)
                    if close is not None and callable(close):
                        await close()
                except Exception as close_exc:
                    logger.error(f"Error closing session: {close_exc}")

    async def health_check(self) -> bool:
        """Perform a health check on the database connection"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            self._health_status = True
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            self._health_status = False
            return False

    async def get_pool_status(self) -> Dict[str, Any]:
        """Get the current status of the connection pool"""
        if self._engine is None:
            return {"status": "not_initialized"}

        pool = self._engine.pool
        return {
            "status": "active",
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "connection_count": self._connection_count,
            "health_status": self._health_status,
        }


# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    db_manager = DatabaseManager()
    async for session in db_manager.get_session():
        yield session


# Create a global instance for dependency injection
db_manager = DatabaseManager()

# Global async_engine for script and migration access
async_engine = DatabaseManager().engine
