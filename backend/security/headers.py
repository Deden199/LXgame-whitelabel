"""Security headers middleware.

Adds production-grade security headers to all responses:
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Removes server fingerprinting
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Strict-Transport-Security (HSTS)
        # max-age=31536000 = 1 year, includeSubDomains for all subdomains
        if os.environ.get("ENABLE_HSTS", "1") == "1":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (basic)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Remove server fingerprinting headers (use del instead of pop)
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        
        return response


async def security_headers_middleware(request: Request, call_next):
    """Function-based middleware for security headers."""
    response = await call_next(request)
    
    # Strict-Transport-Security (HSTS)
    if os.environ.get("ENABLE_HSTS", "1") == "1":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking  
    response.headers["X-Frame-Options"] = "DENY"
    
    # Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # XSS Protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Remove server fingerprinting (use del instead of pop)
    if "Server" in response.headers:
        del response.headers["Server"]
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]
    
    return response
