"""
Application configuration settings.

This module contains all the configuration settings for the FastAPI application
using Pydantic Settings for environment variable management.
"""

from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Backend"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "A robust, scalable, and secure FastAPI backend"

    # CORS Settings
    BACKEND_CORS_ORIGINS: str = ""

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as a list of strings."""
        if not self.BACKEND_CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    # Database Settings
    DATABASE_URL: str = "sqlite:///app.db"
    DATABASE_URL_ASYNC: Optional[str] = "sqlite+aiosqlite:///app.db"

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379"

    # Security Settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # Password Settings (not configurable via env for security)
    PWD_CONTEXT_SCHEMES: List[str] = ["bcrypt"]
    PWD_CONTEXT_DEPRECATED: str = "auto"

    # Development Settings
    DEBUG: bool = False
    TESTING: bool = False

    # Logging Settings
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # Account Lockout Settings
    ACCOUNT_LOCKOUT_THRESHOLD: int = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30

    # Email Settings
    RESEND_API_KEY: str = "re_JASXKcyx_TUQUWs12GhqdyNAk59Bn55FS"
    FROM_EMAIL: str = "no-reply@symtext.com"

    # Frontend Settings
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: The application settings instance
    """
    return Settings() 
