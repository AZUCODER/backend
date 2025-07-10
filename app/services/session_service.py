"""
Session service for managing user sessions.

This module provides session management functionality including
session creation, validation, and cleanup using Redis for storage.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.session import Session, SessionCreate
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token
from app.services.redis_service import redis_service
from app.config import get_settings

settings = get_settings()


async def create_user_session(
    db: AsyncSession,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new user session with Redis caching.

    Args:
        db: Database session
        user: User object
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        Dictionary containing access_token and refresh_token
    """
    # Create tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Create session record in database
    session = Session(
        user_id=str(user.id),
        refresh_token=refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(days=7),  # 7 days
    )

    db.add(session)
    await db.commit()
    # Refresh to get session ID
    await db.refresh(session)

    # Store session data in Redis for faster access
    session_data = {
        "session_id": str(session.id),  # Convert UUID to string
        "user_id": str(user.id),  # Convert UUID to string
        "refresh_token": refresh_token,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "is_active": session.is_active,
    }

    # Cache session for 7 days (same as database)
    redis_service.set_user_session(
        str(user.id), session_data, expire=7 * 24 * 3600  # 7 days in seconds
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "session_id": str(session.id),  # Convert UUID to string
    }


async def refresh_access_token(
    db: AsyncSession, refresh_token: str
) -> Optional[Dict[str, str]]:
    """
    Refresh access token using Redis cache.

    Args:
        db: Database session
        refresh_token: Refresh token

    Returns:
        Dictionary containing new access_token and refresh_token, or None if invalid
    """
    # Try to get session from Redis first
    session_data = None
    user_id = None

    # Find user_id from refresh token (you might need to decode the token)
    # For now, we'll check all user sessions in Redis
    # In a real implementation, you'd decode the token to get user_id

    # Fallback to database lookup
    statement = select(Session).where(
        Session.refresh_token == refresh_token,
        Session.is_active == True,
        Session.expires_at > datetime.utcnow(),
    )
    result = await db.execute(statement)
    session = result.scalars().first()

    if not session:
        return None

    user_id = session.user_id

    # Get user data
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalars().first()

    if not user or not user.is_active:
        return None

    # Create new tokens
    new_access_token = create_access_token(subject=str(user.id))
    new_refresh_token = create_refresh_token(subject=str(user.id))

    # Update session in database
    session.refresh_token = new_refresh_token
    session.updated_at = datetime.utcnow()
    await db.commit()

    # Update Redis cache
    session_data = {
        "session_id": str(session.id),  # Convert UUID to string
        "user_id": str(user.id),  # Convert UUID to string
        "refresh_token": new_refresh_token,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "is_active": session.is_active,
    }

    redis_service.set_user_session(str(user.id), session_data, expire=7 * 24 * 3600)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "session_id": str(session.id),  # Convert UUID to string
    }


async def revoke_session(
    db: AsyncSession,
    *,
    user_id: str,
    session_id: Optional[str] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    """
    Revoke a user session.

    Args:
        db: Database session
        user_id: User ID
        session_id: Specific session ID to revoke (optional)

    Returns:
        True if session was revoked, False otherwise
    """
    if session_id:
        # Revoke specific session
        statement = select(Session).where(
            Session.id == session_id, Session.user_id == user_id
        )
        result = await db.execute(statement)
        session = result.scalars().first()

        if session:
            session.is_active = False
            await db.commit()
            # Optionally log reason or audit here in future

            # Remove from Redis cache
            redis_service.delete_user_session(str(user_id))
            return True
    else:
        # Revoke all user sessions
        statement = select(Session).where(
            Session.user_id == user_id, Session.is_active == True
        )
        result = await db.execute(statement)
        sessions = result.scalars().all()

        for session in sessions:
            session.is_active = False

        await db.commit()

        # Remove from Redis cache
        redis_service.delete_user_session(str(user_id))
        return len(sessions) > 0

    return False


async def revoke_all_user_sessions(
    db: AsyncSession,
    user_id: str,
    reason: Optional[str] = None,
) -> bool:
    """
    Revoke all sessions for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        True if sessions were revoked, False otherwise
    """
    return await revoke_session(db, user_id=user_id, reason=reason)


async def get_user_sessions(db: AsyncSession, user_id: str) -> List[Dict[str, Any]]:
    """
    Get all active sessions for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of session information dictionaries
    """
    # Try to get from Redis first
    session_data = redis_service.get_user_session(str(user_id))
    if session_data:
        return [session_data]

    # Fallback to database
    statement = select(Session).where(
        Session.user_id == user_id,
        Session.is_active == True,
        Session.expires_at > datetime.utcnow(),
    )
    result = await db.execute(statement)
    sessions = result.scalars().all()

    session_list = []
    for session in sessions:
        session_info = {
            "session_id": session.id,
            "user_id": session.user_id,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "is_active": session.is_active,
        }
        session_list.append(session_info)

    return session_list


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """
    Clean up expired sessions from database and Redis.

    Args:
        db: Database session

    Returns:
        Number of sessions cleaned up
    """
    # Clean up database
    statement = select(Session).where(
        Session.expires_at < datetime.utcnow(), Session.is_active == True
    )
    result = await db.execute(statement)
    expired_sessions = result.scalars().all()

    for session in expired_sessions:
        session.is_active = False

    await db.commit()

    # Clean up Redis (this will happen automatically with TTL)
    # But we can also manually clean up user sessions
    # Note: In a production environment, you'd want a more sophisticated cleanup

    return len(expired_sessions)
