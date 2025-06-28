# FastAPI Backend

A robust, scalable, and secure FastAPI backend for modern web applications.

## Features

- **FastAPI**: Modern, fast web framework for building APIs with Python
- **SQLModel**: SQL database toolkit combining SQLAlchemy and Pydantic
- **JWT Authentication**: Secure token-based authentication
- **PostgreSQL/SQLite**: Database support for both development and production
- **Redis**: Caching and session storage
- **Async/Await**: Fully asynchronous for high performance
- **Auto-documentation**: Interactive API docs with Swagger UI
- **Type Safety**: Full type hints throughout the codebase

## Project Structure

```
backend/
├── app/                    # Main application package
│   ├── api/                # API routes
│   │   └── v1/             # API version 1
│   │       └── endpoints/  # Individual endpoint modules
│   ├── core/               # Core functionality (security, config)
│   ├── models/             # SQLModel database models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic services
│   ├── middleware/         # Custom middleware
│   └── tests/              # Test modules
├── alembic/                # Database migrations
├── .env.example            # Environment variables example
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile             # Docker configuration
└── pyproject.toml         # Project dependencies and configuration
```

## Quick Start

### Prerequisites

- Python 3.13+
- uv (recommended) or pip for package management
- PostgreSQL (optional, SQLite is used by default)
- Redis (optional, for caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd backend
   ```

2. **Install dependencies using uv (recommended)**
   ```bash
   # Install uv if you haven't already
   pip install uv
   
   # Create virtual environment and install core dependencies
   uv venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   
   # Install core dependencies
   uv pip install fastapi uvicorn pydantic-settings python-dotenv
   ```

   **Alternative: Install all dependencies**
   ```bash
   # This will install all dependencies from pyproject.toml
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration if needed
   ```

4. **Verify the installation**
   ```bash
   # Test that everything works
   python -c "from app.main import app; from app.config import get_settings; print('✅ Setup successful!')"
   ```

5. **Run the development server**
   ```bash
   # Option 1: Using the main entry point
   python main.py
   
   # Option 2: Using uvicorn directly
   uvicorn app.main:app --reload
   
   # Option 3: Using uv (if all dependencies installed)
   uv run uvicorn app.main:app --reload
   ```

6. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health


## Database Setup

### Current: SQLite (Development)
The application is currently configured to use SQLite for development with all models and migrations working.

### Switching to PostgreSQL (Production)

1. **Set up PostgreSQL database**
   ```bash
   # Create database
   createdb rag-fastapi-db
   ```

2. **Update environment configuration**
   ```bash
   # Edit .env file
   DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/rag-fastapi-db
   ```

3. **Run migrations**
   ```bash
   # Apply all migrations to PostgreSQL
   .venv\Scripts\python -m alembic upgrade head
   ```

### Database Models Implemented
- **User**: Authentication, profile, account status
- **Session**: JWT token management, device tracking  
- **BlacklistedToken**: Revoked JWT tokens
- **AuditLog**: Security events, user actions (24 event types)

## Development

### Project Structure Status

```
backend/
├── app/                    ✅ Complete
│   ├── __init__.py        ✅ Complete
│   ├── main.py            ✅ Complete - FastAPI app with CORS
│   ├── config.py          ✅ Complete - Settings management
│   ├── database.py        ✅ Complete - DB connection setup
│   ├── dependencies.py    ✅ Complete - Common dependencies
│   ├── api/               ✅ Structure complete
│   │   └── v1/           ✅ Complete - Router setup
│   │       ├── router.py ✅ Complete - API v1 router
│   │       └── endpoints/ 🔄 TODO - Individual endpoints
│   ├── core/              ✅ Complete
│   │   └── security.py   ✅ Complete - JWT & password utils
│   ├── models/            ✅ Complete - User, Session, AuditLog, BlacklistedToken
│   ├── schemas/           🔄 TODO - Request/response schemas
│   ├── services/          🔄 TODO - Business logic
│   ├── middleware/        🔄 TODO - Custom middleware
│   └── tests/             🔄 TODO - Test implementation
├── .env                   ✅ Complete - Environment config
├── pyproject.toml         ✅ Complete - Dependencies
├── Dockerfile             ✅ Complete - Container setup
└── docker-compose.yml     ✅ Complete - Development setup
```

### Next Development Steps

1. **Create Database Models**
   ```bash
   # Create User model in app/models/user.py
   # Create base model in app/models/base.py
   ```

2. **Set up Database Migrations**
   ```bash
   # Initialize Alembic (when models are ready)
   alembic init alembic
   alembic revision --autogenerate -m "Create initial tables"
   alembic upgrade head
   ```

3. **Implement Authentication Endpoints**
   ```bash
   # Create auth endpoints in app/api/v1/endpoints/auth.py
   # Create user schemas in app/schemas/user.py
   ```

### Current Development Commands

```bash
# Start development server
uvicorn app.main:app --reload

# Test current setup
python -c "from app.main import app; print('✅ Backend ready for development')"

# Install additional dependencies as needed
uv pip install <package-name>
```

### Running Tests (When Implemented)

```bash
pytest
```

### Code Formatting (When Implemented)

```bash
black .
isort .
```

## Current Status

### ✅ What's Working
- FastAPI application with automatic OpenAPI documentation
- Environment-based configuration management  
- **Database models implemented**: User, Session, AuditLog, BlacklistedToken
- **Database migrations with Alembic** (SQLite working, PostgreSQL ready)
- JWT security utilities (password hashing, token generation)
- CORS middleware configured for frontend integration
- Health check endpoint

### 🚧 In Development  
- Authentication endpoints (register, login, logout)
- User management endpoints
- Error handling middleware
- PostgreSQL setup (models ready, need connection)

## API Endpoints

### Available Now
- `GET /` - API information and status
- `GET /health` - Health check
- `GET /api/v1/` - API v1 information

### Coming Soon (Implementation Planned)
- `POST /api/v1/auth/register` - User registration  
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{id}` - Get user by ID

## Configuration

The application uses environment variables for configuration. See `.env.example` for all available options.

### Key Configuration Options

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT secret key (change in production!)
- `BACKEND_CORS_ORIGINS`: Allowed CORS origins
- `DEBUG`: Enable debug mode
- `REDIS_URL`: Redis connection string

## Security

- JWT-based authentication
- Password hashing with bcrypt
- CORS configuration
- Rate limiting
- Input validation with Pydantic
- SQL injection prevention

## Performance

- Fully asynchronous with async/await
- Connection pooling
- Redis caching
- Optimized database queries
- Background tasks support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
