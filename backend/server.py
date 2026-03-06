from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Header, Security, UploadFile, File, BackgroundTasks
import time
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import asyncio
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import secrets
from email.message import EmailMessage
import smtplib
import httpx
from pymongo import ReturnDocument
from pymongo.errors import ConfigurationError, DuplicateKeyError

# Security modules
from security import (
    verify_webhook_signature,
    WebhookSignatureError,
    WebhookTimestampExpired,
    WebhookSignatureMismatch,
    RateLimiter,
    RateLimitExceeded,
    SecurityHeadersMiddleware,
)
from security.rate_limiter import rate_limiter
from auth import get_current_user_bearer_only

from pydantic import BaseModel, Field, model_validator

from models import (
    Tenant, TenantCreate, TenantUpdate,
    User, UserCreate, UserLogin, UserPublic,
    Game, GameCreate, GameUpdate,
    Transaction, TransactionCreate,
    GameSession,
    TokenResponse, TenantStats, GlobalStats, PlayerStats,
    DepositRequest, WithdrawRequest, PlayerSettings, WalletCallbackResponse,
    PaymentEvent, DepositOrder, WithdrawalOrder,
    ProviderSessionRequest, ProviderSessionResponse,
    TenantSettings, TenantSettingsUpdate,
    TenantDomainSettings, TenantSEOSettings, TenantCustomHeaderSettings,
    ALLOWED_CURRENCIES
)
from auth import (
    hash_password, verify_password, create_access_token,
    set_auth_cookie, clear_auth_cookie, get_current_user, decode_access_token,
    get_token_from_request, ACCESS_TOKEN_EXPIRE_MINUTES
)
from providers import provider_registry, MockProviderAdapter, QTechAdapter, create_seamless_adapter_for_tenant
from wallet import ledger as wallet_ledger
from payments.services.payments_service import PaymentsService
from catalog_normalization import (
    aggregate_category_counts,
    aggregate_provider_rows,
    canonicalize_game_doc,
    clean_text,
    normalize_category,
    normalize_provider_code,
    render_game_thumbnail_svg,
    render_provider_logo_svg,
)
from bootstrap_seamless import bootstrap_default_platform_data
from providers.seamless_callbacks import (
    SeamlessCallbackHandler,
    SeamlessGameCallbackRequest,
    SeamlessMoneyCallbackRequest,
    SeamlessUserBalanceRequest,
    resolve_tenant_from_seamless_agent_code,
)
from finance import (
    TenantFinanceService,
    MongoTenantFinanceRepository,
    TenantFinanceStatus,
    TenantFrozenError,
    TopupResponse,
    ChargeResponse,
    TxType,
    SetupFeeMode,
)
from finance.models import (
    TopupRequest,
    SetThresholdRequest,
    FreezeRequest,
    ChargeInfraRequest,
    ChargeSetupRequest,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection - support common Railway variable names
mongo_url = (
    os.environ.get('MONGO_URL')
    or os.environ.get('MONGO_URI')
    or os.environ.get('MONGODB_URL')
    or os.environ.get('DATABASE_URL')
    or "mongodb://127.0.0.1:27017"
)

if os.environ.get("USE_MOCK_DB", "0") == "1":
    from mongomock_motor import AsyncMongoMockClient

    client = AsyncMongoMockClient()
else:
    # Keep server startup responsive in managed platforms (Railway, Render, etc)
    # by failing fast when MongoDB is temporarily unavailable.
    try:
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=int(os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")),
        )
    except ConfigurationError as exc:
        fallback_mongo_url = "mongodb://127.0.0.1:27017"
        logger = logging.getLogger(__name__)
        logger.error(
            "Invalid MongoDB URI '%s': %s. Falling back to %s",
            mongo_url,
            exc,
            fallback_mongo_url,
        )
        client = AsyncIOMotorClient(
            fallback_mongo_url,
            serverSelectionTimeoutMS=int(os.environ.get("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000")),
        )

db = client[os.environ.get('DB_NAME', 'gaming_platform')]
payments_service = PaymentsService(db)

# Finance service for tenant buffer/escrow management
finance_repo = MongoTenantFinanceRepository(db)
finance_service = TenantFinanceService(finance_repo)

# Frontend URL for CORS (production)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Create the main app
app = FastAPI(title="Gaming Platform Engine API")

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

uploads_dir = ROOT_DIR / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Static files for game icons (permanent local storage)
game_icons_dir = ROOT_DIR / "static" / "game_icons"
game_icons_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/static/game_icons", StaticFiles(directory=game_icons_dir), name="game_icons")


def custom_openapi():
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
        description="LooxGame API including QTech wallet callback endpoints.",
    )
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["APIKeyHeader"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = datetime.now(timezone.utc)
    try:
        response = await call_next(request)
        logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception as exc:
        logger.exception("Unhandled request error: %s", exc)
        asyncio.create_task(send_error_notification(
            "LooxGame API unhandled error",
            f"Path: {request.url.path}\nMethod: {request.method}\nError: {exc}",
        ))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    finally:
        elapsed_ms = (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
        logger.debug("Request finished in %.2fms", elapsed_ms)

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Register providers
mock_provider = MockProviderAdapter()
qtech_provider = QTechAdapter()
provider_registry.register(mock_provider)
provider_registry.register(qtech_provider)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ============ DEPENDENCY HELPERS ============
async def get_db():
    return db


def currency_quant(currency: Optional[str]) -> Decimal:
    normalized = normalize_currency(currency) or "IDR"
    if normalized == "IDR":
        return Decimal("1")
    return Decimal("0.01")


def money_to_decimal(value: float | int | str | Decimal, currency: Optional[str] = "IDR") -> Decimal:
    quant = currency_quant(currency)
    return Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)


def decimal_to_amount(value: Decimal, currency: Optional[str] = "IDR") -> int | float:
    quantized = value.quantize(currency_quant(currency), rounding=ROUND_HALF_UP)
    if normalize_currency(currency) == "IDR":
        return int(quantized)
    return float(quantized)


CURRENCY_CONVERSION_RATE = Decimal("16832.8")  # IDR to USD rate

# Exchange rates (approximate, as of 2025)
# 1 PHP ≈ 287 IDR
# 1 USD ≈ 56.5 PHP
EXCHANGE_RATES = {
    "IDR_USD": Decimal("16832.8"),   # 1 USD = 16832.8 IDR
    "IDR_PHP": Decimal("287.0"),     # 1 PHP = 287 IDR
    "USD_PHP": Decimal("56.5"),      # 1 USD = 56.5 PHP
}


def convert_amount(value: Decimal, from_currency: str, to_currency: str) -> Decimal:
    """Convert amount between currencies.
    
    Supported currencies: IDR, USD, PHP, USDT (treated as USD)
    """
    source = normalize_currency(from_currency) or "IDR"
    target = normalize_currency(to_currency) or "IDR"

    if source == "USDT":
        source = "USD"
    if target == "USDT":
        target = "USD"

    if source == target:
        converted = value
    # IDR conversions
    elif source == "IDR" and target == "USD":
        converted = value / EXCHANGE_RATES["IDR_USD"]
    elif source == "USD" and target == "IDR":
        converted = value * EXCHANGE_RATES["IDR_USD"]
    elif source == "IDR" and target == "PHP":
        converted = value / EXCHANGE_RATES["IDR_PHP"]
    elif source == "PHP" and target == "IDR":
        converted = value * EXCHANGE_RATES["IDR_PHP"]
    # USD-PHP conversions
    elif source == "USD" and target == "PHP":
        converted = value * EXCHANGE_RATES["USD_PHP"]
    elif source == "PHP" and target == "USD":
        converted = value / EXCHANGE_RATES["USD_PHP"]
    else:
        # Fallback: convert via IDR as intermediary
        logger.warning(f"Unknown currency conversion {source} -> {target}, using passthrough")
        converted = value

    return converted.quantize(currency_quant(to_currency), rounding=ROUND_HALF_UP)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def send_system_email(subject: str, body: str, recipients: Optional[list[str]] = None) -> bool:
    recipients = recipients or [os.environ.get("EMAIL_ALERT_TO", os.environ.get("EMAIL_FROM", "partnership@looxgame.com"))]
    sender = os.environ.get("EMAIL_FROM", "partnership@looxgame.com")
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        logger.warning("Email skipped: SMTP_HOST is not configured")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    use_tls = _bool_env("SMTP_USE_TLS", True)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        if use_tls:
            server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password or "")
        server.send_message(msg)
    return True


async def send_integration_notification(subject: str, body: str):
    try:
        await asyncio.to_thread(send_system_email, subject, body)
    except Exception as exc:
        logger.error("Failed to send integration notification: %s", exc)


async def send_error_notification(subject: str, body: str):
    try:
        await asyncio.to_thread(send_system_email, subject, body)
    except Exception as exc:
        logger.error("Failed to send error notification: %s", exc)


qtech_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def validate_qtech_api_key(x_api_key: Optional[str] = Security(qtech_api_key_header)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")

    key_hash = hash_api_key(x_api_key)
    db_key = await db.api_keys.find_one({"key_hash": key_hash, "is_active": True}, {"_id": 0})
    if db_key:
        await db.api_keys.update_one(
            {"id": db_key["id"]},
            {"$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}},
        )
        return

    expected = os.environ.get("QTECH_API_KEY")
    if expected and secrets.compare_digest(x_api_key, expected):
        return

    raise HTTPException(status_code=401, detail="Unauthorized integration request")


def provider_aliases(provider_slug: Optional[str], provider_id: Optional[str]) -> list[str]:
    aliases = ["mock"]
    for value in (provider_slug, provider_id):
        if value:
            aliases.append(str(value).strip().lower())
    # common normalizations
    normalized = []
    for alias in aliases:
        normalized.extend({alias, alias.replace("-", ""), alias.replace("_", "")})
    return list(dict.fromkeys([a for a in normalized if a]))


async def find_valid_game_session(session_id: Optional[str], player_id: str) -> Optional[dict]:
    if not session_id:
        return None
    return await db.game_sessions.find_one(
        {
            "id": session_id,
            "player_id": player_id,
            "status": {"$ne": "closed"},
        },
        {"_id": 0},
    )


async def get_authenticated_user(request: Request):
    return await get_current_user(request, db)


async def ensure_tenant_is_active(tenant_id: str):
    if tenant_id == "system" or tenant_id is None:
        return
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "id": 1, "status": 1, "is_active": 1})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    status = tenant.get("status")
    if status:
        if status != "active":
            raise HTTPException(status_code=403, detail="Tenant is suspended")
    elif tenant.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Tenant is suspended")


async def append_audit_log(actor_user_id: str, action: str, target_type: str, target_id: str, meta: Optional[dict] = None):
    now = datetime.now(timezone.utc).isoformat()
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "actor_user_id": actor_user_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "meta": meta or {},
        "created_at": now,
    })


def parse_datetime(val):
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    return val


# ============ PUBLIC IP HANDLING FOR VD7 ============
# Module-level cache for public IP (5 minute TTL)
_public_ip_cache: dict = {"ip": None, "expires_at": None}


def is_private_ip(ip: str) -> bool:
    """Check if IP is private/local (127.*, 10.*, 192.168.*, 172.16-31.*)"""
    if not ip:
        return True
    parts = ip.split(".")
    if len(parts) != 4:
        return True  # Invalid IP format
    try:
        first = int(parts[0])
        second = int(parts[1])
        if first == 127:  # Loopback
            return True
        if first == 10:  # 10.0.0.0/8
            return True
        if first == 192 and second == 168:  # 192.168.0.0/16
            return True
        if first == 172 and 16 <= second <= 31:  # 172.16.0.0/12
            return True
        return False
    except (ValueError, IndexError):
        return True


async def get_public_ip() -> Optional[str]:
    """Get public IP address with caching (5 min TTL)."""
    global _public_ip_cache
    import httpx
    
    now = datetime.now(timezone.utc)
    if _public_ip_cache["ip"] and _public_ip_cache["expires_at"] and now < _public_ip_cache["expires_at"]:
        return _public_ip_cache["ip"]
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.ipify.org")
            ip = response.text.strip()
            _public_ip_cache["ip"] = ip
            _public_ip_cache["expires_at"] = now + timedelta(minutes=5)
            logger.info(f"Public IP fetched: {ip}")
            return ip
    except Exception as e:
        logger.warning(f"Failed to fetch public IP: {e}")
        return _public_ip_cache.get("ip")  # Return cached value if available


async def get_client_ip_for_vd7(request: Request) -> str:
    """Get client IP for VD7 API calls.
    
    Priority:
    1. VD7_PLAYER_IP_OVERRIDE env var (for Windows localhost with NordVPN)
    2. x-forwarded-for header (for proxied requests)
    3. request.client.host (direct connection)
    4. If IP is private/local, fetch public IP from api.ipify.org
    """
    # Check for override first (Windows localhost + NordVPN scenario)
    override_ip = os.environ.get("VD7_PLAYER_IP_OVERRIDE")
    if override_ip and override_ip.strip():
        logger.info(f"Using VD7_PLAYER_IP_OVERRIDE: {override_ip}")
        return override_ip.strip()
    
    # Get IP from headers or client
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    
    # If private IP, try to get public IP
    if is_private_ip(client_ip):
        logger.info(f"Detected private IP: {client_ip}, fetching public IP...")
        public_ip = await get_public_ip()
        if public_ip:
            logger.info(f"Using public IP: {public_ip}")
            return public_ip
    
    return client_ip


