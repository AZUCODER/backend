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
            # Remove poolclass specification for async engines
            # SQLAlchemy will use the appropriate async pool by default
        }

    def get_postgresql_config(self) -> Dict[str, Any]:
        """Get PostgreSQL-specific configuration"""
        # Use the generic "options" parameter accepted by both psycopg2 and psycopg
        # to pass runtime parameters instead of the psycopg-specific "server_settings".
        # This improves compatibility with different driver versions and avoids errors
        # such as: "invalid connection option \"server_settings\"".
        option_str = (
            f"-c application_name=fastapi_backend "
            f"-c jit=off "
            f"-c statement_timeout={self.query_timeout}s"
        )

        return {
            "options": option_str,
        }

    def get_sqlite_config(self) -> Dict[str, Any]:
        """Get SQLite-specific configuration"""
        return {
            "timeout": self.query_timeout,
            "check_same_thread": False,
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

        # Convert sync URL to async
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite://"):
            return db_url.replace("sqlite://", "sqlite+aiosqlite://")
        elif db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+psycopg://")
        else:
            return db_url

    def _create_engine(self) -> AsyncEngine:
        """Create database engine with optimized configuration"""
        db_url = self._get_database_url()
        engine_kwargs = self._config.get_engine_kwargs()

        # Add database-specific configuration
        if db_url.startswith("postgresql"):
            # asyncpg does NOT accept the "options" parameter – only apply
            # custom connect_args when the sync/psycopg driver is in use.
            if "+psycopg" in db_url or "+psycopg2" in db_url:
                engine_kwargs["connect_args"] = self._config.get_postgresql_config()
        elif db_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = self._config.get_sqlite_config()

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
            """Set connection-specific settings"""
            self._connection_count += 1
            logger.debug(
                f"New database connection established (total: {self._connection_count})"
            )

        @event.listens_for(self.engine.sync_engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Monitor connection checkout from pool"""
            logger.debug("Connection checked out from pool")

        @event.listens_for(self.engine.sync_engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Monitor connection return to pool"""
            logger.debug("Connection returned to pool")

        @event.listens_for(self.engine.sync_engine, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """Monitor connection invalidation"""
            logger.warning(f"Connection invalidated: {exception}")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session with comprehensive error handling.

        Provides proper session lifecycle management with error handling,
        automatic rollback, and resource cleanup.
        """
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
                        if inspect.iscoroutinefunction(rollback):
                            await rollback()
                        else:
                            rollback()
                except Exception as rollback_exc:
                    logger.error(f"Session rollback failed: {rollback_exc}")
            raise
        except Exception as e:
            logger.error(f"Unexpected session error: {e}")
            if isinstance(session, AsyncSession):
                try:
                    rollback = getattr(session, "rollback", None)
                    if rollback is not None and callable(rollback):
                        if inspect.iscoroutinefunction(rollback):
                            await rollback()
                        else:
                            rollback()
                except Exception as rollback_exc:
                    logger.error(f"Session rollback failed: {rollback_exc}")
            raise
        finally:
            if session:
                await session.close()

    async def health_check(self) -> bool:
        """
        Comprehensive database connection health check.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            async with self.session_factory() as session:
                # Simple connectivity test
                await session.execute(text("SELECT 1"))

                # Test transaction capability
                async with session.begin():
                    await session.execute(text("SELECT 1"))

                self._health_status = True
                self._last_health_check = asyncio.get_event_loop().time()
                logger.debug("Database health check passed")
                return True

        except Exception as e:
            self._health_status = False
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_pool_status(self) -> Dict[str, Any]:
        """
        Get connection pool status and metrics.

        Returns:
            Dict containing pool statistics
        """
        pool = self.engine.sync_engine.pool
        pool_status = {}
        for attr in ["size", "checkedin", "checkedout", "overflow"]:
            if hasattr(pool, attr):
                pool_status[attr] = getattr(pool, attr)()
            else:
                pool_status[attr] = None
        pool_status.update(
            {
                "total_connections": self._connection_count,
                "health_status": self._health_status,
                "last_health_check": self._last_health_check,
            }
        )
        return pool_status

    async def close(self):
        """Close database connections and cleanup resources"""
        if self._engine:
            logger.info("Closing database connections...")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


# Enhanced dependency for FastAPI with error handling
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Provides database sessions with proper error handling and monitoring.
    """
    try:
        async for session in db_manager.get_session():
            yield session
    except Exception as e:
        logger.error(f"Database dependency error: {e}")
        raise


# Health check dependency
async def get_db_health() -> Dict[str, Any]:
    """FastAPI dependency for database health status"""
    is_healthy = await db_manager.health_check()
    pool_status = await db_manager.get_pool_status()

    return {
        "healthy": is_healthy,
        "pool_status": pool_status,
    }
