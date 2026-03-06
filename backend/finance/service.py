"""Tenant Finance Service - Business logic layer.

Single entrypoint for all finance operations.
Enforces business rules:
- Auto-freeze when buffer below threshold
- Idempotency on all operations
- Tenant isolation
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timezone

from .repository_interface import ITenantFinanceRepository
from .models import (
    TenantFinance,
    TenantFinanceTx,
    TenantFinanceStatus,
    TenantFrozenError,
    TopupResponse,
    ChargeResponse,
    TxType,
    SetupFeeMode,
    DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
)

logger = logging.getLogger(__name__)


class TenantFinanceService:
    """Business logic service for tenant finance operations.
    
    CRITICAL: This service is the single source of truth for:
    - Buffer balance management
    - Freeze/unfreeze enforcement
    - Idempotent transactions
    """
    
    def __init__(self, repository: ITenantFinanceRepository):
        self.repo = repository
    
    # ============ ENFORCEMENT (CRITICAL) ============
    
    async def check_or_autofreeze(self, tenant_id: str) -> Tuple[bool, Optional[TenantFrozenError]]:
        """Check if tenant can operate (launch games, process bets).
        
        MUST be called before:
        1. /api/wallet/debit (PRIMARY enforcement - single source of truth)
        2. /api/games/{game_id}/launch (UX enhancement)
        
        DO NOT call for player withdrawals - frozen is to stop new play, not hold player funds.
        
        Returns:
            Tuple of (can_operate, error_response)
            - can_operate=True: tenant can proceed
            - can_operate=False: return error_response as HTTP 403
        """
        finance = await self.repo.get_or_create_finance(tenant_id)
        
        # Check if already frozen
        if finance.is_frozen:
            required_topup = max(0, finance.buffer_min_threshold_minor - finance.buffer_balance_minor)
            error = TenantFrozenError(
                message=f"Akun Operator sedang dibekukan. Saldo Buffer di bawah minimum. Topup minimal Rp {required_topup:,} untuk aktif kembali.",
                tenant_id=tenant_id,
                required_topup_minor=required_topup,
                buffer_balance_minor=finance.buffer_balance_minor,
                buffer_min_threshold_minor=finance.buffer_min_threshold_minor,
            )
            return False, error
        
        # Check if should auto-freeze (buffer below threshold)
        if finance.buffer_balance_minor < finance.buffer_min_threshold_minor:
            # Auto-freeze
            reason = f"Saldo Buffer ({finance.buffer_balance_minor:,}) di bawah minimum ({finance.buffer_min_threshold_minor:,})"
            await self.repo.set_frozen(tenant_id, is_frozen=True, reason=reason)
            logger.warning(f"Auto-freeze tenant {tenant_id}: {reason}")
            
            required_topup = finance.buffer_min_threshold_minor - finance.buffer_balance_minor
            error = TenantFrozenError(
                message=f"Akun Operator dibekukan otomatis. {reason}. Topup minimal Rp {required_topup:,} untuk aktif kembali.",
                tenant_id=tenant_id,
                required_topup_minor=required_topup,
                buffer_balance_minor=finance.buffer_balance_minor,
                buffer_min_threshold_minor=finance.buffer_min_threshold_minor,
            )
            return False, error
        
        return True, None
    
    async def get_status(self, tenant_id: str) -> TenantFinanceStatus:
        """Get tenant finance status for display."""
        finance = await self.repo.get_or_create_finance(tenant_id)
        
        required_topup = max(0, finance.buffer_min_threshold_minor - finance.buffer_balance_minor)
        can_operate = not finance.is_frozen and finance.buffer_balance_minor >= finance.buffer_min_threshold_minor
        
        return TenantFinanceStatus(
            tenant_id=tenant_id,
            buffer_balance_minor=finance.buffer_balance_minor,
            buffer_min_threshold_minor=finance.buffer_min_threshold_minor,
            is_frozen=finance.is_frozen,
            frozen_reason=finance.frozen_reason,
            required_topup_minor=required_topup,
            ggr_share_percent=finance.ggr_share_percent,
            infra_fee_monthly_minor=finance.infra_fee_monthly_minor,
            setup_fee_paid=finance.setup_fee_paid,
            can_operate=can_operate,
        )
    
    # ============ TOPUP ============
    
    async def topup_buffer(
        self,
        tenant_id: str,
        amount_minor: int,
        ref_id: str,
        note: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> TopupResponse:
        """Add funds to tenant buffer (Topup Saldo Buffer).
        
        Idempotent by ref_id.
        May auto-unfreeze if balance reaches threshold after topup.
        """
        tx, is_idempotent = await self.repo.atomic_add_buffer(
            tenant_id=tenant_id,
            amount_minor=amount_minor,
            tx_type=TxType.TOPUP,
            ref_id=ref_id,
            note=note,
            created_by=created_by,
        )
        
        if not tx:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Check if we should auto-unfreeze
        finance = await self.repo.get_finance(tenant_id)
        is_frozen = finance.is_frozen if finance else False
        
        if finance and finance.is_frozen:
            # Check if topup brings us above threshold
            if finance.buffer_balance_minor >= finance.buffer_min_threshold_minor:
                await self.repo.set_frozen(tenant_id, is_frozen=False)
                is_frozen = False
                logger.info(f"Auto-unfreeze tenant {tenant_id} after topup")
        
        return TopupResponse(
            success=True,
            tx_id=tx.id,
            tenant_id=tenant_id,
            amount_minor=amount_minor,
            new_balance_minor=tx.balance_after_minor or 0,
            is_frozen=is_frozen,
            idempotent=is_idempotent,
        )
    
    # ============ THRESHOLD ============
    
    async def set_threshold(
        self,
        tenant_id: str,
        threshold_minor: int,
    ) -> TenantFinance:
        """Set buffer minimum threshold.
        
        May trigger auto-freeze if new threshold > current balance.
        """
        finance = await self.repo.update_finance(
            tenant_id,
            buffer_min_threshold_minor=threshold_minor
        )
        
        if not finance:
            # Create with defaults
            await self.repo.get_or_create_finance(tenant_id)
            finance = await self.repo.update_finance(
                tenant_id,
                buffer_min_threshold_minor=threshold_minor
            )
        
        # Check if should auto-freeze
        if finance and finance.buffer_balance_minor < threshold_minor and not finance.is_frozen:
            await self.repo.set_frozen(
                tenant_id,
                is_frozen=True,
                reason=f"Saldo Buffer di bawah threshold baru ({threshold_minor:,})"
            )
        
        return finance
    
    # ============ FREEZE/UNFREEZE ============
    
    async def freeze_tenant(
        self,
        tenant_id: str,
        reason: str,
    ) -> TenantFinance:
        """Manually freeze a tenant."""
        finance = await self.repo.set_frozen(tenant_id, is_frozen=True, reason=reason)
        if not finance:
            await self.repo.get_or_create_finance(tenant_id)
            finance = await self.repo.set_frozen(tenant_id, is_frozen=True, reason=reason)
        logger.info(f"Manual freeze tenant {tenant_id}: {reason}")
        return finance
    
    async def unfreeze_tenant(self, tenant_id: str) -> Tuple[bool, TenantFinance, str]:
        """Unfreeze a tenant if buffer is sufficient.
        
        Returns:
            Tuple of (success, finance, message)
        """
        can_unfreeze, balance, threshold = await self.repo.check_can_unfreeze(tenant_id)
        
        if not can_unfreeze:
            required = threshold - balance
            finance = await self.repo.get_finance(tenant_id)
            message = f"Tidak dapat mengaktifkan. Saldo Buffer (Rp {balance:,}) masih di bawah minimum (Rp {threshold:,}). Topup minimal Rp {required:,}."
            return False, finance, message
        
        finance = await self.repo.set_frozen(tenant_id, is_frozen=False)
        logger.info(f"Unfreeze tenant {tenant_id}")
        return True, finance, "Berhasil diaktifkan kembali"
    
    # ============ FEES (SUPER_ADMIN) ============
    
    async def charge_infra_fee(
        self,
        tenant_id: str,
        month: str,
        amount_minor: int,
        ref_id: str,
        created_by: Optional[str] = None,
    ) -> ChargeResponse:
        """Charge monthly infrastructure fee.
        
        Deducts from buffer and may trigger auto-freeze.
        Idempotent by ref_id.
        """
        tx, is_idempotent, needs_freeze = await self.repo.atomic_deduct_buffer(
            tenant_id=tenant_id,
            amount_minor=amount_minor,
            tx_type=TxType.INFRA_FEE,
            ref_id=ref_id,
            note=f"Biaya Infrastruktur bulan {month}",
            fee_month=month,
            created_by=created_by,
        )
        
        if not tx:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        auto_frozen = False
        if needs_freeze and not is_idempotent:
            finance = await self.repo.get_finance(tenant_id)
            if finance and not finance.is_frozen:
                await self.repo.set_frozen(
                    tenant_id,
                    is_frozen=True,
                    reason=f"Saldo Buffer di bawah minimum setelah charge infra fee {month}"
                )
                auto_frozen = True
                logger.warning(f"Auto-freeze tenant {tenant_id} after infra fee charge")
        
        finance = await self.repo.get_finance(tenant_id)
        
        return ChargeResponse(
            success=True,
            tx_id=tx.id,
            tenant_id=tenant_id,
            amount_minor=amount_minor,
            new_balance_minor=tx.balance_after_minor or 0,
            is_frozen=finance.is_frozen if finance else False,
            auto_frozen=auto_frozen,
            idempotent=is_idempotent,
        )
    
    async def charge_setup_fee(
        self,
        tenant_id: str,
        amount_minor: int,
        ref_id: str,
        mode: SetupFeeMode = SetupFeeMode.ACTIVATION_DEPOSIT,
        created_by: Optional[str] = None,
    ) -> ChargeResponse:
        """Charge setup/activation fee.
        
        ACTIVATION_DEPOSIT: Adds to buffer balance (preferred for Indonesian market)
        NON_REFUNDABLE: Recorded but does not affect buffer
        """
        if mode == SetupFeeMode.ACTIVATION_DEPOSIT:
            # Add to buffer
            tx, is_idempotent = await self.repo.atomic_add_buffer(
                tenant_id=tenant_id,
                amount_minor=amount_minor,
                tx_type=TxType.SETUP_FEE,
                ref_id=ref_id,
                note="Deposit Aktivasi (Masuk Saldo Buffer)",
                setup_fee_mode=mode,
                created_by=created_by,
            )
        else:
            # Non-refundable - record tx but don't affect buffer
            # Still need idempotency check
            existing = await self.repo.get_tx_by_ref_id(tenant_id, ref_id)
            if existing:
                finance = await self.repo.get_finance(tenant_id)
                return ChargeResponse(
                    success=True,
                    tx_id=existing.id,
                    tenant_id=tenant_id,
                    amount_minor=amount_minor,
                    new_balance_minor=finance.buffer_balance_minor if finance else 0,
                    is_frozen=finance.is_frozen if finance else True,
                    auto_frozen=False,
                    idempotent=True,
                )
            
            # Record without affecting buffer (amount=0 for buffer impact)
            tx, is_idempotent = await self.repo.atomic_add_buffer(
                tenant_id=tenant_id,
                amount_minor=0,  # No buffer impact
                tx_type=TxType.SETUP_FEE,
                ref_id=ref_id,
                note=f"Setup Fee (Non-Refundable): Rp {amount_minor:,}",
                setup_fee_mode=mode,
                created_by=created_by,
            )
        
        if not tx:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        # Mark setup fee as paid
        await self.repo.update_finance(tenant_id, setup_fee_paid=True)
        
        # Check if should auto-unfreeze (for ACTIVATION_DEPOSIT)
        finance = await self.repo.get_finance(tenant_id)
        is_frozen = finance.is_frozen if finance else True
        
        if finance and finance.is_frozen and mode == SetupFeeMode.ACTIVATION_DEPOSIT:
            if finance.buffer_balance_minor >= finance.buffer_min_threshold_minor:
                await self.repo.set_frozen(tenant_id, is_frozen=False)
                is_frozen = False
                logger.info(f"Auto-unfreeze tenant {tenant_id} after setup fee")
        
        return ChargeResponse(
            success=True,
            tx_id=tx.id,
            tenant_id=tenant_id,
            amount_minor=amount_minor,
            new_balance_minor=tx.balance_after_minor or 0,
            is_frozen=is_frozen,
            auto_frozen=False,
            idempotent=is_idempotent,
        )
    
    # ============ TRANSACTION LOG ============
    
    async def list_transactions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        tx_type: Optional[TxType] = None,
    ):
        """List finance transactions for tenant."""
        return await self.repo.list_transactions(tenant_id, limit, offset, tx_type)
    
    # ============ INITIALIZATION ============
    
    async def ensure_indexes(self):
        """Ensure database indexes are created."""
        await self.repo.ensure_indexes()
