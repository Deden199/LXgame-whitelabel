"""Finance domain models for LooxGame.

All monetary values stored as integer minor units (IDR: 1 = 1 Rupiah).
Designed for Postgres migration - use BIGINT for all amounts.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


def generate_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============ ENUMS ============
class TxType(str, Enum):
    TOPUP = "TOPUP"
    ADJUST = "ADJUST"
    SETTLEMENT_DEDUCT = "SETTLEMENT_DEDUCT"
    INFRA_FEE = "INFRA_FEE"
    SETUP_FEE = "SETUP_FEE"


class SetupFeeMode(str, Enum):
    NON_REFUNDABLE = "NON_REFUNDABLE"
    ACTIVATION_DEPOSIT = "ACTIVATION_DEPOSIT"


# ============ DEFAULTS (Indonesian Market) ============
DEFAULT_GGR_SHARE_PERCENT = 15.0
DEFAULT_BUFFER_MIN_THRESHOLD_MINOR = 25_000_000  # 25M IDR
DEFAULT_INFRA_FEE_MONTHLY_MINOR = 5_000_000  # 5M IDR
DEFAULT_SETUP_FEE_MINOR = 25_000_000  # 25M IDR


# ============ TENANT FINANCE ============
class TenantFinance(BaseModel):
    """Tenant financial state - buffer/escrow for risk management.
    
    Postgres target: tenant_finance table with tenant_id as PK.
    """
    tenant_id: str = Field(..., description="Primary key, references tenants.id")
    
    # Buffer/Escrow - Saldo Buffer (integer minor units)
    buffer_balance_minor: int = Field(default=0, description="Current buffer balance in IDR minor units")
    buffer_min_threshold_minor: int = Field(
        default=DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
        description="Minimum required buffer (default 25M IDR)"
    )
    
    # Freeze status
    is_frozen: bool = Field(default=False, description="Tenant frozen - blocks game launch and bets")
    frozen_reason: Optional[str] = Field(default=None, description="Reason for freeze")
    frozen_at: Optional[datetime] = Field(default=None, description="When tenant was frozen")
    
    # Commercial terms
    ggr_share_percent: float = Field(
        default=DEFAULT_GGR_SHARE_PERCENT,
        description="GGR share percentage (default 15%)"
    )
    infra_fee_monthly_minor: int = Field(
        default=DEFAULT_INFRA_FEE_MONTHLY_MINOR,
        description="Monthly infrastructure fee (default 5M IDR)"
    )
    setup_fee_minor: int = Field(
        default=DEFAULT_SETUP_FEE_MINOR,
        description="Setup/activation fee (default 25M IDR)"
    )
    setup_fee_mode: SetupFeeMode = Field(
        default=SetupFeeMode.ACTIVATION_DEPOSIT,
        description="Setup fee mode: NON_REFUNDABLE or ACTIVATION_DEPOSIT"
    )
    setup_fee_paid: bool = Field(default=False, description="Whether setup fee has been paid")
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TenantFinanceCreate(BaseModel):
    """Request model for initializing tenant finance."""
    tenant_id: str
    buffer_min_threshold_minor: Optional[int] = DEFAULT_BUFFER_MIN_THRESHOLD_MINOR
    ggr_share_percent: Optional[float] = DEFAULT_GGR_SHARE_PERCENT
    infra_fee_monthly_minor: Optional[int] = DEFAULT_INFRA_FEE_MONTHLY_MINOR
    setup_fee_minor: Optional[int] = DEFAULT_SETUP_FEE_MINOR
    setup_fee_mode: Optional[SetupFeeMode] = SetupFeeMode.ACTIVATION_DEPOSIT


class TenantFinanceStatus(BaseModel):
    """Response model for finance status check."""
    tenant_id: str
    buffer_balance_minor: int
    buffer_min_threshold_minor: int
    is_frozen: bool
    frozen_reason: Optional[str] = None
    required_topup_minor: int = Field(default=0, description="Amount needed to unfreeze")
    ggr_share_percent: float
    infra_fee_monthly_minor: int
    setup_fee_paid: bool
    can_operate: bool = Field(description="Whether tenant can launch games and process bets")


# ============ TENANT FINANCE TRANSACTIONS ============
class TenantFinanceTx(BaseModel):
    """Transaction log for tenant buffer operations.
    
    Idempotent by (tenant_id, ref_id) - unique constraint.
    Postgres target: tenant_finance_tx table.
    """
    id: str = Field(default_factory=generate_id, description="UUID primary key")
    tenant_id: str = Field(..., description="References tenant_finance.tenant_id")
    
    type: TxType = Field(..., description="Transaction type")
    amount_minor: int = Field(..., description="Amount in IDR minor units (positive for credits, negative for debits)")
    
    # Idempotency key - MUST be unique per tenant
    ref_id: str = Field(..., description="Reference ID - unique per tenant for idempotency")
    
    note: Optional[str] = Field(default=None, description="Optional note/description")
    
    # For INFRA_FEE
    fee_month: Optional[str] = Field(default=None, description="YYYY-MM for monthly fees")
    
    # For SETUP_FEE
    setup_fee_mode: Optional[SetupFeeMode] = Field(default=None)
    
    # Audit
    created_by: Optional[str] = Field(default=None, description="User ID who created this tx")
    created_at: datetime = Field(default_factory=utc_now)
    
    # Balance snapshot after this tx
    balance_after_minor: Optional[int] = Field(default=None, description="Buffer balance after this tx")


# ============ API REQUEST MODELS ============
class TopupRequest(BaseModel):
    """Request for buffer topup."""
    amount_idr: int = Field(..., gt=0, description="Amount in IDR (will be stored as minor units)")
    ref_id: str = Field(..., min_length=1, description="Unique reference ID for idempotency")
    note: Optional[str] = Field(default=None, max_length=500)


class SetThresholdRequest(BaseModel):
    """Request to set buffer minimum threshold."""
    threshold_idr: int = Field(..., gt=0, description="Minimum threshold in IDR")


class FreezeRequest(BaseModel):
    """Request to freeze tenant."""
    reason: str = Field(..., min_length=1, max_length=500)


class ChargeInfraRequest(BaseModel):
    """Request to charge monthly infrastructure fee."""
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM format")
    ref_id: str = Field(..., min_length=1)
    amount_idr: int = Field(..., gt=0, description="Amount in IDR")


class ChargeSetupRequest(BaseModel):
    """Request to charge setup fee."""
    ref_id: str = Field(..., min_length=1)
    amount_idr: int = Field(..., gt=0)
    mode: SetupFeeMode = Field(default=SetupFeeMode.ACTIVATION_DEPOSIT)


# ============ API RESPONSE MODELS ============
class TenantFrozenError(BaseModel):
    """Standard error response when tenant is frozen."""
    error_code: Literal["TENANT_FROZEN"] = "TENANT_FROZEN"
    message: str
    tenant_id: str
    required_topup_minor: int
    buffer_balance_minor: int
    buffer_min_threshold_minor: int


class TopupResponse(BaseModel):
    """Response for topup operation."""
    success: bool
    tx_id: str
    tenant_id: str
    amount_minor: int
    new_balance_minor: int
    is_frozen: bool
    idempotent: bool = Field(default=False, description="True if this was a duplicate request")


class ChargeResponse(BaseModel):
    """Response for charge operations (infra fee, setup fee)."""
    success: bool
    tx_id: str
    tenant_id: str
    amount_minor: int
    new_balance_minor: int
    is_frozen: bool
    auto_frozen: bool = Field(default=False, description="True if this charge triggered auto-freeze")
    idempotent: bool = Field(default=False)
