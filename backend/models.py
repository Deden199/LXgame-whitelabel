from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime, timezone
import uuid


ALLOWED_CURRENCIES = ["IDR", "USD", "USDT", "PHP", "TRY"]


def generate_id():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


# ============ TENANT / OPERATOR ============
class TenantBranding(BaseModel):
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    hero_url: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    # Section toggles for player home
    show_hero: bool = True
    show_categories: bool = True
    show_featured: bool = True


class Tenant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    name: str
    slug: str
    theme_preset: str = "royal_gold"
    branding: TenantBranding = Field(default_factory=TenantBranding)
    is_active: bool = True
    provider_config: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TenantCreate(BaseModel):
    name: str
    slug: str
    theme_preset: str = "royal_gold"


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    theme_preset: Optional[str] = None
    branding: Optional[TenantBranding] = None
    is_active: Optional[bool] = None
    provider_config: Optional[dict] = None


# ============ TENANT SETTINGS (OPERATOR FACILITIES) ============
class TenantDomainSettings(BaseModel):
    primary_domain: Optional[str] = None
    allowed_domains: List[str] = Field(default_factory=list)
    enforce_domain: bool = False


class TenantSEOSettings(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image_url: Optional[str] = None
    favicon_url: Optional[str] = None
    robots_index: bool = True
    canonical_base_url: Optional[str] = None


class TenantCustomHeaderSettings(BaseModel):
    custom_head_html: Optional[str] = None
    custom_body_html: Optional[str] = None
    enable_custom_html: bool = False


class TenantSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    domain: TenantDomainSettings = Field(default_factory=TenantDomainSettings)
    seo: TenantSEOSettings = Field(default_factory=TenantSEOSettings)
    custom_header: TenantCustomHeaderSettings = Field(default_factory=TenantCustomHeaderSettings)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TenantSettingsUpdate(BaseModel):
    domain: Optional[TenantDomainSettings] = None
    seo: Optional[TenantSEOSettings] = None
    custom_header: Optional[TenantCustomHeaderSettings] = None


# ============ USER / PLAYER ============
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    email: str
    password_hash: str
    role: Literal["super_admin", "tenant_admin", "player"] = "player"
    display_name: str
    wallet_balance: float = 0.0
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    last_login: Optional[datetime] = None


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str
    role: Literal["super_admin", "tenant_admin", "player"] = "player"
    tenant_id: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str
    tenant_slug: Optional[str] = None


class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    tenant_id: str
    email: str
    role: str
    display_name: str
    wallet_balance: float
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_bets: Optional[float] = None
    total_wins: Optional[float] = None
    games_played_count: Optional[int] = None
    preferred_currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"


# ============ GAME ============
class Game(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    provider_id: str = "mock"
    external_game_id: Optional[str] = None
    name: str
    category: str
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    rtp: float = 96.0
    # Volatility accepts any string value (Low, Medium, High, Very High, etc.)
    volatility: str = "medium"
    min_bet: float = 0.10
    max_bet: float = 1000.0
    is_active: bool = True
    is_enabled: bool = True
    tenant_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    play_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    # Provider-related fields added for asset mapping
    provider_name: Optional[str] = None
    provider_slug: Optional[str] = None
    provider_logo_url: Optional[str] = None
    # VD7 aggregator fields
    aggregator: Optional[str] = None
    source: Optional[str] = None
    is_dummy: Optional[bool] = None
    game_launch_id: Optional[str] = None
    provider_code: Optional[str] = None
    game_code: Optional[str] = None
    supplier: Optional[str] = None
    platform: Optional[str] = None
    # Tag flags
    is_hot: Optional[bool] = False
    is_new: Optional[bool] = False
    is_popular: Optional[bool] = False
    is_active_featured: Optional[bool] = False


class GameCreate(BaseModel):
    provider_id: str = "mock"
    external_game_id: str
    name: str
    category: str
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    rtp: float = 96.0
    volatility: str = "medium"
    min_bet: float = 0.10
    max_bet: float = 1000.0
    tenant_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class GameUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


# ============ GAME SESSION ============
class GameSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    tenant_id: str
    player_id: str
    game_id: str
    provider_id: str
    status: Literal["active", "closed"] = "active"
    launch_url: Optional[str] = None
    balance_at_start: float
    balance_at_end: Optional[float] = None
    total_bet: float = 0.0
    total_win: float = 0.0
    rounds_played: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    closed_at: Optional[datetime] = None


# ============ TRANSACTION / LEDGER ============
class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    tx_id: Optional[str] = Field(default=None)
    tenant_id: str
    # Support both player_id and user_id (legacy)
    player_id: Optional[str] = None
    user_id: Optional[str] = None
    game_id: Optional[str] = None
    game_name: Optional[str] = None
    provider_id: Optional[str] = None
    session_id: Optional[str] = None
    round_id: Optional[str] = None
    reference: Optional[str] = None
    type: Literal["deposit", "withdrawal", "bet", "win", "rollback", "bonus", "adjustment"]
    amount: float
    currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"
    status: Optional[str] = "completed"
    balance_before: Optional[float] = 0
    balance_after: Optional[float] = 0
    description: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    timestamp: Optional[datetime] = Field(default_factory=utc_now)
    created_at: Optional[datetime] = None


class TransactionCreate(BaseModel):
    tenant_id: str
    player_id: str
    game_id: Optional[str] = None
    provider_id: Optional[str] = None
    session_id: Optional[str] = None
    round_id: Optional[str] = None
    type: Literal["deposit", "withdrawal", "bet", "win", "rollback", "bonus", "adjustment"]
    amount: float
    description: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


# ============ DEPOSIT / WITHDRAW REQUEST ============
class DepositRequest(BaseModel):
    amount: float
    currency: Optional[Literal["IDR", "USD", "USDT", "PHP", "TRY"]] = None


class WithdrawRequest(BaseModel):
    amount: float
    currency: Optional[Literal["IDR", "USD", "USDT", "PHP", "TRY"]] = None


# ============ PLAYER SETTINGS ============
class PlayerSettings(BaseModel):
    deposit_limit: Optional[float] = None
    deposit_limit_daily: Optional[float] = None
    loss_limit_daily: Optional[float] = None
    wager_limit_daily: Optional[float] = None
    self_exclusion_until: Optional[datetime] = None
    cooldown_limit_increase_until: Optional[datetime] = None
    session_reminder_minutes: int = 30
    session_reminder_enabled: bool = True
    preferred_currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"


class WalletCallbackResponse(BaseModel):
    status: Literal["ok", "error"]
    code: str
    message: str
    transaction_id: str
    player_id: str
    currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"
    balance: float | int
    idempotent: Optional[bool] = None




class PaymentEvent(BaseModel):
    event_id: str
    provider: str
    tenant_id: str
    player_id: str
    type: Literal["deposit", "withdrawal"]
    amount: float
    currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"
    status: str
    raw: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DepositOrder(BaseModel):
    id: str = Field(default_factory=generate_id)
    provider: str
    tenant_id: str
    player_id: str
    amount: float
    currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"
    status: Literal["created", "pending", "success", "failed"] = "created"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WithdrawalOrder(BaseModel):
    id: str = Field(default_factory=generate_id)
    provider: str
    tenant_id: str
    player_id: str
    amount: float
    currency: Literal["IDR", "USD", "USDT", "PHP", "TRY"] = "IDR"
    status: Literal["requested", "review", "processing", "success", "failed", "cancelled", "rejected"] = "requested"
    bank_info: Optional[dict] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ============ PROVIDER ADAPTER INTERFACE ============
class ProviderSessionRequest(BaseModel):
    player_id: str
    game_id: str
    tenant_id: str
    currency: str = "USD"
    language: str = "en"


class ProviderSessionResponse(BaseModel):
    session_id: str
    launch_url: str
    provider_id: str
    expires_at: Optional[datetime] = None


class ProviderCallbackPayload(BaseModel):
    action: Literal["bet", "win", "rollback"]
    tx_id: str
    round_id: str
    session_id: str
    player_id: str
    amount: float
    metadata: dict = Field(default_factory=dict)


# ============ AUTH RESPONSE ============
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
    tenant: Optional[Tenant] = None
    expires_in: int = 900  # 15 minutes in seconds


# ============ STATS / REPORTING ============
class TenantStats(BaseModel):
    total_players: int
    active_players: int
    total_games: int
    total_transactions: int
    total_deposits: float
    total_withdrawals: float
    total_bets: float
    total_wins: float
    gross_gaming_revenue: float


class GlobalStats(BaseModel):
    total_tenants: int
    total_players: int
    total_games: int
    total_transactions: int
    total_volume: float
    total_deposits: float
    total_bets: float
    total_wins: float


class PlayerStats(BaseModel):
    player_id: str
    total_bets: float
    total_wins: float
    games_played: int
    total_sessions: int
    recent_games: List[dict]
    favorite_category: Optional[str]
    deposit_limit: Optional[float]
    session_reminder_enabled: bool
