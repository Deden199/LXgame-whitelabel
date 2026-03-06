"""Authentication module with security hardening.

SECURITY FEATURES:
1. JWT_SECRET is REQUIRED - no fallback (fail closed)
2. Short token expiry (15 minutes)
3. Secure cookie settings
4. Support for both cookie and Bearer token auth
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request, Response
from functools import wraps
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables early
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =============================================================================
# JWT CONFIGURATION - FAIL CLOSED
# =============================================================================

def _get_jwt_secret() -> str:
    """Get JWT secret from environment. FAILS if not set.
    
    SECURITY: No default fallback - application must have a proper secret.
    This prevents accidentally running with an insecure default.
    """
    secret = os.environ.get("JWT_SECRET")
    
    if not secret:
        error_msg = (
            "CRITICAL SECURITY ERROR: JWT_SECRET environment variable is not set. "
            "The application cannot start without a secure JWT secret. "
            "Please set JWT_SECRET in your .env file or environment."
        )
        logger.critical(error_msg)
        print(f"\n{'='*60}\n{error_msg}\n{'='*60}\n", file=sys.stderr)
        raise RuntimeError(error_msg)
    
    # Warn if secret is too short
    if len(secret) < 32:
        logger.warning(
            "JWT_SECRET is less than 32 characters. "
            "Consider using a longer secret for better security."
        )
    
    return secret


# Initialize secret at module load time - fails fast if missing
try:
    SECRET_KEY = _get_jwt_secret()
except RuntimeError:
    # Re-raise to crash startup
    raise

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes for security

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 60 * 15  # 15 minutes in seconds


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=COOKIE_MAX_AGE,
        path="/"
    )


def clear_auth_cookie(response: Response):
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="none",
        path="/"
    )


def get_token_from_request(request: Request) -> Optional[str]:
    """Get token from either cookie or Authorization header.
    
    Priority:
    1. Authorization: Bearer header (preferred for API calls)
    2. Cookie (for browser-based sessions)
    """
    # First try Authorization header (more secure for API calls)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    
    # Then try cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    
    return None


def get_bearer_token_only(request: Request) -> Optional[str]:
    """Get token from Authorization header ONLY.
    
    Used for financial endpoints that require Bearer auth (CSRF protection).
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


async def get_current_user(request: Request, db) -> dict:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User account is disabled")

    tenant_id = user.get("tenant_id")
    if tenant_id and tenant_id != "system":
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "status": 1, "is_active": 1})
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if tenant.get("status") and tenant.get("status") != "active":
            raise HTTPException(status_code=403, detail="Tenant is suspended")
        if tenant.get("status") is None and tenant.get("is_active") is False:
            raise HTTPException(status_code=403, detail="Tenant is suspended")
    
    return user


async def get_current_user_bearer_only(request: Request, db) -> dict:
    """Get current user from Bearer token ONLY.
    
    SECURITY: This function rejects cookie-based auth.
    Used for financial endpoints to prevent CSRF attacks.
    """
    token = get_bearer_token_only(request)
    
    if not token:
        # Check if cookie is present to give a helpful error
        if request.cookies.get(COOKIE_NAME):
            raise HTTPException(
                status_code=403,
                detail="Financial endpoints require Authorization: Bearer <token> header. "
                       "Cookie-based authentication is not accepted for security reasons."
            )
        raise HTTPException(status_code=401, detail="Authorization header with Bearer token required")
    
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User account is disabled")

    tenant_id = user.get("tenant_id")
    if tenant_id and tenant_id != "system":
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "status": 1, "is_active": 1})
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        if tenant.get("status") and tenant.get("status") != "active":
            raise HTTPException(status_code=403, detail="Tenant is suspended")
        if tenant.get("status") is None and tenant.get("is_active") is False:
            raise HTTPException(status_code=403, detail="Tenant is suspended")
    
    return user


def require_role(*allowed_roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            db = kwargs.get("db")
            
            if not request or not db:
                # Find request and db in args (for dependency injection)
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                    elif hasattr(arg, 'users'):
                        db = arg
            
            user = await get_current_user(request, db)
            if user.get("role") not in allowed_roles:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            kwargs["current_user"] = user
            return await func(*args, **kwargs)
        return wrapper
    return decorator
