"""
Security middleware for FastAPI application.

This module provides middleware to set security headers and other
security-related protections for the FastAPI application.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    This middleware sets standard HTTP security headers to protect
    against common web vulnerabilities and improve security posture.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Set security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=(), "
            "accelerometer=(), ambient-light-sensor=(), "
            "autoplay=(), encrypted-media=(), picture-in-picture=()"
        )
        # Set HSTS header for HTTPS (only in production)
        if request.url.scheme != "http" and request.url.hostname and "localhost" not in request.url.hostname:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Set Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://github.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://accounts.google.com https://github.com https://api.github.com; "
            "frame-src https://accounts.google.com https://github.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response 