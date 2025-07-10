"""
Password reset token service for single-use password reset tokens.

This module contains business logic for managing password reset tokens
including generation, validation, and consumption.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import PasswordResetToken, User
from app.models.audit import AuditLog, AuditEventType
from app.services.email_service import send_email_via_resend
from app.config import get_settings

settings = get_settings()


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Args:
        token: Plain text token

    Returns:
        str: Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()


async def create_password_reset_token(
    db: AsyncSession, user_id: str, username: str, expires_in_hours: int = 24
) -> str:
    """
    Create a new password reset token for a user.

    Args:
        db: Database session
        user_id: User ID to create token for
        username: Username for audit log/email
        expires_in_hours: Token expiration time in hours

    Returns:
        str: Plain text token (to be sent to user)
    """
    # Generate a secure random token
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(hours=expires_in_hours)
    await invalidate_existing_tokens(db, user_id)
    reset_token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        issued_at=issued_at,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token)
    await db.commit()
    audit_log = AuditLog.create_log(
        event_type=AuditEventType.PASSWORD_RESET_REQUESTED,
        event_description=f"Password reset token created for user: {username}",
        user_id=str(user_id),
        username=username,
        success=True,
    )
    db.add(audit_log)
    await db.commit()
    return token


async def validate_password_reset_token(
    db: AsyncSession, token: str
) -> Optional[tuple[int, str]]:
    """
    Validate a password reset token and return the associated user info.

    Args:
        db: Database session
        token: Plain text token to validate

    Returns:
        Tuple of (user_id, username) if token is valid, None otherwise
    """
    token_hash = hash_token(token)

    # Find the token
    statement = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow(),
    )
    result = await db.execute(statement)
    reset_token = result.scalars().first()

    if not reset_token:
        return None

    # Get the associated user info
    statement = select(User.id, User.username).where(
        User.id == reset_token.user_id, User.is_active == True
    )
    result = await db.execute(statement)
    user_info = result.first()

    if not user_info:
        return None

    return (user_info[0], user_info[1])


async def consume_password_reset_token(
    db: AsyncSession, token: str
) -> Optional[tuple[int, str]]:
    """
    Consume a password reset token (mark as used) and return the user info.

    Args:
        db: Database session
        token: Plain text token to consume

    Returns:
        Tuple of (user_id, username) if token was valid and consumed, None otherwise
    """
    token_hash = hash_token(token)

    # Find and mark the token as used
    statement = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow(),
    )
    result = await db.execute(statement)
    reset_token = result.scalars().first()

    if not reset_token:
        return None

    # Store user_id before committing to avoid ORM expiration issues
    user_id = reset_token.user_id

    # Mark as used
    reset_token.used = True
    await db.commit()

    # Get the associated user info
    statement = select(User.id, User.username).where(
        User.id == user_id, User.is_active == True
    )
    result = await db.execute(statement)
    user_info = result.first()

    if not user_info:
        return None

    user_id, username = user_info

    # Create audit log
    audit_log = AuditLog.create_log(
        event_type=AuditEventType.PASSWORD_RESET_COMPLETED,
        event_description=f"Password reset token consumed for user: {username}",
        user_id=str(user_id),
        username=username,
        success=True,
    )
    db.add(audit_log)
    await db.commit()

    return (user_id, username)


async def invalidate_existing_tokens(db: AsyncSession, user_id: str) -> int:
    """
    Invalidate all existing password reset tokens for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        int: Number of tokens invalidated
    """
    statement = select(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id, PasswordResetToken.used == False
    )
    result = await db.execute(statement)
    tokens = result.scalars().all()

    for token in tokens:
        token.used = True

    await db.commit()
    return len(tokens)


async def send_password_reset_email(
    db: AsyncSession, user_email: str, username: str, reset_url: str
) -> bool:
    """
    Send password reset email to user.

    Args:
        db: Database session
        user_email: Email to send to
        username: Username for greeting
        reset_url: Password reset URL with token

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        await send_email_via_resend(
            to_email=user_email,
            subject="Password Reset Request",
            html_body=f"""
                <p>Hello {username},</p>
                <p>You have requested a password reset for your account.</p>
                <p>Click the link below to reset your password:</p>
                <p><a href=\"{reset_url}\">Reset Password</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't request this reset, please ignore this email.</p>
                <p>Thank you,<br/>Security Team</p>
            """,
        )
        return True
    except Exception as e:
        print(f"Failed to send password reset email: {e}")
        return False


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """
    Clean up expired password reset tokens.

    Args:
        db: Database session

    Returns:
        int: Number of tokens cleaned up
    """
    statement = select(PasswordResetToken).where(
        PasswordResetToken.expires_at < datetime.utcnow()
    )
    result = await db.execute(statement)
    expired_tokens = result.scalars().all()

    for token in expired_tokens:
        await db.delete(token)

    await db.commit()
    return len(expired_tokens)
