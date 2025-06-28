"""
User service for database operations.

This module contains business logic for user operations including
registration, authentication, and user management.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserCreate, UserUpdate
from app.models.session import Session
from app.models.audit import AuditLog, AuditEventType


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User object if found, None otherwise
    """
    statement = select(User).where(User.email == email)
    result = await db.execute(statement)
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.

    Args:
        db: Database session
        username: Username

    Returns:
        User object if found, None otherwise
    """
    statement = select(User).where(User.username == username)
    result = await db.execute(statement)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get user by ID.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    return result.scalars().first()


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    """
    Create a new user.

    Args:
        db: Database session
        user_create: User creation data

    Returns:
        Created user object
    """
    # Hash the password
    hashed_password = get_password_hash(user_create.password)

    # Create user instance
    user = User(
        email=user_create.email,
        username=user_create.username,
        hashed_password=hashed_password,
        first_name=user_create.first_name,
        last_name=user_create.last_name,
        full_name=user_create.full_name,
        is_active=True,
        is_verified=False,  # Email verification required
    )

    # Add to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    email_or_username: str,
    password: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Optional[User]:
    """
    Authenticate user with email/username and password.

    Args:
        db: Database session
        email_or_username: Email or username
        password: Plain text password
        ip_address: Client IP address
        user_agent: Client user agent

    Returns:
        User object if authentication successful, None otherwise
    """
    # Try to find user by email first, then username
    user = await get_user_by_email(db, email_or_username)
    if not user:
        user = await get_user_by_username(db, email_or_username)

    if not user:
        # Create audit log for failed login attempt
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.LOGIN_FAILED,
            event_description=f"Login attempt with unknown email/username: {email_or_username}",
            username=email_or_username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="User not found",
        )
        db.add(audit_log)
        await db.commit()
        return None

    # Check if account is locked
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        # Create audit log for locked account access attempt
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            event_description=f"Login attempt on locked account: {user.username}",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Account is locked",
        )
        db.add(audit_log)
        await db.commit()
        return None

    # Verify password
    if not verify_password(password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1

        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=30)

            # Create audit log for account lock
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.ACCOUNT_LOCKED,
                event_description=f"Account locked due to {user.failed_login_attempts} failed login attempts",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
            db.add(audit_log)

        # Create audit log for failed login
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.LOGIN_FAILED,
            event_description=f"Failed login attempt for user: {user.username}",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Invalid password",
        )
        db.add(audit_log)

        await db.commit()
        await db.refresh(user)
        return None

    # Check if user is active
    if not user.is_active:
        # Create audit log for inactive user login attempt
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            event_description=f"Login attempt on inactive account: {user.username}",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Account is inactive",
        )
        db.add(audit_log)
        await db.commit()
        return None

    # Successful login - reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.last_login = datetime.utcnow()

    # Create audit log for successful login
    audit_log = AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_description=f"Successful login for user: {user.username}",
        user_id=user.id,
        username=user.username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(user)

    return user


async def update_user(
    db: AsyncSession, user_id: int, user_update: UserUpdate
) -> Optional[User]:
    """
    Update user information.

    Args:
        db: Database session
        user_id: User ID
        user_update: User update data

    Returns:
        Updated user object if found, None otherwise
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    return user


async def check_user_exists(db: AsyncSession, email: str, username: str) -> dict:
    """
    Check if user exists by email or username.

    Args:
        db: Database session
        email: Email to check
        username: Username to check

    Returns:
        Dict with existence status
    """
    email_exists = await get_user_by_email(db, email) is not None
    username_exists = await get_user_by_username(db, username) is not None

    return {
        "email_exists": email_exists,
        "username_exists": username_exists,
        "any_exists": email_exists or username_exists,
    }
