"""
Base repository with common CRUD operations.

This module provides the BaseRepository class that implements common
database operations and can be extended by specific model repositories.
"""

from typing import TypeVar, Generic, List, Optional, Type, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from sqlalchemy import func, update, delete
from datetime import datetime

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Base repository class with common CRUD operations.

    Provides standard database operations that can be inherited
    by specific model repositories.
    """

    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def create(self, obj_in: SQLModel) -> T:
        """Create new record"""
        db_obj = self.model(**obj_in.model_dump(exclude_unset=True))
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def get(self, id: int) -> Optional[T]:
        """Get record by ID"""
        statement = select(self.model).where(self.model.id == id)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_multi(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get multiple records with pagination and optional filters"""
        statement = select(self.model)

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    statement = statement.where(getattr(self.model, field) == value)

        statement = statement.offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def update(self, id: int, obj_in: SQLModel) -> Optional[T]:
        """Update existing record"""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # Update timestamp if model has updated_at field
        if hasattr(db_obj, "updated_at"):
            setattr(db_obj, "updated_at", datetime.utcnow())

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_bulk(self, filters: Dict[str, Any], values: Dict[str, Any]) -> int:
        """Bulk update records matching filters"""
        statement = update(self.model)

        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                statement = statement.where(getattr(self.model, field) == value)

        # Set updated timestamp if model has it
        if hasattr(self.model, "updated_at"):
            values["updated_at"] = datetime.utcnow()

        statement = statement.values(values)
        result = await self.db.execute(statement)
        await self.db.commit()
        return result.rowcount

    async def delete(self, id: int) -> bool:
        """Delete record by ID"""
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.db.delete(db_obj)
        await self.db.commit()
        return True

    async def delete_bulk(self, filters: Dict[str, Any]) -> int:
        """Bulk delete records matching filters"""
        statement = delete(self.model)

        # Apply filters
        for field, value in filters.items():
            if hasattr(self.model, field):
                statement = statement.where(getattr(self.model, field) == value)

        result = await self.db.execute(statement)
        await self.db.commit()
        return result.rowcount

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total records with optional filters"""
        statement = select(func.count(self.model.id))

        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    statement = statement.where(getattr(self.model, field) == value)

        result = await self.db.execute(statement)
        return result.scalar()

    async def exists(self, id: int) -> bool:
        """Check if record exists by ID"""
        statement = select(func.count(self.model.id)).where(self.model.id == id)
        result = await self.db.execute(statement)
        return result.scalar() > 0
