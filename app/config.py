"""
Application configuration settings.

This module contains all the configuration settings for the FastAPI application
using Pydantic Settings for environment variable management.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, List, Optional, Sequence

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

    # ---------------------------------------------------------------------
    # CORS
    # Accept either: a JSON list, a comma-separated string, or individual
    # environment variables (the JSON list approach is the FastAPI docs
    # default).  The field stores the data normalised to a `list[str]`.
    # ---------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: Sequence[AnyHttpUrl | str] | str = ""

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _assemble_cors_origins(
        cls, v: str | Sequence[AnyHttpUrl | str]
    ) -> Sequence[AnyHttpUrl | str] | str:
        """Support formats: JSON list, comma string, list."""
        if isinstance(v, (list, tuple)):
            return [str(origin) for origin in v]

        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("["):
                # JSON list
                try:
                    origins = json.loads(v)
                    if isinstance(origins, list):
                        return [str(o) for o in origins]
                except json.JSONDecodeError:
                    # fall back to comma split below
                    pass
            # Comma-separated list
            return [o.strip() for o in v.split(",") if o.strip()]

        # Fallback – leave untouched
        return v

    # Convenience property to access the parsed list directly
    @property
    def cors_origins(self) -> List[str]:
        return list(self.BACKEND_CORS_ORIGINS)  # type: ignore[arg-type]

    # Backwards-compat helper – previously used by some modules
    def get_cors_origins(self) -> List[str]:  # pragma: no cover
        """Return CORS origins as list (legacy helper)."""
        return self.cors_origins

    # ---------------------------------------------------------------------
    # Database
    # ---------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_db"
    )
    DATABASE_URL_ASYNC: Optional[str] = None  # Populated automatically if unset

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

    # Email Settings – credentials should come from environment
    RESEND_API_KEY: str = ""  # pragma: allowlist secret (placeholder)
    FROM_EMAIL: str = "no-reply@example.com"

    # Frontend Settings
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Dynamically adjust lockout duration for development
    def model_post_init(self, __context__: Any) -> None:  # type: ignore[override]
        if self.DEBUG and os.getenv("ACCOUNT_LOCKOUT_DURATION_MINUTES") is None:
            # Shorten duration in dev when not explicitly overridden
            object.__setattr__(self, "ACCOUNT_LOCKOUT_DURATION_MINUTES", 2)

        # ------------------------------------------------------------------
        # Derive async DB URL if it wasn't supplied
        # ------------------------------------------------------------------
        if self.DATABASE_URL_ASYNC is None:
            async_url: Optional[str] = None
            if (
                self.DATABASE_URL.startswith("postgresql+")
                and "+psycopg" in self.DATABASE_URL
            ):
                async_url = self.DATABASE_URL.replace("+psycopg", "+asyncpg")
            elif self.DATABASE_URL.startswith("sqlite:///"):
                async_url = self.DATABASE_URL.replace(
                    "sqlite:///", "sqlite+aiosqlite:///"
                )

            if async_url:
                object.__setattr__(self, "DATABASE_URL_ASYNC", async_url)

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: The application settings instance
    """
    return Settings() 
