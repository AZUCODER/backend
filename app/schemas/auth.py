"""
Authentication schemas for request/response validation.

This module contains Pydantic models for authentication-related
API requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class LoginRequest(BaseModel):
    """User login request schema."""

    email_or_username: str = Field(
        ..., min_length=3, max_length=255, description="Email address or username"
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )


class RegisterRequest(BaseModel):
    """User registration request schema."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 characters, alphanumeric and underscores only)",
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="Password (minimum 8 characters)"
    )
    first_name: Optional[str] = Field(
        None, max_length=100, description="User's first name"
    )
    last_name: Optional[str] = Field(
        None, max_length=100, description="User's last name"
    )
    full_name: Optional[str] = Field(
        None, max_length=200, description="User's full name"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    session_id: int = Field(..., description="Session ID")


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request schema."""

    session_id: Optional[int] = Field(
        None, description="Specific session ID to logout (optional)"
    )
    logout_all: bool = Field(
        default=False, description="Logout from all devices/sessions"
    )


class UserProfileResponse(BaseModel):
    """User profile response schema."""

    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: str  # ISO format datetime string
    last_login: Optional[str] = None  # ISO format datetime string
    email_verified_at: Optional[str] = None  # ISO format datetime string


class AuthResponse(BaseModel):
    """Generic authentication response."""

    message: str
    success: bool = True
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str
    error_code: Optional[str] = None
    success: bool = False


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""

    current_password: str = Field(
        ..., min_length=8, max_length=128, description="Current password"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v


class SessionInfo(BaseModel):
    """Session information schema."""

    id: int
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str  # ISO format datetime string
    last_used_at: str  # ISO format datetime string
    expires_at: str  # ISO format datetime string
    is_current: bool = False


class UserSessionsResponse(BaseModel):
    """User sessions response schema."""

    sessions: list[SessionInfo]
    total_sessions: int
    active_sessions: int


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr = Field(..., description="Email address to send reset link to")


class PasswordResetComplete(BaseModel):
    """Password reset completion schema."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ..., min_length=8, max_length=128, description="New password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v


class EmailVerificationRequest(BaseModel):
    """Request body for verifying email with token."""

    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseModel):
    """Request to resend verification link."""

    email: EmailStr = Field(..., description="User email address")
