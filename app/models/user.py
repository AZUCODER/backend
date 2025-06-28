"""
User model for authentication and user management.

This module contains the User SQLModel class for storing user information
including authentication credentials and profile data.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.base import BaseModel


class User(BaseModel, table=True):
    """
    User model for authentication and user management.

    Stores user credentials, profile information, and account status.
    """

    __tablename__ = "users"

    # Authentication fields
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    username: str = Field(unique=True, index=True, nullable=False, max_length=50)
    hashed_password: str = Field(nullable=False)

    # Profile fields
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=200)

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

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


# Pydantic models for API requests/responses
class UserBase(SQLModel):
    """Base user fields for API operations."""

    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""

    password: str


class UserUpdate(SQLModel):
    """User update schema."""

    email: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""

    id: int
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
