# AI Instructions for Aixiate FastAPI Backend Project

## Project Overview
Aixiate is a robust, scalable, and secure FastAPI backend built with Python 3.13+, SQLModel, and modern async patterns. The project implements comprehensive authentication, audit logging, and follows enterprise-grade security practices.

## Key Technologies & Dependencies
- **Framework**: FastAPI 0.104.1+ with async support
- **Python**: 3.13+ with comprehensive type hints
- **Database**: SQLModel (SQLAlchemy + Pydantic) with PostgreSQL
- **Authentication**: JWT tokens with automatic refresh and session management
- **Security**: Passlib with bcrypt, audit logging, rate limiting
- **Validation**: Pydantic 2.9.0+ with field validators
- **Testing**: pytest with async support
- **Migrations**: Alembic for database schema management
- **Caching**: Redis for sessions and frequently accessed data
- **Email**: Resend API for transactional emails

## Project Structure & Architecture
```
app/
├── main.py                     # FastAPI application entry point
├── config.py                   # Pydantic Settings configuration
├── database.py                 # Database connection and session management
├── dependencies.py             # FastAPI dependency injection
├── api/                        # API layer
│   └── v1/
│       ├── router.py           # Main API router
│       └── endpoints/          # API endpoints by feature
├── models/                     # SQLModel database models
│   ├── base.py                # BaseModel with common fields
│   ├── user.py                # User model and schemas
│   ├── session.py             # Session management
│   └── audit.py               # Audit logging
├── schemas/                    # Pydantic request/response schemas
├── services/                   # Business logic layer
├── repositories/               # Data access layer
├── core/                       # Core utilities (security, etc.)
├── middleware/                 # Custom middleware
└── utils/                      # Utility functions
```

## Import Conventions
- **Absolute imports**: Use full module paths (e.g., `from app.models.user import User`)
- **Models**: `from app.models.*` for database models
- **Schemas**: `from app.schemas.*` for Pydantic schemas
- **Services**: `from app.services.*` for business logic
- **Dependencies**: `from app.dependencies import *` for FastAPI dependencies
- **Core**: `from app.core.*` for security and core utilities

## Code Patterns

### FastAPI Endpoints
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from app.dependencies import get_db, get_current_active_user
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.user_service import authenticate_user

router = APIRouter()

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return JWT tokens",
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Authenticate user and return JWT tokens.
    
    Args:
        login_data: Login credentials
        db: Database session
        
    Returns:
        TokenResponse: JWT tokens and session info
        
    Raises:
        HTTPException: If authentication fails
    """
    # Implementation here
    pass
```

### Database Models (SQLModel)
```python
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

from app.models.base import BaseModel

class ExampleModel(BaseModel, table=True):
    """
    Example database model with proper documentation.
    """
    
    __tablename__: str = "example_table"
    
    # Required fields
    name: str = Field(nullable=False, max_length=255, index=True)
    
    # Optional fields with defaults
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True, nullable=False)
    
    # Relationships
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="examples")
    
    def __repr__(self) -> str:
        """String representation of ExampleModel."""
        return f"<ExampleModel(id={self.id}, name='{self.name}')>"
```

### Pydantic Schemas
```python
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

class ExampleRequest(BaseModel):
    """Example request schema with validation."""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="Example name"
    )
    email: str = Field(
        ..., 
        description="Email address"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Optional description"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name format."""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()
    
    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v.lower().strip()
```

### Service Layer
```python
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.example import ExampleModel, ExampleCreate
from app.models.audit import AuditLog, AuditEventType

async def create_example(
    db: AsyncSession, 
    example_data: ExampleCreate,
    user_id: Optional[int] = None
) -> ExampleModel:
    """
    Create a new example record.
    
    Args:
        db: Database session
        example_data: Example creation data
        user_id: Optional user ID for audit logging
        
    Returns:
        ExampleModel: Created example record
        
    Raises:
        ValueError: If validation fails
    """
    try:
        # Create example instance
        example = ExampleModel(
            name=example_data.name,
            description=example_data.description,
            user_id=user_id
        )
        
        # Add to database
        db.add(example)
        await db.commit()
        await db.refresh(example)
        
        # Create audit log
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
        
        # Create audit log for failure
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
```

## Authentication & Security Patterns
- **JWT Tokens**: Access and refresh tokens with proper expiration
- **Password Hashing**: bcrypt through passlib
- **Session Management**: Database-backed sessions with cleanup
- **Audit Logging**: Comprehensive security event logging
- **Rate Limiting**: Configurable rate limiting for endpoints
- **Account Lockout**: Automatic account locking after failed attempts
- **Email Verification**: Required email verification for new accounts

## Error Handling Patterns
- **FastAPI HTTPException**: Proper HTTP status codes and error messages
- **Database Transactions**: Automatic rollback on errors
- **Audit Logging**: Log all errors with context
- **Validation Errors**: Pydantic validation with detailed error messages
- **Global Exception Handlers**: Consistent error response format

## Database Patterns
- **Async Operations**: All database operations are async
- **SQLModel**: Modern ORM with Pydantic integration
- **Connection Pooling**: Efficient database connection management
- **Transactions**: Proper transaction handling with rollback
- **Migrations**: Alembic for schema versioning

## Testing Patterns
- **pytest**: Comprehensive testing framework
- **Async Testing**: pytest-asyncio for async test support
- **Database Testing**: Separate test database
- **Mocking**: Mock external dependencies
- **Coverage**: High test coverage for critical business logic

## Performance Considerations
- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient database connections
- **Caching**: Redis for frequently accessed data
- **Query Optimization**: Select only needed fields
- **Pagination**: Handle large datasets efficiently

## Security Best Practices
- **Input Validation**: Pydantic schemas for all inputs
- **SQL Injection Prevention**: Parameterized queries
- **Password Security**: Strong password requirements
- **Session Security**: Secure session management
- **Audit Trail**: Comprehensive security logging
- **Rate Limiting**: Prevent abuse and brute force attacks

## Configuration Management
- **Pydantic Settings**: Environment-based configuration
- **Environment Variables**: Secure secret management
- **Validation**: Configuration value validation
- **Caching**: LRU cache for configuration instances
- **Documentation**: Comprehensive configuration documentation 