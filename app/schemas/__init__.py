"""
Pydantic schemas for request/response validation.

This package contains all the Pydantic models used for API
request validation and response serialization.
"""

from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    UserProfileResponse,
    AuthResponse,
    ErrorResponse,
    PasswordChangeRequest,
    SessionInfo,
    UserSessionsResponse,
)

__all__ = [
    # Authentication schemas
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
    "LogoutRequest",
    "TokenResponse",
    "UserProfileResponse",
    "AuthResponse",
    "ErrorResponse",
    "PasswordChangeRequest",
    "SessionInfo",
    "UserSessionsResponse",
]
