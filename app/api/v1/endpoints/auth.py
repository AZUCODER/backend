"""
Authentication endpoints.

This module contains all authentication-related API endpoints including
user registration, login, logout, token refresh, and profile management.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
)
from app.models.user import User, UserCreate
from app.models.session import SessionCreate
from app.models.audit import AuditLog, AuditEventType
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    UserProfileResponse,
    AuthResponse,
    ErrorResponse,
    UserSessionsResponse,
    SessionInfo,
)
from app.services.user_service import (
    create_user,
    authenticate_user,
    check_user_exists,
    get_user_by_id,
)
from app.services.session_service import (
    create_user_session,
    refresh_access_token,
    revoke_session,
    revoke_all_user_sessions,
    get_user_sessions,
)

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

        # Create audit log for successful registration
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"User registered successfully: {user.username}",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        db.add(audit_log)
        await db.commit()

        return AuthResponse(
            message="User registered successfully",
            success=True,
            data={
                "user_id": user.id,
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
        db=db, user_id=user.id, session_data=session_data, ip_address=ip_address
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
        ip_address=ip_address,
        user_agent=user_agent,
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
            user_id=current_user.id,
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
            
            user_sessions = await get_user_sessions(
                db, current_user.id, active_only=True
            )
            if user_sessions:
                session_id = user_sessions[0].id

        if session_id:
            success = await revoke_session(
                db=db,
                session_id=session_id,
                user_id=current_user.id,  # type: ignore
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
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user profile.

    Returns the authenticated user's profile information.
    """
    return UserProfileResponse(
        id=current_user.id if current_user.id is not None else 0,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat(),
        last_login=(
            current_user.last_login.isoformat() if current_user.last_login else None
        ),
        email_verified_at=(
            current_user.email_verified_at.isoformat()
            if current_user.email_verified_at
            else None
        ),
    )


@router.get(
    "/sessions",
    response_model=UserSessionsResponse,
    summary="Get user sessions",
    description="Get all active sessions for the authenticated user",
)
async def get_user_sessions_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get user sessions.

    Returns all active sessions for the authenticated user.
    """
    if current_user.id is None:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    user_sessions = await get_user_sessions(db, current_user.id, active_only=True)

    sessions_info = []
    for session in user_sessions:
        session_info = SessionInfo(
            id=session.id if session.id is not None else 0,
            device_info=session.device_info,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            created_at=session.created_at.isoformat(),
            last_used_at=session.last_used_at.isoformat(),
            expires_at=session.expires_at.isoformat(),
            is_current=False,  # We'd need token info to determine current session
        )
        sessions_info.append(session_info)

    return UserSessionsResponse(
        sessions=sessions_info,
        total_sessions=len(sessions_info),
        active_sessions=len(
            [s for s in user_sessions if s.is_active and not s.is_revoked]
        ),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=AuthResponse,
    summary="Revoke specific session",
    description="Revoke a specific session by ID",
)
async def revoke_session_endpoint(
    session_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Revoke specific session.

    - **session_id**: ID of the session to revoke

    Revokes the specified session for the authenticated user.
    """
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    success = await revoke_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id if current_user.id is not None else 0,
        reason="Session revoked by user",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked",
        )

    return AuthResponse(
        message="Session revoked successfully",
        success=True,
        data={"session_id": session_id},
    )
