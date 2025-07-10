# Cursor Rules for Backend Python Codebase

# Python Static Typing
- Use type hints for all function signatures, variables, and class attributes.
- Prefer Optional[], List[], Dict[], etc. from typing for clarity.
- Use Pydantic/SQLModel for schema/model validation and serialization.

# DRY & Reusability
- Abstract repeated logic into utility functions, base classes, or mixins.
- Use repository and service patterns for business logic and data access.
- Prefer dependency injection for shared resources (e.g., DB sessions).

# Robustness & Error Handling
- Always handle exceptions with try/except and log errors.
- Use FastAPI's HTTPException for API errors; rollback DB transactions on failure.
- Validate all external input with Pydantic models.

# Performance & Speed
- Use async/await for all I/O and DB operations.
- Use connection pooling and efficient queries (select only needed fields).
- Implement caching (e.g., Redis) for frequently accessed data.

# Maintainability
- Follow PEP8 and use black for formatting.
- Use meaningful names and comprehensive docstrings.
- Keep functions/classes small and focused (single responsibility principle).
- Group related code into modules/packages (API, services, models, etc.).
- Write unit/integration tests for all business logic (pytest, pytest-asyncio).

# Security
- Hash passwords, never log sensitive data.
- Use parameterized queries to prevent SQL injection.
- Store secrets in environment variables, not code.

# Reference
- For detailed rules, see backend/.cursor/rules.json 