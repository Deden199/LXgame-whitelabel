"""Abstract repository interface for Tenant Finance.

Designed for DB-agnostic implementation.
Currently implemented: MongoDB
Future: PostgreSQL (AWS RDS)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from datetime import datetime

from .models import (
    TenantFinance,
    TenantFinanceTx,
    TenantFinanceCreate,
    TxType,
    SetupFeeMode,
)


class ITenantFinanceRepository(ABC):
    """Abstract interface for tenant finance data access.
    
    All implementations must ensure:
    1. Tenant isolation - operations scoped by tenant_id
    2. Idempotency - (tenant_id, ref_id) unique for transactions
    3. Atomicity - balance updates must be atomic
    """
    
    # ============ TENANT FINANCE CRUD ============
    
    @abstractmethod
    async def get_finance(self, tenant_id: str) -> Optional[TenantFinance]:
        """Get tenant finance record.
        
        Returns None if not found.
        """
        pass
    
    @abstractmethod
    async def get_or_create_finance(self, tenant_id: str) -> TenantFinance:
        """Get or create tenant finance with defaults.
        
        Always returns a valid TenantFinance object.
        """
        pass
    
    @abstractmethod
    async def create_finance(self, data: TenantFinanceCreate) -> TenantFinance:
        """Create new tenant finance record.
        
        Raises if tenant_id already exists.
        """
        pass
    
    @abstractmethod
    async def update_finance(
        self,
        tenant_id: str,
        **updates
    ) -> Optional[TenantFinance]:
        """Update tenant finance fields.
        
        Returns updated record or None if not found.
        """
        pass
    
    # ============ BUFFER OPERATIONS (ATOMIC) ============
    
    @abstractmethod
    async def atomic_add_buffer(
        self,
        tenant_id: str,
        amount_minor: int,
        tx_type: TxType,
        ref_id: str,
        note: Optional[str] = None,
        fee_month: Optional[str] = None,
        setup_fee_mode: Optional[SetupFeeMode] = None,
        created_by: Optional[str] = None,
    ) -> Tuple[Optional[TenantFinanceTx], bool]:
        """Atomically add to buffer balance and record transaction.
        
        Idempotent by (tenant_id, ref_id).
        
        Args:
            tenant_id: Tenant identifier
            amount_minor: Amount to add (positive) or subtract (negative)
            tx_type: Transaction type
            ref_id: Unique reference for idempotency
            note: Optional description
            fee_month: For INFRA_FEE, the month being charged (YYYY-MM)
            setup_fee_mode: For SETUP_FEE, the mode
            created_by: User ID who initiated
        
        Returns:
            Tuple of (TenantFinanceTx, is_idempotent)
            - is_idempotent=True if ref_id was already processed
            - Returns (None, False) if tenant not found
        """
        pass
    
    @abstractmethod
    async def atomic_deduct_buffer(
        self,
        tenant_id: str,
        amount_minor: int,
        tx_type: TxType,
        ref_id: str,
        note: Optional[str] = None,
        fee_month: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Tuple[Optional[TenantFinanceTx], bool, bool]:
        """Atomically deduct from buffer and check threshold.
        
        Returns:
            Tuple of (TenantFinanceTx, is_idempotent, needs_freeze)
            - needs_freeze=True if balance dropped below threshold
        """
        pass
    
    # ============ FREEZE/UNFREEZE ============
    
    @abstractmethod
    async def set_frozen(
        self,
        tenant_id: str,
        is_frozen: bool,
        reason: Optional[str] = None,
    ) -> Optional[TenantFinance]:
        """Set tenant frozen status.
        
        Returns updated record or None if not found.
        """
        pass
    
    @abstractmethod
    async def check_can_unfreeze(self, tenant_id: str) -> Tuple[bool, int, int]:
        """Check if tenant can be unfrozen.
        
        Returns:
            Tuple of (can_unfreeze, current_balance_minor, threshold_minor)
            - can_unfreeze=True if buffer_balance >= buffer_min_threshold
        """
        pass
    
    # ============ TRANSACTION LOG ============
    
    @abstractmethod
    async def get_tx_by_ref_id(self, tenant_id: str, ref_id: str) -> Optional[TenantFinanceTx]:
        """Get transaction by reference ID.
        
        Used for idempotency check.
        """
        pass
    
    @abstractmethod
    async def list_transactions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[TxType] = None,
    ) -> List[TenantFinanceTx]:
        """List transactions for a tenant.
        
        Ordered by created_at DESC (most recent first).
        """
        pass
    
    # ============ INDEXES (for initialization) ============
    
    @abstractmethod
    async def ensure_indexes(self) -> None:
        """Create required database indexes.
        
        MongoDB: unique index on (tenant_id, ref_id) in tenant_finance_tx
        PostgreSQL: handled by Alembic migrations
        """
        pass
