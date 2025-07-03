from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dependencies import get_db, require_role, get_current_active_user
from app.models.user import User, UserResponse, UserRole, UserUpdate
from app.services.user_service import get_user_by_id, update_user

router = APIRouter()


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List users",
    description="List all users (admin only)",
)
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Max number of users to return"),
):
    from sqlmodel import select

    statement = select(User).offset(skip).limit(limit)
    result = await db.execute(statement)
    users = result.scalars().all()
    return users


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get user by ID (admin or self)",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user (admin or self)",
)
async def update_user_endpoint(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    updated = await update_user(db, user_id, user_update)
    return updated


@router.delete(
    "/{user_id}", summary="Delete user", description="Delete user (admin or self)"
)
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully", "user_id": user_id}
