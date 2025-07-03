# FastAPI Backend

A robust, scalable, and secure FastAPI backend with **enterprise-grade database architecture** for modern web applications.

## 🚀 Features

- **FastAPI**: Modern, fast web framework for building APIs with Python
- **Enhanced Database Layer**: Production-ready database architecture with monitoring
- **Repository Pattern**: Clean data access layer with type safety
- **Transaction Management**: Automatic retry logic and error recovery
- **Performance Monitoring**: Real-time query analytics and slow query detection
- **Health Monitoring**: Comprehensive system health checks and metrics
- **JWT Authentication**: Secure token-based authentication with enhanced security
- **PostgreSQL/SQLite**: Database support for both development and production
- **Async/Await**: Fully asynchronous for high performance
- **Auto-documentation**: Interactive API docs with Swagger UI
- **Type Safety**: Full type hints throughout the codebase

## 🏗️ Project Structure

```
backend/
├── app/                    # Main application package
│   ├── api/                # API routes
│   │   └── v1/             # API version 1
│   │       ├── router.py   # API v1 router
│   │       └── endpoints/  # Individual endpoint modules (auth.py, users.py, health.py)
│   ├── core/               # Core functionality (security)
│   ├── database/           # Database layer (connection, monitoring, transactions)
│   ├── models/             # SQLModel database models (user, session, audit, etc.)
│   ├── repositories/       # Repository pattern implementation (base, user)
│   ├── schemas/            # Pydantic schemas (auth, etc.)
│   ├── services/           # Business logic services (user, session, email, etc.)
│   ├── middleware/         # Custom middleware
│   ├── utils/              # Utility modules (url_utils)
│   ├── config.py           # Settings management
│   ├── database.py         # Database setup
│   ├── dependencies.py     # Dependency injection
│   ├── main.py             # FastAPI app entry point
│   └── tests/              # Test modules (to be implemented)
├── alembic/                # Database migrations
├── alembic.ini             # Alembic configuration
├── .env.example            # Environment variables example
├── .env                    # Actual environment variables (not committed)
├── pyproject.toml          # Project dependencies and configuration
├── DATABASE_IMPROVEMENTS_SUMMARY.md # Database improvements documentation
├── main.py                 # Entry point for running the app
├── test_db.py              # Test database script
└── Planning.md             # Planning and notes
```

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- uv (recommended) or pip for package management
- PostgreSQL (optional, SQLite is used by default)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd backend
   ```

2. **Install dependencies using uv (recommended)**
   ```bash
   pip install uv
   uv venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   uv pip install -r pyproject.toml
   ```

   **Alternative: Install all dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration if needed
   ```

4. **Run the development server**
   ```bash
   python main.py
   # or
   uvicorn app.main:app --reload
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health

## 🗄️ Database Architecture

- Repository pattern for all database operations (see `app/repositories/`)
- Transaction management with retry logic (see `app/database/transactions.py`)
- Performance monitoring (see `app/database/monitoring.py`)
- Health check endpoints (see `app/api/v1/endpoints/health.py`)

## 🗃️ Database Setup

- Default: SQLite for development
- Production: PostgreSQL (update `DATABASE_URL` in `.env`)
- Migrations: Alembic (see `alembic/` and `alembic.ini`)

## 🛠️ Development

- All main modules are implemented and production-ready except for tests (to be added)
- See `DATABASE_IMPROVEMENTS_SUMMARY.md` for details on database enhancements

## 🔌 API Endpoints

- `GET /` - API information and status
- `GET /health` - Basic health check
- `GET /api/v1/` - API v1 information
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info
- `GET /api/v1/auth/sessions` - User sessions
- `POST /api/v1/auth/password-reset` - Password reset
- `GET /api/v1/users/` - List users
- `GET /api/v1/users/{id}` - Get user by ID
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user
- `GET /health/database` - Database connectivity status
- `GET /health/database/detailed` - Detailed health info
- `GET /metrics/database` - Performance metrics
- `GET /metrics/database/queries` - Query analytics

## ⚙️ Configuration

- All configuration is via environment variables (`.env` and `.env.example`)
- Key variables: `DATABASE_URL`, `SECRET_KEY`, `BACKEND_CORS_ORIGINS`, `FRONTEND_BASE_URL`, etc.

## 🔒 Security

- JWT-based authentication
- Password hashing (bcrypt)
- Account lockout protection
- Audit logging
- CORS configuration
- Input validation (Pydantic)
- SQL injection prevention

## 📈 Performance

- Fully async with async/await
- Connection pooling
- Retry logic for transient failures
- Performance monitoring
- Redis caching (if enabled)

## 📊 Monitoring & Analytics

- Health monitoring
- Query analytics
- Security monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests (when test suite is implemented)
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📚 Additional Documentation

- [Database Improvements Summary](./DATABASE_IMPROVEMENTS_SUMMARY.md)
- [Planning](./Planning.md)

## 🔑 Authentication & Email Flows

- **Email Verification**: Users must verify their email after registration. A verification link is sent using the configured email service. The link uses the `FRONTEND_BASE_URL` from your `.env`.
- **Password Reset**: Users can request a password reset. The reset link is also sent using the configured email service and uses the same frontend URL config.
- **Reusable URL Helper**: All links in emails are generated using a single helper, so changing `FRONTEND_BASE_URL` updates all links.

## ⚙️ Environment Configuration

- **.env**: The file actually used by the backend. Contains real secrets and config. **Never commit this to public repos.**
- **.env.example**: Template for onboarding. Copy to `.env` and fill in your values.
- **Key variables:**
  - `DATABASE_URL` (default: SQLite for dev)
  - `FROM_EMAIL`, `RESEND_API_KEY` (for email delivery)
  - `FRONTEND_BASE_URL` (must match your running frontend, e.g. `http://localhost:3000`)

## 🔄 Recent Improvements

- Email verification and password reset flows are fully production-ready.
- All URLs in emails are absolute and environment-driven.
- Error handling and user feedback are robust and user-friendly.
