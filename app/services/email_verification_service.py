from __future__ import annotations

"""Email verification token service.

Handles creation, validation, consumption, and email delivery for email verification
links that activate a user account.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.models.audit import AuditLog, AuditEventType
from app.services.email_service import send_email_via_resend
from app.utils.url_utils import build_frontend_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_token(token: str) -> str:
    """Return SHA-256 hash for the given token."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Token lifecycle
# ---------------------------------------------------------------------------


async def create_verification_token(
    db: AsyncSession,
    user_id: int,
    username: str,
    expires_in_hours: int = 48,
) -> str:
    """Create a unique verification token and persist it.

    Returns the **plain token** (not hashed) so it can be e-mailed to the user.
    """
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    issued_at = datetime.utcnow()
    expires_at = issued_at + timedelta(hours=expires_in_hours)

    # Invalidate any previous unused tokens for this user
    await invalidate_existing_tokens(db, user_id)

    record = EmailVerificationToken(
        user_id=user_id,
        token_hash=token_hash,
        issued_at=issued_at,
        expires_at=expires_at,
        used=False,
    )
    db.add(record)
    await db.commit()

    # Audit
    db.add(
        AuditLog.create_log(
            event_type=AuditEventType.EMAIL_VERIFICATION_CREATED,
            event_description=f"Verification token created for user: {username}",
            user_id=user_id,
            username=username,
            success=True,
        )
    )
    await db.commit()

    return token


async def validate_verification_token(
    db: AsyncSession, token: str
) -> Optional[tuple[int, str]]:
    """Return (user_id, username) if token is valid and not yet consumed."""
    token_hash = _hash_token(token)
    stmt = select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash == token_hash,
        getattr(EmailVerificationToken, "used").is_(False),
        EmailVerificationToken.expires_at > datetime.utcnow(),
    )
    res = await db.execute(stmt)
    record = res.scalars().first()
    if not record:
        return None

    # fetch user details
    stmt = select(User.id, User.username).where(User.id == record.user_id)
    res = await db.execute(stmt)
    info = res.first()
    if not info:
        return None
    return info[0], info[1]


async def consume_verification_token(
    db: AsyncSession, token: str
) -> Optional[tuple[int, str]]:
    """Mark token as used and return (user_id, username)."""
    token_hash = _hash_token(token)
    stmt = select(EmailVerificationToken).where(
        EmailVerificationToken.token_hash == token_hash,
        getattr(EmailVerificationToken, "used").is_(False),
        EmailVerificationToken.expires_at > datetime.utcnow(),
    )
    res = await db.execute(stmt)
    record = res.scalars().first()
    if not record:
        return None

    user_id = record.user_id
    record.used = True
    await db.commit()

    stmt = select(User.id, User.username).where(User.id == user_id)
    res = await db.execute(stmt)
    info = res.first()
    if not info:
        return None

    db.add(
        AuditLog.create_log(
            event_type=AuditEventType.EMAIL_VERIFICATION_COMPLETED,
            event_description=f"Email verified for user: {info[1]}",
            user_id=user_id,
            username=info[1],
            success=True,
        )
    )
    await db.commit()

    return info[0], info[1]


async def invalidate_existing_tokens(db: AsyncSession, user_id: int) -> int:
    stmt = select(EmailVerificationToken).where(
        EmailVerificationToken.user_id == user_id,
        getattr(EmailVerificationToken, "used").is_(False),
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    for rec in records:
        rec.used = True
    await db.commit()
    return len(records)


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    stmt = select(EmailVerificationToken).where(
        EmailVerificationToken.expires_at < datetime.utcnow()
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    count = len(records)
    for rec in records:
        await db.delete(rec)
    await db.commit()
    return count


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------


async def send_verification_email(
    db: AsyncSession,
    user_email: str,
    username: str,
    token: str,
) -> bool:
    """Send verification e-mail with the given token."""
    verify_url = build_frontend_url(f"verify-email?token={token}")
    try:
        await send_email_via_resend(
            to_email=user_email,
            subject="Verify your email address",
            html_body=f"""
                <p>Hello {username},</p>
                <p>Thank you for signing up. Please verify your email address by clicking the link below:</p>
                <p><a href=\"{verify_url}\">Verify Email</a></p>
                <p>This link will expire in 48 hours.</p>
                <p>If you didn't create an account, please ignore this email.</p>
                <p>Thank you,<br/>Security Team</p>
            """,
        )
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False
