"""
Base model with common fields for all database models.

This module contains the base SQLModel class that provides common fields
like id, created_at, and updated_at for all database tables.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """
    Base model with common fields for all database tables.

    Provides:
    - id: Primary key (UUID)
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated
    """

    id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    class Config:
        """SQLModel configuration."""

        # Enable ORM mode for Pydantic compatibility
        from_attributes = True