def normalize_currency(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return str(value).upper()


async def get_player_preferred_currency(player_id: str) -> str:
    stats = await db.player_stats.find_one({"player_id": player_id}, {"_id": 0, "preferred_currency": 1})
    preferred = normalize_currency(stats.get("preferred_currency")) if stats else None
    if preferred in ALLOWED_CURRENCIES:
        return preferred
    return "IDR"


def resolve_request_currency(request_currency: Optional[str], preferred_currency: str) -> str:
    normalized = normalize_currency(request_currency)
    if normalized is None:
        return preferred_currency
    if normalized not in ALLOWED_CURRENCIES:
        raise HTTPException(status_code=400, detail="Mata uang tidak didukung")
    return normalized


async def ensure_player_wallet_currency(player_id: str, preferred_currency: str) -> tuple[float | int, str]:
    stats = await db.player_stats.find_one({"player_id": player_id}, {"_id": 0, "wallet_currency": 1})
    wallet_currency = normalize_currency(stats.get("wallet_currency")) if stats else None

    # Legacy compatibility: historical balances were stored in IDR while wallet_currency was absent.
    if wallet_currency not in ALLOWED_CURRENCIES:
        wallet_currency = "IDR"

    if wallet_currency == preferred_currency:
        player = await db.users.find_one({"id": player_id}, {"_id": 0, "wallet_balance": 1})
        return player.get("wallet_balance", 0), wallet_currency

    player = await db.users.find_one({"id": player_id}, {"_id": 0, "wallet_balance": 1})
    current_balance = money_to_decimal(player.get("wallet_balance", 0), wallet_currency)
    converted_balance = convert_amount(current_balance, wallet_currency, preferred_currency)
    converted_amount = decimal_to_amount(converted_balance, preferred_currency)

    await db.users.update_one({"id": player_id}, {"$set": {"wallet_balance": converted_amount}})
    await db.player_stats.update_one(
        {"player_id": player_id},
        {"$set": {"wallet_currency": preferred_currency, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    return converted_amount, preferred_currency


async def ensure_test_seed_data():
    tenant_count = await db.tenants.count_documents({})
    if tenant_count > 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    tenant_doc = {
        "id": "tenant_aurum_001",
        "name": "AurumBet",
        "slug": "aurumbet",
        "theme_preset": "royal_gold",
        "branding": {},
        "status": "active",
        "is_active": True,
        "provider_config": {"mock": {"enabled": True}},
        "created_at": now,
        "updated_at": now,
    }
    player_doc = {
        "id": "user_player_aurum_001",
        "tenant_id": "tenant_aurum_001",
        "email": "player1@aurumbet.demo",
        "password_hash": hash_password("player123"),
        "role": "player",
        "display_name": "Player Aurum",
        "wallet_balance": 1000000.0,
        "avatar_url": None,
        "is_active": True,
        "created_at": now,
        "last_login": None,
    }

    await db.tenants.insert_one(tenant_doc)
    await db.users.insert_many([
        {
            "id": "user_superadmin_001",
            "tenant_id": "system",
            "email": "admin@platform.com",
            "password_hash": hash_password("admin123"),
            "role": "super_admin",
            "display_name": "Platform Admin",
            "wallet_balance": 0,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        {
            "id": "user_admin_aurum_001",
            "tenant_id": "tenant_aurum_001",
            "email": "admin@aurumbet.com",
            "password_hash": hash_password("admin123"),
            "role": "tenant_admin",
            "display_name": "Aurum Admin",
            "wallet_balance": 0,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        player_doc,
    ])
    await db.providers.update_one(
        {"id": "mock"},
        {"$set": {"id": "mock", "name": "Mock Provider", "slug": "mock", "is_active": True}},
        upsert=True,
    )
    await db.games.update_one(
        {"id": "game_mock_001"},
        {
            "$set": {
                "id": "game_mock_001",
                "provider_id": "mock",
                "provider_slug": "mock",
                "external_game_id": "mock_ext_001",
                "name": "Mock Fortune",
                "category": "slot",
                "thumbnail_url": None,
                "description": "Seeded mock game",
                "rtp": 96.0,
                "volatility": "medium",
                "min_bet": 0.1,
                "max_bet": 1000,
                "is_active": True,
                "is_enabled": True,
                "tenant_ids": ["tenant_aurum_001"],
                "tags": ["mock"],
                "play_count": 0,
                "created_at": now,
            }
        },
        upsert=True,
    )
    await db.player_stats.insert_one({
        "player_id": player_doc["id"],
        "total_bets": 0,
        "total_wins": 0,
        "games_played": 0,
        "total_sessions": 0,
        "recent_games": [],
        "favorite_category": None,
        "deposit_limit": None,
        "session_reminder_enabled": True,
        "preferred_currency": "IDR",
        "wallet_currency": "IDR",
        "updated_at": now,
    })


# ============ AUTH ROUTES ============
@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, response: Response, request: Request):
    """Login for all user roles with rate limiting."""
    # Rate limiting by IP + email
    client_ip = rate_limiter.get_client_ip(request)
    try:
        rate_limiter.check_rate_limit("login", client_ip, credentials.email)
    except RateLimitExceeded as e:
        logger.warning(f"Login rate limit exceeded for {client_ip}/{credentials.email}")
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    
    query = {"email": credentials.email}
    
    if credentials.tenant_slug:
        tenant = await db.tenants.find_one({"slug": credentials.tenant_slug}, {"_id": 0})
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        query["tenant_id"] = tenant["id"]
    
    user = await db.users.find_one(query, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Account is disabled")

    await ensure_tenant_is_active(user["tenant_id"])

    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user["tenant_id"]
    }
    access_token = create_access_token(token_data)
    set_auth_cookie(response, access_token)
    
    if user['role'] == 'player':
        preferred_currency = await get_player_preferred_currency(user['id'])
        wallet_balance, _ = await ensure_player_wallet_currency(user['id'], preferred_currency)
        user['wallet_balance'] = wallet_balance
        user['preferred_currency'] = preferred_currency
        user['preferences'] = {'currency': preferred_currency}

    tenant = None
    if user["tenant_id"] != "system":
        tenant_doc = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
        if tenant_doc:
            tenant_doc['created_at'] = parse_datetime(tenant_doc['created_at'])
            tenant_doc['updated_at'] = parse_datetime(tenant_doc['updated_at'])
            tenant = Tenant(**tenant_doc)
    
    user['created_at'] = parse_datetime(user['created_at'])
    user['last_login'] = parse_datetime(user.get('last_login')) if user.get('last_login') else None
    user_public = UserPublic(**user)
    
    return TokenResponse(
        access_token=access_token,
        user=user_public,
        tenant=tenant,
        expires_in=TOKEN_EXPIRE_SECONDS
    )


@api_router.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully"}


@api_router.get("/auth/me", response_model=TokenResponse)
async def get_me(request: Request):
    user = await get_authenticated_user(request)
    await ensure_tenant_is_active(user["tenant_id"])
    user['created_at'] = parse_datetime(user['created_at'])
    user['last_login'] = parse_datetime(user.get('last_login')) if user.get('last_login') else None

    if user['role'] == 'player':
        preferred_currency = await get_player_preferred_currency(user['id'])
        wallet_balance, _ = await ensure_player_wallet_currency(user['id'], preferred_currency)
        user['wallet_balance'] = wallet_balance
        user['preferred_currency'] = preferred_currency
        user['preferences'] = {'currency': preferred_currency}
    
    tenant = None
    if user["tenant_id"] != "system":
        tenant_doc = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
        if tenant_doc:
            tenant_doc['created_at'] = parse_datetime(tenant_doc['created_at'])
            tenant_doc['updated_at'] = parse_datetime(tenant_doc['updated_at'])
            tenant = Tenant(**tenant_doc)
    
    return TokenResponse(
        access_token="",
        user=UserPublic(**user),
        tenant=tenant,
        expires_in=TOKEN_EXPIRE_SECONDS
    )


@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh auth token"""
    user = await get_authenticated_user(request)
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user["tenant_id"]
    }
    access_token = create_access_token(token_data)
    set_auth_cookie(response, access_token)
    return {"access_token": access_token, "expires_in": TOKEN_EXPIRE_SECONDS}


def _ensure_operator(user: dict):
    if user["role"] not in ["super_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def _normalize_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip().lower()


def _normalize_list_status(values: set[str]) -> set[str]:
    return {str(v).strip().lower() for v in values if v is not None}


async def _append_payment_audit_log(*, tenant_id: str, actor_role: str, actor_id: str, action: str, entity_type: str, entity_id: str, before: Optional[dict] = None, after: Optional[dict] = None):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "actor_role": actor_role,
        "actor_id": actor_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "before": before or {},
        "after": after or {},
        "ts": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


class GameToggleRequest(BaseModel):
    is_enabled: bool


class GameLimitsRequest(BaseModel):
    min_bet: float
    max_bet: float


@api_router.get('/operator/reports/ledger.csv')
async def export_ledger_csv(request: Request, from_date: Optional[str] = None, to_date: Optional[str] = None, type: Optional[str] = None, player_id: Optional[str] = None, game_id: Optional[str] = None):
    import csv
    import io
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    query = {'tenant_id': user['tenant_id']}
    if type:
        query['type'] = type
    if player_id:
        query['player_id'] = player_id
    if game_id:
        query['game_id'] = game_id
    if from_date or to_date:
        rng = {}
        if from_date:
            rng['$gte'] = from_date
        if to_date:
            rng['$lte'] = to_date
        query['timestamp'] = rng

    rows = await db.transactions.find(query, {'_id': 0}).sort('timestamp', -1).to_list(5000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['timestamp', 'tx_id', 'player_id', 'game_id', 'type', 'amount', 'currency', 'balance_before', 'balance_after'])
    for tx in rows:
        w.writerow([tx.get('timestamp'), tx.get('tx_id'), tx.get('player_id'), tx.get('game_id'), tx.get('type'), tx.get('amount'), tx.get('currency'), tx.get('balance_before'), tx.get('balance_after')])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=ledger.csv'})


@api_router.get('/operator/reports/revenue')
async def operator_revenue_report(request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    pipeline = [
        {'$match': {'tenant_id': user['tenant_id'], 'type': {'$in': ['bet', 'win']}}},
        {'$group': {
            '_id': {'game_id': '$game_id', 'provider_id': '$provider_id', 'type': '$type'},
            'total': {'$sum': '$amount'}
        }}
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(2000)
    grouped = {}
    for r in rows:
        key = (r['_id'].get('provider_id') or 'unknown', r['_id'].get('game_id') or 'unknown')
        grouped.setdefault(key, {'provider_id': key[0], 'game_id': key[1], 'bet': 0, 'win': 0})
        grouped[key][r['_id']['type']] = r['total']
    result = []
    for item in grouped.values():
        item['ggr'] = item['bet'] - item['win']
        result.append(item)
    return result


@api_router.post('/operator/games/{game_id}/toggle')
async def operator_toggle_game(game_id: str, payload: GameToggleRequest, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    result = await db.games.update_one({'id': game_id, 'tenant_ids': user['tenant_id']}, {'$set': {'is_enabled': payload.is_enabled}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Game not found for tenant')
    return {'success': True}


@api_router.post('/operator/games/{game_id}/limits')
async def operator_set_game_limits(game_id: str, payload: GameLimitsRequest, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    result = await db.games.update_one({'id': game_id, 'tenant_ids': user['tenant_id']}, {'$set': {'min_bet': payload.min_bet, 'max_bet': payload.max_bet}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Game not found for tenant')
    return {'success': True}


@api_router.get('/operator/risk/flags')
async def operator_risk_flags(request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    pipeline = [
        {'$match': {'tenant_id': user['tenant_id'], 'type': {'$in': ['deposit', 'withdrawal', 'bet']}}},
        {'$group': {
            '_id': '$player_id',
            'total_volume': {'$sum': '$amount'},
            'withdrawals': {'$sum': {'$cond': [{'$eq': ['$type', 'withdrawal']}, '$amount', 0]}},
            'deposits': {'$sum': {'$cond': [{'$eq': ['$type', 'deposit']}, '$amount', 0]}},
            'bets': {'$sum': {'$cond': [{'$eq': ['$type', 'bet']}, '$amount', 0]}},
            'tx_count': {'$sum': 1}
        }}
    ]
    rows = await db.transactions.aggregate(pipeline).to_list(1000)
    flags = []
    for r in rows:
        reasons = []
        if r['total_volume'] >= 50_000_000:
            reasons.append('high_volume')
        if r['deposits'] > 0 and r['withdrawals'] / max(r['deposits'], 1) > 0.8:
            reasons.append('withdraw_spike')
        if r['tx_count'] > 300:
            reasons.append('high_frequency')
        if reasons:
            flags.append({'player_id': r['_id'], 'reasons': reasons, **{k: r[k] for k in ['total_volume', 'withdrawals', 'deposits', 'bets', 'tx_count']}})
    return flags


@api_router.get("/operator/api-keys")
async def list_operator_api_keys(request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    records = await db.api_keys.find(
        {"tenant_id": user["tenant_id"]},
        {"_id": 0, "id": 1, "label": 1, "prefix": 1, "is_active": 1, "created_at": 1, "last_used_at": 1},
    ).sort("created_at", -1).to_list(100)
    return records


@api_router.post("/operator/api-keys")
async def create_operator_api_key(payload: dict, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    raw_key = f"qtk_{secrets.token_urlsafe(24)}"
    key_hash = hash_api_key(raw_key)
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "id": secrets.token_hex(16),
        "tenant_id": user["tenant_id"],
        "created_by": user["id"],
        "label": (payload or {}).get("label"),
        "prefix": raw_key[:12],
        "key_hash": key_hash,
        "is_active": True,
        "created_at": now,
        "last_used_at": None,
    }
    await db.api_keys.insert_one(record)
    return {
        "id": record["id"],
        "label": record["label"],
        "key": raw_key,
        "prefix": record["prefix"],
        "created_at": record["created_at"],
    }


@api_router.post("/operator/api-keys/{key_id}/revoke")
async def revoke_operator_api_key(key_id: str, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    result = await db.api_keys.update_one(
        {"id": key_id, "tenant_id": user["tenant_id"]},
        {"$set": {"is_active": False, "revoked_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True}


# ============ OPERATOR SETTINGS (DOMAIN, SEO, CUSTOM HEADER) ============
@api_router.get("/operator/settings")
async def get_operator_settings(request: Request):
    """Get tenant settings (domain, SEO, custom header)"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    settings = await db.tenant_settings.find_one({"tenant_id": user["tenant_id"]}, {"_id": 0})
    if not settings:
        # Return default settings
        default_settings = TenantSettings(tenant_id=user["tenant_id"]).model_dump()
        default_settings["created_at"] = default_settings["created_at"].isoformat()
        default_settings["updated_at"] = default_settings["updated_at"].isoformat()
        return default_settings
    
    return settings


# ============ VD7 AGGREGATOR STATUS ============
@api_router.get("/operator/vd7/status")
async def get_vd7_status(request: Request):
    """Get VD7 aggregator status for operator dashboard."""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    vd7_config = tenant.get("provider_config", {}).get("vd7", {})
    
    # Get VD7 game count for this tenant
    vd7_game_count = await db.games.count_documents({
        "tenant_ids": user["tenant_id"],
        "aggregator": "VD7",
        "is_active": True,
    })
    
    # Get last sync info (from game import)
    last_imported_game = await db.games.find_one(
        {"tenant_ids": user["tenant_id"], "aggregator": "VD7"},
        {"_id": 0, "created_at": 1, "updated_at": 1},
        sort=[("created_at", -1)],
    )
    
    last_sync = None
    if last_imported_game:
        last_sync = last_imported_game.get("updated_at") or last_imported_game.get("created_at")
    
    # Get recent game sessions for VD7 games
    recent_sessions = await db.game_sessions.count_documents({
        "tenant_id": user["tenant_id"],
        "provider_id": "vd7",
    })
    
    return {
        "enabled": vd7_config.get("enabled", False),
        "agent_code": vd7_config.get("agent_code", ""),
        "has_credentials": bool(
            vd7_config.get("client_id") and 
            vd7_config.get("client_secret") and 
            vd7_config.get("agent_secret")
        ),
        "api_base_url": vd7_config.get("api_base_url", os.environ.get("VD7_API_BASE_URL", "")),
        "game_count": vd7_game_count,
        "last_sync": last_sync,
        "total_sessions": recent_sessions,
        "status": "connected" if vd7_config.get("enabled") and vd7_config.get("client_id") else "not_configured",
    }


@api_router.post("/operator/vd7/sync-icons")
async def sync_vd7_icons(request: Request, background_tasks: BackgroundTasks):
    """Sync game icons from VD7 API (runs in background).
    
    Icons sourced ONLY from POST /api/v1/game/gamelist endpoint.
    REQUIRED: provider_codes must be configured in tenant.provider_config.vd7.provider_codes
    
    Thumbnail logic:
    - if mobileImgUrl not empty -> thumbnail_url = mobileImgUrl
    - else if pcImgUrl not empty -> thumbnail_url = pcImgUrl  
    - else -> thumbnail_url = null
    
    No Excel/Google Drive fallback. No hardcoded CDN patterns.
    Must be called from an IP-whitelisted environment.
    """
    import httpx
    
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    # Get public IP for error reporting
    public_ip = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            ip_response = await http_client.get("https://api.ipify.org")
            public_ip = ip_response.text.strip()
    except Exception:
        pass
    
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    vd7_config = tenant.get("provider_config", {}).get("vd7", {})
    if not vd7_config.get("enabled"):
        raise HTTPException(status_code=400, detail="VD7 not enabled for this tenant")
    
    # Get provider_codes - REQUIRED by API docs
    provider_codes = vd7_config.get("provider_codes") or os.environ.get("VD7_PROVIDER_CODES", "")
    
    if not provider_codes or not provider_codes.strip():
        raise HTTPException(
            status_code=400, 
            detail="provider_codes REQUIRED by VD7 API docs. Configure tenant.provider_config.vd7.provider_codes (e.g., 'FC,KM,SB') or set env VD7_PROVIDER_CODES"
        )
    
    from providers.vd7_adapter import VD7Adapter
    
    adapter = VD7Adapter(
        agent_code=vd7_config.get("agent_code"),
        agent_secret=vd7_config.get("agent_secret"),
        client_id=vd7_config.get("client_id"),
        client_secret=vd7_config.get("client_secret"),
        api_base_url=vd7_config.get("api_base_url"),
    )
    
    try:
        # Split provider_codes and loop per provider (VD7 API requires single provider per call)
        provider_code_list = [p.strip() for p in provider_codes.split(",") if p.strip()]
        all_games = []
        provider_results = {}
        errors = []
        
        for provider_code in provider_code_list:
            provider_results[provider_code] = {"fetched": 0, "status": "pending"}
            page = 1
            page_size = 1000
            
            while True:
                try:
                    result = await adapter.get_games(
                        provider_code=provider_code,  # Single provider per call
                        page=page, 
                        page_size=page_size
                    )
                    
                    # Check for record_not_found (code 114)
                    if result.get("error_code") == 114:
                        provider_results[provider_code]["status"] = "no_games"
                        break
                    
                    games = result.get("games", [])
                    all_games.extend(games)
                    provider_results[provider_code]["fetched"] += len(games)
                    
                    total_pages = result.get("total_pages", 1)
                    if page >= total_pages:
                        break
                    page += 1
                except Exception as e:
                    error_msg = str(e)
                    if "invalid_ip" in error_msg.lower() or "104" in error_msg:
                        provider_results[provider_code]["status"] = "ip_blocked"
                        errors.append(f"[{provider_code}] IP not whitelisted (code 104)")
                    elif "114" in error_msg or "record_not_found" in error_msg.lower():
                        provider_results[provider_code]["status"] = "no_games"
                    else:
                        provider_results[provider_code]["status"] = "error"
                        errors.append(f"[{provider_code}] {error_msg}")
                    break  # Continue to next provider
            
            if provider_results[provider_code]["fetched"] > 0:
                provider_results[provider_code]["status"] = "success"
        
        # If all providers blocked by IP, raise error
        all_blocked = all(r["status"] == "ip_blocked" for r in provider_results.values())
        if all_blocked and not all_games:
            return {
                "error": True,
                "error_code": 104,
                "egress_ip": public_ip,
                "message": f"IP WHITELIST ERROR (code 104): Request not from whitelisted IP. Current public IP: {public_ip}. Sync must be executed from a VD7-whitelisted environment.",
                "provider_results": provider_results
            }
        
        # Update database with icon URLs
        now_iso = datetime.now(timezone.utc).isoformat()
        updated_count = 0
        skipped_count = 0
        sample_games = []
        
        for game in all_games:
            game_code = game.get("game_code")
            if not game_code:
                skipped_count += 1
                continue
            
            mobile_url = game.get("mobile_img_url")
            pc_url = game.get("pc_img_url")
            
            # Get remote URL
            remote_url = mobile_url or pc_url
            
            # Download to local storage for permanent availability
            local_url = None
            if remote_url and game_code:
                try:
                    # Sanitize filename
                    safe_code = game_code.replace('/', '_').replace('\\', '_')
                    ext = '.png'
                    if '.webp' in remote_url.lower():
                        ext = '.webp'
                    elif '.jpg' in remote_url.lower() or '.jpeg' in remote_url.lower():
                        ext = '.jpg'
                    
                    filename = f"{safe_code}{ext}"
                    filepath = ROOT_DIR / "static" / "game_icons" / filename
                    
                    # Download image
                    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as dl_client:
                        img_response = await dl_client.get(remote_url)
                        if img_response.status_code == 200:
                            with open(filepath, 'wb') as f:
                                f.write(img_response.content)
                            local_url = f"/api/static/game_icons/{filename}"
                except Exception as dl_err:
                    logger.warning(f"Failed to download icon for {game_code}: {dl_err}")
            
            # Use local URL if downloaded, else fallback to remote
            thumbnail_url = local_url or remote_url
            
            update_data = {
                "icon_mobile_url": mobile_url,
                "icon_pc_url": pc_url,
                "thumbnail_url": thumbnail_url,
                "thumbnail_remote_url": remote_url,  # Keep original for reference
                "thumbnailUrl": thumbnail_url,
                "icon_source": "aggregator_api_local" if local_url else "aggregator_api",
                "icon_synced_at": now_iso,
            }
            
            result = await db.games.update_many(
                {
                    "$or": [
                        {"game_launch_id": game_code},
                        {"game_code": game_code},
                        {"external_game_id": game_code},
                    ],
                },
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                updated_count += result.modified_count
                if len(sample_games) < 3 and thumbnail_url:
                    sample_games.append({
                        "game_code": game_code,
                        "thumbnail_url": thumbnail_url
                    })
            else:
                skipped_count += 1
        
        return {
            "success": True,
            "public_ip": public_ip,
            "total_fetched": len(all_games),
            "total_updated": updated_count,
            "total_skipped": skipped_count,
            "sample_games": sample_games,
            "provider_results": provider_results,
            "message": f"Synced {updated_count} game icons from VD7 API"
        }
        
    except ValueError as e:
        # provider_codes required error
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        if "invalid_ip" in error_msg.lower() or "104" in error_msg:
            raise HTTPException(
                status_code=403, 
                detail=f"IP WHITELIST ERROR (code 104): Request not from whitelisted IP. Current public IP: {public_ip}. Sync must be executed from a VD7-whitelisted environment."
            )
        raise HTTPException(status_code=500, detail=f"Sync failed: {error_msg}")


# Global sync status tracking
_sync_status = {
    "is_running": False,
    "started_at": None,
    "completed_at": None,
    "total_downloaded": 0,
    "total_updated": 0,
    "last_error": None,
}


async def _background_sync_icons(tenant_id: str, provider_codes_list: list):
    """Background task to sync icons."""
    from providers import create_vd7_adapter_for_tenant
    
    global _sync_status
    _sync_status["is_running"] = True
    _sync_status["started_at"] = datetime.now(timezone.utc).isoformat()
    _sync_status["total_downloaded"] = 0
    _sync_status["total_updated"] = 0
    _sync_status["last_error"] = None
    
    logger.info(f"Background sync started for tenant {tenant_id}, providers: {provider_codes_list}")
    
    try:
        # Get tenant VD7 config
        tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "provider_config": 1})
        if not tenant:
            _sync_status["last_error"] = f"Tenant not found: {tenant_id}"
            logger.error(f"Tenant not found: {tenant_id}")
            return
            
        vd7_config = tenant.get("provider_config", {}).get("vd7", {})
        logger.info(f"VD7 config: enabled={vd7_config.get('enabled')}")
        
        provider = create_vd7_adapter_for_tenant(vd7_config)
        if not provider:
            _sync_status["last_error"] = "VD7 not configured"
            logger.error("VD7 adapter not configured")
            return
        
        all_games = []
        for provider_code in provider_codes_list:
            logger.info(f"Fetching games for provider: {provider_code}")
            page = 1
            while page <= 10:  # Max 10 pages per provider
                try:
                    result = await provider.get_games(provider_code=provider_code, page=page, page_size=100)
                    games = result.get("games", [])
                    all_games.extend(games)
                    logger.info(f"  Page {page}: got {len(games)} games")
                    
                    total_pages = result.get("total_pages", 1)
                    if page >= total_pages:
                        break
                    page += 1
                except Exception as e:
                    logger.error(f"Error fetching games for {provider_code}: {e}")
                    break
        
        logger.info(f"Total games to process: {len(all_games)}")
        
        # Download icons
        now_iso = datetime.now(timezone.utc).isoformat()
        for game in all_games:
            game_code = game.get("game_code")
            if not game_code:
                continue
            
            remote_url = game.get("mobile_img_url") or game.get("pc_img_url")
            if not remote_url:
                continue
            
            # Download to local
            local_url = None
            try:
                safe_code = game_code.replace('/', '_').replace('\\', '_')
                ext = '.png'
                if '.webp' in remote_url.lower():
                    ext = '.webp'
                elif '.jpg' in remote_url.lower() or '.jpeg' in remote_url.lower():
                    ext = '.jpg'
                
                filename = f"{safe_code}{ext}"
                filepath = ROOT_DIR / "static" / "game_icons" / filename
                
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as dl_client:
                    img_response = await dl_client.get(remote_url)
                    if img_response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        local_url = f"/api/static/game_icons/{filename}"
                        _sync_status["total_downloaded"] += 1
            except Exception as dl_err:
                logger.warning(f"Failed to download icon for {game_code}: {dl_err}")
            
            thumbnail_url = local_url or remote_url
            
            result = await db.games.update_many(
                {
                    "$or": [
                        {"game_launch_id": game_code},
                        {"game_code": game_code},
                        {"external_game_id": game_code},
                    ],
                },
                {"$set": {
                    "thumbnail_url": thumbnail_url,
                    "thumbnail_remote_url": remote_url,
                    "icon_source": "aggregator_api_local" if local_url else "aggregator_api",
                    "icon_synced_at": now_iso,
                }}
            )
            
            if result.modified_count > 0:
                _sync_status["total_updated"] += result.modified_count
        
        _sync_status["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Background sync completed: downloaded={_sync_status['total_downloaded']}, updated={_sync_status['total_updated']}")
        
    except Exception as e:
        _sync_status["last_error"] = str(e)
        logger.error(f"Background sync error: {e}")
    finally:
        _sync_status["is_running"] = False


@api_router.post("/operator/vd7/sync-icons-async")
async def sync_vd7_icons_async(request: Request, background_tasks: BackgroundTasks):
    """Start background sync of game icons from VD7 API.
    Returns immediately with status. Check /operator/vd7/sync-icons-status for progress.
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    if _sync_status["is_running"]:
        return {
            "success": False,
            "message": "Sync already in progress",
            "status": _sync_status
        }
    
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0, "provider_config": 1})
    vd7_config = tenant.get("provider_config", {}).get("vd7", {}) if tenant else {}
    
    provider_codes_str = vd7_config.get("provider_codes", "PP,ZF_PGSOFT")
    provider_codes_list = [p.strip() for p in provider_codes_str.split(",") if p.strip()]
    
    # Start background task using asyncio.create_task for proper async execution
    import asyncio
    asyncio.create_task(_background_sync_icons(user["tenant_id"], provider_codes_list))
    
    return {
        "success": True,
        "message": "Sync started in background",
        "providers": provider_codes_list,
        "check_status_at": "/api/operator/vd7/sync-icons-status"
    }


@api_router.get("/operator/vd7/sync-icons-status")
async def get_sync_icons_status(request: Request):
    """Get status of background icon sync."""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    # Also count local icons
    local_icons_count = len(list((ROOT_DIR / "static" / "game_icons").glob("*")))
    
    return {
        **_sync_status,
        "local_icons_count": local_icons_count,
    }


@api_router.put("/operator/settings")
async def update_operator_settings(payload: TenantSettingsUpdate, request: Request):
    """Update tenant settings (domain, SEO, custom header)"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    update_data = {}
    if payload.domain is not None:
        update_data["domain"] = payload.domain.model_dump()
    if payload.seo is not None:
        update_data["seo"] = payload.seo.model_dump()
    if payload.custom_header is not None:
        update_data["custom_header"] = payload.custom_header.model_dump()
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.tenant_settings.find_one_and_update(
        {"tenant_id": user["tenant_id"]},
        {"$set": update_data, "$setOnInsert": {
            "id": str(uuid.uuid4()),
            "tenant_id": user["tenant_id"],
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0}
    )
    
    return result


# ============ TENANT FINANCE & RISK (SALDO BUFFER/ESCROW) ============
@api_router.get("/tenant/finance")
async def get_tenant_finance(request: Request):
    """Get tenant finance status (Saldo Buffer, freeze status, commercial terms).
    
    Returns:
        TenantFinanceStatus with buffer balance, threshold, freeze status
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    status = await finance_service.get_status(user["tenant_id"])
    return status.model_dump()


@api_router.post("/tenant/buffer/topup")
async def topup_tenant_buffer(payload: TopupRequest, request: Request):
    """Topup tenant buffer (Saldo Buffer).
    
    Idempotent by ref_id - same ref_id will return same result without double-applying.
    May auto-unfreeze tenant if buffer reaches threshold after topup.
    
    Request:
        - amount_idr: Amount in IDR (integer)
        - ref_id: Unique reference ID for idempotency
        - note: Optional description
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    try:
        result = await finance_service.topup_buffer(
            tenant_id=user["tenant_id"],
            amount_minor=payload.amount_idr,  # IDR is already minor units
            ref_id=payload.ref_id,
            note=payload.note,
            created_by=user["id"],
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/tenant/buffer/set-threshold")
async def set_tenant_buffer_threshold(payload: SetThresholdRequest, request: Request):
    """Set buffer minimum threshold.
    
    May trigger auto-freeze if new threshold > current balance.
    Requires tenant_admin or super_admin role.
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    finance = await finance_service.set_threshold(
        tenant_id=user["tenant_id"],
        threshold_minor=payload.threshold_idr,
    )
    
    if not finance:
        raise HTTPException(status_code=404, detail="Tenant finance not found")
    
    return {
        "success": True,
        "tenant_id": user["tenant_id"],
        "buffer_min_threshold_minor": finance.buffer_min_threshold_minor,
        "buffer_balance_minor": finance.buffer_balance_minor,
        "is_frozen": finance.is_frozen,
    }


@api_router.post("/tenant/freeze")
async def freeze_tenant(payload: FreezeRequest, request: Request):
    """Manually freeze tenant.
    
    Super admin can force freeze any tenant.
    Tenant admin can request freeze for their own tenant.
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    finance = await finance_service.freeze_tenant(
        tenant_id=user["tenant_id"],
        reason=payload.reason,
    )
    
    return {
        "success": True,
        "tenant_id": user["tenant_id"],
        "is_frozen": finance.is_frozen,
        "frozen_reason": finance.frozen_reason,
    }


@api_router.post("/tenant/unfreeze")
async def unfreeze_tenant(request: Request):
    """Unfreeze tenant (only works if buffer >= threshold).
    
    Returns error if buffer is still below minimum threshold.
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    success, finance, message = await finance_service.unfreeze_tenant(user["tenant_id"])
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "success": True,
        "tenant_id": user["tenant_id"],
        "is_frozen": finance.is_frozen if finance else False,
        "message": message,
    }


@api_router.get("/tenant/finance/transactions")
async def list_tenant_finance_transactions(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    tx_type: Optional[str] = None,
):
    """List tenant finance transactions (topups, fees, adjustments).
    
    Query params:
        - limit: Max results (default 50)
        - offset: Pagination offset
        - tx_type: Filter by type (TOPUP, INFRA_FEE, SETUP_FEE, etc.)
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    type_filter = TxType(tx_type) if tx_type else None
    
    transactions = await finance_service.list_transactions(
        tenant_id=user["tenant_id"],
        limit=limit,
        offset=offset,
        tx_type=type_filter,
    )
    
    return {
        "transactions": [tx.model_dump() for tx in transactions],
        "count": len(transactions),
    }


# ============ SUPER ADMIN FINANCE OPERATIONS ============
@api_router.post("/admin/tenant/{tenant_id}/fees/charge-infra")
async def charge_tenant_infra_fee(tenant_id: str, payload: ChargeInfraRequest, request: Request):
    """Charge monthly infrastructure fee to tenant (super_admin only).
    
    Deducts from tenant buffer. May trigger auto-freeze.
    Idempotent by ref_id.
    """
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    # Verify tenant exists
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        result = await finance_service.charge_infra_fee(
            tenant_id=tenant_id,
            month=payload.month,
            amount_minor=payload.amount_idr,
            ref_id=payload.ref_id,
            created_by=user["id"],
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.post("/admin/tenant/{tenant_id}/fees/charge-setup")
async def charge_tenant_setup_fee(tenant_id: str, payload: ChargeSetupRequest, request: Request):
    """Charge setup/activation fee to tenant (super_admin only).
    
    ACTIVATION_DEPOSIT mode: Amount is added to buffer (Deposit Aktivasi)
    NON_REFUNDABLE mode: Recorded but does not affect buffer
    
    Idempotent by ref_id.
    """
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    # Verify tenant exists
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        result = await finance_service.charge_setup_fee(
            tenant_id=tenant_id,
            amount_minor=payload.amount_idr,
            ref_id=payload.ref_id,
            mode=payload.mode,
            created_by=user["id"],
        )
        return result.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@api_router.get("/admin/tenant/{tenant_id}/finance")
async def get_tenant_finance_admin(tenant_id: str, request: Request):
    """Get tenant finance status (super_admin only)."""
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    status = await finance_service.get_status(tenant_id)
    return status.model_dump()


@api_router.post("/admin/tenant/{tenant_id}/freeze")
async def admin_freeze_tenant(tenant_id: str, payload: FreezeRequest, request: Request):
    """Force freeze a tenant (super_admin only)."""
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    finance = await finance_service.freeze_tenant(
        tenant_id=tenant_id,
        reason=f"[Admin] {payload.reason}",
    )
    
    return {
        "success": True,
        "tenant_id": tenant_id,
        "is_frozen": finance.is_frozen,
        "frozen_reason": finance.frozen_reason,
    }


@api_router.post("/admin/tenant/{tenant_id}/unfreeze")
async def admin_unfreeze_tenant(tenant_id: str, request: Request):
    """Force unfreeze a tenant (super_admin only).
    
    Unlike tenant unfreeze, admin can force unfreeze even if below threshold.
    """
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin access required")
    
    finance = await finance_repo.set_frozen(tenant_id, is_frozen=False, reason=None)
    
    if not finance:
        raise HTTPException(status_code=404, detail="Tenant finance not found")
    
    return {
        "success": True,
        "tenant_id": tenant_id,
        "is_frozen": finance.is_frozen,
        "message": "Tenant unfrozen by admin",
    }


# ============ OPERATOR WITHDRAWALS MANAGEMENT ============
@api_router.get("/operator/withdrawals")
async def list_operator_withdrawals(
    request: Request,
    status: Optional[str] = None,
    currency: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 100
):
    """List withdrawal orders for operator"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = _normalize_status(status)
    if currency:
        query["currency"] = currency
    if from_date or to_date:
        rng = {}
        if from_date:
            rng["$gte"] = from_date
        if to_date:
            rng["$lte"] = to_date
        query["created_at"] = rng
    
    withdrawals = await db.withdrawal_orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Enrich with player info
    player_ids = list(set(w.get("player_id") for w in withdrawals if w.get("player_id")))
    players = await db.users.find({"id": {"$in": player_ids}}, {"_id": 0, "id": 1, "email": 1, "display_name": 1}).to_list(len(player_ids))
    players_map = {p["id"]: p for p in players}
    
    for w in withdrawals:
        player = players_map.get(w.get("player_id"), {})
        w["player_email"] = player.get("email")
        w["player_name"] = player.get("display_name")
        w["status"] = _normalize_status(w.get("status"))
    
    return withdrawals


# ============ OPERATOR GAMES MANAGEMENT ============
@api_router.get("/operator/games")
async def list_operator_games(
    request: Request,
    category: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    limit: int = 200
):
    """List games for operator management"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    query = {"tenant_ids": user["tenant_id"]}
    if category and category != "all":
        query["category"] = category
    if provider and provider != "all":
        query["$or"] = [
            {"provider_name": provider},
            {"provider_slug": provider}
        ]
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    if is_enabled is not None:
        query["is_enabled"] = is_enabled
    
    games = await db.games.find(query, {"_id": 0}).sort("name", 1).to_list(limit)
    
    for g in games:
        g['created_at'] = parse_datetime(g['created_at'])
        g.setdefault('is_enabled', True)
        g.setdefault('min_bet', 0.1)
        g.setdefault('max_bet', 1000)
        g.setdefault('tags', [])
    
    return games


class GameTagsRequest(BaseModel):
    tags: List[str]


@api_router.post('/operator/games/{game_id}/tags')
async def operator_set_game_tags(game_id: str, payload: GameTagsRequest, request: Request):
    """Set game tags (Hot, New, Popular, etc)"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    result = await db.games.update_one(
        {'id': game_id, 'tenant_ids': user['tenant_id']},
        {'$set': {'tags': payload.tags}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail='Game not found for tenant')
    return {'success': True}


# ============ OPERATOR RISK FLAGS MANAGEMENT ============
class AdminTenantCreateRequest(BaseModel):
    name: str
    slug: str
    branding: Optional[dict] = None


class AdminTenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    branding: Optional[dict] = None


class AdminTenantAdminCreateRequest(BaseModel):
    email: str
    password: str
    display_name: str


class RiskFlagRequest(BaseModel):
    reason: Optional[str] = None


@api_router.post('/operator/risk/flag/{player_id}')
async def flag_player_risk(player_id: str, payload: RiskFlagRequest, request: Request):
    """Flag a player for risk review"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    await db.risk_flags.update_one(
        {"tenant_id": user["tenant_id"], "player_id": player_id},
        {"$set": {
            "tenant_id": user["tenant_id"],
            "player_id": player_id,
            "flagged": True,
            "reason": payload.reason,
            "flagged_by": user["id"],
            "flagged_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    return {"success": True}


@api_router.post('/operator/risk/unflag/{player_id}')
async def unflag_player_risk(player_id: str, request: Request):
    """Remove risk flag from player"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    await db.risk_flags.update_one(
        {"tenant_id": user["tenant_id"], "player_id": player_id},
        {"$set": {"flagged": False, "unflagged_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True}


@api_router.get('/operator/risk/flagged')
async def list_flagged_players(request: Request):
    """List all flagged players"""
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    flags = await db.risk_flags.find(
        {"tenant_id": user["tenant_id"], "flagged": True},
        {"_id": 0}
    ).to_list(500)
    
    # Enrich with player info
    player_ids = [f["player_id"] for f in flags]
    players = await db.users.find({"id": {"$in": player_ids}}, {"_id": 0, "id": 1, "email": 1, "display_name": 1}).to_list(len(player_ids))
    players_map = {p["id"]: p for p in players}
    
    for f in flags:
        player = players_map.get(f["player_id"], {})
        f["player_email"] = player.get("email")
        f["player_name"] = player.get("display_name")
    
    return flags


# ============ SUPER ADMIN CONSOLE ROUTES ============
@api_router.post("/admin/tenants", response_model=Tenant)
async def admin_create_tenant(payload: AdminTenantCreateRequest, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    slug = payload.slug.strip().lower()
    existing_slug = await db.tenants.find_one({"slug": slug}, {"_id": 0, "id": 1})
    if existing_slug:
        raise HTTPException(status_code=409, detail="Tenant slug already exists")

    now = datetime.now(timezone.utc)
    tenant_obj = Tenant(
        name=payload.name,
        slug=slug,
        branding=payload.branding or {},
        is_active=True,
    )
    tenant_doc = tenant_obj.model_dump()
    tenant_doc["status"] = "active"
    tenant_doc["created_at"] = now.isoformat()
    tenant_doc["updated_at"] = now.isoformat()

    await db.tenants.insert_one(tenant_doc)
    await append_audit_log(user["id"], "tenant.created", "tenant", tenant_doc["id"], {
        "name": payload.name,
        "slug": slug,
    })

    tenant_doc["created_at"] = parse_datetime(tenant_doc["created_at"])
    tenant_doc["updated_at"] = parse_datetime(tenant_doc["updated_at"])
    return tenant_doc


@api_router.get("/admin/tenants")
async def admin_list_tenants(request: Request, search: Optional[str] = None, status: Optional[str] = None):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"slug": {"$regex": search, "$options": "i"}},
        ]
    if status in {"active", "suspended"}:
        query["status"] = status

    tenants = await db.tenants.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)

    tenant_ids = [t["id"] for t in tenants]
    admins_by_tenant = {}
    if tenant_ids:
        admins = await db.users.find(
            {"tenant_id": {"$in": tenant_ids}, "role": "tenant_admin"},
            {"_id": 0, "tenant_id": 1, "id": 1, "email": 1, "display_name": 1, "is_active": 1, "created_at": 1},
        ).to_list(1000)
        for admin in admins:
            admin["created_at"] = parse_datetime(admin.get("created_at")) if admin.get("created_at") else None
            admins_by_tenant.setdefault(admin["tenant_id"], []).append(admin)

    for tenant in tenants:
        tenant["created_at"] = parse_datetime(tenant["created_at"])
        tenant["updated_at"] = parse_datetime(tenant["updated_at"])
        tenant.setdefault("status", "active" if tenant.get("is_active", True) else "suspended")
        tenant["admin_count"] = len(admins_by_tenant.get(tenant["id"], []))

    return tenants


@api_router.get("/admin/tenants/{tenant_id}")
async def admin_get_tenant(tenant_id: str, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant_admins = await db.users.find(
        {"tenant_id": tenant_id, "role": "tenant_admin"},
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).to_list(200)

    for admin in tenant_admins:
        admin["created_at"] = parse_datetime(admin.get("created_at")) if admin.get("created_at") else None
        admin["last_login"] = parse_datetime(admin.get("last_login")) if admin.get("last_login") else None

    tenant["created_at"] = parse_datetime(tenant["created_at"])
    tenant["updated_at"] = parse_datetime(tenant["updated_at"])
    tenant.setdefault("status", "active" if tenant.get("is_active", True) else "suspended")

    return {"tenant": tenant, "admins": tenant_admins}


@api_router.patch("/admin/tenants/{tenant_id}")
async def admin_update_tenant(tenant_id: str, payload: AdminTenantUpdateRequest, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update fields provided")

    if "status" in update_data:
        if update_data["status"] not in {"active", "suspended"}:
            raise HTTPException(status_code=400, detail="status must be active or suspended")
        update_data["is_active"] = update_data["status"] == "active"
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await append_audit_log(user["id"], "tenant.updated", "tenant", tenant_id, update_data)

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant["created_at"] = parse_datetime(tenant["created_at"])
    tenant["updated_at"] = parse_datetime(tenant["updated_at"])
    tenant.setdefault("status", "active" if tenant.get("is_active", True) else "suspended")
    return tenant


@api_router.post("/admin/tenants/{tenant_id}/admins")
async def admin_create_tenant_admin(tenant_id: str, payload: AdminTenantAdminCreateRequest, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "id": 1})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    existing_email = await db.users.find_one({"email": payload.email.lower()}, {"_id": 0, "id": 1})
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    admin_user = User(
        tenant_id=tenant_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="tenant_admin",
        display_name=payload.display_name,
        wallet_balance=0,
        is_active=True,
    )
    admin_doc = admin_user.model_dump()
    admin_doc["created_at"] = admin_doc["created_at"].isoformat()
    admin_doc["last_login"] = None

    await db.users.insert_one(admin_doc)
    admin_doc.pop("_id", None)
    await append_audit_log(user["id"], "tenant_admin.created", "user", admin_doc["id"], {
        "tenant_id": tenant_id,
        "email": admin_doc["email"],
    })

    admin_doc.pop("password_hash", None)
    admin_doc["created_at"] = parse_datetime(admin_doc["created_at"])
    return admin_doc


@api_router.get("/admin/audit-logs")
async def admin_audit_logs(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for log in logs:
        log["created_at"] = parse_datetime(log.get("created_at")) if log.get("created_at") else None
    return logs


# ============ TENANT ROUTES ============
@api_router.get("/tenants", response_model=List[Tenant])
async def list_tenants(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    for t in tenants:
        t['created_at'] = parse_datetime(t['created_at'])
        t['updated_at'] = parse_datetime(t['updated_at'])
    return tenants


@api_router.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin" and user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant['created_at'] = parse_datetime(tenant['created_at'])
    tenant['updated_at'] = parse_datetime(tenant['updated_at'])
    return tenant


@api_router.get("/tenants/slug/{slug}", response_model=Tenant)
async def get_tenant_by_slug(slug: str):
    tenant = await db.tenants.find_one({"slug": slug}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant['created_at'] = parse_datetime(tenant['created_at'])
    tenant['updated_at'] = parse_datetime(tenant['updated_at'])
    return tenant


@api_router.get("/resolve-domain")
async def resolve_tenant_by_domain(request: Request):
    """Resolve tenant by Host header domain"""
    host = request.headers.get("host", "").split(":")[0].lower()
    
    # Skip resolution for localhost and dev domains
    if host in ["localhost", "127.0.0.1", "0.0.0.0"] or host.endswith(".preview.emergentagent.com"):
        return {"tenant_id": None, "resolved": False, "host": host}
    
    # Find tenant settings with this domain
    settings = await db.tenant_settings.find_one({
        "$or": [
            {"domain.primary_domain": host},
            {"domain.allowed_domains": host}
        ]
    }, {"_id": 0, "tenant_id": 1, "domain": 1})
    
    if settings:
        tenant = await db.tenants.find_one({"id": settings["tenant_id"]}, {"_id": 0})
        if tenant:
            tenant['created_at'] = parse_datetime(tenant['created_at'])
            tenant['updated_at'] = parse_datetime(tenant['updated_at'])
            
            # Get SEO settings too
            full_settings = await db.tenant_settings.find_one({"tenant_id": settings["tenant_id"]}, {"_id": 0})
            
            return {
                "tenant_id": settings["tenant_id"],
                "resolved": True,
                "host": host,
                "tenant": tenant,
                "settings": full_settings
            }
    
    return {"tenant_id": None, "resolved": False, "host": host}


@api_router.get("/tenant-meta/{tenant_id}")
async def get_tenant_meta(tenant_id: str):
    """Get tenant meta tags for SEO (public endpoint)"""
    settings = await db.tenant_settings.find_one({"tenant_id": tenant_id}, {"_id": 0, "seo": 1, "custom_header": 1})
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0, "name": 1, "branding": 1})
    
    return {
        "seo": settings.get("seo") if settings else {},
        "custom_header": settings.get("custom_header") if settings else {},
        "tenant_name": tenant.get("name") if tenant else None,
        "branding": tenant.get("branding") if tenant else {}
    }


@api_router.put("/tenants/{tenant_id}", response_model=Tenant)
async def update_tenant(tenant_id: str, update: TenantUpdate, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] not in ["super_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if user["role"] == "tenant_admin" and user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Cannot modify other tenants")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if update_data.get("branding"):
        update_data["branding"] = update_data["branding"].model_dump() if hasattr(update_data["branding"], "model_dump") else update_data["branding"]
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.tenants.update_one({"id": tenant_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    tenant['created_at'] = parse_datetime(tenant['created_at'])
    tenant['updated_at'] = parse_datetime(tenant['updated_at'])
    return tenant


# ============ USER/PLAYER ROUTES ============
@api_router.get("/users", response_model=List[UserPublic])
async def list_users(request: Request, tenant_id: Optional[str] = None, role: Optional[str] = None):
    user = await get_authenticated_user(request)
    query = {}
    
    if user["role"] == "super_admin":
        if tenant_id:
            query["tenant_id"] = tenant_id
    elif user["role"] == "tenant_admin":
        query["tenant_id"] = user["tenant_id"]
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if role:
        query["role"] = role
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    for u in users:
        u['created_at'] = parse_datetime(u['created_at'])
        u['last_login'] = parse_datetime(u.get('last_login')) if u.get('last_login') else None
    return users


@api_router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: str, request: Request):
    current_user = await get_authenticated_user(request)
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if current_user["role"] == "player" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user["role"] == "tenant_admin" and current_user["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    user['created_at'] = parse_datetime(user['created_at'])
    user['last_login'] = parse_datetime(user.get('last_login')) if user.get('last_login') else None
    return user


# ============ PLAYER STATS ROUTES ============
@api_router.get("/player/stats")


async def get_player_settings_doc(player_id: str) -> dict:
    stats = await db.player_stats.find_one({"player_id": player_id}, {"_id": 0})
    return stats or {}


async def enforce_responsible_gaming(player_id: str, tenant_id: str, amount: Decimal, currency: str):
    settings = await get_player_settings_doc(player_id)
    now = datetime.now(timezone.utc)
    self_exclusion_until = settings.get('self_exclusion_until')
    if self_exclusion_until:
        exclusion_dt = parse_datetime(self_exclusion_until)
        if exclusion_dt and exclusion_dt > now:
            return False, 'SELF_EXCLUDED', f'Self exclusion active until {exclusion_dt.isoformat()}'

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    day_query = {"tenant_id": tenant_id, "player_id": player_id, "timestamp": {"$gte": day_start}}
    txs = await db.transactions.find(day_query, {"_id": 0, "type": 1, "amount": 1, "currency": 1}).to_list(5000)

    daily_wager = Decimal('0')
    daily_bet = Decimal('0')
    daily_win = Decimal('0')
    for tx in txs:
        tx_amt = money_to_decimal(tx.get('amount', 0), tx.get('currency', currency))
        if tx.get('type') == 'bet':
            daily_wager += tx_amt
            daily_bet += tx_amt
        elif tx.get('type') == 'win':
            daily_win += tx_amt

    wager_limit = settings.get('wager_limit_daily')
    if wager_limit is not None and daily_wager + amount > money_to_decimal(wager_limit, currency):
        return False, 'LIMIT_EXCEEDED', 'Daily wager limit exceeded'

    loss_limit = settings.get('loss_limit_daily')
    if loss_limit is not None:
        projected_loss = (daily_bet + amount) - daily_win
        if projected_loss > money_to_decimal(loss_limit, currency):
            return False, 'LIMIT_EXCEEDED', 'Daily loss limit exceeded'

    return True, 'OK', 'Allowed'

async def get_player_stats(request: Request):
    """Get current player's stats"""
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players have stats")
    
    stats = await db.player_stats.find_one({"player_id": user["id"]}, {"_id": 0})
    if not stats:
        stats = {
            "player_id": user["id"],
            "total_bets": 0,
            "total_wins": 0,
            "games_played": 0,
            "total_sessions": 0,
            "recent_games": [],
            "favorite_category": None,
            "deposit_limit": None,
            "session_reminder_enabled": True,
            "preferred_currency": "IDR"
        }
    else:
        stats["preferred_currency"] = normalize_currency(stats.get("preferred_currency")) or "IDR"
    return stats


@api_router.put("/player/settings")
async def update_player_settings(settings: PlayerSettings, request: Request):
    """Update player's responsible gaming settings"""
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can update settings")
    
    preferred_currency = normalize_currency(settings.preferred_currency) or "IDR"

    update_data = {
        "deposit_limit": settings.deposit_limit,
        "deposit_limit_daily": settings.deposit_limit_daily if settings.deposit_limit_daily is not None else settings.deposit_limit,
        "loss_limit_daily": settings.loss_limit_daily,
        "wager_limit_daily": settings.wager_limit_daily,
        "self_exclusion_until": settings.self_exclusion_until.isoformat() if settings.self_exclusion_until else None,
        "cooldown_limit_increase_until": settings.cooldown_limit_increase_until.isoformat() if settings.cooldown_limit_increase_until else None,
        "session_reminder_enabled": settings.session_reminder_enabled,
        "preferred_currency": preferred_currency,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.player_stats.update_one(
        {"player_id": user["id"]},
        {"$set": update_data},
        upsert=True
    )

    await ensure_player_wallet_currency(user["id"], preferred_currency)
    return {"success": True}


@api_router.get("/player/recent-games")
async def get_recent_games(request: Request):
    """Get player's recently played games"""
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players")
    
    stats = await db.player_stats.find_one({"player_id": user["id"]}, {"_id": 0})
    recent = stats.get("recent_games", []) if stats else []
    
    # Enrich with game data
    game_ids = [rg["game_id"] for rg in recent]
    games = await db.games.find({"id": {"$in": game_ids}}, {"_id": 0}).to_list(10)
    games_map = {g["id"]: g for g in games}
    
    enriched = []
    for rg in recent:
        game = games_map.get(rg["game_id"], {})
        enriched.append({
            **rg,
            "thumbnail_url": game.get("thumbnail_url"),
            "category": game.get("category")
        })
    
    return enriched


# ============ GAME ROUTES ============
@api_router.get("/providers")
async def list_providers(request: Request, tenant_id: Optional[str] = None):
    """Get normalized provider list for the current tenant."""
    user = await get_authenticated_user(request)
    effective_tenant = tenant_id or (user["tenant_id"] if user["tenant_id"] != "system" else None)
    query = {"is_active": True, "is_enabled": {"$ne": False}}
    if effective_tenant:
        query["tenant_ids"] = effective_tenant

    raw_games = await db.games.find(query, {"_id": 0}).to_list(5000)
    games = [canonicalize_game_doc(game) for game in raw_games if clean_text(game.get("name"))]
    return aggregate_provider_rows(games)


@api_router.get("/games", response_model=List[Game])
async def list_games(
    request: Request,
    tenant_id: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    provider: Optional[str] = None
):
    user = await get_authenticated_user(request)
    effective_tenant = tenant_id or (user["tenant_id"] if user["tenant_id"] != "system" else None)
    query = {"is_active": True, "is_enabled": {"$ne": False}}
    if effective_tenant:
        query["tenant_ids"] = effective_tenant
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    raw_games = await db.games.find(query, {"_id": 0}).to_list(5000)
    games = [canonicalize_game_doc(game) for game in raw_games if clean_text(game.get("name"))]

    if category and category != "all":
        normalized_category = normalize_category(category)
        games = [game for game in games if game.get("category") == normalized_category]

    if provider and provider != "all":
        provider_value = clean_text(provider).lower()
        games = [
            game for game in games
            if provider_value in {
                clean_text(game.get("provider_code")).lower(),
                clean_text(game.get("provider_name")).lower(),
                clean_text(game.get("provider_slug")).lower(),
                clean_text(game.get("provider_id")).lower(),
            }
        ]

    if tag:
        tag_value = clean_text(tag).lower()
        games = [
            game for game in games
            if tag_value in {item.lower() for item in game.get("tags", [])}
            or (tag_value == "hot" and game.get("is_hot"))
            or (tag_value == "new" and game.get("is_new"))
            or (tag_value == "popular" and game.get("is_popular"))
        ]

    for game in games:
        game["created_at"] = parse_datetime(game["created_at"])
        if game.get("updated_at"):
            game["updated_at"] = parse_datetime(game["updated_at"])
        game.setdefault("play_count", 0)
        if game.get("rtp") is None:
            game["rtp"] = 96.0

    games.sort(
        key=lambda item: (
            -int(item.get("is_hot", False)),
            -int(item.get("is_new", False)),
            -int(item.get("is_popular", False)),
            -int(item.get("play_count", 0)),
            item.get("provider_name", "").lower(),
            item.get("name", "").lower(),
        )
    )
    return games


@api_router.get("/games/categories")
async def get_game_categories(request: Request):
    """Get normalized game categories with accurate tenant counts."""
    user = await get_authenticated_user(request)
    raw_games = await db.games.find(
        {"is_active": True, "is_enabled": {"$ne": False}, "tenant_ids": user["tenant_id"]},
        {"_id": 0},
    ).to_list(5000)
    games = [canonicalize_game_doc(game) for game in raw_games if clean_text(game.get("name"))]
    return aggregate_category_counts(games)


@api_router.get("/games/{game_id}", response_model=Game)
async def get_game(game_id: str, request: Request):
    await get_authenticated_user(request)
    game = await db.games.find_one({"id": game_id}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    game = canonicalize_game_doc(game)
    game['created_at'] = parse_datetime(game['created_at'])
    if game.get('updated_at'):
        game['updated_at'] = parse_datetime(game['updated_at'])
    return game


@api_router.put("/games/{game_id}")
async def update_game(game_id: str, update: GameUpdate, request: Request):
    """Update game (enable/disable, tags)"""
    user = await get_authenticated_user(request)
    if user["role"] not in ["super_admin", "tenant_admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data")
    
    result = await db.games.update_one({"id": game_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return {"success": True}


# ============ WALLET / DEPOSIT / WITHDRAW ROUTES ============
class QTechWalletRequest(BaseModel):
    tenant_id: str
    player_id: str
    session_id: Optional[str] = None
    transaction_id: str = Field(min_length=1, max_length=128)
    reference_transaction_id: Optional[str] = None
    round_id: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "IDR"

    @model_validator(mode="after")
    def validate_currency(self):
        currency = normalize_currency(self.currency)
        if currency not in ALLOWED_CURRENCIES:
            raise ValueError("Unsupported currency")
        return self


class ApiKeyCreateResponse(BaseModel):
    id: str
    label: Optional[str] = None
    key: str
    prefix: str
    created_at: str


class ApiKeyPublic(BaseModel):
    id: str
    label: Optional[str] = None
    prefix: str
    is_active: bool
    created_at: str
    last_used_at: Optional[str] = None


class ApiKeyCreateRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=64)


def qtech_balance_tx_id(transaction_id: str) -> str:
    return f"bal:{transaction_id}"


def wallet_ok(*, code: str = "OK", message: str = "Success", transaction_id: str, player_id: str, currency: str, balance: int | float, idempotent: Optional[bool] = None):
    return {
        "status": "ok",
        "code": code,
        "message": message,
        "transaction_id": transaction_id,
        "player_id": player_id,
        "currency": currency,
        "balance": balance,
        "idempotent": idempotent,
    }


def wallet_error(*, code: str, message: str, transaction_id: str, player_id: str, currency: str = "IDR", balance: int | float = 0):
    return {
        "status": "error",
        "code": code,
        "message": message,
        "transaction_id": transaction_id,
        "player_id": player_id,
        "currency": currency,
        "balance": balance,
    }


def _idempotent_wallet_response(existing_tx: dict, transaction_id: str, player_id: str) -> dict:
    return wallet_ok(
        transaction_id=transaction_id,
        player_id=player_id,
        currency=existing_tx.get("currency", "IDR"),
        balance=existing_tx.get("balance_after", 0),
        message="Duplicate callback acknowledged",
        idempotent=True,
    )


async def _create_wallet_tx(
    *,
    tenant_id: str,
    player_id: str,
    tx_type: str,
    tx_id: str,
    amount: Decimal,
    currency: str,
    balance_before: Decimal,
    balance_after: Decimal,
    session_id: Optional[str] = None,
    round_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    from models import Transaction

    tx = Transaction(
        tenant_id=tenant_id,
        player_id=player_id,
        session_id=session_id,
        round_id=round_id,
        type=tx_type,
        tx_id=tx_id,
        amount=decimal_to_amount(amount, currency),
        currency=currency,
        balance_before=decimal_to_amount(balance_before, currency),
        balance_after=decimal_to_amount(balance_after, currency),
        description=description,
        metadata=metadata or {},
    )

    tx_doc = tx.model_dump()
    tx_doc["timestamp"] = tx_doc["timestamp"].isoformat()
    try:
        await db.transactions.insert_one(tx_doc)
        return tx_doc, False
    except DuplicateKeyError:
        existing = await db.transactions.find_one(
            {"tenant_id": tenant_id, "tx_id": tx_id},
            {"_id": 0},
        )
        if not existing:
            raise
        return existing, True




async def _normalized_wallet_balance(player_id: str, currency: str) -> Decimal:
    player_doc = await db.users.find_one({"id": player_id}, {"_id": 0, "wallet_balance": 1})
    if not player_doc:
        raise HTTPException(status_code=404, detail="Player wallet not found")
    normalized = money_to_decimal(player_doc.get("wallet_balance", 0), currency)
    normalized_amount = decimal_to_amount(normalized, currency)
    if player_doc.get("wallet_balance") != normalized_amount:
        await db.users.update_one({"id": player_id}, {"$set": {"wallet_balance": normalized_amount}})
    return normalized


async def _validate_player_wallet_access(payload: QTechWalletRequest) -> dict:
    player = await db.users.find_one(
        {
            "id": payload.player_id,
            "tenant_id": payload.tenant_id,
            "role": "player",
            "is_active": True,
        },
        {"_id": 0},
    )
    if not player:
        raise HTTPException(status_code=404, detail="Player not found or inactive")

    if payload.session_id:
        session = await find_valid_game_session(payload.session_id, payload.player_id)
        if not session:
            raise HTTPException(status_code=403, detail="Invalid player session")

    return player


@api_router.post("/wallet/deposit")
async def deposit(deposit_req: DepositRequest, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can make deposits")
    
    if deposit_req.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal setoran tidak valid")

    preferred_currency = await get_player_preferred_currency(user["id"])
    tx_currency = resolve_request_currency(deposit_req.currency, preferred_currency)

    # Check deposit limit
    stats = await db.player_stats.find_one({"player_id": user["id"]}, {"_id": 0})
    if stats and stats.get("deposit_limit"):
        # Get today's deposits
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_deposits = await db.transactions.aggregate([
            {"$match": {
                "player_id": user["id"],
                "type": "deposit",
                "timestamp": {"$gte": today_start.isoformat()}
            }},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(1)
        
        today_total = today_deposits[0]["total"] if today_deposits else 0
        if today_total + deposit_req.amount > stats["deposit_limit"]:
            raise HTTPException(
                status_code=400, 
                detail="Melebihi batas deposit harian. Silakan coba lagi besok atau kurangi nominal."
            )
    
    wallet_balance, wallet_currency = await ensure_player_wallet_currency(user["id"], preferred_currency)

    deposit_amount = money_to_decimal(deposit_req.amount, tx_currency)
    deposit_in_wallet = convert_amount(deposit_amount, tx_currency, wallet_currency)

    current_balance = money_to_decimal(wallet_balance, wallet_currency)
    new_balance = current_balance + deposit_in_wallet
    new_balance_amount = decimal_to_amount(new_balance, wallet_currency)

    await db.users.update_one({"id": user["id"]}, {"$set": {"wallet_balance": new_balance_amount}})

    tx_balance_before = convert_amount(current_balance, wallet_currency, tx_currency)
    tx_balance_after = convert_amount(new_balance, wallet_currency, tx_currency)

    from models import Transaction, generate_id
    tx = Transaction(
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        type="deposit",
        amount=decimal_to_amount(deposit_amount, tx_currency),
        currency=tx_currency,
        balance_before=decimal_to_amount(tx_balance_before, tx_currency),
        balance_after=decimal_to_amount(tx_balance_after, tx_currency),
        description="Setoran via metode demo"
    )
    
    tx_doc = tx.model_dump()
    tx_doc['timestamp'] = tx_doc['timestamp'].isoformat()
    await db.transactions.insert_one(tx_doc)
    
    return {
        "success": True,
        "amount": decimal_to_amount(deposit_amount, tx_currency),
        "balance_before": decimal_to_amount(tx_balance_before, tx_currency),
        "balance_after": decimal_to_amount(tx_balance_after, tx_currency),
        "transaction_id": tx.tx_id,
        "currency": tx_currency
    }


@api_router.post(
    "/wallet/balance",
    dependencies=[Depends(validate_qtech_api_key)],
    response_model=WalletCallbackResponse,
    openapi_extra={
        "security": [{"APIKeyHeader": []}],
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "tenant_id": "tenant_aurum_001",
                        "player_id": "user_player_aurum_001",
                        "transaction_id": "bal-1001",
                        "currency": "IDR"
                    }
                }
            }
        },
    },
)
async def qtech_wallet_balance(payload: QTechWalletRequest):
    player = await _validate_player_wallet_access(payload)
    currency = resolve_request_currency(payload.currency, "IDR")

    ledger_tx_id = qtech_balance_tx_id(payload.transaction_id)
    existing = await wallet_ledger.find_tx_by_tx_id(db, payload.tenant_id, payload.player_id, ledger_tx_id)
    if existing:
        return _idempotent_wallet_response(existing, payload.transaction_id, payload.player_id)

    balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)
    await wallet_ledger.record_tx(
        db,
        tenant_id=payload.tenant_id,
        player_id=payload.player_id,
        tx_id=ledger_tx_id,
        tx_type="adjustment",
        amount=wallet_ledger.money_to_decimal("0", currency),
        currency=currency,
        balance_before=balance,
        balance_after=balance,
        session_id=payload.session_id,
        round_id=payload.round_id,
        description="QTech balance check",
        metadata={"source": "qtech", "operation": "balance", "original_transaction_id": payload.transaction_id},
    )
    return wallet_ok(
        transaction_id=payload.transaction_id,
        player_id=payload.player_id,
        currency=currency,
        balance=wallet_ledger.decimal_to_amount(balance, currency),
    )


@api_router.post(
    "/wallet/debit",
    dependencies=[Depends(validate_qtech_api_key)],
    response_model=WalletCallbackResponse,
)
async def qtech_wallet_debit(payload: QTechWalletRequest):
    """Wallet debit for bets - CRITICAL ENFORCEMENT POINT.
    
    This is the SINGLE SOURCE OF TRUTH for tenant freeze enforcement.
    If tenant is frozen or buffer below threshold, bets are blocked here.
    """
    # FINANCE ENFORCEMENT (CRITICAL): Check tenant can operate before any bet
    can_operate, frozen_error = await finance_service.check_or_autofreeze(payload.tenant_id)
    if not can_operate:
        # Return wallet error format for provider compatibility
        return wallet_error(
            code="TENANT_FROZEN",
            message=frozen_error.message,
            transaction_id=payload.transaction_id,
            player_id=payload.player_id,
            currency=payload.currency or "IDR",
            balance=0  # Will be updated below if player found
        )
    
    player = await _validate_player_wallet_access(payload)
    currency = resolve_request_currency(payload.currency, "IDR")
    current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)

    if payload.amount is None or payload.amount <= 0:
        return wallet_error(code="VALIDATION_ERROR", message="Amount must be greater than 0", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    existing = await wallet_ledger.find_tx_by_tx_id(db, payload.tenant_id, payload.player_id, payload.transaction_id)
    if existing:
        return _idempotent_wallet_response(existing, payload.transaction_id, payload.player_id)

    amount = wallet_ledger.money_to_decimal(payload.amount, currency)
    allowed, rg_code, rg_msg = await enforce_responsible_gaming(payload.player_id, payload.tenant_id, amount, currency)
    if not allowed:
        return wallet_error(code=rg_code, message=rg_msg, transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))
    if current_balance < amount:
        return wallet_error(code="INSUFFICIENT_BALANCE", message="Insufficient balance", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    after = await wallet_ledger.atomic_debit(db, tenant_id=payload.tenant_id, player_id=payload.player_id, amount=amount, currency=currency)
    if after is None:
        return wallet_error(code="CONFLICT", message="Concurrent debit conflict", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    before = after + amount
    tx_doc, is_idempotent = await wallet_ledger.record_tx(
        db,
        tenant_id=payload.tenant_id,
        player_id=payload.player_id,
        tx_id=payload.transaction_id,
        tx_type="bet",
        amount=amount,
        currency=currency,
        balance_before=before,
        balance_after=after,
        session_id=payload.session_id,
        round_id=payload.round_id,
        description="QTech debit",
        metadata={"source": "qtech", "operation": "debit"},
    )
    if is_idempotent:
        return _idempotent_wallet_response(tx_doc, payload.transaction_id, payload.player_id)
    return wallet_ok(transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(after, currency))


@api_router.post(
    "/wallet/credit",
    dependencies=[Depends(validate_qtech_api_key)],
    response_model=WalletCallbackResponse,
)
async def qtech_wallet_credit(payload: QTechWalletRequest):
    player = await _validate_player_wallet_access(payload)
    currency = resolve_request_currency(payload.currency, "IDR")
    current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)

    if payload.amount is None or payload.amount <= 0:
        return wallet_error(code="VALIDATION_ERROR", message="Amount must be greater than 0", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    existing = await wallet_ledger.find_tx_by_tx_id(db, payload.tenant_id, payload.player_id, payload.transaction_id)
    if existing:
        return _idempotent_wallet_response(existing, payload.transaction_id, payload.player_id)

    amount = wallet_ledger.money_to_decimal(payload.amount, currency)
    after = await wallet_ledger.atomic_credit(db, tenant_id=payload.tenant_id, player_id=payload.player_id, amount=amount, currency=currency)
    if after is None:
        return wallet_error(code="CONFLICT", message="Wallet update conflict", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    before = after - amount
    tx_doc, is_idempotent = await wallet_ledger.record_tx(
        db,
        tenant_id=payload.tenant_id,
        player_id=payload.player_id,
        tx_id=payload.transaction_id,
        tx_type="win",
        amount=amount,
        currency=currency,
        balance_before=before,
        balance_after=after,
        session_id=payload.session_id,
        round_id=payload.round_id,
        description="QTech credit",
        metadata={"source": "qtech", "operation": "credit"},
    )
    if is_idempotent:
        return _idempotent_wallet_response(tx_doc, payload.transaction_id, payload.player_id)
    return wallet_ok(transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(after, currency))


@api_router.post(
    "/wallet/rollback",
    dependencies=[Depends(validate_qtech_api_key)],
    response_model=WalletCallbackResponse,
)
async def qtech_wallet_rollback(payload: QTechWalletRequest):
    player = await _validate_player_wallet_access(payload)
    currency = resolve_request_currency(payload.currency, "IDR")
    current_balance = wallet_ledger.money_to_decimal(player.get("wallet_balance", 0), currency)

    if payload.amount is None or payload.amount <= 0:
        return wallet_error(code="VALIDATION_ERROR", message="Amount must be greater than 0", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    if not payload.reference_transaction_id:
        return wallet_error(code="VALIDATION_ERROR", message="reference_transaction_id is required", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    existing = await wallet_ledger.find_tx_by_tx_id(db, payload.tenant_id, payload.player_id, payload.transaction_id)
    if existing:
        return _idempotent_wallet_response(existing, payload.transaction_id, payload.player_id)

    amount = wallet_ledger.money_to_decimal(payload.amount, currency)
    source_debit = await wallet_ledger.find_tx_by_tx_id(db, payload.tenant_id, payload.player_id, payload.reference_transaction_id)
    tolerance = wallet_ledger.money_to_decimal(0 if currency == "IDR" else 0.01, currency)

    if not source_debit or source_debit.get("type") != "bet":
        return wallet_error(code="INVALID_REFERENCE", message="Reference debit transaction not found", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    source_amount = wallet_ledger.money_to_decimal(source_debit.get("amount", 0), currency)
    if abs(source_amount - amount) > tolerance:
        return wallet_error(code="INVALID_REFERENCE", message="Rollback amount mismatch", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    already_rollback = await db.transactions.find_one(
        {
            "tenant_id": payload.tenant_id,
            "player_id": payload.player_id,
            "type": "rollback",
            "metadata.reference_transaction_id": payload.reference_transaction_id,
        },
        {"_id": 0, "tx_id": 1},
    )
    if already_rollback:
        return wallet_error(code="CONFLICT", message="Referenced debit already rolled back", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    after = await wallet_ledger.atomic_credit(db, tenant_id=payload.tenant_id, player_id=payload.player_id, amount=amount, currency=currency)
    if after is None:
        return wallet_error(code="CONFLICT", message="Wallet update conflict", transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(current_balance, currency))

    before = after - amount
    tx_doc, is_idempotent = await wallet_ledger.record_tx(
        db,
        tenant_id=payload.tenant_id,
        player_id=payload.player_id,
        tx_id=payload.transaction_id,
        tx_type="rollback",
        amount=amount,
        currency=currency,
        balance_before=before,
        balance_after=after,
        session_id=payload.session_id,
        round_id=payload.round_id,
        description="QTech rollback",
        metadata={
            "source": "qtech",
            "operation": "rollback",
            "reference_transaction_id": payload.reference_transaction_id,
            "debit_tx_id": source_debit.get("tx_id"),
        },
    )
    if is_idempotent:
        return _idempotent_wallet_response(tx_doc, payload.transaction_id, payload.player_id)
    return wallet_ok(transaction_id=payload.transaction_id, player_id=payload.player_id, currency=currency, balance=wallet_ledger.decimal_to_amount(after, currency))


@api_router.post("/wallet/withdraw")
async def withdraw(withdraw_req: WithdrawRequest, request: Request):
    """Simulate withdrawal"""
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can withdraw")
    
    if withdraw_req.amount <= 0:
        raise HTTPException(status_code=400, detail="Nominal penarikan tidak valid")

    preferred_currency = await get_player_preferred_currency(user["id"])
    tx_currency = resolve_request_currency(withdraw_req.currency, preferred_currency)
    
    wallet_balance, wallet_currency = await ensure_player_wallet_currency(user["id"], preferred_currency)

    withdraw_amount = money_to_decimal(withdraw_req.amount, tx_currency)
    withdraw_in_wallet = convert_amount(withdraw_amount, tx_currency, wallet_currency)

    current_balance = money_to_decimal(wallet_balance, wallet_currency)

    if withdraw_in_wallet > current_balance:
        raise HTTPException(status_code=400, detail="Saldo tidak mencukupi")

    min_withdraw = money_to_decimal("10", tx_currency)
    if withdraw_amount < min_withdraw:
        raise HTTPException(status_code=400, detail="Minimal penarikan adalah 10")

    new_balance = current_balance - withdraw_in_wallet
    new_balance_amount = decimal_to_amount(new_balance, wallet_currency)
    await db.users.update_one({"id": user["id"]}, {"$set": {"wallet_balance": new_balance_amount}})

    tx_balance_before = convert_amount(current_balance, wallet_currency, tx_currency)
    tx_balance_after = convert_amount(new_balance, wallet_currency, tx_currency)

    from models import Transaction, generate_id
    tx = Transaction(
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        type="withdrawal",
        amount=decimal_to_amount(withdraw_amount, tx_currency),
        currency=tx_currency,
        balance_before=decimal_to_amount(tx_balance_before, tx_currency),
        balance_after=decimal_to_amount(tx_balance_after, tx_currency),
        description="Penarikan ke rekening demo"
    )
    
    tx_doc = tx.model_dump()
    tx_doc['timestamp'] = tx_doc['timestamp'].isoformat()
    await db.transactions.insert_one(tx_doc)
    
    return {
        "success": True,
        "amount": decimal_to_amount(withdraw_amount, tx_currency),
        "balance_before": decimal_to_amount(tx_balance_before, tx_currency),
        "balance_after": decimal_to_amount(tx_balance_after, tx_currency),
        "transaction_id": tx.tx_id,
        "status": "processing",
        "estimated_arrival": "1-3 business days",
        "currency": tx_currency
    }


@api_router.get("/wallet/balance")
async def get_balance(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players have wallets")
    preferred_currency = await get_player_preferred_currency(user["id"])
    balance, _ = await ensure_player_wallet_currency(user["id"], preferred_currency)
    return {"balance": balance, "currency": preferred_currency}


# ============ TRANSACTION / LEDGER ROUTES ============
class PaymentCreateRequest(BaseModel):
    provider: str = "dummy"
    amount: float
    currency: str = "IDR"
    bank_info: Optional[dict] = None


class BankAccountCreateRequest(BaseModel):
    bank_name: str
    account_number: str
    account_name: str
    is_active: bool = True


class BankAccountUpdateRequest(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None


class DepositBankCreateRequest(BaseModel):
    amount: float
    currency: Optional[str] = "IDR"
    bank_account_id: str
    note: Optional[str] = None
    proof_url: Optional[str] = None


class DepositRejectRequest(BaseModel):
    reason: Optional[str] = None


class WithdrawalOrderCreateRequest(BaseModel):
    provider: str = "dummy"
    amount: float
    currency: str = "IDR"
    bank_info: dict


class PaymentWebhookRequest(BaseModel):
    event_id: str
    order_id: str
    player_id: str
    tenant_id: str
    amount: float
    currency: str = "IDR"
    status: str
    raw: dict = Field(default_factory=dict)


@api_router.get("/operator/bank-accounts")
async def list_operator_bank_accounts(request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    rows = await db.tenant_bank_accounts.find({"tenant_id": user["tenant_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@api_router.post("/operator/bank-accounts")
async def create_operator_bank_account(payload: BankAccountCreateRequest, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    account_number = ''.join(ch for ch in str(payload.account_number) if ch.isdigit())
    if not payload.bank_name.strip() or not payload.account_name.strip() or not account_number:
        raise HTTPException(status_code=400, detail="Data rekening tidak valid")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "tenant_id": user["tenant_id"],
        "bank_name": payload.bank_name.strip(),
        "account_number": account_number,
        "account_name": payload.account_name.strip(),
        "is_active": payload.is_active,
        "created_at": now,
        "updated_at": now,
    }
    await db.tenant_bank_accounts.insert_one(doc)
    doc.pop("_id", None)
    await _append_payment_audit_log(
        tenant_id=user["tenant_id"],
        actor_role=user["role"],
        actor_id=user["id"],
        action="create_bank_account",
        entity_type="tenant_bank_account",
        entity_id=doc["id"],
        after=doc,
    )
    return doc


@api_router.patch("/operator/bank-accounts/{bank_account_id}")
async def update_operator_bank_account(bank_account_id: str, payload: BankAccountUpdateRequest, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    current = await db.tenant_bank_accounts.find_one({"id": bank_account_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Bank account not found")

    updates = {}
    if payload.bank_name is not None:
        updates["bank_name"] = payload.bank_name.strip()
    if payload.account_name is not None:
        updates["account_name"] = payload.account_name.strip()
    if payload.account_number is not None:
        updates["account_number"] = ''.join(ch for ch in str(payload.account_number) if ch.isdigit())

    if not updates:
        return current

    if ("bank_name" in updates and not updates["bank_name"]) or ("account_name" in updates and not updates["account_name"]) or ("account_number" in updates and not updates["account_number"]):
        raise HTTPException(status_code=400, detail="Data rekening tidak valid")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.tenant_bank_accounts.update_one({"id": bank_account_id, "tenant_id": user["tenant_id"]}, {"$set": updates})
    latest = await db.tenant_bank_accounts.find_one({"id": bank_account_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    await _append_payment_audit_log(
        tenant_id=user["tenant_id"],
        actor_role=user["role"],
        actor_id=user["id"],
        action="update_bank_account",
        entity_type="tenant_bank_account",
        entity_id=bank_account_id,
        before=current,
        after=latest,
    )
    return latest


@api_router.post("/operator/bank-accounts/{bank_account_id}/toggle")
async def toggle_operator_bank_account(bank_account_id: str, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    current = await db.tenant_bank_accounts.find_one({"id": bank_account_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Bank account not found")

    next_state = not bool(current.get("is_active", True))
    await db.tenant_bank_accounts.update_one(
        {"id": bank_account_id, "tenant_id": user["tenant_id"]},
        {"$set": {"is_active": next_state, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    latest = await db.tenant_bank_accounts.find_one({"id": bank_account_id, "tenant_id": user["tenant_id"]}, {"_id": 0})
    await _append_payment_audit_log(
        tenant_id=user["tenant_id"],
        actor_role=user["role"],
        actor_id=user["id"],
        action="toggle_bank_account",
        entity_type="tenant_bank_account",
        entity_id=bank_account_id,
        before=current,
        after=latest,
    )
    return latest


@api_router.get("/player/bank-accounts")
async def list_player_bank_accounts(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can access bank accounts")
    rows = await db.tenant_bank_accounts.find({"tenant_id": user["tenant_id"], "is_active": True}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


@api_router.get("/player/deposits")
async def list_player_deposits(request: Request, limit: int = 100):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can view deposits")
    rows = await db.deposit_orders.find({"tenant_id": user["tenant_id"], "player_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


@api_router.get("/operator/deposits")
async def list_operator_deposits(request: Request, status: Optional[str] = None, player_id: Optional[str] = None, search: Optional[str] = None, limit: int = 100, offset: int = 0):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    query = {"tenant_id": user["tenant_id"]}
    if status:
        query["status"] = _normalize_status(status)
    if player_id:
        query["player_id"] = player_id
    if search:
        query["player_id"] = {"$regex": search, "$options": "i"}

    rows = await db.deposit_orders.find(query, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    bank_ids = list({r.get("bank_account_id") for r in rows if r.get("bank_account_id")})
    banks = await db.tenant_bank_accounts.find({"id": {"$in": bank_ids}}, {"_id": 0, "id": 1, "bank_name": 1, "account_number": 1, "account_name": 1}).to_list(len(bank_ids) or 1)
    bank_map = {b["id"]: b for b in banks}
    for row in rows:
        row["status"] = _normalize_status(row.get("status"))
        row["bank_account"] = bank_map.get(row.get("bank_account_id"))
    return rows


@api_router.post("/payments/deposit/bank/create")
async def create_bank_deposit_order(
    payload: DepositBankCreateRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create bank deposit order.
    
    SECURITY:
    - Requires Bearer token (cookie auth rejected)
    - Requires Idempotency-Key header
    """
    # CSRF Protection: Require Bearer token, reject cookies
    user = await get_current_user_bearer_only(request, db)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can create deposits")

    # Require idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header required for financial operations"
        )
    
    # Check idempotency
    idem_doc = await db.idempotency_keys.find_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "bank_deposit_create",
    })
    if idem_doc:
        return {"order": idem_doc.get("response"), "idempotent": True}

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    bank_account = await db.tenant_bank_accounts.find_one({"id": payload.bank_account_id, "tenant_id": user["tenant_id"], "is_active": True}, {"_id": 0})
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    currency = resolve_request_currency(payload.currency, await get_player_preferred_currency(user["id"]))
    now = datetime.now(timezone.utc).isoformat()
    order_id = str(uuid.uuid4())
    amount = wallet_ledger.money_to_decimal(payload.amount, currency)
    order = {
        "id": order_id,
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "amount": wallet_ledger.decimal_to_amount(amount, currency),
        "currency": currency,
        "method": "bank_manual",
        "bank_account_id": payload.bank_account_id,
        "status": "created",
        "note": payload.note,
        "proof_url": payload.proof_url,
        "created_at": now,
        "updated_at": now,
        "approved_by": None,
        "rejected_by": None,
        "approved_at": None,
        "rejected_at": None,
        "tx_id": f"dep:{order_id}",
    }
    await db.deposit_orders.insert_one(order)
    order.pop("_id", None)
    
    # Store idempotency key
    await db.idempotency_keys.insert_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "bank_deposit_create",
        "response": order,
        "created_at": now,
    })
    
    await _append_payment_audit_log(
        tenant_id=user["tenant_id"],
        actor_role=user["role"],
        actor_id=user["id"],
        action="create_deposit_order",
        entity_type="deposit_order",
        entity_id=order_id,
        after=order,
    )
    return {"order": order}


@api_router.post('/operator/deposits/{order_id}/approve')
async def approve_deposit(order_id: str, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    order = await db.deposit_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail='Deposit order not found')

    current_status = _normalize_status(order.get('status')) or 'created'
    allowed = _normalize_list_status({'created', 'pending', 'requested', 'review'})
    if current_status == 'success':
        return {'success': True, 'idempotent': True, 'status': 'success'}
    if current_status not in allowed:
        raise HTTPException(status_code=400, detail='Deposit order cannot be approved')

    amount = wallet_ledger.money_to_decimal(order['amount'], order['currency'])
    tx_id = order.get('tx_id') or f"dep:{order_id}"

    existing_tx = await wallet_ledger.find_tx_by_tx_id(db, order['tenant_id'], order['player_id'], tx_id)
    if existing_tx:
        await db.deposit_orders.update_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'$set': {'status': 'success', 'updated_at': datetime.now(timezone.utc).isoformat(), 'approved_by': user['id'], 'approved_at': datetime.now(timezone.utc).isoformat()}})
        return {'success': True, 'idempotent': True, 'status': 'success'}

    before_wallet = await db.users.find_one({'id': order['player_id'], 'tenant_id': order['tenant_id']}, {'_id': 0, 'wallet_balance': 1})
    before = wallet_ledger.money_to_decimal((before_wallet or {}).get('wallet_balance', 0), order['currency'])
    after = await wallet_ledger.atomic_credit(db, tenant_id=order['tenant_id'], player_id=order['player_id'], amount=amount, currency=order['currency'])
    if after is None:
        raise HTTPException(status_code=404, detail='Player wallet not found')

    await wallet_ledger.record_tx(
        db,
        tenant_id=order['tenant_id'],
        player_id=order['player_id'],
        tx_id=tx_id,
        tx_type='deposit',
        amount=amount,
        currency=order['currency'],
        balance_before=before,
        balance_after=after,
        description='Manual bank deposit approved',
        metadata={'order_id': order_id, 'method': 'bank_manual'}
    )

    now = datetime.now(timezone.utc).isoformat()
    await db.deposit_orders.update_one(
        {'id': order_id, 'tenant_id': user['tenant_id']},
        {'$set': {'status': 'success', 'updated_at': now, 'approved_by': user['id'], 'approved_at': now, 'tx_id': tx_id}},
    )
    latest = await db.deposit_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    await _append_payment_audit_log(
        tenant_id=user['tenant_id'],
        actor_role=user['role'],
        actor_id=user['id'],
        action='approve_deposit_order',
        entity_type='deposit_order',
        entity_id=order_id,
        before=order,
        after=latest,
    )
    return {'success': True, 'idempotent': False, 'order': latest}


@api_router.post('/operator/deposits/{order_id}/reject')
async def reject_deposit(order_id: str, payload: DepositRejectRequest, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)

    order = await db.deposit_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail='Deposit order not found')

    current_status = _normalize_status(order.get('status')) or 'created'
    if current_status == 'rejected':
        return {'success': True, 'idempotent': True, 'status': 'rejected'}
    if current_status == 'success':
        raise HTTPException(status_code=400, detail='Deposit already approved')

    now = datetime.now(timezone.utc).isoformat()
    await db.deposit_orders.update_one(
        {'id': order_id, 'tenant_id': user['tenant_id']},
        {'$set': {'status': 'rejected', 'updated_at': now, 'rejected_by': user['id'], 'rejected_at': now, 'reject_reason': payload.reason}},
    )
    latest = await db.deposit_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    await _append_payment_audit_log(
        tenant_id=user['tenant_id'],
        actor_role=user['role'],
        actor_id=user['id'],
        action='reject_deposit_order',
        entity_type='deposit_order',
        entity_id=order_id,
        before=order,
        after=latest,
    )
    return {'success': True, 'idempotent': False, 'order': latest}


@api_router.post("/uploads/proof")
async def upload_proof(request: Request, file: UploadFile = File(...)):
    user = await get_authenticated_user(request)
    if user["role"] not in {"player", "tenant_admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_ext:
        raise HTTPException(status_code=400, detail="File type not allowed")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    upload_root = ROOT_DIR / "uploads" / "proofs"
    upload_root.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{suffix}"
    target = upload_root / filename
    with target.open("wb") as out:
        out.write(data)

    return {"proof_url": f"/uploads/proofs/{filename}"}


@api_router.post("/payments/deposit/create")
async def create_deposit_order(
    payload: PaymentCreateRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create deposit order.
    
    SECURITY:
    - Requires Bearer token (cookie auth rejected)
    - Requires Idempotency-Key header
    """
    # CSRF Protection: Require Bearer token, reject cookies
    user = await get_current_user_bearer_only(request, db)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can create deposits")
    
    # Require idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header required for financial operations"
        )
    
    # Check idempotency - scoped by (tenant_id, player_id, idempotency_key)
    idem_doc = await db.idempotency_keys.find_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "deposit_create",
    })
    if idem_doc:
        return {"order": idem_doc.get("response"), "provider": idem_doc.get("provider_response"), "idempotent": True}

    now = datetime.now(timezone.utc).isoformat()
    order = DepositOrder(
        provider=payload.provider,
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        amount=payload.amount,
        currency=resolve_request_currency(payload.currency, await get_player_preferred_currency(user["id"])),
        status="pending",
    ).model_dump()
    order["created_at"] = now
    order["updated_at"] = now
    order["idempotency_key"] = idempotency_key
    await db.deposit_orders.insert_one(order)
    order.pop("_id", None)  # Remove MongoDB's ObjectId

    adapter_data = await payments_service.adapter(payload.provider).create_deposit({"order_id": order["id"], **order})
    
    # Store idempotency key
    await db.idempotency_keys.insert_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "deposit_create",
        "response": order,
        "provider_response": adapter_data,
        "created_at": now,
    })
    
    return {"order": order, "provider": adapter_data}


@api_router.post("/payments/deposit/webhook/{provider}")
async def deposit_webhook(provider: str, request: Request):
    """Deposit webhook with signature verification.
    
    Required headers:
    - X-Signature: HMAC SHA256 signature
    - X-Timestamp: Unix timestamp
    """
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Verify webhook signature
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    try:
        verify_webhook_signature(provider, raw_body, signature, timestamp)
    except WebhookTimestampExpired as e:
        logger.warning(f"Webhook timestamp expired for provider {provider}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except WebhookSignatureMismatch as e:
        logger.warning(f"Webhook signature mismatch for provider {provider}: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except WebhookSignatureError as e:
        logger.warning(f"Webhook signature error for provider {provider}: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    # Rate limit webhooks by provider + IP
    client_ip = rate_limiter.get_client_ip(request)
    try:
        rate_limiter.check_rate_limit("webhook", client_ip, provider)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    
    # Parse payload
    import json
    try:
        payload_data = json.loads(raw_body)
        payload = PaymentWebhookRequest(**payload_data)
    except (json.JSONDecodeError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    
    # Idempotency check - scoped by (provider, tenant_id, event_id)
    idempotency_key = f"{provider}:{payload.tenant_id}:{payload.event_id}"
    event_data, is_dup = await payments_service.record_event_if_new({
        "event_id": payload.event_id,
        "idempotency_key": idempotency_key,
        "provider": provider,
        "tenant_id": payload.tenant_id,
        "player_id": payload.player_id,
        "type": "deposit",
        "amount": payload.amount,
        "currency": payload.currency,
        "status": payload.status,
        "raw": payload.raw,
    })
    if is_dup:
        return {"success": True, "idempotent": True, "event": event_data}

    order = await db.deposit_orders.find_one({"id": payload.order_id, "tenant_id": payload.tenant_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Deposit order not found")

    if payload.status == "success":
        amount = wallet_ledger.money_to_decimal(payload.amount, payload.currency)
        after = await wallet_ledger.atomic_credit(db, tenant_id=payload.tenant_id, player_id=payload.player_id, amount=amount, currency=payload.currency)
        if after is None:
            raise HTTPException(status_code=404, detail="Player wallet not found or inactive")
        before = after - amount
        await wallet_ledger.record_tx(
            db,
            tenant_id=payload.tenant_id,
            player_id=payload.player_id,
            tx_id=f"deposit:{payload.order_id}:{payload.event_id}",
            tx_type="deposit",
            amount=amount,
            currency=payload.currency,
            balance_before=before,
            balance_after=after,
            description="Payment deposit success",
            metadata={"provider": provider, "order_id": payload.order_id, "event_id": payload.event_id},
        )

    await db.deposit_orders.update_one(
        {"id": payload.order_id, "tenant_id": payload.tenant_id},
        {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "idempotent": False}


@api_router.post("/payments/withdraw/create")
async def create_withdraw_order(
    payload: WithdrawalOrderCreateRequest,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Create withdrawal order.
    
    SECURITY:
    - Requires Bearer token (cookie auth rejected)
    - Rate limited per IP + user
    - Requires Idempotency-Key header
    """
    # CSRF Protection: Require Bearer token, reject cookies
    user = await get_current_user_bearer_only(request, db)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can create withdrawals")
    
    # Rate limiting
    client_ip = rate_limiter.get_client_ip(request)
    try:
        rate_limiter.check_rate_limit("withdraw", client_ip, user["id"])
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    
    # Require idempotency key
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header required for financial operations"
        )
    
    # Check idempotency - scoped by (tenant_id, player_id, idempotency_key)
    idem_doc = await db.idempotency_keys.find_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "withdraw_create",
    })
    if idem_doc:
        return {"order": idem_doc.get("response"), "idempotent": True}

    currency = resolve_request_currency(payload.currency, await get_player_preferred_currency(user["id"]))
    amount = wallet_ledger.money_to_decimal(payload.amount, currency)
    
    # Atomic debit with tenant binding
    after = await wallet_ledger.atomic_debit(db, tenant_id=user["tenant_id"], player_id=user["id"], amount=amount, currency=currency)
    if after is None:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    before = after + amount
    now = datetime.now(timezone.utc).isoformat()
    order = WithdrawalOrder(
        provider=payload.provider,
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        amount=wallet_ledger.decimal_to_amount(amount, currency),
        currency=currency,
        status="requested",
        bank_info=payload.bank_info,
    ).model_dump()
    order["tx_id"] = f"wd:{order['id']}"
    order["created_at"] = now
    order["updated_at"] = now
    await db.withdrawal_orders.insert_one(order)
    order.pop("_id", None)  # Remove MongoDB's ObjectId

    await wallet_ledger.record_tx(
        db,
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        tx_id=f"withdraw_request:{order['id']}",
        tx_type="withdrawal",
        amount=amount,
        currency=currency,
        balance_before=before,
        balance_after=after,
        description="Withdrawal requested",
        metadata={"status": "requested", "order_id": order["id"], "idempotency_key": idempotency_key},
    )
    
    # Store idempotency key
    await db.idempotency_keys.insert_one({
        "tenant_id": user["tenant_id"],
        "player_id": user["id"],
        "key": idempotency_key,
        "operation": "withdraw_create",
        "response": order,
        "created_at": now,
    })
    
    return {"order": order}


@api_router.post("/payments/withdraw/webhook/{provider}")
async def withdraw_webhook(provider: str, request: Request):
    """Withdraw webhook with signature verification.
    
    Required headers:
    - X-Signature: HMAC SHA256 signature
    - X-Timestamp: Unix timestamp
    """
    # Get raw body for signature verification
    raw_body = await request.body()
    
    # Verify webhook signature
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    try:
        verify_webhook_signature(provider, raw_body, signature, timestamp)
    except WebhookTimestampExpired as e:
        logger.warning(f"Webhook timestamp expired for provider {provider}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except WebhookSignatureMismatch as e:
        logger.warning(f"Webhook signature mismatch for provider {provider}: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except WebhookSignatureError as e:
        logger.warning(f"Webhook signature error for provider {provider}: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    # Rate limit webhooks by provider + IP
    client_ip = rate_limiter.get_client_ip(request)
    try:
        rate_limiter.check_rate_limit("webhook", client_ip, provider)
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after)}
        )
    
    # Parse payload
    import json
    try:
        payload_data = json.loads(raw_body)
        payload = PaymentWebhookRequest(**payload_data)
    except (json.JSONDecodeError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    
    # Idempotency check - scoped by (provider, tenant_id, event_id)
    idempotency_key = f"{provider}:{payload.tenant_id}:{payload.event_id}"
    event_data, is_dup = await payments_service.record_event_if_new({
        "event_id": payload.event_id,
        "idempotency_key": idempotency_key,
        "provider": provider,
        "tenant_id": payload.tenant_id,
        "player_id": payload.player_id,
        "type": "withdrawal",
        "amount": payload.amount,
        "currency": payload.currency,
        "status": payload.status,
        "raw": payload.raw,
    })
    if is_dup:
        return {"success": True, "idempotent": True, "event": event_data}

    await db.withdrawal_orders.update_one(
        {"id": payload.order_id, "tenant_id": payload.tenant_id},
        {"$set": {"status": payload.status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "idempotent": False}


@api_router.get('/payments/orders/me')
async def my_payment_orders(request: Request):
    user = await get_authenticated_user(request)
    if user['role'] != 'player':
        raise HTTPException(status_code=403, detail='Only players can view their orders')
    deposits = await db.deposit_orders.find({'player_id': user['id']}, {'_id': 0}).sort('created_at', -1).to_list(200)
    withdrawals = await db.withdrawal_orders.find({'player_id': user['id']}, {'_id': 0}).sort('created_at', -1).to_list(200)
    return {'deposits': deposits, 'withdrawals': withdrawals}


@api_router.post('/operator/withdrawals/{order_id}/approve')
async def approve_withdrawal(order_id: str, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    order = await db.withdrawal_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail='Withdrawal order not found')

    status = _normalize_status(order.get('status')) or 'requested'
    allowed = _normalize_list_status({'requested', 'review', 'processing', 'pending', 'created'})
    if status == 'success':
        return {'success': True, 'idempotent': True, 'status': 'success'}
    if status in {'rejected', 'cancelled', 'failed'}:
        raise HTTPException(status_code=400, detail='Withdrawal order already final')
    if status not in allowed:
        raise HTTPException(status_code=400, detail='Withdrawal order cannot be approved')

    now = datetime.now(timezone.utc).isoformat()
    tx_id = order.get('tx_id') or f"wd:{order_id}"
    await db.withdrawal_orders.update_one(
        {'id': order_id, 'tenant_id': user['tenant_id']},
        {'$set': {'status': 'success', 'updated_at': now, 'approved_by': user['id'], 'approved_at': now, 'tx_id': tx_id}},
    )
    latest = await db.withdrawal_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    await _append_payment_audit_log(
        tenant_id=user['tenant_id'],
        actor_role=user['role'],
        actor_id=user['id'],
        action='approve_withdrawal_order',
        entity_type='withdrawal_order',
        entity_id=order_id,
        before=order,
        after=latest,
    )
    return {'success': True, 'idempotent': False, 'order': latest}


@api_router.post('/operator/withdrawals/{order_id}/reject')
async def reject_withdrawal(order_id: str, request: Request):
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    order = await db.withdrawal_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=404, detail='Withdrawal order not found')

    status = _normalize_status(order.get('status')) or 'requested'
    if status == 'rejected':
        return {'success': True, 'idempotent': True, 'status': 'rejected'}
    if status == 'success':
        raise HTTPException(status_code=400, detail='Withdrawal already approved')

    amount = wallet_ledger.money_to_decimal(order['amount'], order['currency'])
    refund_tx_id = f"withdraw_reject_refund:{order_id}"
    existing_refund = await wallet_ledger.find_tx_by_tx_id(db, order['tenant_id'], order['player_id'], refund_tx_id)
    if not existing_refund:
        before_wallet = await db.users.find_one({'id': order['player_id'], 'tenant_id': order['tenant_id']}, {'_id': 0, 'wallet_balance': 1})
        before = wallet_ledger.money_to_decimal((before_wallet or {}).get('wallet_balance', 0), order['currency'])
        after = await wallet_ledger.atomic_credit(db, tenant_id=order['tenant_id'], player_id=order['player_id'], amount=amount, currency=order['currency'])
        if after is None:
            raise HTTPException(status_code=404, detail='Player wallet not found')
        await wallet_ledger.record_tx(
            db,
            tenant_id=order['tenant_id'],
            player_id=order['player_id'],
            tx_id=refund_tx_id,
            tx_type='adjustment',
            amount=amount,
            currency=order['currency'],
            balance_before=before,
            balance_after=after,
            description='Withdrawal rejected refund',
            metadata={'order_id': order_id, 'status': 'rejected'},
        )

    now = datetime.now(timezone.utc).isoformat()
    await db.withdrawal_orders.update_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'$set': {'status': 'rejected', 'updated_at': now, 'rejected_by': user['id'], 'rejected_at': now}})
    latest = await db.withdrawal_orders.find_one({'id': order_id, 'tenant_id': user['tenant_id']}, {'_id': 0})
    await _append_payment_audit_log(
        tenant_id=user['tenant_id'],
        actor_role=user['role'],
        actor_id=user['id'],
        action='reject_withdrawal_order',
        entity_type='withdrawal_order',
        entity_id=order_id,
        before=order,
        after=latest,
    )
    return {'success': True, 'idempotent': existing_refund is not None, 'order': latest}


@api_router.get("/transactions", response_model=List[Transaction])
async def list_transactions(
    request: Request,
    tenant_id: Optional[str] = None,
    player_id: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    user = await get_authenticated_user(request)
    query = {}
    
    if user["role"] == "super_admin":
        if tenant_id:
            query["tenant_id"] = tenant_id
    elif user["role"] == "tenant_admin":
        query["tenant_id"] = user["tenant_id"]
    elif user["role"] == "player":
        # Support both user_id and player_id fields
        query["$or"] = [{"player_id": user["id"]}, {"user_id": user["id"]}]
    
    if player_id and user["role"] != "player":
        query["$or"] = [{"player_id": player_id}, {"user_id": player_id}]
    
    if type:
        # Support comma-separated types
        if ',' in type:
            query["type"] = {"$in": type.split(',')}
        else:
            query["type"] = type
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    for tx in transactions:
        # Handle both timestamp and created_at fields
        ts = tx.get('timestamp') or tx.get('created_at')
        if ts:
            tx['timestamp'] = parse_datetime(ts)
    return transactions


@api_router.get("/transactions/count")
async def count_transactions(
    request: Request,
    tenant_id: Optional[str] = None,
    player_id: Optional[str] = None,
    type: Optional[str] = None
):
    user = await get_authenticated_user(request)
    query = {}
    
    if user["role"] == "super_admin":
        if tenant_id:
            query["tenant_id"] = tenant_id
    elif user["role"] == "tenant_admin":
        query["tenant_id"] = user["tenant_id"]
    elif user["role"] == "player":
        query["player_id"] = user["id"]
    
    if player_id and user["role"] != "player":
        query["player_id"] = player_id
    if type:
        query["type"] = type
    
    count = await db.transactions.count_documents(query)
    return {"count": count}


# ============ GAME SESSION / LAUNCH ROUTES ============
@api_router.post("/games/{game_id}/launch", response_model=ProviderSessionResponse)
async def launch_game(game_id: str, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can launch games")

    settings = await get_player_settings_doc(user["id"])
    self_exclusion_until = settings.get("self_exclusion_until")
    if self_exclusion_until and parse_datetime(self_exclusion_until) > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="SELF_EXCLUDED: Account currently in self-exclusion period")

    # FINANCE ENFORCEMENT (UX): Check if tenant can operate
    can_operate, frozen_error = await finance_service.check_or_autofreeze(user["tenant_id"])
    if not can_operate:
        return JSONResponse(
            status_code=403,
            content=frozen_error.model_dump()
        )

    game = await db.games.find_one({"id": game_id}, {"_id": 0})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if user["tenant_id"] not in game.get("tenant_ids", []):
        raise HTTPException(status_code=403, detail="Game not available")
    
    game = canonicalize_game_doc(game)
    tenant = await db.tenants.find_one({"id": user["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=500, detail="Tenant not found")

    player = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    seamless_config = tenant.get("provider_config", {}).get("seamless", {})
    is_seamless_game = game.get("aggregator") == "seamless" or str(game.get("source", "")).startswith("seamless")

    if is_seamless_game:
        provider = create_seamless_adapter_for_tenant(tenant.get("provider_config", {}))
        if not provider:
            raise HTTPException(status_code=500, detail="Seamless provider is not enabled for this tenant")

        launch_preview = provider.launch_contract_preview(
            user_code=user["id"],
            user_balance=player.get("wallet_balance", 0),
            provider_code=game.get("launch_provider_code") or game.get("provider_code", ""),
            game_code=game.get("launch_game_code") or game.get("game_code") or game.get("game_launch_id"),
            category=game.get("category", "slots"),
            language=seamless_config.get("language", "en"),
        )
        if launch_preview["missing_config"]:
            missing = ", ".join(launch_preview["missing_config"])
            logger.error("Seamless launch blocked for tenant %s game %s: missing %s", user["tenant_id"], game_id, missing)
            raise HTTPException(status_code=503, detail=f"Seamless launch unavailable: missing {missing}")

        try:
            session_data = await provider.create_session(
                player_id=user["id"],
                game_id=game.get("launch_game_code") or game.get("game_code") or game.get("game_launch_id"),
                tenant_id=user["tenant_id"],
                currency=seamless_config.get("default_currency", await get_player_preferred_currency(user["id"])),
                language=seamless_config.get("language", "en"),
                user_balance=player.get("wallet_balance", 0),
                provider_code=game.get("launch_provider_code") or game.get("provider_code", ""),
                category=game.get("category", "slots"),
            )
        except Exception as exc:
            logger.exception("Seamless launch failed for tenant=%s player=%s game=%s provider=%s", user["tenant_id"], user["id"], game_id, game.get("provider_code"))
            raise HTTPException(status_code=502, detail=f"Seamless launch failed: {exc}")
    else:
        provider = None
        for alias in provider_aliases(game.get("provider_slug"), game.get("provider_id")):
            provider = provider_registry.get(alias)
            if provider:
                break
        if not provider:
            raise HTTPException(status_code=500, detail="Provider not available")

        preferred_currency = await get_player_preferred_currency(user["id"])
        session_data = await provider.create_session(
            player_id=user["id"],
            game_id=game_id,
            tenant_id=user["tenant_id"],
            currency=preferred_currency,
            language="id"
        )
    
    game_session = GameSession(
        id=session_data["session_id"],
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        game_id=game_id,
        provider_id=game.get("provider_id", "vd7" if game.get("aggregator") == "VD7" else "mock"),
        launch_url=session_data["launch_url"],
        balance_at_start=player.get("wallet_balance", 0)
    )
    
    session_doc = game_session.model_dump()
    session_doc['created_at'] = session_doc['created_at'].isoformat()
    if session_doc.get('closed_at'):
        session_doc['closed_at'] = session_doc['closed_at'].isoformat()
    await db.game_sessions.insert_one(session_doc)
    
    # Update play count
    await db.games.update_one({"id": game_id}, {"$inc": {"play_count": 1}})
    
    # Update player's recent games
    await db.player_stats.update_one(
        {"player_id": user["id"]},
        {
            "$push": {
                "recent_games": {
                    "$each": [{"game_id": game_id, "game_name": game["name"], "last_played": datetime.now(timezone.utc).isoformat()}],
                    "$position": 0,
                    "$slice": 10
                }
            }
        },
        upsert=True
    )
    
    return ProviderSessionResponse(
        session_id=session_data["session_id"],
        launch_url=session_data["launch_url"],
        provider_id=game.get("provider_id", "vd7" if game.get("aggregator") == "VD7" else "mock"),
        expires_at=session_data.get("expires_at")
    )


@api_router.post("/games/spin")
async def game_spin(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "player":
        raise HTTPException(status_code=403, detail="Only players can play")
    
    body = await request.json()
    session_id = body.get("session_id")
    bet_amount = body.get("bet_amount", 1.0)
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    player = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    current_balance = player.get("wallet_balance", 0)
    
    if bet_amount > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    if bet_amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid bet amount")
    
    session = await db.game_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = await mock_provider.simulate_spin(
        session_id=session_id,
        bet_amount=bet_amount,
        current_balance=current_balance
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Spin failed"))
    
    new_balance = result["balance_after"]
    await db.users.update_one({"id": user["id"]}, {"$set": {"wallet_balance": new_balance}})
    
    # Update player stats
    await db.player_stats.update_one(
        {"player_id": user["id"]},
        {
            "$inc": {
                "total_bets": bet_amount,
                "total_wins": result["win_amount"],
                "games_played": 1
            }
        },
        upsert=True
    )
    
    from models import Transaction
    
    bet_tx = Transaction(
        tenant_id=user["tenant_id"],
        player_id=user["id"],
        game_id=session.get("game_id"),
        provider_id="mock",
        session_id=session_id,
        round_id=result["round_id"],
        type="bet",
        amount=bet_amount,
        balance_before=current_balance,
        balance_after=current_balance - bet_amount
    )
    bet_doc = bet_tx.model_dump()
    bet_doc['timestamp'] = bet_doc['timestamp'].isoformat()
    await db.transactions.insert_one(bet_doc)
    
    if result["win_amount"] > 0:
        win_tx = Transaction(
            tenant_id=user["tenant_id"],
            player_id=user["id"],
            game_id=session.get("game_id"),
            provider_id="mock",
            session_id=session_id,
            round_id=result["round_id"],
            type="win",
            amount=result["win_amount"],
            balance_before=current_balance - bet_amount,
            balance_after=new_balance
        )
        win_doc = win_tx.model_dump()
        win_doc['timestamp'] = win_doc['timestamp'].isoformat()
        await db.transactions.insert_one(win_doc)
    
    await db.game_sessions.update_one(
        {"id": session_id},
        {"$inc": {"total_bet": bet_amount, "total_win": result["win_amount"], "rounds_played": 1}}
    )
    
    return result


# ============ REPORTING / STATS ROUTES ============
@api_router.get("/stats/global", response_model=GlobalStats)
async def get_global_stats(request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    total_tenants = await db.tenants.count_documents({})
    total_players = await db.users.count_documents({"role": "player"})
    total_games = await db.games.count_documents({})
    total_transactions = await db.transactions.count_documents({})
    
    pipeline = [
        {"$group": {
            "_id": "$type",
            "total": {"$sum": "$amount"}
        }}
    ]
    stats_result = await db.transactions.aggregate(pipeline).to_list(10)
    stats_by_type = {item["_id"]: item["total"] for item in stats_result}
    
    total_deposits = stats_by_type.get("deposit", 0)
    total_bets = stats_by_type.get("bet", 0)
    total_wins = stats_by_type.get("win", 0)
    total_volume = total_deposits + total_bets + total_wins
    
    return GlobalStats(
        total_tenants=total_tenants,
        total_players=total_players,
        total_games=total_games,
        total_transactions=total_transactions,
        total_volume=round(total_volume, 2),
        total_deposits=round(total_deposits, 2),
        total_bets=round(total_bets, 2),
        total_wins=round(total_wins, 2)
    )


@api_router.get("/stats/tenant/{tenant_id}", response_model=TenantStats)
async def get_tenant_stats(tenant_id: str, request: Request):
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin" and user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    total_players = await db.users.count_documents({"tenant_id": tenant_id, "role": "player"})
    active_players = await db.users.count_documents({"tenant_id": tenant_id, "role": "player", "is_active": True})
    total_games = await db.games.count_documents({"tenant_ids": tenant_id})
    total_transactions = await db.transactions.count_documents({"tenant_id": tenant_id})
    
    pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}}
    ]
    stats_result = await db.transactions.aggregate(pipeline).to_list(10)
    stats_by_type = {item["_id"]: item["total"] for item in stats_result}
    
    total_deposits = stats_by_type.get("deposit", 0)
    total_withdrawals = stats_by_type.get("withdrawal", 0)
    total_bets = stats_by_type.get("bet", 0)
    total_wins = stats_by_type.get("win", 0)
    ggr = total_bets - total_wins
    
    return TenantStats(
        total_players=total_players,
        active_players=active_players,
        total_games=total_games,
        total_transactions=total_transactions,
        total_deposits=round(total_deposits, 2),
        total_withdrawals=round(total_withdrawals, 2),
        total_bets=round(total_bets, 2),
        total_wins=round(total_wins, 2),
        gross_gaming_revenue=round(ggr, 2)
    )


@api_router.get("/stats/tenant/{tenant_id}/top-games")
async def get_top_games(tenant_id: str, request: Request):
    """Get top 5 games by bets and wins for operator snapshot"""
    user = await get_authenticated_user(request)
    if user["role"] != "super_admin" and user["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Top 5 games by bets
    bets_pipeline = [
        {"$match": {"tenant_id": tenant_id, "type": "bet", "game_id": {"$ne": None}}},
        {"$group": {"_id": "$game_id", "total_bets": {"$sum": "$amount"}}},
        {"$sort": {"total_bets": -1}},
        {"$limit": 5}
    ]
    top_by_bets = await db.transactions.aggregate(bets_pipeline).to_list(5)
    
    # Top 5 games by wins
    wins_pipeline = [
        {"$match": {"tenant_id": tenant_id, "type": "win", "game_id": {"$ne": None}}},
        {"$group": {"_id": "$game_id", "total_wins": {"$sum": "$amount"}}},
        {"$sort": {"total_wins": -1}},
        {"$limit": 5}
    ]
    top_by_wins = await db.transactions.aggregate(wins_pipeline).to_list(5)
    
    # Get game details
    game_ids = list(set([g["_id"] for g in top_by_bets] + [g["_id"] for g in top_by_wins]))
    games = await db.games.find({"id": {"$in": game_ids}}, {"_id": 0, "id": 1, "name": 1, "thumbnail_url": 1}).to_list(None)
    games_map = {g["id"]: g for g in games}
    
    # Format response
    top_bets = []
    for g in top_by_bets:
        game_info = games_map.get(g["_id"], {})
        top_bets.append({
            "game_id": g["_id"],
            "name": game_info.get("name", "Unknown"),
            "thumbnail_url": game_info.get("thumbnail_url"),
            "total_bets": round(g["total_bets"], 2)
        })
    
    top_wins = []
    for g in top_by_wins:
        game_info = games_map.get(g["_id"], {})
        top_wins.append({
            "game_id": g["_id"],
            "name": game_info.get("name", "Unknown"),
            "thumbnail_url": game_info.get("thumbnail_url"),
            "total_wins": round(g["total_wins"], 2)
        })
    
    return {
        "top_by_bets": top_bets,
        "top_by_wins": top_wins
    }


# ============ PROVIDER REGISTRY ROUTES ============
# Note: Main provider endpoint is defined earlier in the file (lines 364-394)
# This would be for provider adapters registry if needed separately


# ============ HEALTH CHECK ============
@api_router.get("/")
async def root():
    return {"message": "Gaming Platform Engine API", "version": "1.0.0"}


@api_router.get("/health")
async def health_check():
    return {"ok": True}


@api_router.post("/test/bootstrap")
async def test_bootstrap():
    if os.environ.get("USE_MOCK_DB", "0") != "1":
        raise HTTPException(status_code=403, detail="Test bootstrap hanya untuk mode test")
    await ensure_test_seed_data()
    return {"ok": True}


# ============ SEAMLESS CALLBACKS ============

async def _resolve_seamless_tenant(agent_code: str) -> tuple[dict, dict]:
    try:
        tenant, seamless_config = await resolve_tenant_from_seamless_agent_code(db, agent_code)
    except LookupError as exc:
        logger.warning("Seamless callback tenant resolution failed: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not seamless_config.get("agent_secret"):
        raise HTTPException(status_code=500, detail="Seamless callback configuration incomplete")
    return tenant, seamless_config


@api_router.post("/gold_api/user_balance")
async def seamless_user_balance(request: Request):
    try:
        payload = await request.json()
        req = SeamlessUserBalanceRequest(**payload)
    except Exception as exc:
        logger.error("Seamless user_balance validation error: %s", exc)
        return JSONResponse(status_code=400, content={"status": 0, "user_balance": 0, "msg": str(exc)})

    try:
        tenant, seamless_config = await _resolve_seamless_tenant(req.agent_code)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"status": 0, "user_balance": 0, "msg": str(exc.detail)})

    handler = SeamlessCallbackHandler(
        db,
        tenant_id=tenant["id"],
        agent_code=seamless_config["agent_code"],
        agent_secret=seamless_config["agent_secret"],
        currency=seamless_config.get("default_currency", "PHP"),
    )
    if not handler.authenticate(req.agent_code, req.agent_secret):
        return JSONResponse(status_code=401, content={"status": 0, "user_balance": 0, "msg": "INVALID_AGENT_SECRET"})
    result = await handler.handle_user_balance(req)
    return JSONResponse(content=result)


@api_router.post("/gold_api/game_callback")
async def seamless_game_callback(request: Request):
    try:
        payload = await request.json()
        req = SeamlessGameCallbackRequest(**payload)
    except Exception as exc:
        logger.error("Seamless game_callback validation error: %s", exc)
        return JSONResponse(status_code=400, content={"status": 0, "user_balance": 0, "msg": str(exc)})

    try:
        tenant, seamless_config = await _resolve_seamless_tenant(req.agent_code)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"status": 0, "user_balance": 0, "msg": str(exc.detail)})

    handler = SeamlessCallbackHandler(
        db,
        tenant_id=tenant["id"],
        agent_code=seamless_config["agent_code"],
        agent_secret=seamless_config["agent_secret"],
        currency=seamless_config.get("default_currency", "PHP"),
    )
    if not handler.authenticate(req.agent_code, req.agent_secret):
        return JSONResponse(status_code=401, content={"status": 0, "user_balance": 0, "msg": "INVALID_AGENT_SECRET"})

    if req.slot.txn_type.lower() in {"debit", "debit_credit"}:
        can_operate, frozen_error = await finance_service.check_or_autofreeze(tenant["id"])
        if not can_operate:
            return JSONResponse(content={"status": 0, "user_balance": 0, "msg": frozen_error.message if frozen_error else "TENANT_FROZEN"})

    result = await handler.handle_game_callback(req)
    return JSONResponse(content=result)


@api_router.post("/gold_api/money_callback")
async def seamless_money_callback(request: Request):
    try:
        payload = await request.json()
        req = SeamlessMoneyCallbackRequest(**payload)
    except Exception as exc:
        logger.error("Seamless money_callback validation error: %s", exc)
        return JSONResponse(status_code=400, content={"status": 0, "msg": str(exc)})

    try:
        tenant, seamless_config = await _resolve_seamless_tenant(req.agent_code)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"status": 0, "msg": str(exc.detail)})

    handler = SeamlessCallbackHandler(
        db,
        tenant_id=tenant["id"],
        agent_code=seamless_config["agent_code"],
        agent_secret=seamless_config["agent_secret"],
        currency=seamless_config.get("default_currency", "PHP"),
    )
    if not handler.authenticate(req.agent_code, req.agent_secret):
        return JSONResponse(status_code=401, content={"status": 0, "msg": "INVALID_AGENT_SECRET"})

    if (req.type or "").lower() in {"debit", "withdraw", "withdrawal", "debit_credit", "adjustment"}:
        can_operate, frozen_error = await finance_service.check_or_autofreeze(tenant["id"])
        if not can_operate:
            return JSONResponse(content={"status": 0, "msg": frozen_error.message if frozen_error else "TENANT_FROZEN"})

    result = await handler.handle_money_callback(req)
    return JSONResponse(content=result)


@api_router.get("/assets/providers/{provider_code}.svg")
async def provider_logo_asset(provider_code: str):
    provider = await db.providers.find_one({"code": normalize_provider_code(provider_code)}, {"_id": 0, "name": 1})
    svg = render_provider_logo_svg(provider_code, provider.get("name") if provider else provider_code)
    return Response(content=svg, media_type="image/svg+xml")


@api_router.get("/assets/games/{provider_code}/{game_code}.svg")
async def game_thumbnail_asset(provider_code: str, game_code: str):
    normalized_provider_code = normalize_provider_code(provider_code)
    game = await db.games.find_one(
        {
            "provider_code": normalized_provider_code,
            "$or": [
                {"game_code": game_code},
                {"game_launch_id": game_code},
                {"external_game_id": game_code},
            ],
        },
        {"_id": 0, "name": 1, "category": 1},
    )
    svg = render_game_thumbnail_svg(
        normalized_provider_code,
        game_code,
        game.get("name") if game else game_code,
        game.get("category") if game else "slots",
    )
    return Response(content=svg, media_type="image/svg+xml")


# CORS configuration - MUST be added BEFORE routes for proper preflight handling
# When credentials are used, we cannot use "*" - must specify exact origins
ALLOWED_ORIGINS = [
    "https://looxgame.com",
    "https://www.looxgame.com",
    "http://localhost:3000",
]

# Add FRONTEND_URL if set and not already in list
if FRONTEND_URL and FRONTEND_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

# Add any additional origins from env (excluding "*" since credentials are used)
cors_origins_env = os.environ.get('CORS_ORIGINS', '')
if cors_origins_env and cors_origins_env != '*':
    for origin in cors_origins_env.split(','):
        origin = origin.strip()
        if origin and origin != '*' and origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    expose_headers=["Content-Length", "Content-Type"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Include the router AFTER middleware
app.include_router(api_router)

# ============================================================
# Seamless callback aliases (root-level for provider delivery)
# Contract paths: /gold_api/user_balance, /gold_api/game_callback, /gold_api/money_callback
# ============================================================

@app.post("/gold_api/user_balance")
async def seamless_user_balance_root(request: Request):
    return await seamless_user_balance(request)


@app.post("/gold_api/game_callback")
async def seamless_game_callback_root(request: Request):
    return await seamless_game_callback(request)


@app.post("/gold_api/money_callback")
async def seamless_money_callback_root(request: Request):
    return await seamless_money_callback(request)


# Compatibility health routes at app root (some platforms default to `/health`)
@app.get("/")
async def app_root():
    return {"message": "Gaming Platform Engine API", "version": "1.0.0"}


@app.get("/health")
async def app_health_check():
    return {"ok": True}


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Gaming Platform Engine...")
    try:
        tenant_count = await db.tenants.count_documents({})
        seamless_game_count = await db.games.count_documents({"aggregator": "seamless", "is_active": True})
        if tenant_count == 0 and os.environ.get("USE_MOCK_DB", "0") == "1":
            logger.info("No tenants found in mock mode, creating mock seed data...")
            await ensure_test_seed_data()
            logger.info("Mock seed complete")
        elif tenant_count == 0 or seamless_game_count < 3000:
            logger.info("Running seamless bootstrap (tenant_count=%s seamless_game_count=%s)", tenant_count, seamless_game_count)
            await bootstrap_default_platform_data(db)
            logger.info("Seamless bootstrap complete")
        else:
            logger.info("Database already has %s tenants and %s seamless games, skipping bootstrap", tenant_count, seamless_game_count)

        if os.environ.get("SYNC_ASSETS_ON_BOOT", "0") == "1":
            logger.info("AUTO SYNC SKIP | legacy asset sync disabled for seamless runtime")
        else:
            logger.info("AUTO SYNC SKIP | SYNC_ASSETS_ON_BOOT is not enabled")
    except Exception as e:
        logger.error(f"Startup error: {e}")

    try:
        # Data integrity indexes for wallet and ledger safety
        # tx_id uniqueness should be tenant-scoped because providers can reuse
        # transaction IDs across different tenants.
        tx_indexes = await db.transactions.index_information()
        legacy_tx_index = tx_indexes.get("uniq_tx_id")
        if legacy_tx_index and legacy_tx_index.get("key") == [("tx_id", 1)]:
            await db.transactions.drop_index("uniq_tx_id")

        try:
            await db.transactions.create_index(
                [("tenant_id", 1), ("tx_id", 1)],
                unique=True,
                name="uniq_tenant_tx_id",
            )
        except DuplicateKeyError as dup_err:
            logger.error(
                "Unable to create unique tenant transaction index; continuing startup: %s",
                dup_err,
            )
        await db.transactions.create_index([("timestamp", -1)], name="tx_timestamp_desc")
        await db.users.create_index([("id", 1)], unique=True, name="uniq_user_id")
        await db.users.create_index([("email", 1)], unique=True, name="uniq_user_email")
        await db.tenants.create_index([("slug", 1)], unique=True, name="uniq_tenant_slug")
        await db.tenants.create_index([("id", 1)], unique=True, name="uniq_tenant_id")
        await db.audit_logs.create_index([("created_at", -1)], name="audit_logs_created_desc")
        await db.games.create_index([("id", 1)], unique=True, name="uniq_game_id")
        await db.providers.create_index([("id", 1)], unique=True, name="uniq_provider_id")
        await db.wallets.create_index([("player_id", 1)], unique=True, name="uniq_wallet_player")
        await db.api_keys.create_index([("key_hash", 1)], unique=True, name="uniq_api_key_hash")
        await db.api_keys.create_index([("tenant_id", 1), ("is_active", 1)], name="idx_api_key_tenant_active")
        await db.callback_events.create_index([("tenant_id", 1), ("event_key", 1)], unique=True, name="uniq_callback_event")
        await db.catalog_import_runs.create_index([("created_at", -1)], name="idx_catalog_import_runs_created")
        await db.games.create_index([("tenant_ids", 1), ("provider_code", 1)], name="idx_games_tenant_provider_code")
        await db.games.create_index([("tenant_ids", 1), ("category", 1)], name="idx_games_tenant_category")
        await db.providers.create_index([("code", 1)], unique=True, name="uniq_provider_code")
        await db.tenant_bank_accounts.create_index([("id", 1)], unique=True, name="uniq_tenant_bank_account_id")
        await db.tenant_bank_accounts.create_index([("tenant_id", 1), ("is_active", 1)], name="idx_tenant_bank_accounts_active")
        await db.deposit_orders.create_index([("id", 1)], unique=True, name="uniq_deposit_order_id")
        await db.deposit_orders.create_index([("tenant_id", 1), ("status", 1), ("created_at", -1)], name="idx_deposit_orders_tenant_status_created")
        await db.withdrawal_orders.create_index([("id", 1)], unique=True, name="uniq_withdrawal_order_id")
        await db.withdrawal_orders.create_index([("tenant_id", 1), ("status", 1), ("created_at", -1)], name="idx_withdrawal_orders_tenant_status_created")
        
        # Finance module indexes for tenant buffer/escrow
        await finance_service.ensure_indexes()
        
        logger.info("Indexes ensured at startup; run backend/scripts/create_indexes.py for full index sync")
    except Exception as index_err:
        logger.error("Skipping index setup because database is unavailable: %s", index_err)

    try:
        await send_integration_notification(
            "LooxGame startup integration notice",
            "Platform startup completed and integrity indexes are ensured.",
        )
    except Exception as notify_err:
        logger.warning("Startup notification failed: %s", notify_err)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


@api_router.get("/proxy/image/{game_id}")
async def proxy_game_image(game_id: str, request: Request):
    """Proxy game thumbnail images through our server.
    
    This handles signed S3 URLs from VD7 that expire.
    Caches images in memory for 5 minutes.
    """
    import httpx
    from fastapi.responses import Response
    
    # Simple in-memory cache
    cache_key = f"game_image_{game_id}"
    
    # Check cache (stored in app state)
    if hasattr(app.state, 'image_cache') and cache_key in app.state.image_cache:
        cached = app.state.image_cache[cache_key]
        if cached['expires'] > time.time():
            return Response(content=cached['data'], media_type=cached['content_type'])
    
    # Get game from database
    game = await db.games.find_one({"id": game_id}, {"thumbnail_url": 1, "name": 1})
    if not game or not game.get("thumbnail_url"):
        raise HTTPException(status_code=404, detail="Image not found")
    
    thumbnail_url = game["thumbnail_url"]
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(thumbnail_url, follow_redirects=True)
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "image/png")
                image_data = response.content
                
                # Cache for 5 minutes
                if not hasattr(app.state, 'image_cache'):
                    app.state.image_cache = {}
                
                app.state.image_cache[cache_key] = {
                    'data': image_data,
                    'content_type': content_type,
                    'expires': time.time() + 300  # 5 minutes
                }
                
                return Response(content=image_data, media_type=content_type)
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch image")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image fetch timeout")
    except Exception as e:
        logger.error(f"Image proxy error: {e}")
        raise HTTPException(status_code=500, detail="Failed to proxy image")


@api_router.get("/proxy/refresh-icons")
async def refresh_game_icons(request: Request, limit: int = 100):
    """Refresh icon URLs for games by re-fetching from VD7 API.
    
    This is needed because VD7 returns signed S3 URLs that expire.
    Call this endpoint periodically (e.g., every 5 minutes) to keep icons fresh.
    """
    user = await get_authenticated_user(request)
    _ensure_operator(user)
    
    # Trigger background icon refresh (non-blocking)
    # For now, just return info about current state
    games_with_icons = await db.games.count_documents({"thumbnail_url": {"$nin": [None, ""]}})
    total_games = await db.games.count_documents({})
    
    return {
        "message": "Use POST /operator/vd7/sync-icons to refresh icon URLs",
        "games_with_icons": games_with_icons,
        "total_games": total_games,
        "note": "VD7 returns signed S3 URLs that expire in 10 minutes. Icons need periodic refresh."
    }
