"""
Enhanced user service with repository pattern and performance monitoring.

This module provides an improved user service that uses the repository pattern,
transaction management, and performance monitoring for better maintainability
and reliability.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.repositories.user import UserRepository
from app.database.transactions import transactional, TransactionContext
from app.database.monitoring import track_query_performance
from app.models.user import User, UserCreate, UserUpdate, UserRole
from app.models.audit import AuditLog, AuditEventType
from app.core.security import get_password_hash, verify_password
from app.config import get_settings

settings = get_settings()


class EnhancedUserService:
    """
    Enhanced user service with repository pattern and monitoring.

    Provides user management operations with improved error handling,
    transaction management, and performance monitoring.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    @track_query_performance
    @transactional(max_retries=3)
    async def create_user_with_audit(
        self,
        user_data: UserCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        """
        Create user with automatic audit logging and transaction handling.

        Args:
            user_data: User creation data
            ip_address: Client IP address for audit
            user_agent: Client user agent for audit

        Returns:
            Created user object

        Raises:
            ValueError: If user already exists
        """
        # Check if user already exists
        existing = await self.user_repo.check_user_exists(
            user_data.email, user_data.username
        )

        if existing["email_exists"]:
            # Create audit log for failed registration attempt
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.USER_CREATED,
                event_description=f"Registration attempt with existing email: {user_data.email}",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="Email already registered",
            )
            self.db.add(audit_log)
            raise ValueError("Email already registered")

        if existing["username_exists"]:
            # Create audit log for failed registration attempt
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.USER_CREATED,
                event_description=f"Registration attempt with existing username: {user_data.username}",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="Username already taken",
            )
            self.db.add(audit_log)
            raise ValueError("Username already taken")

            # Create user with hashed password
        user_data_dict = user_data.model_dump()
        user_data_dict["hashed_password"] = get_password_hash(user_data.password)
        del user_data_dict["password"]  # Remove plain password

        # Create SQLModel instance directly for repository
        from sqlmodel import SQLModel

        class UserCreateWithHash(SQLModel):
            email: str
            username: str
            hashed_password: str
            first_name: Optional[str] = None
            last_name: Optional[str] = None
            is_verified: bool = False
            is_active: bool = True
            role: UserRole = UserRole.USER

        # Create user using repository
        user = await self.user_repo.create(UserCreateWithHash(**user_data_dict))

        # Create audit log for successful registration
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_CREATED,
            event_description=f"User registered successfully: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        self.db.add(audit_log)

        return user

    @track_query_performance
    async def authenticate_user(
        self,
        email_or_username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[User]:
        """
        Authenticate user with enhanced security and audit logging.

        Args:
            email_or_username: Email or username for login
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            User object if authentication successful, None otherwise
        """
        # Get user by email or username
        user = await self.user_repo.get_by_email_or_username(email_or_username)

        if not user:
            # Create audit log for unknown user
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.LOGIN_FAILED,
                event_description=f"Login attempt with unknown email/username: {email_or_username}",
                username=email_or_username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message="User not found",
            )
            self.db.add(audit_log)
            await self.db.commit()
            return None

        # Use transaction context for account lockout logic
        async with TransactionContext(self.db, max_retries=2) as tx:
            # Check if account is locked
            if (
                user.account_locked_until
                and user.account_locked_until > datetime.utcnow()
            ):
                audit_log = AuditLog.create_log(
                    event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                    event_description=f"Login attempt on locked account: {user.username}",
                    user_id=str(user.id),
                    username=user.username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message="Account is locked",
                )
                self.db.add(audit_log)
                return None

            # Verify password
            if not verify_password(password, user.hashed_password):
                # Handle failed login
                await self._handle_failed_login(user, ip_address, user_agent)
                return None

            # Check if user is active and verified
            if not user.is_active:
                audit_log = AuditLog.create_log(
                    event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                    event_description=f"Login attempt on inactive account: {user.username}",
                    user_id=str(user.id),
                    username=user.username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message="Account is inactive",
                )
                self.db.add(audit_log)
                return None

            if not user.is_verified:
                audit_log = AuditLog.create_log(
                    event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                    event_description=f"Login attempt with unverified email: {user.username}",
                    user_id=str(user.id),
                    username=user.username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message="Email not verified",
                )
                self.db.add(audit_log)
                return None

            # Successful login - reset failed attempts
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login = datetime.utcnow()

            # Create audit log for successful login
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.LOGIN_SUCCESS,
                event_description=f"Successful login for user: {user.username}",
                user_id=str(user.id),
                username=user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
            self.db.add(audit_log)

            await self.db.commit()
            await self.db.refresh(user)
            return user

    async def _handle_failed_login(
        self, user: User, ip_address: Optional[str], user_agent: Optional[str]
    ):
        """Handle failed login attempt with account lockout logic"""
        user.failed_login_attempts += 1

        # Lock account if threshold exceeded
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            from datetime import timedelta

            user.account_locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES
            )

            # Create audit log for account lock
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.ACCOUNT_LOCKED,
                event_description=f"Account locked due to {user.failed_login_attempts} failed login attempts",
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
            self.db.add(audit_log)

            # Send lockout notification email (fire and forget)
            await self._send_lockout_notification(user)

        # Create audit log for failed login
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.LOGIN_FAILED,
            event_description=f"Failed login attempt for user: {user.username}",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message="Invalid password",
        )
        self.db.add(audit_log)

    async def _send_lockout_notification(self, user: User):
        """Send account lockout notification email"""
        try:
            from app.services.email_service import send_email_via_resend
            import asyncio

            asyncio.create_task(
                send_email_via_resend(
                    to_email=user.email,
                    subject="Your account has been locked",
                    html_body=f"""
                        <p>Hello {user.username},</p>
                        <p>Your account has been locked due to too many failed login attempts.</p>
                        <p>It will be unlocked after {settings.ACCOUNT_LOCKOUT_DURATION_MINUTES} minutes.</p>
                        <p>If this wasn't you, please contact support immediately.</p>
                        <p>Thank you,<br/>Security Team</p>
                    """,
                )
            )
        except Exception as e:
            # Log but don't block the flow
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send lockout email: {e}")

    @track_query_performance
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID with performance monitoring"""
        return await self.user_repo.get(user_id)

    @track_query_performance
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with performance monitoring"""
        return await self.user_repo.get_by_email(email)

    @track_query_performance
    async def search_users(
        self, query: str, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> List[User]:
        """Search users with performance monitoring"""
        return await self.user_repo.search_users(query, skip, limit, active_only)

    @track_query_performance
    @transactional(max_retries=2)
    async def update_user(
        self,
        user_id: str,
        user_update: UserUpdate,
        current_user_id: Optional[str] = None,
    ) -> Optional[User]:
        """
        Update user with validation and audit logging.

        Args:
            user_id: ID of user to update
            user_update: Update data
            current_user_id: ID of user making the update

        Returns:
            Updated user object
        """
        user = await self.user_repo.get(user_id)
        if not user:
            return None

        # Validate email uniqueness if being updated
        update_data = user_update.model_dump(exclude_unset=True)
        if "email" in update_data:
            if await self.user_repo.check_email_exists(update_data["email"], user_id):
                raise ValueError("Email already exists")

        # Validate username uniqueness if being updated
        if "username" in update_data:
            if await self.user_repo.check_username_exists(
                update_data["username"], user_id
            ):
                raise ValueError("Username already exists")

        # Update user
        updated_user = await self.user_repo.update(user_id, user_update)

        # Create audit log
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.USER_UPDATED,
            event_description=f"User updated: {user.username}",
            user_id=current_user_id,
            resource_type="user",
            resource_id=str(user_id),
            success=True,
            event_data={"updated_fields": list(update_data.keys())},
        )
        self.db.add(audit_log)

        return updated_user

    @track_query_performance
    async def get_user_statistics(self) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        stats = {}

        # Total counts
        stats["total_users"] = await self.user_repo.count()
        stats["active_users"] = await self.user_repo.count({"is_active": True})
        stats["verified_users"] = await self.user_repo.count({"is_verified": True})

        # Role distribution
        stats["users_by_role"] = await self.user_repo.count_by_role()

        # Recent activity
        stats["recent_signups"] = len(await self.user_repo.get_users_by_last_login(1))
        stats["inactive_users_30_days"] = len(
            await self.user_repo.get_users_by_last_login(30)
        )

        # Security metrics
        locked_users = await self.user_repo.get_locked_users()
        stats["locked_accounts"] = len(locked_users)

        return stats

    @track_query_performance
    @transactional(max_retries=2)
    async def deactivate_user(
        self, user_id: str, current_user_id: str, reason: str = "User deactivated"
    ) -> bool:
        """
        Deactivate user account with audit logging.

        Args:
            user_id: ID of user to deactivate
            current_user_id: ID of user performing the action
            reason: Reason for deactivation

        Returns:
            True if successful, False otherwise
        """
        user = await self.user_repo.get(user_id)
        if not user:
            return False

        # Deactivate user
        success = await self.user_repo.deactivate_user(user_id)

        if success:
            # Create audit log
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.USER_DEACTIVATED,
                event_description=f"User deactivated: {user.username} - {reason}",
                user_id=current_user_id,
                resource_type="user",
                resource_id=str(user_id),
                success=True,
                event_data={"reason": reason},
            )
            self.db.add(audit_log)

        return success

    @track_query_performance
    async def cleanup_expired_locks(self) -> int:
        """Clean up expired account locks"""
        return await self.user_repo.unlock_expired_accounts()


# Factory function for dependency injection
def get_enhanced_user_service(db: AsyncSession) -> EnhancedUserService:
    """Factory function to create enhanced user service"""
    return EnhancedUserService(db)
