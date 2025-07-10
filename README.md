# FastAPI Backend

A robust, scalable, and secure FastAPI backend for modern web applications, featuring enterprise-grade database architecture, OAuth, advanced monitoring, Redis caching, and production-ready security.

**NOTE:** This project uses PostgreSQL for all environments (development, testing, production). SQLite is not supported or used anywhere in this project.

## 🚀 Features

- **FastAPI**: Modern, high-performance web framework
- **PostgreSQL**: Production-ready database with async support and UUID primary keys
- **Redis**: Caching and session management
- **OAuth2 & Social Login**: Google and GitHub login support
- **JWT Authentication**: Secure, stateless token-based auth
- **Repository Pattern**: Clean, type-safe data access with UUID support
- **Async/Await**: Fully asynchronous for high throughput
- **Database Monitoring**: Real-time query analytics, slow query detection
- **Health & Metrics Endpoints**: For system, database, and Kubernetes readiness/liveness
- **Production Security**: Password hashing, audit logging, CORS, input validation, rate limiting
- **Account Lockout Protection**: Brute force attack prevention
- **Email Services**: Email verification and password reset via Resend
- **Auto-generated Docs**: Swagger UI and ReDoc
- **Type Safety**: Full type hints throughout
- **Database Migrations**: Alembic for schema management
- **UUID Primary Keys**: All database tables use UUID strings for primary keys and foreign keys

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py         # Auth endpoints (register, login, etc.)
│   │       │   ├── oauth.py        # OAuth endpoints (initiate, callback, providers)
│   │       │   ├── users.py        # User management endpoints
│   │       │   ├── health.py       # Health, metrics, readiness/liveness
│   │       │   └── cache.py        # Redis cache management endpoints
│   │       └── router.py           # API v1 router
│   ├── core/                       # Core security logic
│   ├── database/                   # DB connection, monitoring, transactions
│   │   ├── connection.py           # Enhanced async database connection management
│   │   ├── monitoring.py           # Database performance monitoring
│   │   └── transactions.py         # Transaction management with retry logic
│   ├── models/                     # SQLModel DB models with UUID primary keys
│   │   ├── base.py                 # Base model with UUID id and timestamps
│   │   ├── user.py                 # User model with audit fields and OAuth support
│   │   ├── session.py              # Session management with UUID foreign keys
│   │   ├── email_verification.py   # Email verification tokens
│   │   └── audit.py                # Comprehensive audit logging
│   ├── repositories/               # Repository pattern with UUID support
│   │   ├── base.py                 # Base repository with common CRUD operations
│   │   └── user.py                 # User-specific repository operations
│   ├── schemas/                    # Pydantic schemas
│   ├── services/                   # Business logic
│   │   ├── user_service.py         # User management with UUID handling
│   │   ├── enhanced_user_service.py # Advanced user operations
│   │   ├── session_service.py      # Session management
│   │   ├── oauth_providers.py      # OAuth integration
│   │   ├── redis_service.py        # Redis caching
│   │   ├── email_service.py        # Email sending
│   │   ├── email_verification_service.py # Email verification
│   │   ├── password_reset_service.py # Password reset
│   │   └── auth_service_improved.py # Enhanced authentication service
│   ├── middleware/                 # Custom middleware
│   │   ├── rate_limit.py           # Rate limiting
│   │   └── security.py             # Security headers
│   ├── utils/                      # Utility modules
│   ├── config.py                   # Settings management
│   ├── database.py                 # DB setup
│   ├── dependencies.py             # Dependency injection
│   └── tests/                      # Test modules
├── alembic/                        # DB migrations
├── alembic.ini                     # Alembic config
├── pyproject.toml                  # Project dependencies/config
├── main.py                         # App entry point
├── tests/                          # Top-level tests
│   └── test_oauth_endpoints.py     # OAuth endpoint tests
├── REDIS_SETUP.md                  # Redis setup guide
├── alembic_manual.md               # Alembic usage guide
└── README.md                       # This file
```

## ⚡ Quick Start

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- PostgreSQL (required)
- Redis (optional but recommended for caching)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd backend
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   uv sync
   
   # Or using pip
   pip install -r pyproject.toml
   ```

3. **Set up PostgreSQL**
   ```bash
   # Create database
   createdb aixiate_db
   
   # Or using Docker
   docker run --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=aixiate_db -p 5432:5432 -d postgres:15
   ```

