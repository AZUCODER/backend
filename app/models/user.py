"""
User model for authentication and user management.

This module contains the User SQLModel class for storing user information
including authentication credentials and profile data.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
import uuid

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint

from app.models.base import BaseModel


class UserRole(str, Enum):
    """Enumeration of user roles."""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(BaseModel, table=True):
    """
    User model for authentication and user management.

    Stores user credentials, profile information, account status, and role.
    """

    __tablename__: str = "users"

    # Authentication fields
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    username: str = Field(unique=True, index=True, nullable=False, max_length=50)
    # Password is required for traditional accounts but can be null for social accounts
    hashed_password: str | None = Field(default=None, nullable=True)

    # Profile fields
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)

    # Role field
    role: UserRole = Field(
        default=UserRole.USER,
        nullable=False,
        max_length=10,
        description="User role: admin, user, guest",
    )

    # Account status
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)

    # Account security
    last_login: Optional[datetime] = Field(default=None)
    failed_login_attempts: int = Field(default=0, nullable=False)
    account_locked_until: Optional[datetime] = Field(default=None)

    # Email verification
    email_verified_at: Optional[datetime] = Field(default=None)

    # OAuth-specific fields
    oauth_provider: str | None = Field(default=None, max_length=20, nullable=True)
    oauth_sub: str | None = Field(default=None, max_length=255, nullable=True)
    avatar_url: str | None = Field(default=None, max_length=500, nullable=True)

    # Composite unique constraint on provider + sub ensures each social account is unique
    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_sub", name="uq_user_oauth"),
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return (
            f"<User(id={self.id}, username='{self.username}', email='{self.email}', "
            f"role='{self.role}', provider='{self.oauth_provider}')>"
        )


# Pydantic models for API requests/responses
class UserBase(SQLModel):
    """Base user fields for API operations."""

    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None


class UserCreate(UserBase):
    """User creation schema."""

    password: str
    role: Optional[UserRole] = (
        None  # Allow specifying role on creation (default to user)
    )


class UserUpdate(SQLModel):
    """User update schema."""

    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    """User response schema."""

    id: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    role: UserRole = Field(default=UserRole.USER)


class PasswordResetToken(SQLModel, table=True):
    __tablename__: str = "password_reset_tokens"
    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True
    )
    user_id: str = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(unique=True, nullable=False, max_length=128, index=True)
    issued_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False)
    used: bool = Field(default=False, nullable=False)
