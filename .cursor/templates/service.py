"""
Example service layer template.

This module contains a template for creating service layer functions
following the project's patterns and conventions.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.example import ExampleModel, ExampleCreate, ExampleUpdate
from app.models.audit import AuditLog, AuditEventType


async def get_example_by_id(db: AsyncSession, example_id: int) -> Optional[ExampleModel]:
    """
    Get example by ID.
    
    Args:
        db: Database session
        example_id: Example ID
        
    Returns:
        ExampleModel: Example if found, None otherwise
    """
    statement = select(ExampleModel).where(ExampleModel.id == example_id)
    result = await db.execute(statement)
    return result.scalars().first()


async def get_examples(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[int] = None
) -> List[ExampleModel]:
    """
    Get paginated list of examples.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        user_id: Optional user ID to filter by
        
    Returns:
        List[ExampleModel]: List of examples
    """
    statement = select(ExampleModel)
    
    if user_id:
        statement = statement.where(ExampleModel.user_id == user_id)
    
    statement = statement.offset(skip).limit(limit)
    result = await db.execute(statement)
    return result.scalars().all()


async def create_example(
    db: AsyncSession, 
    example_data: ExampleCreate,
    user_id: Optional[int] = None
) -> ExampleModel:
    """
    Create a new example.
    
    Args:
        db: Database session
        example_data: Example creation data
        user_id: Optional user ID for ownership
        
    Returns:
        ExampleModel: Created example
        
    Raises:
        ValueError: If creation fails
    """
    try:
        # Create example instance
        example = ExampleModel(
            name=example_data.name,
            description=example_data.description,
            status=example_data.status,
            is_active=example_data.is_active,
            user_id=user_id
        )
        
        # Add to database
        db.add(example)
        await db.commit()
        await db.refresh(example)
        
        # Create audit log for successful creation
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_CREATED,
            event_description=f"Example created: {example.name}",
            user_id=user_id,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return example
        
    except Exception as e:
        await db.rollback()
        
        # Create audit log for creation failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_CREATED,
            event_description=f"Failed to create example: {example_data.name}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        db.add(audit_log)
        await db.commit()
        
        raise ValueError(f"Failed to create example: {e}")


async def update_example(
    db: AsyncSession,
    example_id: int,
    example_data: ExampleUpdate,
    user_id: Optional[int] = None
) -> Optional[ExampleModel]:
    """
    Update an existing example.
    
    Args:
        db: Database session
        example_id: Example ID to update
        example_data: Update data
        user_id: Optional user ID for audit logging
        
    Returns:
        ExampleModel: Updated example if found, None otherwise
        
    Raises:
        ValueError: If update fails
    """
    try:
        # Get existing example
        example = await get_example_by_id(db, example_id)
        if not example:
            return None
        
        # Update fields
        update_data = example_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(example, field, value)
        
        # Update timestamp
        example.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(example)
        
        # Create audit log for successful update
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_UPDATED,
            event_description=f"Example updated: {example.name}",
            user_id=user_id,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return example
        
    except Exception as e:
        await db.rollback()
        
        # Create audit log for update failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_UPDATED,
            event_description=f"Failed to update example ID: {example_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        db.add(audit_log)
        await db.commit()
        
        raise ValueError(f"Failed to update example: {e}")


async def delete_example(
    db: AsyncSession,
    example_id: int,
    user_id: Optional[int] = None
) -> bool:
    """
    Delete an example.
    
    Args:
        db: Database session
        example_id: Example ID to delete
        user_id: Optional user ID for audit logging
        
    Returns:
        bool: True if deleted, False if not found
        
    Raises:
        ValueError: If deletion fails
    """
    try:
        # Get existing example
        example = await get_example_by_id(db, example_id)
        if not example:
            return False
        
        example_name = example.name
        
        # Delete from database
        await db.delete(example)
        await db.commit()
        
        # Create audit log for successful deletion
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_DELETED,
            event_description=f"Example deleted: {example_name}",
            user_id=user_id,
            success=True
        )
        db.add(audit_log)
        await db.commit()
        
        return True
        
    except Exception as e:
        await db.rollback()
        
        # Create audit log for deletion failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_DELETED,
            event_description=f"Failed to delete example ID: {example_id}",
            user_id=user_id,
            success=False,
            error_message=str(e)
        )
        db.add(audit_log)
        await db.commit()
        
        raise ValueError(f"Failed to delete example: {e}")


async def search_examples(
    db: AsyncSession,
    query: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ExampleModel]:
    """
    Search examples with filters.
    
    Args:
        db: Database session
        query: Search query for name/description
        status: Filter by status
        is_active: Filter by active status
        user_id: Optional user ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List[ExampleModel]: Filtered list of examples
    """
    statement = select(ExampleModel)
    
    # Apply filters
    if user_id:
        statement = statement.where(ExampleModel.user_id == user_id)
    
    if query:
        statement = statement.where(
            ExampleModel.name.ilike(f"%{query}%") |
            ExampleModel.description.ilike(f"%{query}%")
        )
    
    if status:
        statement = statement.where(ExampleModel.status == status)
    
    if is_active is not None:
        statement = statement.where(ExampleModel.is_active == is_active)
    
    # Apply pagination
    statement = statement.offset(skip).limit(limit)
    
    result = await db.execute(statement)
    return result.scalars().all() 