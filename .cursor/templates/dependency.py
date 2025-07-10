"""
Example FastAPI dependency template.

This module contains a template for creating FastAPI dependencies
following the project's patterns and conventions.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.user import User, UserRole
from app.core.security import decode_access_token
from app.services.user_service import get_user_by_id


async def get_db() -> AsyncSession:
    """
    Get database session dependency.
    
    Returns:
        AsyncSession: Database session
    """
    async for session in get_async_session():
        yield session


async def get_current_user(
    token: str = Depends(decode_access_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: Decoded JWT token payload
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If user not found or inactive
    """
    user_id = token.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await get_user_by_id(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current verified user.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current verified user
        
    Raises:
        HTTPException: If user is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


def require_role(*roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Args:
        *roles: Required user roles
        
    Returns:
        Dependency function that checks user roles
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        """
        Check if user has required role.
        
        Args:
            current_user: Current active user
            
        Returns:
            User: Current user if role check passes
            
        Raises:
            HTTPException: If user doesn't have required role
        """
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker


async def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    # Check for forwarded headers first (for proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


async def get_user_agent(request: Request) -> str:
    """
    Get user agent from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: User agent string
    """
    return request.headers.get("User-Agent", "unknown")


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require admin role for endpoint access.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require superuser status for endpoint access.
    
    Args:
        current_user: Current active user
        
    Returns:
        User: Current user if superuser
        
    Raises:
        HTTPException: If user is not superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(decode_access_token),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get optional authenticated user (doesn't raise exception if not authenticated).
    
    Args:
        token: Optional decoded JWT token payload
        db: Database session
        
    Returns:
        Optional[User]: User if authenticated, None otherwise
    """
    if token is None:
        return None
    
    user_id = token.get("sub")
    if user_id is None:
        return None
    
    try:
        user = await get_user_by_id(db, int(user_id))
        return user if user and user.is_active else None
    except (ValueError, TypeError):
        return None 