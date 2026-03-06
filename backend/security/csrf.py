"""CSRF protection via Bearer token enforcement for financial endpoints.

Financial mutation endpoints MUST use Authorization: Bearer <JWT> header.
Cookie-based authentication is rejected for these endpoints.
"""

from fastapi import HTTPException, Request
from typing import Optional


COOKIE_NAME = "access_token"


def get_bearer_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header only.
    
    Does NOT accept cookie-based tokens for financial endpoints.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def require_bearer_token(request: Request) -> str:
    """Require Bearer token for request. Rejects cookie-based auth.
    
    This function enforces that financial endpoints MUST use
    Authorization: Bearer <JWT> header for CSRF protection.
    
    Cookie-based auth with SameSite=None is vulnerable to CSRF
    attacks, so financial mutations must use Bearer tokens.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        JWT token string
    
    Raises:
        HTTPException 401: If no Bearer token provided
        HTTPException 403: If attempting to use cookie for financial endpoint
    """
    # Check if request has cookie but no Bearer token
    has_cookie = request.cookies.get(COOKIE_NAME) is not None
    bearer_token = get_bearer_token(request)
    
    if bearer_token:
        return bearer_token
    
    if has_cookie:
        raise HTTPException(
            status_code=403,
            detail="Financial endpoints require Authorization: Bearer <token> header. "
                   "Cookie-based authentication is not accepted for security reasons."
        )
    
    raise HTTPException(
        status_code=401,
        detail="Authorization header with Bearer token required"
    )
