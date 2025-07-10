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
from app.models.user import User, UserCreate, UserUpdate, UserRole
from app.models.session import Session
from app.models.audit import AuditLog, AuditEventType
from app.config import get_settings
from app.services.email_service import send_email_via_resend
from app.services.redis_service import redis_service

settings = get_settings()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email address with caching.

    Args:
        db: Database session
        email: User's email address

    Returns:
        User object if found, None otherwise
    """
    # Check cache first
    cache_key = f"user_email:{email}"
    cached_user = redis_service.get_cache(cache_key)
    if cached_user:
        # Convert cached data back to User object
        try:
            # Convert role string back to UserRole enum if needed
            if cached_user.get("role"):
                from app.models.user import UserRole

                if isinstance(cached_user["role"], str):
                    cached_user["role"] = UserRole(cached_user["role"])

            # Convert datetime strings back to datetime objects
            from datetime import datetime
            from uuid import UUID

            # Convert UUID string back to UUID object
            if cached_user.get("id"):
                cached_user["id"] = UUID(cached_user["id"])

            datetime_fields = [
                "account_locked_until",
                "last_login",
                "email_verified_at",
                "created_at",
                "updated_at",
            ]
            for field in datetime_fields:
                if cached_user.get(field):
                    cached_user[field] = datetime.fromisoformat(cached_user[field])

            return User(**cached_user)
        except Exception as e:
            # If cache data is corrupted, ignore it and fetch from DB
            print(f"Cache data corrupted for {email}: {e}")
            redis_service.delete(cache_key)

    # Query database
    statement = select(User).where(User.email == email)
    result = await db.execute(statement)
    user = result.scalars().first()

    # Cache user data for 5 minutes
    if user:
        user_dict = {
            "id": str(user.id),  # Convert UUID to string for JSON serialization
            "email": user.email,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            # Always store role as string for cache consistency
            "role": (
                user.role.value
                if hasattr(user.role, "value")
                else str(user.role) if user.role else None
            ),
            "failed_login_attempts": user.failed_login_attempts,
            "account_locked_until": (
                user.account_locked_until.isoformat()
                if user.account_locked_until
                else None
            ),
            # Add missing datetime fields
            "is_superuser": user.is_superuser,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "email_verified_at": (
                user.email_verified_at.isoformat() if user.email_verified_at else None
            ),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "oauth_provider": user.oauth_provider,
            "oauth_sub": user.oauth_sub,
            "avatar_url": user.avatar_url,
        }
        redis_service.set_cache(cache_key, user_dict, expire=300)

    return user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username with caching.

    Args:
        db: Database session
        username: Username

    Returns:
        User object if found, None otherwise
    """
    # Check cache first
    cache_key = f"user_username:{username}"
    cached_user = redis_service.get_cache(cache_key)
    if cached_user:
        # Convert cached data back to User object
        try:
            # Convert role string back to UserRole enum if needed
            if cached_user.get("role"):
                from app.models.user import UserRole

                if isinstance(cached_user["role"], str):
                    cached_user["role"] = UserRole(cached_user["role"])

            # Convert datetime strings back to datetime objects
            from datetime import datetime
            from uuid import UUID

            # Convert UUID string back to UUID object
            if cached_user.get("id"):
                cached_user["id"] = UUID(cached_user["id"])

            datetime_fields = [
                "account_locked_until",
                "last_login",
                "email_verified_at",
                "created_at",
                "updated_at",
            ]
            for field in datetime_fields:
                if cached_user.get(field):
                    cached_user[field] = datetime.fromisoformat(cached_user[field])

            return User(**cached_user)
        except Exception as e:
            # If cache data is corrupted, ignore it and fetch from DB
            print(f"Cache data corrupted for username {username}: {e}")
            redis_service.delete(cache_key)

    # Query database
    statement = select(User).where(User.username == username)
    result = await db.execute(statement)
    user = result.scalars().first()

    # Cache user data for 5 minutes
    if user:
        user_dict = {
            "id": str(user.id),  # Convert UUID to string for JSON serialization
            "email": user.email,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            # Always store role as string for cache consistency
            "role": (
                user.role.value
                if hasattr(user.role, "value")
                else str(user.role) if user.role else None
            ),
            "failed_login_attempts": user.failed_login_attempts,
            "account_locked_until": (
                user.account_locked_until.isoformat()
                if user.account_locked_until
                else None
            ),
            # Add missing datetime fields
            "is_superuser": user.is_superuser,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "email_verified_at": (
                user.email_verified_at.isoformat() if user.email_verified_at else None
            ),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "oauth_provider": user.oauth_provider,
            "oauth_sub": user.oauth_sub,
            "avatar_url": user.avatar_url,
        }
        redis_service.set_cache(cache_key, user_dict, expire=300)

    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """
    Get user by ID with caching.

    Args:
        db: Database session
        user_id: User ID (UUID string)

    Returns:
        User object if found, None otherwise
    """
    # Check cache first
    cache_key = f"user_id:{user_id}"
    cached_user = redis_service.get_cache(cache_key)
    if cached_user:
        # Convert cached data back to User object
        try:
            # Convert role string back to UserRole enum if needed
            if cached_user.get("role"):
                from app.models.user import UserRole

                if isinstance(cached_user["role"], str):
                    cached_user["role"] = UserRole(cached_user["role"])

            # Convert datetime strings back to datetime objects
            from datetime import datetime
            from uuid import UUID

            # Convert UUID string back to UUID object
            if cached_user.get("id"):
                cached_user["id"] = UUID(cached_user["id"])

            datetime_fields = [
                "account_locked_until",
                "last_login",
                "email_verified_at",
                "created_at",
                "updated_at",
            ]
            for field in datetime_fields:
                if cached_user.get(field):
                    cached_user[field] = datetime.fromisoformat(cached_user[field])

            return User(**cached_user)
        except Exception as e:
            # If cache data is corrupted, ignore it and fetch from DB
            print(f"Cache data corrupted for user_id {user_id}: {e}")
            redis_service.delete(cache_key)

    # Query database
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalars().first()

    # Cache user data for 5 minutes
    if user:
        user_dict = {
            "id": str(user.id),  # Convert UUID to string for JSON serialization
            "email": user.email,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            # Always store role as string for cache consistency
            "role": (
                user.role.value
                if hasattr(user.role, "value")
                else str(user.role) if user.role else None
            ),
            "failed_login_attempts": user.failed_login_attempts,
            "account_locked_until": (
                user.account_locked_until.isoformat()
                if user.account_locked_until
                else None
            ),
            # Add missing datetime fields
            "is_superuser": user.is_superuser,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "email_verified_at": (
                user.email_verified_at.isoformat() if user.email_verified_at else None
            ),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "oauth_provider": user.oauth_provider,
            "oauth_sub": user.oauth_sub,
            "avatar_url": user.avatar_url,
        }
        redis_service.set_cache(cache_key, user_dict, expire=300)

    return user


