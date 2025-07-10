# Cursor AI Configuration for Aixiate Backend

This `.cursor` folder contains comprehensive configuration files and templates for Cursor AI to better understand and assist with the Aixiate FastAPI backend project.

## 📁 Structure

```
.cursor/
├── README.md                    # This documentation
├── coding-standards.md          # Comprehensive coding standards (from .cursorrules)
├── ai-instructions.md           # Project-specific AI instructions
├── templates/                   # Reusable code templates
│   ├── endpoint.py              # FastAPI endpoint template
│   ├── model.py                 # SQLModel database model template
│   ├── schema.py                # Pydantic schema template
│   ├── service.py               # Service layer template
│   ├── repository.py            # Repository pattern template
│   └── dependency.py            # FastAPI dependency template
└── snippets/                    # Code snippets for common patterns
    ├── async-function.json      # Async function with proper typing
    ├── database-query.json      # SQLModel select query
    ├── error-handling.json      # FastAPI error handling
    ├── audit-log.json           # Audit logging pattern
    ├── password-validation.json # Password validation
    └── jwt-token.json           # JWT token operations
```

## 🎯 Purpose

Cursor AI will automatically read these files to:
- **Maintain Consistency**: Follow established coding patterns and standards
- **Improve Suggestions**: Provide context-aware code recommendations
- **Enforce Best Practices**: Apply project-specific conventions and rules
- **Speed Up Development**: Use pre-built templates and snippets
- **Ensure Quality**: Follow the comprehensive coding standards

## 🚀 Key Features

### Templates
- **FastAPI Endpoints**: Proper HTTP methods, status codes, and documentation
- **Database Models**: SQLModel with BaseModel inheritance and relationships
- **Pydantic Schemas**: Request/response validation with field validators
- **Service Layer**: Business logic with proper error handling
- **Repository Pattern**: Data access layer with async operations
- **Dependencies**: FastAPI dependency injection patterns

### Snippets
- **Async Operations**: Proper async/await patterns
- **Database Queries**: SQLModel select statements
- **Error Handling**: FastAPI HTTPException patterns
- **Security**: Password hashing and JWT operations
- **Logging**: Audit logging for security events
- **Validation**: Pydantic field validators

### Standards
- **Python 3.13+**: Modern Python features and type hints
- **FastAPI**: RESTful API design with OpenAPI documentation
- **SQLModel**: Database ORM with Pydantic integration
- **Security**: JWT authentication, password hashing, audit logging
- **Testing**: pytest with async support
- **Performance**: Async operations, connection pooling

## 📋 Usage

### For Developers
1. Use templates when creating new endpoints, models, or services
2. Apply snippets for common patterns (database queries, error handling, etc.)
3. Follow the coding standards for consistency
4. Reference AI instructions for project-specific guidance

### For Cursor AI
- Automatically applies project patterns and conventions
- Suggests appropriate imports and function structures
- Maintains consistency with existing codebase
- Provides context-aware recommendations

## 🔧 Technologies Covered

- **FastAPI 0.104.1+** with async support
- **Python 3.13+** with type hints
- **SQLModel** for database ORM
- **Pydantic 2.9.0+** for validation
- **PostgreSQL** with async driver
- **Redis** for caching and sessions
- **JWT** for authentication
- **Alembic** for database migrations
- **pytest** with async support
- **Passlib** for password hashing

## 📝 Maintenance

- Update templates when new patterns emerge
- Add new snippets for frequently used code patterns
- Keep coding standards current with project evolution
- Review and update AI instructions as needed

This configuration ensures that Cursor AI provides the most relevant and consistent assistance for the Aixiate backend project. 