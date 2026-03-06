"""Finance & Risk module for LooxGame multi-tenant platform.

This module implements:
- Operator buffer/escrow management (Saldo Buffer)
- GGR share tracking
- Auto-freeze enforcement when buffer below threshold
- Idempotent financial transactions

Designed to be DB-agnostic for future Postgres migration.
"""

from .models import (
    TenantFinance,
    TenantFinanceTx,
    TenantFinanceCreate,
    TenantFinanceStatus,
    TenantFrozenError,
    TopupResponse,
    ChargeResponse,
    TxType,
    SetupFeeMode,
)
from .repository_interface import ITenantFinanceRepository
from .mongo_repository import MongoTenantFinanceRepository
from .service import TenantFinanceService

__all__ = [
    "TenantFinance",
    "TenantFinanceTx",
    "TenantFinanceCreate",
    "TenantFinanceStatus",
    "TenantFrozenError",
    "TopupResponse",
    "ChargeResponse",
    "TxType",
    "SetupFeeMode",
    "ITenantFinanceRepository",
    "MongoTenantFinanceRepository",
    "TenantFinanceService",
]
