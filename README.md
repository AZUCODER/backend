# FastAPI Backend

A robust, scalable, and secure FastAPI backend application with comprehensive authentication, authorization, and monitoring capabilities.

## 🚀 Overview

This backend application is built with FastAPI and provides a complete foundation for modern web applications with enterprise-grade security features, comprehensive authentication flows, and production-ready monitoring.

### Key Features

- **🔐 Authentication & Authorization**: JWT-based authentication with refresh tokens, OAuth integration (Google, GitHub), role-based access control
- **👥 User Management**: Complete user lifecycle with email verification, password reset, account lockout protection
- **🛡️ Security**: Rate limiting, security headers, CORS protection, audit logging, password hashing with bcrypt
- **📊 Monitoring**: Database connection monitoring, query performance metrics, health checks
- **🗄️ Database**: PostgreSQL with SQLModel (SQLAlchemy + Pydantic), Alembic migrations, UUID-based primary keys
- **⚡ Caching**: Redis integration for sessions and rate limiting
- **📧 Email**: Transactional emails via Resend API for verification and password reset
- **🐳 Containerization**: Multi-stage Docker builds with production optimizations
- **🧪 Testing**: Comprehensive test suite with pytest and async support

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic Settings configuration
│   ├── database.py             # Database connection and session management
│   ├── dependencies.py         # FastAPI dependency injection
│   │
│   ├── api/                    # API layer
│   │   └── v1/
│   │       ├── router.py       # Main API router
│   │       └── endpoints/      # API endpoints by feature
│   │           ├── auth.py     # Authentication endpoints
│   │           ├── oauth.py    # OAuth endpoints (Google, GitHub)
│   │           ├── users.py    # User management endpoints
│   │           ├── health.py   # Health check endpoints
│   │           └── cache.py    # Cache management endpoints
│   │
│   ├── models/                 # SQLModel database models
│   │   ├── base.py            # BaseModel with common fields (UUID, timestamps)
│   │   ├── user.py            # User model with roles and OAuth support
│   │   ├── session.py         # Session management and token blacklisting
│   │   ├── audit.py           # Audit logging for security events
│   │   └── email_verification.py # Email verification tokens
│   │
│   ├── schemas/                # Pydantic request/response schemas
│   │   └── auth.py            # Authentication-related schemas
│   │
│   ├── services/               # Business logic layer
│   │   ├── user_service.py    # User CRUD operations
│   │   ├── auth_service_improved.py # Enhanced authentication service
│   │   ├── session_service.py # Session and token management
│   │   ├── oauth_providers.py # OAuth provider implementations
│   │   ├── email_service.py   # Email delivery via Resend
│   │   ├── password_reset_service.py # Password reset functionality
│   │   ├── email_verification_service.py # Email verification
│   │   └── redis_service.py   # Redis operations and caching
│   │
│   ├── core/                   # Core utilities
│   │   └── security.py        # JWT token creation/validation, password hashing
│   │
│   ├── middleware/             # Custom middleware
│   │   ├── security.py        # Security headers middleware
│   │   └── rate_limit.py      # Rate limiting middleware
│   │
│   ├── database/               # Enhanced database components
│   │   ├── connection.py      # Database connection management
│   │   └── monitoring.py      # Database performance monitoring
│   │
│   ├── utils/                  # Utility functions
│   │   └── url_utils.py       # URL building utilities
│   │
│   └── tests/                  # Test modules
│       └── __init__.py
│
├── alembic/                    # Database migrations
│   ├── versions/              # Migration files
│   ├── env.py                 # Alembic environment configuration
│   └── alembic.ini           # Alembic configuration
│
├── tests/                      # Integration tests
│   └── test_oauth_endpoints.py
│
├── Dockerfile                  # Multi-stage Docker build
├── pyproject.toml             # Python dependencies and project metadata
├── uv.lock                    # Dependency lock file
└── main.py                    # Application entry point
```

## 🏗️ Architecture

### Authentication & Authorization System

The application implements a comprehensive authentication system with multiple layers of security:

#### **JWT Token Management**
- **Access Tokens**: Short-lived (30 minutes) for API access
- **Refresh Tokens**: Long-lived (7 days) for token renewal
- **Token Rotation**: Automatic refresh token rotation for enhanced security
- **Blacklisting**: Revoked tokens are tracked to prevent reuse

#### **OAuth Integration**
- **Google OAuth**: Complete PKCE flow with state validation
- **GitHub OAuth**: Secure OAuth implementation with user info fetching
- **Account Linking**: Automatic linking of OAuth accounts to existing users
- **CSRF Protection**: State parameter validation and secure cookie handling

#### **User Roles & Permissions**
```python
class UserRole(str, Enum):
    ADMIN = "admin"      # Full system access
    USER = "user"        # Standard user access
    GUEST = "guest"      # Limited access
