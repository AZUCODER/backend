"""
Audit log model for security tracking and compliance.

This module contains the AuditLog SQLModel class for tracking user actions,
security events, and maintaining compliance audit trails.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import json

from sqlmodel import Field, SQLModel, Column, Text
from sqlalchemy import JSON

from app.models.base import BaseModel


class AuditEventType(str, Enum):
    """Audit event types for categorizing actions."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"

    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"

    # Permission events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"

    # Security events
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"

    # System events
    SYSTEM_CONFIGURATION_CHANGED = "system_config_changed"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"


class AuditLog(BaseModel, table=True):
    """
    Audit log model for tracking user actions and security events.

    Maintains a comprehensive audit trail for compliance, security monitoring,
    and debugging purposes.
    """

    __tablename__: str = "audit_logs"

    # Event classification
    event_type: AuditEventType = Field(nullable=False, index=True)
    event_category: str = Field(nullable=False, max_length=50, index=True)

    # User and session tracking
    user_id: Optional[int] = Field(foreign_key="users.id", default=None, index=True)
    session_id: Optional[int] = Field(foreign_key="sessions.id", default=None)
    username: Optional[str] = Field(default=None, max_length=50, index=True)

    # Request metadata
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    request_method: Optional[str] = Field(default=None, max_length=10)
    request_path: Optional[str] = Field(default=None, max_length=500)

    # Event details
    event_description: str = Field(nullable=False, max_length=500)
    resource_type: Optional[str] = Field(default=None, max_length=50)
    resource_id: Optional[str] = Field(default=None, max_length=100)

    # Event outcome
    success: bool = Field(default=True, nullable=False)
    error_message: Optional[str] = Field(default=None, max_length=1000)

    # Additional event data (stored as JSON)
    event_data: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))

    # Compliance and retention
    retention_category: str = Field(default="standard", max_length=20)
    archived: bool = Field(default=False, nullable=False)

    def __repr__(self) -> str:
        """String representation of AuditLog."""
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', user_id={self.user_id})>"

    @classmethod
    def create_log(
        cls,
        event_type: AuditEventType,
        event_description: str,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
    ) -> "AuditLog":
        """
        Create a new audit log entry.

        Args:
            event_type: Type of event being logged
            event_description: Human-readable description of the event
            user_id: ID of the user performing the action
            session_id: ID of the session (if applicable)
            username: Username of the user (for cases where user might be deleted)
            ip_address: IP address of the request
            user_agent: User agent string
            request_method: HTTP method
            request_path: Request path
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource
            success: Whether the action was successful
            error_message: Error message if action failed
            event_data: Additional event-specific data

        Returns:
            AuditLog: New audit log instance
        """
        # Determine event category based on event type
        event_category = "system"
        if event_type.value.startswith(("login", "logout", "password", "account")):
            event_category = "authentication"
        elif event_type.value.startswith("user"):
            event_category = "user_management"
        elif event_type.value.startswith(("permission", "role")):
            event_category = "authorization"
        elif event_type.value.startswith(("unauthorized", "suspicious")):
            event_category = "security"

        return cls(
            event_type=event_type,
            event_category=event_category,
            event_description=event_description,
            user_id=user_id,
            session_id=session_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            event_data=event_data,
        )


# Pydantic models for API operations
class AuditLogResponse(SQLModel):
    """Audit log response schema."""

    id: int
    event_type: AuditEventType
    event_category: str
    event_description: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool
    created_at: datetime
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None


class AuditLogFilter(SQLModel):
    """Audit log filtering parameters."""

    event_type: Optional[AuditEventType] = None
    event_category: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    success: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
