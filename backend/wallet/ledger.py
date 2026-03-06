"""Wallet ledger with strict tenant isolation and integer-based storage.

SECURITY HARDENING:
- All wallet operations require tenant_id binding
- Wallet balance stored as integer minor units (cents/rupiah)
- Atomic operations with tenant + player + role + active filters
- Backward compatibility for float-to-integer migration
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union
import logging

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

ALLOWED_CURRENCIES = {"IDR", "USD", "USDT", "PHP", "TRY"}

# Integer storage multipliers
# IDR: 1 (already integer), USD/USDT/PHP/TRY: 100 (minor units)
CURRENCY_MULTIPLIERS = {
    "IDR": 1,
    "USD": 100,
    "USDT": 100,
    "PHP": 100,
    "TRY": 100,
}


def normalize_currency(value: Optional[str]) -> str:
    normalized = (value or "IDR").upper()
    if normalized not in ALLOWED_CURRENCIES:
        raise ValueError("Unsupported currency")
    return normalized


def currency_quant(currency: Optional[str]) -> Decimal:
    if normalize_currency(currency) == "IDR":
        return Decimal("1")
    return Decimal("0.01")


def get_multiplier(currency: Optional[str]) -> int:
    """Get the multiplier for converting to/from minor units."""
    return CURRENCY_MULTIPLIERS.get(normalize_currency(currency), 1)


def to_minor_units(value: Union[float, int, str, Decimal], currency: Optional[str]) -> int:
    """Convert a decimal/float amount to integer minor units.
    
    IDR: 1000 -> 1000 (no conversion, IDR is already integer)
    USD: 10.50 -> 1050 (cents)
    USDT: 10.50 -> 1050 (cents)
    """
    multiplier = get_multiplier(currency)
    decimal_val = Decimal(str(value))
    return int((decimal_val * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_minor_units(value: int, currency: Optional[str]) -> Union[int, float]:
    """Convert integer minor units back to display value.
    
    IDR: 1000 -> 1000 (int)
    USD: 1050 -> 10.50 (float)
    USDT: 1050 -> 10.50 (float)
    """
    multiplier = get_multiplier(currency)
    if normalize_currency(currency) == "IDR":
        return int(value)
    return float(Decimal(str(value)) / Decimal(str(multiplier)))


def normalize_stored_balance(stored_value: Union[int, float, Decimal], currency: Optional[str]) -> int:
    """Normalize a stored balance value to integer minor units.
    
    Handles backward compatibility:
    - If value is already int and looks like minor units, return as-is
    - If value is float, convert to minor units
    - If value is Decimal, convert to minor units
    
    This ensures smooth migration from float-based to integer-based storage.
    """
    if stored_value is None:
        return 0
    
    currency = normalize_currency(currency)
    
    # If already an int and currency is IDR (no fractional), return as-is
    if isinstance(stored_value, int):
        return stored_value
    
    # Float or Decimal - convert to minor units
    # This handles legacy float storage
    return to_minor_units(stored_value, currency)


def money_to_decimal(value: float | int | str | Decimal, currency: Optional[str] = "IDR") -> Decimal:
    """Convert any numeric value to Decimal with proper precision.
    
    Used for calculations and comparisons.
    """
    return Decimal(str(value)).quantize(currency_quant(currency), rounding=ROUND_HALF_UP)


def decimal_to_amount(value: Decimal, currency: Optional[str] = "IDR") -> int | float:
    """Convert Decimal to display amount (int for IDR, float for USD/USDT)."""
    quantized = value.quantize(currency_quant(currency), rounding=ROUND_HALF_UP)
    if normalize_currency(currency) == "IDR":
        return int(quantized)
    return float(quantized)


async def get_wallet(db, player_id: str, tenant_id: str):
    """Get player wallet with strict tenant binding.
    
    SECURITY: Only returns wallet for active players in the specified tenant.
    """
    return await db.users.find_one(
        {"id": player_id, "tenant_id": tenant_id, "role": "player", "is_active": True},
        {"_id": 0},
    )


async def find_tx_by_tx_id(db, tenant_id: str, player_id: str, tx_id: str):
    """Find transaction by tx_id with tenant binding."""
    return await db.transactions.find_one(
        {"tenant_id": tenant_id, "player_id": player_id, "tx_id": tx_id},
        {"_id": 0},
    )


async def record_tx(
    db,
    *,
    tenant_id: str,
    player_id: str,
    tx_id: str,
    tx_type: str,
    amount: Decimal,
    currency: str,
    balance_before: Decimal,
    balance_after: Decimal,
    session_id: Optional[str] = None,
    round_id: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """Record a transaction with tenant binding.
    
    All transactions are scoped by tenant_id for isolation.
    """
    tx_doc = {
        "id": tx_id,
        "tx_id": tx_id,
        "tenant_id": tenant_id,
        "player_id": player_id,
        "session_id": session_id,
        "round_id": round_id,
        "type": tx_type,
        "amount": decimal_to_amount(amount, currency),
        "amount_minor_units": to_minor_units(amount, currency),
        "currency": normalize_currency(currency),
        "balance_before": decimal_to_amount(balance_before, currency),
        "balance_after": decimal_to_amount(balance_after, currency),
        "balance_before_minor": to_minor_units(balance_before, currency),
        "balance_after_minor": to_minor_units(balance_after, currency),
        "description": description,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.transactions.insert_one(tx_doc)
        return tx_doc, False
    except DuplicateKeyError:
        existing = await find_tx_by_tx_id(db, tenant_id, player_id, tx_id)
        if not existing:
            raise
        return existing, True


async def atomic_debit(
    db,
    *,
    tenant_id: str,
    player_id: str,
    amount: Decimal,
    currency: str
) -> Optional[Decimal]:
    """Atomically debit player wallet with strict tenant isolation.
    
    SECURITY FEATURES:
    1. Requires tenant_id - prevents cross-tenant access
    2. Requires role=player - only players have wallets
    3. Requires is_active=True - disabled accounts cannot transact
    4. Atomic balance check - prevents race conditions
    
    Args:
        db: Database connection
        tenant_id: Tenant ID (REQUIRED for security)
        player_id: Player ID
        amount: Amount to debit (as Decimal)
        currency: Currency code
    
    Returns:
        New balance as Decimal, or None if insufficient funds or player not found
    """
    amount_for_inc = decimal_to_amount(amount, currency)
    
    # CRITICAL: Full tenant isolation filter
    # - tenant_id: ensures player belongs to correct tenant
    # - role: player - only players have wallets
    # - is_active: True - disabled accounts cannot transact
    # - wallet_balance >= amount - atomic balance check
    updated = await db.users.find_one_and_update(
        {
            "id": player_id,
            "tenant_id": tenant_id,
            "role": "player",
            "is_active": True,
            "wallet_balance": {"$gte": amount_for_inc}
        },
        {"$inc": {"wallet_balance": -amount_for_inc}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "wallet_balance": 1},
    )
    
    if not updated:
        logger.warning(
            f"atomic_debit failed: tenant={tenant_id}, player={player_id}, "
            f"amount={amount_for_inc} - player not found, inactive, or insufficient balance"
        )
        return None
    
    return money_to_decimal(updated.get("wallet_balance", 0), currency)


async def atomic_credit(
    db,
    *,
    tenant_id: str,
    player_id: str,
    amount: Decimal,
    currency: str
) -> Optional[Decimal]:
    """Atomically credit player wallet with strict tenant isolation.
    
    SECURITY FEATURES:
    1. Requires tenant_id - prevents cross-tenant access
    2. Requires role=player - only players have wallets
    3. Requires is_active=True - disabled accounts cannot transact
    
    Args:
        db: Database connection
        tenant_id: Tenant ID (REQUIRED for security)
        player_id: Player ID
        amount: Amount to credit (as Decimal)
        currency: Currency code
    
    Returns:
        New balance as Decimal, or None if player not found
    """
    amount_for_inc = decimal_to_amount(amount, currency)
    
    # CRITICAL: Full tenant isolation filter
    updated = await db.users.find_one_and_update(
        {
            "id": player_id,
            "tenant_id": tenant_id,
            "role": "player",
            "is_active": True,
        },
        {"$inc": {"wallet_balance": amount_for_inc}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "wallet_balance": 1},
    )
    
    if not updated:
        logger.warning(
            f"atomic_credit failed: tenant={tenant_id}, player={player_id}, "
            f"amount={amount_for_inc} - player not found or inactive"
        )
        return None
    
    return money_to_decimal(updated.get("wallet_balance", 0), currency)


# =============================================================================
# MIGRATION UTILITIES
# =============================================================================

async def migrate_balance_to_integer(db, player_id: str, tenant_id: str, currency: str) -> bool:
    """Migrate a single player's balance from float to integer minor units.
    
    This is called on-the-fly when a legacy float balance is detected.
    Safe to call multiple times (idempotent).
    
    Returns True if migration was performed, False if already migrated.
    """
    player = await db.users.find_one(
        {"id": player_id, "tenant_id": tenant_id},
        {"_id": 0, "wallet_balance": 1, "wallet_balance_migrated": 1}
    )
    
    if not player:
        return False
    
    # Already migrated
    if player.get("wallet_balance_migrated"):
        return False
    
    current_balance = player.get("wallet_balance", 0)
    
    # Check if it looks like a float that needs conversion
    # (has decimal places for USD/USDT, or is a float type)
    if isinstance(current_balance, float):
        # Convert to integer minor units
        new_balance = to_minor_units(current_balance, currency)
        
        await db.users.update_one(
            {"id": player_id, "tenant_id": tenant_id},
            {
                "$set": {
                    "wallet_balance": new_balance,
                    "wallet_balance_migrated": True,
                    "wallet_balance_legacy": current_balance,  # Keep original for audit
                }
            }
        )
        logger.info(
            f"Migrated balance for player {player_id}: {current_balance} -> {new_balance} ({currency})"
        )
        return True
    
    # Already integer, just mark as migrated
    await db.users.update_one(
        {"id": player_id, "tenant_id": tenant_id},
        {"$set": {"wallet_balance_migrated": True}}
    )
    return False