```

#### **Security Features**
- **Account Lockout**: Configurable failed login attempt protection
- **Password Security**: bcrypt hashing with secure defaults
- **Email Verification**: Required for account activation
- **Audit Logging**: Comprehensive security event tracking
- **Rate Limiting**: Per-endpoint and global rate limits

### Database Architecture

#### **Models & Relationships**
- **BaseModel**: UUID primary keys, automatic timestamps
- **User Model**: Complete user profile with OAuth support
- **Session Model**: JWT session tracking with device info
- **Audit Model**: Security event logging
- **Email Verification**: Token-based email verification

#### **Database Features**
- **PostgreSQL**: Primary database with full ACID compliance
- **SQLModel**: Type-safe ORM with Pydantic integration
- **Alembic**: Database migration management
- **Connection Pooling**: Optimized connection management
- **Health Monitoring**: Real-time database performance metrics

### Caching & Performance

#### **Redis Integration**
- **Session Storage**: Distributed session management
- **Rate Limiting**: Request throttling and abuse prevention
- **Caching**: Frequently accessed data caching
- **Resilience**: Graceful degradation when Redis is unavailable

## 🔧 Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/aixiate_db
REDIS_URL=redis://localhost:6379

# Security Configuration
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080  # 7 days
ALGORITHM=HS256

# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Email Configuration
RESEND_API_KEY=your-resend-api-key
FROM_EMAIL=no-reply@example.com

# Application Configuration
DEBUG=false
TESTING=false
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=60

# CORS Configuration
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_BASE_URL=http://localhost:8000

# Account Security
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
```

### Development vs Production

The application automatically adjusts settings based on the `DEBUG` flag:
- **Development**: Shorter lockout durations, verbose logging, CORS relaxed
- **Production**: Strict security settings, optimized performance, comprehensive monitoring

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Redis 7+ (optional but recommended)
- Docker & Docker Compose (for containerized setup)

### Local Development

1. **Clone and Setup**
```bash
cd backend
pip install uv  # Fast Python package manager
uv sync         # Install dependencies
```

2. **Database Setup**
```bash
# Start PostgreSQL and Redis
docker-compose up postgres redis -d

# Run migrations
alembic upgrade head
```

3. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start Development Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations in container
docker-compose exec backend alembic upgrade head
```

## 📚 API Documentation

### Interactive Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core Endpoints

#### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/password-reset` - Password reset request
- `POST /api/v1/auth/password-reset/complete` - Complete password reset

#### OAuth
- `GET /oauth/{provider}/initiate` - Start OAuth flow
- `GET /oauth/{provider}/callback` - OAuth callback handler
- `GET /oauth/providers` - List available providers

#### User Management
- `GET /api/v1/users/profile` - Get user profile
- `PUT /api/v1/users/profile` - Update user profile
- `GET /api/v1/users/sessions` - List user sessions
- `DELETE /api/v1/users/sessions/{session_id}` - Revoke session

#### Health & Monitoring
- `GET /health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health status
- `GET /api/v1/health/database` - Database health metrics

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_oauth_endpoints.py -v
```

### Test Structure
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing
- **Security Tests**: Authentication and authorization testing

## 🔒 Security Considerations

### Production Deployment

1. **Environment Security**
   - Use strong, unique `SECRET_KEY`
   - Configure OAuth credentials securely
   - Set up proper CORS origins
   - Enable HTTPS with proper certificates

2. **Database Security**
   - Use connection pooling
   - Enable SSL connections
   - Regular backup procedures
   - Monitor for suspicious activity

3. **Monitoring & Logging**
   - Set up centralized logging
   - Monitor authentication failures
   - Track API usage patterns
   - Set up alerting for security events

### Security Headers

The application automatically sets comprehensive security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (HTTPS only)
- `Content-Security-Policy` with OAuth provider allowlists

## 📊 Monitoring & Observability

### Health Checks
- **Basic Health**: Application status and version
- **Database Health**: Connection status and query performance
- **Redis Health**: Cache availability and performance
- **Detailed Metrics**: Response times, error rates, resource usage

### Logging
- **Structured Logging**: JSON format for easy parsing
- **Audit Trails**: Security events and user actions
- **Performance Metrics**: Query times and resource usage
- **Error Tracking**: Comprehensive error logging with context

## 🤝 Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 and use type hints
2. **Testing**: Write tests for new features
3. **Documentation**: Update API documentation
4. **Security**: Follow security best practices
5. **Performance**: Consider performance implications

### Code Quality Tools
- **Type Checking**: mypy for static type analysis
- **Linting**: flake8 and black for code formatting
- **Testing**: pytest with async support
- **Security**: bandit for security linting

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation at `/docs`
- Review the health endpoints for system status
- Check logs for detailed error information
- Refer to the configuration guide for setup issues
