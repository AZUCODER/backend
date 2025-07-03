"""
Repository package for database operations.

This package contains repository classes that abstract database operations
and provide a clean interface for data access.
"""

from .base import BaseRepository
from .user import UserRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
]