4. **Set up Redis (optional but recommended)**
   ```bash
   # Using Docker
   docker run --name redis -p 6379:6379 -d redis:7-alpine
   
   # See REDIS_SETUP.md for detailed instructions
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Run the development server**
   ```bash
   python main.py
   # or
   uvicorn app.main:app --reload
   ```

8. **Access the API**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health: http://localhost:8000/health

## 🗄️ Database Architecture

### UUID Primary Keys
- **All tables use UUID strings** as primary keys for enhanced security and scalability
- **BaseModel**: Provides common fields including UUID `id`, `created_at`, and `updated_at`
- **Foreign Keys**: All foreign key relationships use UUID strings for consistency
- **Migration Support**: Alembic migrations handle UUID conversion and foreign key relationships

### Database Features
- **PostgreSQL**: Primary database with async support via psycopg
- **Repository pattern**: All DB operations in `app/repositories/` with UUID support
- **Transaction management**: With retry logic in `app/database/transactions.py`
- **Performance monitoring**: Real-time analytics in `app/database/monitoring.py`
- **Health check endpoints**: Database status in `app/api/v1/endpoints/health.py`
- **Migrations**: Alembic for schema management (see `alembic_manual.md`)

### Database Tables
- **users**: User accounts with OAuth support and audit fields
- **sessions**: JWT session management with UUID foreign keys
- **email_verification_tokens**: Email verification with UUID primary keys
- **password_reset_tokens**: Password reset functionality
- **audit_logs**: Comprehensive audit trail with JSON event data
- **blacklisted_tokens**: Token blacklisting for security

## 🔌 API Endpoints (Summary)

### Auth
- `POST /api/v1/auth/register` — Register user
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/auth/logout` — Logout
- `POST /api/v1/auth/refresh` — Refresh token
- `GET /api/v1/auth/me` — Current user profile
- `GET /api/v1/auth/sessions` — List user sessions
- `DELETE /api/v1/auth/sessions/{session_id}` — Revoke session
- `POST /api/v1/auth/logout-everywhere` — Logout all sessions
- `POST /api/v1/auth/forgot-password` — Request password reset
- `POST /api/v1/auth/reset-password` — Complete password reset
- `POST /api/v1/auth/verify-email` — Verify email
- `POST /api/v1/auth/resend-verification` — Resend verification email

### OAuth (Social Login)
- `GET /api/v1/oauth/providers` — List supported providers
- `GET /api/v1/oauth/{provider}/initiate` — Start OAuth flow
- `GET /api/v1/oauth/{provider}/callback` — OAuth callback handler

### Users
- `GET /api/v1/users/` — List users (admin only)
- `GET /api/v1/users/{user_id}` — Get user by ID (admin or self)
- `PUT /api/v1/users/{user_id}` — Update user (admin or self)
- `DELETE /api/v1/users/{user_id}` — Delete user (admin or self)

### Health, Readiness, Liveness, Metrics
- `GET /health` — Basic health check
- `GET /health/database` — DB health
- `GET /health/database/detailed` — Detailed DB health (admin)
- `GET /health/readiness` — Readiness probe (Kubernetes)
- `GET /health/liveness` — Liveness probe (Kubernetes)
- `GET /metrics/database` — DB performance metrics (admin)
- `GET /metrics/database/queries` — Query analytics (admin)
- `GET /metrics/database/slow-queries` — Slow queries (admin)
- `POST /metrics/database/reset` — Reset DB metrics (admin)
- `GET /status` — System status (admin)

### Cache Management
- `GET /api/v1/cache/status` — Redis cache status
- `POST /api/v1/cache/clear` — Clear all cache
- `DELETE /api/v1/cache/{key}` — Clear specific cache key

## ⚙️ Configuration

### Environment Variables (`.env`)
```env
# API Settings
API_V1_STR=/api/v1
PROJECT_NAME=FastAPI Backend
VERSION=0.1.0

# CORS Settings
BACKEND_CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Database Settings
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aixiate_db
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:postgres@localhost:5432/aixiate_db

# Database Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_QUERY_TIMEOUT=30

# Redis Settings
REDIS_URL=redis://localhost:6379

# Security Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Email Settings
FROM_EMAIL=no-reply@example.com
RESEND_API_KEY=your-resend-api-key
FRONTEND_BASE_URL=http://localhost:3000

# OAuth Settings
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Account Security
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

## 🔒 Security Features

- **JWT Authentication**: Secure, stateless token-based auth
- **Password Hashing**: bcrypt with configurable schemes
- **Account Lockout**: Brute force attack prevention
- **Rate Limiting**: Configurable per-minute limits
- **Audit Logging**: Comprehensive activity tracking with JSON event data
- **CORS Configuration**: Secure cross-origin requests
- **Input Validation**: Pydantic schemas throughout
- **SQL Injection Prevention**: Parameterized queries
- **Security Headers**: Middleware for security headers
- **UUID Primary Keys**: Enhanced security through non-sequential IDs

## 📈 Performance & Monitoring

- **Fully Async**: async/await throughout the application
- **Connection Pooling**: Efficient database connections with configurable pool settings
- **Redis Caching**: Session and data caching
- **Retry Logic**: Transient failure handling
- **Performance Monitoring**: Real-time query analytics
- **Health Monitoring**: Comprehensive health checks
- **Query Analytics**: Slow query detection and reporting
- **Database Monitoring**: Connection pool status and performance metrics

## 🧪 Testing

- **OAuth Tests**: Comprehensive OAuth endpoint testing
- **Test Coverage**: Expanding test suite (contributions welcome!)
- **Test Client**: FastAPI TestClient for integration tests
- **Isolated Testing**: In-memory database for tests

## 📚 Additional Documentation

- [Redis Setup Guide](./REDIS_SETUP.md) — Complete Redis installation and configuration
- [Alembic Manual](./alembic_manual.md) — Database migration guide and cheatsheet

## 🔑 Authentication & Email Flows

- **Email Verification**: Required after registration with verification links
- **Password Reset**: Secure password reset via email
- **OAuth Integration**: Google and GitHub social login
- **Session Management**: Multi-device session tracking with UUID support
- **Account Security**: Lockout protection and audit logging

## 🚀 Deployment

### Docker
```bash
# Build and run with Docker Compose
docker-compose up -d
```

### Manual Deployment
1. Set up PostgreSQL and Redis
2. Configure environment variables
3. Run database migrations: `alembic upgrade head`
4. Start the application: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add/expand tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
