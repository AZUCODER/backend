"""
Authentication endpoints.

This module contains all authentication-related API endpoints including
user registration, login, logout, token refresh, and profile management.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.dependencies import (
    get_db,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
    require_role,
    require_verified_user,
    require_verified_user_debug_aware,
)
from app.models.user import User, UserCreate, UserRole
from app.models.session import SessionCreate
from app.models.audit import AuditLog, AuditEventType
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    UserProfileResponse,
    ProfileUpdate,
    AuthResponse,
    ErrorResponse,
    UserSessionsResponse,
    SessionInfo,
    PasswordResetRequest,
    PasswordResetComplete,
    EmailVerificationRequest,
    ResendVerificationRequest,
)
from app.services.user_service import (
    create_user,
    authenticate_user,
    check_user_exists,
    get_user_by_id,
    get_user_by_email,
)
from app.services.session_service import (
    create_user_session,
    refresh_access_token,
    revoke_session,
    revoke_all_user_sessions,
    get_user_sessions,
)
from app.services.password_reset_service import (
    create_password_reset_token,
    consume_password_reset_token,
    send_password_reset_email,
)
from app.core.security import get_password_hash
from app.services.email_verification_service import (
    create_verification_token,
    consume_verification_token,
    send_verification_email,
)
from app.config import get_settings
from app.utils.url_utils import build_frontend_url

router = APIRouter()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email and username validation",
)
async def register(
    user_data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user.

    - **email**: User's email address (must be unique)
    - **username**: Username (3-50 chars, alphanumeric and underscores only)
    - **password**: Password (min 8 chars, must contain uppercase, lowercase, and number)
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    - **full_name**: Optional full name
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Check if user already exists
    existing = await check_user_exists(db, user_data.email, user_data.username)

    if existing["email_exists"]:
        # Create audit log for registration attempt with existing email
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"Registration attempt with existing email: {user_data.email}",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Email already registered",
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    if existing["username_exists"]:
        # Create audit log for registration attempt with existing username
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"Registration attempt with existing username: {user_data.username}",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Username already taken",
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Create user
    user_create = UserCreate(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        full_name=user_data.full_name,
    )

    try:
        user = await create_user(db, user_create)

        # Generate email verification token and send email (fire and forget)
        try:
            if user.id is None:
                raise ValueError("User ID cannot be None")
            token = await create_verification_token(db, user.id, user.username)
            import asyncio

            asyncio.create_task(
                send_verification_email(db, user.email, user.username, token)
            )
        except Exception as e:
            # Log email sending failure but do not block registration
            print(f"Failed to send verification email: {e}")

        # Create audit log for successful registration
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"User registered successfully: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        db.add(audit_log)
        await db.commit()

        return AuthResponse(
            message="User registered successfully. Please check your email to verify your account.",
            success=True,
            data={
                "user_id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_verified": user.is_verified,
            },
        )

    except Exception as e:
        # Create audit log for registration failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"Registration failed for email: {user_data.email}",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=str(e),
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    login_data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> Any:
    """
    User login.

    - **email_or_username**: Email address or username
    - **password**: User password

    Returns JWT access and refresh tokens for authenticated user.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Authenticate user
    user = await authenticate_user(
        db=db,
        email_or_username=login_data.email_or_username,
        password=login_data.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create session and tokens
    session_data = SessionCreate(
        user_agent=user_agent,
        ip_address=ip_address,
        device_info=f"{user_agent[:100]}..." if len(user_agent) > 100 else user_agent,
    )
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User ID is missing",
        )

    token_data = await create_user_session(
        db=db, user=user, ip_address=ip_address, user_agent=user_agent
    )

    return TokenResponse(**token_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Refresh access token.

    - **refresh_token**: Valid refresh token

    Returns new JWT access and refresh tokens.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Refresh tokens
    token_data = await refresh_access_token(
        db=db,
        refresh_token=refresh_data.refresh_token,
    )

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(**token_data)


@router.post(
    "/logout",
    response_model=AuthResponse,
    summary="User logout",
    description="Logout user and revoke session(s)",
)
async def logout(
    logout_data: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    User logout.

    - **session_id**: Optional specific session ID to logout
    - **logout_all**: Whether to logout from all devices/sessions

    Revokes the specified session or all user sessions.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    if logout_data.logout_all:
        # Logout from all sessions
        # Check if current_user.id is not None before passing to revoke_all_user_sessions
        if current_user.id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required for logout",
            )

        revoked_count = await revoke_all_user_sessions(
            db=db,
            user_id=str(current_user.id),
            reason="User requested logout from all devices",
        )

        return AuthResponse(
            message=f"Logged out from all devices ({revoked_count} sessions revoked)",
            success=True,
            data={"revoked_sessions": revoked_count},
        )

    else:
        # Logout from specific session or current session
        session_id = logout_data.session_id

        # If no session ID provided, we would need to get it from the token
        # For now, we'll revoke the most recent active session
        if not session_id:
            # Check if current_user.id is not None before passing to get_user_sessions
            if current_user.id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User ID is required for logout",
                )

            user_sessions = await get_user_sessions(db, current_user.id)
            if user_sessions:
                session_id = user_sessions[0].id

        if session_id:
            success = await revoke_session(
                db=db,
                user_id=str(current_user.id),
                session_id=session_id,
                reason="User logout",
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if success:
                return AuthResponse(
                    message="Logged out successfully",
                    success=True,
                    data={"session_id": session_id},
                )

        return AuthResponse(message="No active session found to logout", success=True)


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Get authenticated user's profile information",
)
async def get_current_user_profile(
    current_user: User = Depends(require_verified_user_debug_aware),
) -> Any:
    """
    Get current user profile.

    Returns the authenticated user's profile information including:
    - Basic profile data (name, email, username)
    - Account status (active, verified, role)
    - Timestamps (created, last login, email verified)
    """
    return UserProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        role=current_user.role.value,
        created_at=(
            current_user.created_at.isoformat() if current_user.created_at else ""
        ),
        last_login=(
            current_user.last_login.isoformat() if current_user.last_login else None
        ),
        email_verified_at=(
            current_user.email_verified_at.isoformat()
            if current_user.email_verified_at
            else None
        ),
    )


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update own profile",
    description="Authenticated users can update permitted profile fields.",
)
async def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: User = Depends(require_verified_user_debug_aware),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Update current user's profile.

    Allows authenticated users to update their own profile fields:
    - Email (must be unique)
    - Username (must be unique, 3-50 chars, alphanumeric + underscores)
    - First name, last name, full name

    Returns the updated user profile.
    """
    # Get client information for audit logging
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    try:
        # Check for email uniqueness if email is being updated
        if payload.email and payload.email != current_user.email:
            existing_user = await get_user_by_email(db, payload.email)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use by another user",
                )

        # Check for username uniqueness if username is being updated
        if payload.username and payload.username != current_user.username:
            existing = await check_user_exists(db, email="", username=payload.username)
            if existing["username_exists"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        # Update user fields
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)

        # If email was updated, mark as unverified and send new verification
        if payload.email and payload.email != current_user.email:
            current_user.is_verified = False
            current_user.email_verified_at = None

            # Send new verification email (fire and forget)
            try:
                token = await create_verification_token(
                    db, current_user.id, current_user.username
                )
                import asyncio

                asyncio.create_task(
                    send_verification_email(
                        db, current_user.email, current_user.username, token
                    )
                )
            except Exception as e:
                print(f"Failed to send verification email: {e}")

        # Save changes
        await db.commit()
        await db.refresh(current_user)

        # Create audit log
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_UPDATED,
            event_description=f"Profile updated for user: {current_user.username}",
            user_id=str(current_user.id),
            username=current_user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        db.add(audit_log)
        await db.commit()

        return UserProfileResponse(
            id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            full_name=current_user.full_name,
            is_active=current_user.is_active,
            is_superuser=current_user.is_superuser,
            is_verified=current_user.is_verified,
            role=current_user.role.value,
            created_at=(
                current_user.created_at.isoformat() if current_user.created_at else ""
            ),
            last_login=(
                current_user.last_login.isoformat() if current_user.last_login else None
            ),
            email_verified_at=(
                current_user.email_verified_at.isoformat()
                if current_user.email_verified_at
                else None
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        # Create audit log for failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_UPDATED,
            event_description=f"Profile update failed for user: {current_user.username}",
            user_id=str(current_user.id),
            username=current_user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=str(e),
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed",
        )


@router.get(
    "/sessions",
    response_model=UserSessionsResponse,
    summary="Get user sessions",
    description="Get all active sessions for the authenticated user (user or admin only)",
)
async def get_user_sessions_endpoint(
    current_user: User = Depends(require_role(UserRole.USER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Guests are not allowed to access session management
    return await get_user_sessions(db, str(current_user.id))


@router.delete(
    "/sessions/{session_id}",
    response_model=AuthResponse,
    summary="Revoke specific session",
    description="Revoke a specific session by ID (user or admin only)",
)
async def revoke_session_endpoint(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_role(UserRole.USER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Guests are not allowed to revoke sessions
    return await revoke_session(
        db=db,
        user_id=str(current_user.id),
        session_id=session_id,
        reason="User revoked specific session",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


@router.post(
    "/logout-everywhere",
    response_model=AuthResponse,
    summary="Log out everywhere",
    description="Log out from all devices (user or admin only)",
)
async def logout_everywhere_endpoint(
    request: Request,
    current_user: User = Depends(require_role(UserRole.USER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    # Guests are not allowed to log out everywhere
    await revoke_all_user_sessions(
        db=db,
        user_id=str(current_user.id),
        reason="User logout everywhere",
    )
    return AuthResponse(message="Logged out everywhere", success=True)


@router.post(
    "/forgot-password",
    response_model=AuthResponse,
    summary="Request password reset",
    description="Send password reset email to user",
)
async def forgot_password(
    reset_request: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Request password reset.

    - **email**: Email address to send reset link to

    Sends a password reset email if the user exists.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Find user by email
    user = await get_user_by_email(db, reset_request.email)

    if user:
        user_id = user.id
        username = user.username
        email = user.email
        # Create password reset token
        if user_id is not None:
            token = await create_password_reset_token(db, user_id, username)
            # Build reset URL (frontend should handle this)
            reset_url = build_frontend_url(f"reset-password?token={token}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
            )

        # Send email (fire and forget)
        try:
            import asyncio

            asyncio.create_task(
                send_password_reset_email(db, email, username, reset_url)
            )
        except Exception as e:
            print(f"Failed to send password reset email: {e}")

        # Create audit log for password reset request
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.PASSWORD_RESET_REQUESTED,
            event_description=f"Password reset requested for user: {username}",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        db.add(audit_log)
        await db.commit()

    return AuthResponse(
        message="If the email exists, a password reset link has been sent.",
        success=True,
    )


@router.post(
    "/reset-password",
    response_model=AuthResponse,
    summary="Complete password reset",
    description="Reset password using token",
)
async def reset_password(
    reset_data: PasswordResetComplete,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Complete password reset.

    - **token**: Password reset token
    - **new_password**: New password

    Resets the user's password using the provided token.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Consume the token and get the user info
    user_info = await consume_password_reset_token(db, reset_data.token)

    if not user_info:
        # Create audit log for invalid token
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.PASSWORD_RESET_COMPLETED,
            event_description="Password reset attempt with invalid token",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Invalid or expired token",
        )
        db.add(audit_log)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id, username = user_info

    # Get the user object for password update
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    # Update user's password
    user.hashed_password = get_password_hash(reset_data.new_password)
    user.updated_at = datetime.utcnow()

    # Revoke all existing sessions for security
    await revoke_all_user_sessions(
        db, user_id, reason="Password reset - security logout"
    )

    # Create audit log for successful password reset
    audit_log = AuditLog.create_log(
        event_type=AuditEventType.PASSWORD_RESET_COMPLETED,
        event_description=f"Password reset completed for user: {username}",
        user_id=str(user_id),
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
    )
    db.add(audit_log)

    await db.commit()

    return AuthResponse(
        message="Password reset successfully. Please login with your new password.",
        success=True,
    )


@router.post(
    "/verify-email",
    response_model=AuthResponse,
    summary="Verify email",
    description="Verify a user's email address using a token sent via email",
)
async def verify_email(
    request_data: EmailVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify a user's email using the token provided."""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    result = await consume_verification_token(db, request_data.token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )

    user_id, username = result
    # Fetch user object directly from DB to ensure it is attached to the session
    from sqlmodel import select  # lazy import to avoid circular
    from app.models.user import User

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Mark the user as verified
    if not user.is_verified:
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        await db.commit()

        # Invalidate cached user data so the updated verification status is used
        try:
            from app.services.user_service import _invalidate_user_cache  # noqa: WPS433

            _invalidate_user_cache(user)
        except Exception as cache_exc:  # pragma: no cover
            import logging

            logging.getLogger(__name__).warning(
                "Failed to invalidate user cache after verification: %s", cache_exc
            )

    return AuthResponse(
        message="Email verified successfully. You can now log in.",
        success=True,
    )


@router.post(
    "/resend-verification",
    response_model=AuthResponse,
    summary="Resend verification email",
    description="Send a new verification email to an unverified user",
)
async def resend_verification_email(
    request_data: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Resend verification email if the user is not verified yet."""
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    user = await get_user_by_email(db, request_data.email)
    if not user or user.is_verified:
        # Do not reveal whether email exists for security reasons
        return AuthResponse(
            message="If the email exists and is not verified, a verification link has been sent.",
            success=True,
        )
    # Generate new token and send email
    if user.id is not None:
        token = await create_verification_token(db, user.id, user.username)
        try:
            await send_verification_email(db, user.email, user.username, token)
        except Exception as e:
            print(f"Failed to resend verification email: {e}")

    return AuthResponse(
        message="If the email exists and is not verified, a verification link has been sent.",
        success=True,
    )
