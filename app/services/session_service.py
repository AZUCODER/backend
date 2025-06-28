"""
Session service for JWT token and session management.

This module contains business logic for managing user sessions,
JWT tokens, and token blacklisting for security.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc
from sqlmodel import select

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.models.session import Session, BlacklistedToken, SessionCreate
from app.models.audit import AuditLog, AuditEventType
from app.config import get_settings

settings = get_settings()


async def create_user_session(
    db: AsyncSession,
    user_id: int,
    session_data: SessionCreate,
    ip_address: Optional[str] = None,
) -> dict:
    """
    Create a new user session with access and refresh tokens.

    Args:
        db: Database session
        user_id: User ID
        session_data: Session creation data
        ip_address: Client IP address

    Returns:
        Dict with access_token, refresh_token, and session info
    """
    # Generate tokens
    access_token = create_access_token(subject=str(user_id))
    refresh_token = create_refresh_token(subject=str(user_id))

    # Generate session JTI (unique identifier)
    access_token_jti = secrets.token_urlsafe(32)

    # Create session record
    session = Session(
        user_id=user_id,
        refresh_token=refresh_token,
        access_token_jti=access_token_jti,
        user_agent=session_data.user_agent,
        ip_address=ip_address or session_data.ip_address,
        device_info=session_data.device_info,
        expires_at=datetime.utcnow()
        + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
        is_active=True,
        is_revoked=False,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "session_id": session.id,
    }


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[dict]:
    """
    Refresh access token using refresh token.

    Args:
        db: Database session
        refresh_token: Refresh token
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        Dict with new tokens if successful, None otherwise
    """
    # Find session by refresh token
    statement = select(Session).where(
        Session.refresh_token == refresh_token,
        Session.is_active == True,
        Session.is_revoked == False,
    )
    result = await db.execute(statement)
    session = result.scalars().first()

    if not session:
        return None

    # Check if session is expired
    if session.expires_at < datetime.utcnow():
        # Mark session as revoked
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = "Session expired"
        await db.commit()
        return None

    # Generate new tokens
    access_token = create_access_token(subject=str(session.user_id))
    new_refresh_token = create_refresh_token(subject=str(session.user_id))

    # Update session
    session.refresh_token = new_refresh_token
    session.access_token_jti = secrets.token_urlsafe(32)
    session.last_used_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()

    # Update IP and user agent if provided
    if ip_address:
        session.ip_address = ip_address
    if user_agent:
        session.user_agent = user_agent

    await db.commit()
    await db.refresh(session)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "session_id": session.id,
    }


async def revoke_session(
    db: AsyncSession,
    session_id: int,
    user_id: int,
    reason: str = "User logout",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> bool:
    """
    Revoke a user session.

    Args:
        db: Database session
        session_id: Session ID to revoke
        user_id: User ID (for security check)
        reason: Reason for revocation
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        True if session was revoked, False otherwise
    """
    # Find session
    statement = select(Session).where(
        Session.id == session_id, Session.user_id == user_id, Session.is_active == True
    )
    result = await db.execute(statement)
    session = result.scalars().first()

    if not session:
        return False

    # Revoke session
    session.is_revoked = True
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = reason

    # Create audit log
    audit_log = AuditLog.create_log(
        event_type=AuditEventType.LOGOUT,
        event_description=f"Session revoked: {reason}",
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )
    db.add(audit_log)

    await db.commit()
    return True


async def revoke_all_user_sessions(
    db: AsyncSession,
    user_id: int,
    reason: str = "Security logout",
    except_session_id: Optional[int] = None,
) -> int:
    """
    Revoke all active sessions for a user.

    Args:
        db: Database session
        user_id: User ID
        reason: Reason for revocation
        except_session_id: Session ID to exclude from revocation

    Returns:
        Number of sessions revoked
    """
    # Find all active sessions for user
    statement = select(Session).where(
        Session.user_id == user_id,
        Session.is_active == True,
        Session.is_revoked == False,
    )

    if except_session_id:
        statement = statement.where(Session.id != except_session_id)

    result = await db.execute(statement)
    sessions = result.scalars().all()

    # Revoke all sessions
    revoked_count = 0
    for session in sessions:
        session.is_revoked = True
        session.revoked_at = datetime.utcnow()
        session.revoked_reason = reason
        revoked_count += 1

    if revoked_count > 0:
        # Create audit log
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.LOGOUT,
            event_description=f"All sessions revoked: {reason} ({revoked_count} sessions)",
            user_id=user_id,
            success=True,
        )
        db.add(audit_log)

        await db.commit()

    return revoked_count


async def blacklist_token(
    db: AsyncSession,
    jti: str,
    token_type: str,
    user_id: int,
    expires_at: datetime,
    session_id: Optional[int] = None,
    reason: str = "Token revoked",
) -> BlacklistedToken:
    """
    Add token to blacklist.

    Args:
        db: Database session
        jti: JWT ID
        token_type: Type of token ('access' or 'refresh')
        user_id: User ID
        expires_at: Token expiration time
        session_id: Associated session ID
        reason: Reason for blacklisting

    Returns:
        BlacklistedToken object
    """
    blacklisted_token = BlacklistedToken(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        session_id=session_id,
        expires_at=expires_at,
        revoked_reason=reason,
    )

    db.add(blacklisted_token)
    await db.commit()
    await db.refresh(blacklisted_token)

    return blacklisted_token


async def is_token_blacklisted(db: AsyncSession, jti: str) -> bool:
    """
    Check if token is blacklisted.

    Args:
        db: Database session
        jti: JWT ID to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    statement = select(BlacklistedToken).where(
        BlacklistedToken.jti == jti, BlacklistedToken.expires_at > datetime.utcnow()
    )
    result = await db.execute(statement)
    return result.scalars().first() is not None


async def get_user_sessions(
    db: AsyncSession, user_id: int, active_only: bool = True
) -> list[Session]:
    """
    Get all sessions for a user.

    Args:
        db: Database session
        user_id: User ID
        active_only: Only return active sessions

    Returns:
        List of Session objects
    """
    statement = select(Session).where(Session.user_id == user_id)

    if active_only:
        statement = statement.where(
            Session.is_active == True, Session.is_revoked == False
        )

    statement = statement.order_by(Session.last_used_at.desc())  # type: ignore
    result = await db.execute(statement)
    return list(result.scalars().all())


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """
    Clean up expired sessions and blacklisted tokens.

    Args:
        db: Database session

    Returns:
        Number of items cleaned up
    """
    now = datetime.utcnow()

    # Find expired sessions
    expired_sessions_statement = select(Session).where(
        Session.expires_at < now, Session.is_revoked == False
    )
    expired_sessions_result = await db.execute(expired_sessions_statement)
    expired_sessions = expired_sessions_result.scalars().all()

    # Mark expired sessions as revoked
    for session in expired_sessions:
        session.is_revoked = True
        session.revoked_at = now
        session.revoked_reason = "Expired"

    # Find expired blacklisted tokens
    expired_tokens_statement = select(BlacklistedToken).where(
        BlacklistedToken.expires_at < now
    )
    expired_tokens_result = await db.execute(expired_tokens_statement)
    expired_tokens = expired_tokens_result.scalars().all()

    # Delete expired blacklisted tokens
    for token in expired_tokens:
        await db.delete(token)

    cleanup_count = len(expired_sessions) + len(expired_tokens)

    if cleanup_count > 0:
        await db.commit()

    return cleanup_count
