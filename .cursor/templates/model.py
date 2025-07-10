"""
Example database model template.

This module contains a template for creating SQLModel database models
following the project's patterns and conventions.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

from app.models.base import BaseModel


class ExampleStatus(str, Enum):
    """Enumeration of example statuses."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"


class ExampleModel(BaseModel, table=True):
    """
    Example database model with proper documentation.
    
    This model demonstrates the standard patterns for database models
    including relationships, enums, and proper field definitions.
    """
    
    __tablename__: str = "examples"
    
    # Required fields
    name: str = Field(
        nullable=False, 
        max_length=255, 
        index=True,
        description="Example name"
    )
    
    # Optional fields with defaults
    description: Optional[str] = Field(
        default=None, 
        max_length=1000,
        description="Example description"
    )
    status: ExampleStatus = Field(
        default=ExampleStatus.ACTIVE,
        nullable=False,
        description="Example status"
    )
    is_active: bool = Field(
        default=True, 
        nullable=False,
        description="Whether the example is active"
    )
    
    # Foreign key relationships
    user_id: Optional[int] = Field(
        default=None, 
        foreign_key="users.id",
        description="Owner of this example"
    )
    
    # Relationships
    user: Optional["User"] = Relationship(
        back_populates="examples",
        description="User who owns this example"
    )
    
    def __repr__(self) -> str:
        """String representation of ExampleModel."""
        return f"<ExampleModel(id={self.id}, name='{self.name}', status='{self.status}')>"
    
    @property
    def display_name(self) -> str:
        """Get display name for the example."""
        return f"{self.name} ({self.status})"


# Pydantic models for API operations
class ExampleBase(SQLModel):
    """Base example fields for API operations."""
    
    name: str
    description: Optional[str] = None
    status: Optional[ExampleStatus] = None
    is_active: Optional[bool] = None


class ExampleCreate(ExampleBase):
    """Example creation schema."""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: ExampleStatus = Field(default=ExampleStatus.ACTIVE)
    is_active: bool = Field(default=True)


class ExampleUpdate(SQLModel):
    """Example update schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ExampleStatus] = None
    is_active: Optional[bool] = None


class ExampleResponse(ExampleBase):
    """Example response schema."""
    
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    status: ExampleStatus
    is_active: bool


class ExampleListResponse(SQLModel):
    """Example list response schema."""
    
    examples: list[ExampleResponse]
    total: int
    skip: int
    limit: int 