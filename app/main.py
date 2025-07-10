"""
FastAPI application entry point.

This module contains the main FastAPI application instance with
middleware, CORS, and API route configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.middleware import RateLimitMiddleware, SecurityMiddleware

settings = get_settings()

# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add security middleware first (before CORS)
app.add_middleware(SecurityMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

# When credentials are allowed, '*' is invalid. If no CORS origins are set, fallback to the
# configured FRONTEND_BASE_URL so that Axios requests with cookies/Authorization succeed during dev.
cors_origins = settings.get_cors_origins()
if not cors_origins or cors_origins == ["*"]:
    cors_origins = [settings.FRONTEND_BASE_URL.rstrip("/")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message
    """
    return {
        "message": "Welcome to FastAPI Backend",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    ) 
