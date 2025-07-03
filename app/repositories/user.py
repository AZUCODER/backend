"""
User repository for user-specific database operations.

This module provides the UserRepository class that extends BaseRepository
with user-specific database operations and queries.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, and_, or_
from datetime import datetime, timedelta

from app.models.user import User, UserCreate, UserUpdate, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User repository with user-specific database operations.

    Extends BaseRepository to provide user-specific queries and operations.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        statement = select(User).where(User.email == email)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        statement = select(User).where(User.username == username)
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_by_email_or_username(self, email_or_username: str) -> Optional[User]:
        """Get user by email or username"""
        statement = select(User).where(
            or_(User.email == email_or_username, User.username == email_or_username)
        )
        result = await self.db.execute(statement)
        return result.scalars().first()

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users only"""
        statement = select(User).where(User.is_active == True).offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_verified_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get verified users only"""
        statement = (
            select(User)
            .where(and_(User.is_active == True, User.is_verified == True))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_by_role(
        self, role: UserRole, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get users by role"""
        statement = (
            select(User)
            .where(and_(User.role == role, User.is_active == True))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def search_users(
        self, query: str, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[User]:
        """Search users by email, username, or name"""
        search_term = f"%{query}%"

        conditions = [
            User.email.ilike(search_term),
            User.username.ilike(search_term),
        ]

        # Add name search conditions if fields exist
        if User.first_name:
            conditions.append(User.first_name.ilike(search_term))
        if User.last_name:
            conditions.append(User.last_name.ilike(search_term))
        if User.full_name:
            conditions.append(User.full_name.ilike(search_term))

        statement = select(User).where(or_(*conditions))

        if active_only:
            statement = statement.where(User.is_active == True)

        statement = statement.offset(skip).limit(limit)
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def check_email_exists(
        self, email: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """Check if email exists, optionally excluding a specific user"""
        statement = select(User.id).where(User.email == email)

        if exclude_user_id:
            statement = statement.where(User.id != exclude_user_id)

        result = await self.db.execute(statement)
        return result.first() is not None

    async def check_username_exists(
        self, username: str, exclude_user_id: Optional[int] = None
    ) -> bool:
        """Check if username exists, optionally excluding a specific user"""
        statement = select(User.id).where(User.username == username)

        if exclude_user_id:
            statement = statement.where(User.id != exclude_user_id)

        result = await self.db.execute(statement)
        return result.first() is not None

    async def check_user_exists(self, email: str, username: str) -> dict:
        """Check if user exists by email or username"""
        email_exists = await self.check_email_exists(email)
        username_exists = await self.check_username_exists(username)

        return {
            "email_exists": email_exists,
            "username_exists": username_exists,
            "any_exists": email_exists or username_exists,
        }

    async def get_locked_users(self) -> List[User]:
        """Get users with active account locks"""
        now = datetime.utcnow()
        statement = select(User).where(
            and_(
                User.account_locked_until.is_not(None), User.account_locked_until > now
            )
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def unlock_expired_accounts(self) -> int:
        """Unlock accounts where lock period has expired"""
        from sqlalchemy import update

        now = datetime.utcnow()

        # Update users where lock has expired using direct SQLAlchemy update
        statement = (
            update(User)
            .where(
                and_(
                    User.account_locked_until.is_not(None),
                    User.account_locked_until < now,
                )
            )
            .values(account_locked_until=None, failed_login_attempts=0, updated_at=now)
        )

        result = await self.db.execute(statement)
        await self.db.commit()
        return result.rowcount

    async def get_users_by_last_login(
        self, days_ago: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get users who haven't logged in for specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)

        statement = (
            select(User)
            .where(or_(User.last_login.is_(None), User.last_login < cutoff_date))
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def count_by_role(self) -> dict:
        """Count users by role"""
        roles_count = {}

        for role in UserRole:
            count = await self.count(filters={"role": role, "is_active": True})
            roles_count[role.value] = count

        return roles_count

    async def get_admin_users(self) -> List[User]:
        """Get all admin users"""
        return await self.get_by_role(UserRole.ADMIN)

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account"""
        user = await self.get(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(user)
        return True

    async def activate_user(self, user_id: int) -> bool:
        """Activate a user account"""
        user = await self.get(user_id)
        if not user:
            return False

        user.is_active = True
        user.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(user)
        return True
