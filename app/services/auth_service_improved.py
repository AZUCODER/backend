"""
Improved Authentication Service

This module provides a comprehensive, robust authentication service that handles
all authentication flows with proper UUID support, error handling, and security.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)
from app.models.user import User, UserRole
from app.models.session import Session
from app.models.audit import AuditLog, AuditEventType
from app.services.user_service import (
    get_user_by_email,
    get_user_by_username,
    get_user_by_id,
    create_user,
)
from app.services.session_service import create_user_session
from app.services.redis_service import redis_service
from app.config import get_settings

settings = get_settings()


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ImprovedAuthService:
    """
    Improved authentication service with comprehensive error handling,
    UUID support, and security features.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(
        self,
        email_or_username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user and return tokens with comprehensive error handling.
        
        Args:
            email_or_username: Email or username for login
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing tokens and user info
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Find user by email or username
            user = await self._find_user(email_or_username)
            
            # Validate user account
            await self._validate_user_account(user, ip_address, user_agent)
            
            # Verify password
            if not verify_password(password, user.hashed_password):
                await self._handle_failed_login(user, ip_address, user_agent)
                raise AuthenticationError("Invalid credentials", "INVALID_CREDENTIALS")
            
            # Successful authentication
            await self._handle_successful_login(user, ip_address, user_agent)
            
            # Create session and tokens
            token_data = await create_user_session(
                db=self.db,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Add user info to response
            token_data.update({
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_verified": user.is_verified,
                    "is_active": user.is_active,
                }
            })
            
            return token_data
            
        except AuthenticationError:
            raise
        except Exception as e:
            # Log unexpected errors
            await self._log_error("Unexpected authentication error", str(e), ip_address, user_agent)
            raise AuthenticationError("Authentication failed", "SYSTEM_ERROR")
    
    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new user with comprehensive validation.
        
        Args:
            email: User email
            username: Username
            password: Plain text password
            first_name: First name
            last_name: Last name
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing user info and tokens
            
        Raises:
            AuthenticationError: If registration fails
        """
        try:
            # Check if user already exists
            existing_user = await get_user_by_email(self.db, email)
            if existing_user:
                raise AuthenticationError("Email already registered", "EMAIL_EXISTS")
            
            existing_user = await get_user_by_username(self.db, username)
            if existing_user:
                raise AuthenticationError("Username already taken", "USERNAME_EXISTS")
            
            # Create user
            from app.schemas.auth import UserCreate
            user_create = UserCreate(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=UserRole.USER  # Default role for new users
            )
            
            user = await create_user(self.db, user_create)
            
            # Log registration
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.USER_REGISTERED,
                event_description=f"New user registered: {username}",
                user_id=str(user.id),
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
            )
            self.db.add(audit_log)
            await self.db.commit()
            
            # Create initial session if email verification is not required in DEBUG mode
            if settings.DEBUG or user.is_verified:
                token_data = await create_user_session(
                    db=self.db,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:
                token_data = {}
            
            # Add user info to response
            token_data.update({
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                    "is_verified": user.is_verified,
                    "is_active": user.is_active,
                },
                "requires_verification": not user.is_verified and not settings.DEBUG
            })
            
            return token_data
            
        except AuthenticationError:
            raise
        except Exception as e:
            await self._log_error("Registration error", str(e), ip_address, user_agent)
            raise AuthenticationError("Registration failed", "SYSTEM_ERROR")
    
    async def refresh_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict containing new tokens
            
        Raises:
            AuthenticationError: If refresh fails
        """
        try:
            from app.services.session_service import refresh_access_token
            
            token_data = await refresh_access_token(self.db, refresh_token)
            if not token_data:
                raise AuthenticationError("Invalid refresh token", "INVALID_REFRESH_TOKEN")
            
            return token_data
            
        except AuthenticationError:
            raise
        except Exception as e:
            await self._log_error("Token refresh error", str(e), ip_address, user_agent)
            raise AuthenticationError("Token refresh failed", "SYSTEM_ERROR")
    
    async def _find_user(self, email_or_username: str) -> User:
        """Find user by email or username."""
        user = await get_user_by_email(self.db, email_or_username)
        if not user:
            user = await get_user_by_username(self.db, email_or_username)
        
        if not user:
            # Log failed attempt
            audit_log = AuditLog.create_log(
                event_type=AuditEventType.LOGIN_FAILED,
                event_description=f"Login attempt with unknown email/username: {email_or_username}",
                username=email_or_username,
                success=False,
                error_message="User not found",
            )
            self.db.add(audit_log)
            await self.db.commit()
            raise AuthenticationError("Invalid credentials", "USER_NOT_FOUND")
        
        return user
    
    async def _validate_user_account(
        self, 
        user: User, 
        ip_address: Optional[str], 
        user_agent: Optional[str]
    ) -> None:
        """Validate user account status."""
        # Check if account is locked
        if user.account_locked_until and user.account_locked_until > datetime.utcnow():
            await self._log_audit(
                AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                f"Login attempt on locked account: {user.username}",
                user,
                ip_address,
                user_agent,
                False,
                "Account is locked"
            )
            raise AuthenticationError("Account is locked", "ACCOUNT_LOCKED")
        
        # Check if user is active
        if not user.is_active:
            await self._log_audit(
                AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                f"Login attempt on inactive account: {user.username}",
                user,
                ip_address,
                user_agent,
                False,
                "Account is inactive"
            )
            raise AuthenticationError("Account is inactive", "ACCOUNT_INACTIVE")
        
        # Check email verification (except in DEBUG mode)
        if not user.is_verified and not settings.DEBUG:
            await self._log_audit(
                AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                f"Login attempt with unverified email: {user.username}",
                user,
                ip_address,
                user_agent,
                False,
                "Email not verified"
            )
            raise AuthenticationError("Email not verified", "EMAIL_NOT_VERIFIED")
    
    async def _handle_failed_login(
        self, 
        user: User, 
        ip_address: Optional[str], 
        user_agent: Optional[str]
    ) -> None:
        """Handle failed login attempt."""
        user.failed_login_attempts += 1
        
        # Lock account if threshold reached
        if user.failed_login_attempts >= settings.ACCOUNT_LOCKOUT_THRESHOLD:
            user.account_locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES
            )
            
            await self._log_audit(
                AuditEventType.ACCOUNT_LOCKED,
                f"Account locked due to {user.failed_login_attempts} failed login attempts",
                user,
                ip_address,
                user_agent,
                True
            )
        else:
            await self._log_audit(
                AuditEventType.LOGIN_FAILED,
                f"Failed login attempt {user.failed_login_attempts}/{settings.ACCOUNT_LOCKOUT_THRESHOLD}",
                user,
                ip_address,
                user_agent,
                False,
                "Invalid password"
            )
        
        await self.db.commit()
    
    async def _handle_successful_login(
        self, 
        user: User, 
        ip_address: Optional[str], 
        user_agent: Optional[str]
    ) -> None:
        """Handle successful login."""
        # Reset failed attempts
        user.failed_login_attempts = 0
        user.account_locked_until = None
        user.last_login = datetime.utcnow()
        
        await self._log_audit(
            AuditEventType.LOGIN_SUCCESS,
            f"Successful login for user: {user.username}",
            user,
            ip_address,
            user_agent,
            True
        )
        
        await self.db.commit()
    
    async def _log_audit(
        self,
        event_type: AuditEventType,
        description: str,
        user: Optional[User],
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Log audit event."""
        audit_log = AuditLog.create_log(
            event_type=event_type,
            event_description=description,
            user_id=str(user.id) if user else None,
            username=user.username if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )
        self.db.add(audit_log)
    
    async def _log_error(
        self,
        message: str,
        error: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> None:
        """Log system error."""
        audit_log = AuditLog.create_log(
            event_type=AuditEventType.SYSTEM_ERROR,
            event_description=f"{message}: {error}",
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            error_message=error,
        )
        self.db.add(audit_log)
        await self.db.commit()
