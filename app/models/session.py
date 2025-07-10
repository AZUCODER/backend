"""
Session model for JWT token management.

This module contains the Session SQLModel class for managing user sessions,
token blacklisting, and refresh token tracking.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, Relationship

from app.models.base import BaseModel


class Session(BaseModel, table=True):
    """
    Session model for JWT token management.

    Tracks user sessions, refresh tokens, and provides token blacklisting
    functionality for security.
    """

    __tablename__: str = "sessions"

    # User relationship
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)

    # Token information
    refresh_token: str = Field(unique=True, nullable=False, index=True)
    access_token_jti: Optional[str] = Field(
        default=None, index=True
    )  # JWT ID for access token

    # Session metadata
    user_agent: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)  # Support IPv6
    device_info: Optional[str] = Field(default=None, max_length=200)

    # Session status
    is_active: bool = Field(default=True, nullable=False)
    is_revoked: bool = Field(default=False, nullable=False)

    # Expiration tracking
    expires_at: datetime = Field(nullable=False)
    last_used_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Security tracking
    revoked_at: Optional[datetime] = Field(default=None)
    revoked_reason: Optional[str] = Field(default=None, max_length=100)

    def __repr__(self) -> str:
        """String representation of Session."""
        return (
            f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
        )


class BlacklistedToken(BaseModel, table=True):
    """
    Blacklisted token model for revoked JWTs.

    Stores revoked tokens to prevent their reuse until expiration.
    """

    __tablename__: str = "blacklisted_tokens"

    # Token information
    jti: str = Field(unique=True, nullable=False, index=True)  # JWT ID
    token_type: str = Field(nullable=False, max_length=20)  # 'access' or 'refresh'

    # User and session relationship
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    session_id: Optional[str] = Field(foreign_key="sessions.id", default=None)

    # Token metadata
    expires_at: datetime = Field(nullable=False, index=True)
    revoked_reason: Optional[str] = Field(default=None, max_length=100)

    def __repr__(self) -> str:
        """String representation of BlacklistedToken."""
        return f"<BlacklistedToken(id={self.id}, jti='{self.jti}', type='{self.token_type}')>"


# Pydantic models for API operations
class SessionResponse(SQLModel):
    """Session response schema."""

    id: str
    user_id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime


class SessionCreate(SQLModel):
    """Session creation schema."""

    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