def _invalidate_user_cache(user: User) -> None:
    """Invalidate all cached data for a user."""
    if user:
        redis_service.delete(f"user_id:{user.id}")
        redis_service.delete(f"user_email:{user.email}")
        redis_service.delete(f"user_username:{user.username}")


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

    # Determine role - default to USER for new registrations
    role = user_create.role if user_create.role is not None else UserRole.USER

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
        role=role,
    )

    # Add to database
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Cache the new user
    user_dict = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "hashed_password": user.hashed_password,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        # Always store role as string for cache consistency
        "role": (
            user.role.value
            if hasattr(user.role, "value")
            else str(user.role) if user.role else None
        ),
        "failed_login_attempts": user.failed_login_attempts,
        "account_locked_until": (
            user.account_locked_until.isoformat() if user.account_locked_until else None
        ),
        # Add missing datetime fields
        "is_superuser": user.is_superuser,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "email_verified_at": (
            user.email_verified_at.isoformat() if user.email_verified_at else None
        ),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "oauth_provider": user.oauth_provider,
        "oauth_sub": user.oauth_sub,
        "avatar_url": user.avatar_url,
    }
    redis_service.set_cache(f"user_id:{user.id}", user_dict, expire=300)
    redis_service.set_cache(f"user_email:{user.email}", user_dict, expire=300)
    redis_service.set_cache(f"user_username:{user.username}", user_dict, expire=300)

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
            user_id=str(user.id),
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

        # Lock account after configurable failed attempts
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            user.account_locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES
            )

            # Create audit log for account lock
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.ACCOUNT_LOCKED,
                event_description=f"Account locked due to {user.failed_login_attempts} failed login attempts",
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
            db.add(audit_log)

            # Send lockout notification email (fire and forget)
            if user.email:
                try:
                    import asyncio

                    asyncio.create_task(
                        send_email_via_resend(
                            to_email=user.email,
                            subject="Your account has been locked",
                            html_body=f"""
                                <p>Hello {user.username},</p>
                                <p>Your account has been locked due to too many failed login attempts.</p>
                                <p>It will be unlocked after {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes.</p>
                                <p>If this wasn't you, please contact support immediately.</p>
                                <p>Thank you,<br/>Security Team</p>
                            """,
                        )
                    )
                except Exception as e:
                    # Log but do not block login flow
                    print(f"Failed to send lockout email: {e}")

        # Create audit log for failed login
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.LOGIN_FAILED,
            event_description=f"Failed login attempt for user: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Invalid password",
        )
        db.add(audit_log)

        await db.commit()
        return None

    # Check if user is active
    if not user.is_active:
        # Create audit log for inactive user login attempt
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            event_description=f"Login attempt on inactive account: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Account is inactive",
        )
        db.add(audit_log)
        await db.commit()
        return None

    # Enforce email verification before allowing login, except in DEBUG mode
    if not user.is_verified and not settings.DEBUG:
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            event_description=f"Login attempt with unverified email: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Email not verified",
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
        user_id=str(user.id),
        username=user.username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )
    db.add(audit_log)

    await db.commit()
    return user


async def update_user(
    db: AsyncSession, user_id: str, user_update: UserUpdate
) -> Optional[User]:
    """
    Update user information.

    Args:
        db: Database session
        user_id: User ID (UUID string)
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

    # Invalidate user cache after update
    _invalidate_user_cache(user)

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
