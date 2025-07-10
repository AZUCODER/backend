"""
Example Pydantic schema template.

This module contains a template for creating Pydantic schemas
following the project's patterns and conventions.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class ExampleRequest(BaseModel):
    """Example request schema with comprehensive validation."""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Example name (1-255 characters)"
    )
    email: str = Field(
        ..., 
        description="Email address"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Optional description (max 1000 characters)"
    )
    status: Optional[str] = Field(
        "active",
        description="Example status (active, inactive, pending, archived)"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name format and content."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        
        # Check for valid characters (letters, numbers, spaces, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", v):
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, and underscores")
        
        return v.strip()
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        valid_statuses = ["active", "inactive", "pending", "archived"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()


class ExampleResponse(BaseModel):
    """Example response schema."""
    
    id: int = Field(..., description="Example ID")
    name: str = Field(..., description="Example name")
    email: str = Field(..., description="Email address")
    description: Optional[str] = Field(None, description="Example description")
    status: str = Field(..., description="Example status")
    is_active: bool = Field(..., description="Whether the example is active")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")
    user_id: Optional[int] = Field(None, description="Owner user ID")


class ExampleUpdateRequest(BaseModel):
    """Example update request schema."""
    
    name: Optional[str] = Field(
        None, 
        min_length=1, 
        max_length=255, 
        description="Example name (1-255 characters)"
    )
    email: Optional[str] = Field(
        None, 
        description="Email address"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Optional description (max 1000 characters)"
    )
    status: Optional[str] = Field(
        None,
        description="Example status (active, inactive, pending, archived)"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Whether the example is active"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name format and content."""
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        
        # Check for valid characters (letters, numbers, spaces, hyphens, underscores)
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", v):
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, and underscores")
        
        return v.strip()
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is None:
            return v
        
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is None:
            return v
        
        valid_statuses = ["active", "inactive", "pending", "archived"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower()


class ExampleListResponse(BaseModel):
    """Example list response schema."""
    
    examples: list[ExampleResponse] = Field(..., description="List of examples")
    total: int = Field(..., description="Total number of examples")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
    has_more: bool = Field(..., description="Whether there are more records available")


class ExampleSearchRequest(BaseModel):
    """Example search request schema."""
    
    query: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Search query"
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status"
    )
    is_active: Optional[bool] = Field(
        None,
        description="Filter by active status"
    )
    skip: int = Field(
        default=0, 
        ge=0, 
        description="Number of records to skip"
    )
    limit: int = Field(
        default=100, 
        ge=1, 
        le=1000, 
        description="Maximum number of records to return"
    )
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value."""
        if v is None:
            return v
        
        valid_statuses = ["active", "inactive", "pending", "archived"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v.lower() 