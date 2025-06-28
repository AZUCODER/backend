"""
SQLModel database models.

This package contains all the database models using SQLModel
(combination of SQLAlchemy and Pydantic).
"""

from app.models.base import BaseModel
from app.models.user import User, UserBase, UserCreate, UserUpdate, UserResponse
from app.models.session import Session, BlacklistedToken, SessionResponse, SessionCreate
from app.models.audit import AuditLog, AuditEventType, AuditLogResponse, AuditLogFilter

__all__ = [
    # Base model
    "BaseModel",
    # User models
    "User",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Session models
    "Session",
    "BlacklistedToken",
    "SessionResponse",
    "SessionCreate",
    # Audit models
    "AuditLog",
    "AuditEventType",
    "AuditLogResponse",
    "AuditLogFilter",
]
