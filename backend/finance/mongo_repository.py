"""MongoDB implementation of Tenant Finance Repository.

Uses existing MongoDB patterns from the codebase.
Ensures idempotency via unique index on (tenant_id, ref_id).
"""

import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from pymongo import ReturnDocument, DESCENDING
from pymongo.errors import DuplicateKeyError

from .repository_interface import ITenantFinanceRepository
from .models import (
    TenantFinance,
    TenantFinanceTx,
    TenantFinanceCreate,
    TxType,
    SetupFeeMode,
    generate_id,
    DEFAULT_GGR_SHARE_PERCENT,
    DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
    DEFAULT_INFRA_FEE_MONTHLY_MINOR,
    DEFAULT_SETUP_FEE_MINOR,
)

logger = logging.getLogger(__name__)


class MongoTenantFinanceRepository(ITenantFinanceRepository):
    """MongoDB implementation of tenant finance repository.
    
    Collections:
    - tenant_finance: One document per tenant
    - tenant_finance_tx: Transaction log with idempotency
    """
    
    def __init__(self, db):
        """Initialize with MongoDB database instance."""
        self.db = db
        self.finance_col = db.tenant_finance
        self.tx_col = db.tenant_finance_tx
    
    async def ensure_indexes(self) -> None:
        """Create required indexes for finance collections."""
        # tenant_finance: unique index on tenant_id
        await self.finance_col.create_index("tenant_id", unique=True)
        
        # tenant_finance_tx: unique index on (tenant_id, ref_id) for idempotency
        await self.tx_col.create_index(
            [("tenant_id", 1), ("ref_id", 1)],
            unique=True,
            name="idx_tenant_ref_id_unique"
        )
        
        # tenant_finance_tx: index for listing by tenant + created_at
        await self.tx_col.create_index(
            [("tenant_id", 1), ("created_at", DESCENDING)],
            name="idx_tenant_created_at"
        )
        
        logger.info("Finance indexes ensured")
    
    # ============ TENANT FINANCE CRUD ============
    
    async def get_finance(self, tenant_id: str) -> Optional[TenantFinance]:
        doc = await self.finance_col.find_one({"tenant_id": tenant_id}, {"_id": 0})
        if not doc:
            return None
        return TenantFinance(**doc)
    
    async def get_or_create_finance(self, tenant_id: str) -> TenantFinance:
        doc = await self.finance_col.find_one({"tenant_id": tenant_id}, {"_id": 0})
        if doc:
            return TenantFinance(**doc)
        
        # Create with defaults
        now = datetime.now(timezone.utc)
        new_finance = TenantFinance(
            tenant_id=tenant_id,
            buffer_balance_minor=0,
            buffer_min_threshold_minor=DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
            is_frozen=True,  # New tenants start frozen until setup fee paid
            frozen_reason="Menunggu Deposit Aktivasi (Setup Fee)",
            ggr_share_percent=DEFAULT_GGR_SHARE_PERCENT,
            infra_fee_monthly_minor=DEFAULT_INFRA_FEE_MONTHLY_MINOR,
            setup_fee_minor=DEFAULT_SETUP_FEE_MINOR,
            setup_fee_mode=SetupFeeMode.ACTIVATION_DEPOSIT,
            setup_fee_paid=False,
            created_at=now,
            updated_at=now,
        )
        
        try:
            await self.finance_col.insert_one(self._to_doc(new_finance))
        except DuplicateKeyError:
            # Race condition - another request created it
            doc = await self.finance_col.find_one({"tenant_id": tenant_id}, {"_id": 0})
            if doc:
                return TenantFinance(**doc)
        
        return new_finance
    
    async def create_finance(self, data: TenantFinanceCreate) -> TenantFinance:
        now = datetime.now(timezone.utc)
        finance = TenantFinance(
            tenant_id=data.tenant_id,
            buffer_balance_minor=0,
            buffer_min_threshold_minor=data.buffer_min_threshold_minor or DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
            is_frozen=True,
            frozen_reason="Menunggu Deposit Aktivasi (Setup Fee)",
            ggr_share_percent=data.ggr_share_percent or DEFAULT_GGR_SHARE_PERCENT,
            infra_fee_monthly_minor=data.infra_fee_monthly_minor or DEFAULT_INFRA_FEE_MONTHLY_MINOR,
            setup_fee_minor=data.setup_fee_minor or DEFAULT_SETUP_FEE_MINOR,
            setup_fee_mode=data.setup_fee_mode or SetupFeeMode.ACTIVATION_DEPOSIT,
            setup_fee_paid=False,
            created_at=now,
            updated_at=now,
        )
        await self.finance_col.insert_one(self._to_doc(finance))
        return finance
    
    async def update_finance(self, tenant_id: str, **updates) -> Optional[TenantFinance]:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        doc = await self.finance_col.find_one_and_update(
            {"tenant_id": tenant_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0}
        )
        
        if not doc:
            return None
        return TenantFinance(**doc)
    
    # ============ BUFFER OPERATIONS ============
    
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
        """Atomically add to buffer and record transaction."""
        
        # Check idempotency first
        existing_tx = await self.get_tx_by_ref_id(tenant_id, ref_id)
        if existing_tx:
            logger.info(f"Idempotent topup: tenant={tenant_id}, ref_id={ref_id}")
            return existing_tx, True
        
        # Ensure tenant finance exists
        await self.get_or_create_finance(tenant_id)
        
        now = datetime.now(timezone.utc)
        
        # Atomic increment buffer
        updated = await self.finance_col.find_one_and_update(
            {"tenant_id": tenant_id},
            {
                "$inc": {"buffer_balance_minor": amount_minor},
                "$set": {"updated_at": now.isoformat()}
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0, "buffer_balance_minor": 1}
        )
        
        if not updated:
            logger.error(f"Failed to add buffer: tenant={tenant_id} not found")
            return None, False
        
        new_balance = updated.get("buffer_balance_minor", 0)
        
        # Record transaction
        tx = TenantFinanceTx(
            id=generate_id(),
            tenant_id=tenant_id,
            type=tx_type,
            amount_minor=amount_minor,
            ref_id=ref_id,
            note=note,
            fee_month=fee_month,
            setup_fee_mode=setup_fee_mode,
            created_by=created_by,
            created_at=now,
            balance_after_minor=new_balance,
        )
        
        try:
            await self.tx_col.insert_one(self._tx_to_doc(tx))
            return tx, False
        except DuplicateKeyError:
            # Race condition - another request created this tx
            # Rollback the buffer increment
            await self.finance_col.update_one(
                {"tenant_id": tenant_id},
                {"$inc": {"buffer_balance_minor": -amount_minor}}
            )
            existing = await self.get_tx_by_ref_id(tenant_id, ref_id)
            return existing, True
    
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
        """Atomically deduct from buffer and check threshold."""
        
        # Check idempotency first
        existing_tx = await self.get_tx_by_ref_id(tenant_id, ref_id)
        if existing_tx:
            logger.info(f"Idempotent deduct: tenant={tenant_id}, ref_id={ref_id}")
            finance = await self.get_finance(tenant_id)
            needs_freeze = finance and finance.buffer_balance_minor < finance.buffer_min_threshold_minor
            return existing_tx, True, needs_freeze
        
        # Ensure tenant finance exists
        finance = await self.get_or_create_finance(tenant_id)
        
        now = datetime.now(timezone.utc)
        deduct_amount = abs(amount_minor)  # Ensure we're deducting
        
        # Atomic decrement buffer
        updated = await self.finance_col.find_one_and_update(
            {"tenant_id": tenant_id},
            {
                "$inc": {"buffer_balance_minor": -deduct_amount},
                "$set": {"updated_at": now.isoformat()}
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0, "buffer_balance_minor": 1, "buffer_min_threshold_minor": 1}
        )
        
        if not updated:
            return None, False, False
        
        new_balance = updated.get("buffer_balance_minor", 0)
        threshold = updated.get("buffer_min_threshold_minor", DEFAULT_BUFFER_MIN_THRESHOLD_MINOR)
        needs_freeze = new_balance < threshold
        
        # Record transaction
        tx = TenantFinanceTx(
            id=generate_id(),
            tenant_id=tenant_id,
            type=tx_type,
            amount_minor=-deduct_amount,  # Negative for deduction
            ref_id=ref_id,
            note=note,
            fee_month=fee_month,
            created_by=created_by,
            created_at=now,
            balance_after_minor=new_balance,
        )
        
        try:
            await self.tx_col.insert_one(self._tx_to_doc(tx))
            return tx, False, needs_freeze
        except DuplicateKeyError:
            # Rollback
            await self.finance_col.update_one(
                {"tenant_id": tenant_id},
                {"$inc": {"buffer_balance_minor": deduct_amount}}
            )
            existing = await self.get_tx_by_ref_id(tenant_id, ref_id)
            finance = await self.get_finance(tenant_id)
            needs_freeze = finance and finance.buffer_balance_minor < finance.buffer_min_threshold_minor
            return existing, True, needs_freeze
    
    # ============ FREEZE/UNFREEZE ============
    
    async def set_frozen(
        self,
        tenant_id: str,
        is_frozen: bool,
        reason: Optional[str] = None,
    ) -> Optional[TenantFinance]:
        now = datetime.now(timezone.utc)
        
        update_fields = {
            "is_frozen": is_frozen,
            "updated_at": now.isoformat(),
        }
        
        if is_frozen:
            update_fields["frozen_reason"] = reason
            update_fields["frozen_at"] = now.isoformat()
        else:
            update_fields["frozen_reason"] = None
            update_fields["frozen_at"] = None
        
        doc = await self.finance_col.find_one_and_update(
            {"tenant_id": tenant_id},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0}
        )
        
        if not doc:
            return None
        return TenantFinance(**doc)
    
    async def check_can_unfreeze(self, tenant_id: str) -> Tuple[bool, int, int]:
        finance = await self.get_finance(tenant_id)
        if not finance:
            return False, 0, DEFAULT_BUFFER_MIN_THRESHOLD_MINOR
        
        can_unfreeze = finance.buffer_balance_minor >= finance.buffer_min_threshold_minor
        return can_unfreeze, finance.buffer_balance_minor, finance.buffer_min_threshold_minor
    
    # ============ TRANSACTION LOG ============
    
    async def get_tx_by_ref_id(self, tenant_id: str, ref_id: str) -> Optional[TenantFinanceTx]:
        doc = await self.tx_col.find_one(
            {"tenant_id": tenant_id, "ref_id": ref_id},
            {"_id": 0}
        )
        if not doc:
            return None
        return TenantFinanceTx(**doc)
    
    async def list_transactions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[TxType] = None,
    ) -> List[TenantFinanceTx]:
        query = {"tenant_id": tenant_id}
        if tx_type:
            query["type"] = tx_type.value
        
        cursor = self.tx_col.find(query, {"_id": 0})
        cursor = cursor.sort("created_at", DESCENDING)
        cursor = cursor.skip(offset).limit(limit)
        
        docs = await cursor.to_list(length=limit)
        return [TenantFinanceTx(**doc) for doc in docs]
    
    # ============ HELPERS ============
    
    def _to_doc(self, finance: TenantFinance) -> dict:
        """Convert TenantFinance to MongoDB document."""
        doc = finance.model_dump()
        # Convert datetime to ISO string for MongoDB
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], 'isoformat') else doc["created_at"]
        if doc.get("updated_at"):
            doc["updated_at"] = doc["updated_at"].isoformat() if hasattr(doc["updated_at"], 'isoformat') else doc["updated_at"]
        if doc.get("frozen_at"):
            doc["frozen_at"] = doc["frozen_at"].isoformat() if hasattr(doc["frozen_at"], 'isoformat') else doc["frozen_at"]
        # Convert enum to value
        if doc.get("setup_fee_mode"):
            doc["setup_fee_mode"] = doc["setup_fee_mode"].value if hasattr(doc["setup_fee_mode"], 'value') else doc["setup_fee_mode"]
        return doc
    
    def _tx_to_doc(self, tx: TenantFinanceTx) -> dict:
        """Convert TenantFinanceTx to MongoDB document."""
        doc = tx.model_dump()
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat() if hasattr(doc["created_at"], 'isoformat') else doc["created_at"]
        if doc.get("type"):
            doc["type"] = doc["type"].value if hasattr(doc["type"], 'value') else doc["type"]
        if doc.get("setup_fee_mode"):
            doc["setup_fee_mode"] = doc["setup_fee_mode"].value if hasattr(doc["setup_fee_mode"], 'value') else doc["setup_fee_mode"]
        return doc
