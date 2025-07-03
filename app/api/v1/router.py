"""
Main API router for version 1.

This module contains the main API router that includes all the
endpoint routers for version 1 of the API.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth
from app.api.v1.endpoints import users
from app.api.v1.endpoints import health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="", tags=["health", "monitoring"])


# Placeholder endpoints for now
@api_router.get("/")
async def api_root():
    """
    API root endpoint.

    Returns:
        dict: API information
    """
    return {
        "message": "FastAPI Backend API v1",
        "version": "1.0.0",
        "endpoints": {
            "auth": "Authentication endpoints",
            "users": "User management endpoints (coming soon)",
        },
    }
