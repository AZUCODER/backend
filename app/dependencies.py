"""
Common FastAPI dependencies.

This module contains common dependencies used across the FastAPI application
such as database sessions, authentication, and common utilities with enhanced
database monitoring and connection management.
"""

from typing import AsyncGenerator, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_session
from app.database.monitoring import (
    get_query_metrics,
    get_performance_summary,
    health_check_queries,
)
from app.models.user import UserRole
from app.services.enhanced_user_service import EnhancedUserService

# Security dependency
security = HTTPBearer()


# Enhanced database dependency with monitoring
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Enhanced database session dependency with monitoring and retry logic.

    Yields:
        AsyncSession: Database session with enhanced features
    """
    async for session in get_session():
        yield session


# Legacy database dependency for backward compatibility
async def get_db_legacy() -> AsyncGenerator[AsyncSession, None]:
    """
    Legacy database session dependency for backward compatibility.

    Yields:
        AsyncSession: Database session
    """
    import importlib

    db_module = importlib.import_module("app.database")
    get_session_legacy = getattr(db_module, "get_session_legacy", None)
    if get_session_legacy is None:
        raise RuntimeError("get_session_legacy is not available in app.database")

    async for session in get_session_legacy():
        yield session


# Enhanced user service dependency
async def get_enhanced_user_service(
    db: AsyncSession = Depends(get_db),
) -> EnhancedUserService:
    """
    Enhanced user service dependency with monitoring and transaction support.

    Args:
        db: Database session

    Returns:
        EnhancedUserService: Enhanced user service instance
    """
    return EnhancedUserService(db)


# Database health check dependencies
async def get_db_health() -> Dict[str, Any]:
    """
    Database health check dependency.

    Returns:
        Dict: Database health status
    """
    from app.database.connection import db_manager

    healthy = await db_manager.health_check()
    return {"healthy": healthy}


async def get_db_pool_status() -> Dict[str, Any]:
    """
    Database pool status dependency.

    Returns:
        Dict: Database connection pool status
    """
    from app.database.connection import db_manager

    return await db_manager.get_pool_status()


async def get_query_performance_metrics() -> Dict[str, Any]:
    """
    Query performance metrics dependency.

    Returns:
        Dict: Query performance metrics
    """
    return get_query_metrics()


async def get_db_performance_summary() -> Dict[str, Any]:
    """
    Database performance summary dependency.

    Returns:
        Dict: Performance summary
    """
    return get_performance_summary()


async def get_db_health_check() -> Dict[str, Any]:
    """
    Comprehensive database health check dependency.

    Returns:
        Dict: Comprehensive health check results
    """
    return await health_check_queries()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    Get current user ID from JWT token.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        int: User ID

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        # Token payloads store subject as string; cast to int for DB queries
        try:
            return int(user_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_active_user(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    """
    Get current active user from database.

    Args:
        db: Database session
        current_user_id: Current user ID from token

    Returns:
        User: Current user object

    Raises:
        HTTPException: If user not found or inactive
    """
    from app.models.user import User
    from app.services.user_service import get_user_by_id

    user = await get_user_by_id(db, current_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return user


def get_client_ip(request) -> str:
    """
    Get client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Try to get real IP from various headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to client host
    return request.client.host if request.client else "unknown"


def get_user_agent(request) -> str:
    """
    Get user agent from request.

    Args:
        request: FastAPI request object

    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")


def require_role(*roles: UserRole):
    """
    Dependency to require a user to have one of the specified roles.
    Usage: Depends(require_role(UserRole.ADMIN, UserRole.USER))
    Raises 403 if the user does not have the required role.
    """

    async def _require_role(current_user=Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join([r.value for r in roles])}",
            )
        return current_user

    return _require_role


def require_verified_user(current_user=Depends(get_current_active_user)):
    """
    Dependency to require a user to have a verified email.
    Usage: Depends(require_verified_user)
    Raises 403 if the user is not verified.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email to access this resource.",
        )
    return current_user
