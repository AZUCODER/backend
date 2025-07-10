"""
Example endpoint template.

This module contains a template for creating FastAPI endpoints
following the project's patterns and conventions.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
)
from app.models.user import User
from app.models.audit import AuditLog, AuditEventType
from app.schemas.example import (
    ExampleRequest,
    ExampleResponse,
    ExampleListResponse,
)
from app.services.example_service import (
    create_example,
    get_example_by_id,
    get_examples,
    update_example,
    delete_example,
)

router = APIRouter()


@router.post(
    "/examples",
    response_model=ExampleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new example",
    description="Create a new example record with proper validation",
)
async def create_example_endpoint(
    example_data: ExampleRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a new example record.
    
    Args:
        example_data: Example creation data
        request: FastAPI request object
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ExampleResponse: Created example data
        
    Raises:
        HTTPException: If creation fails
    """
    # Get client information for audit logging
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    try:
        # Create example
        example = await create_example(
            db=db,
            example_data=example_data,
            user_id=current_user.id
        )
        
        # Create audit log for successful creation
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_CREATED,
            event_description=f"Example created: {example.name}",
            user_id=str(current_user.id),
            username=current_user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        db.add(audit_log)
        await db.commit()
        
        return ExampleResponse(
            id=example.id,
            name=example.name,
            description=example.description,
            created_at=example.created_at,
            updated_at=example.updated_at,
        )
        
    except Exception as e:
        # Create audit log for creation failure
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.EXAMPLE_CREATED,
            event_description=f"Failed to create example: {example_data.name}",
            user_id=str(current_user.id),
            username=current_user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=str(e),
        )
        db.add(audit_log)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create example",
        )


@router.get(
    "/examples/{example_id}",
    response_model=ExampleResponse,
    summary="Get example by ID",
    description="Retrieve a specific example by its ID",
)
async def get_example_endpoint(
    example_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a specific example by ID.
    
    Args:
        example_id: Example ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ExampleResponse: Example data
        
    Raises:
        HTTPException: If example not found
    """
    example = await get_example_by_id(db, example_id)
    
    if not example:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found",
        )
    
    return ExampleResponse(
        id=example.id,
        name=example.name,
        description=example.description,
        created_at=example.created_at,
        updated_at=example.updated_at,
    )


@router.get(
    "/examples",
    response_model=ExampleListResponse,
    summary="Get all examples",
    description="Retrieve a paginated list of examples",
)
async def get_examples_endpoint(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get a paginated list of examples.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Authenticated user
        db: Database session
        
    Returns:
        ExampleListResponse: Paginated list of examples
    """
    examples = await get_examples(db, skip=skip, limit=limit)
    
    return ExampleListResponse(
        examples=[
            ExampleResponse(
                id=example.id,
                name=example.name,
                description=example.description,
                created_at=example.created_at,
                updated_at=example.updated_at,
            )
            for example in examples
        ],
        total=len(examples),
        skip=skip,
        limit=limit,
    ) 