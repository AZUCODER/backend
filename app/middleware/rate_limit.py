"""
Rate limiting middleware using Redis.

This module provides rate limiting functionality using Redis to track
API requests per user/IP address.
"""

import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.services.redis_service import redis_service
from app.config import get_settings

settings = get_settings()


from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(self._get_remaining_requests(client_id))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try to get user ID from request if authenticated
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fallback to IP address
        client_ip = request.client.host
        return f"ip:{client_ip}"
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        if not redis_service.is_connected():
            # If Redis is not available, allow all requests
            return True
        
        key = f"rate_limit:{client_id}"
        current_count = redis_service.increment(key, 1)
        
        if current_count == 1:
            # Set expiration for the first request
            redis_service.expire(key, 60)  # 1 minute window
        
        return current_count <= self.requests_per_minute
    
    def _get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if not redis_service.is_connected():
            return self.requests_per_minute
        
        key = f"rate_limit:{client_id}"
        current_count = redis_service.get(key)
        
        if current_count is None:
            return self.requests_per_minute
        
        remaining = self.requests_per_minute - int(current_count)
        return max(0, remaining)


class PerEndpointRateLimit(BaseHTTPMiddleware):
    """
    Per-endpoint rate limiting with different limits for different endpoints.
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Define rate limits for different endpoints
        self.endpoint_limits = {
            "/api/v1/auth/login": 5,      # 5 login attempts per minute
            "/api/v1/auth/register": 3,   # 3 registrations per minute
            "/api/v1/auth/refresh": 10,   # 10 token refreshes per minute
            "/api/v1/users": 30,          # 30 user operations per minute
            "/api/v1/health": 100,        # 100 health checks per minute
        }
        self.default_limit = 60
    
    async def dispatch(self, request: Request, call_next):
        # Get endpoint-specific limit
        path = request.url.path
        limit = self.endpoint_limits.get(path, self.default_limit)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        endpoint_key = f"rate_limit:{client_id}:{path}"
        
        # Check rate limit
        if not self._check_rate_limit(endpoint_key, limit):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded for {path}. Please try again later.",
                    "retry_after": 60
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(self._get_remaining_requests(endpoint_key, limit))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier."""
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        client_ip = request.client.host
        return f"ip:{client_ip}"
    
    def _check_rate_limit(self, key: str, limit: int) -> bool:
        """Check if client has exceeded rate limit for specific endpoint."""
        if not redis_service.is_connected():
            return True
        
        current_count = redis_service.increment(key, 1)
        
        if current_count == 1:
            redis_service.expire(key, 60)
        
        return current_count <= limit
    
    def _get_remaining_requests(self, key: str, limit: int) -> int:
        """Get remaining requests for client on specific endpoint."""
        if not redis_service.is_connected():
            return limit
        
        current_count = redis_service.get(key)
        
        if current_count is None:
            return limit
        
        remaining = limit - int(current_count)
        return max(0, remaining) 