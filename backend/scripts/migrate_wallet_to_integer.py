#!/usr/bin/env python3
"""One-time migration script: Convert wallet_balance from float to integer minor units.

This script safely migrates all player wallet balances from float storage
to integer storage (minor units).

IDR: 1000.0 -> 1000 (no change, already whole numbers)
USD/USDT: 10.50 -> 1050 (convert to cents)

SAFETY FEATURES:
- Creates backup of original balance in wallet_balance_legacy field
- Sets wallet_balance_migrated flag to prevent re-migration
- Transaction-safe with atomic operations
- Dry-run mode available
- Detailed logging

Usage:
    # Dry run (no changes made)
    python scripts/migrate_wallet_to_integer.py --dry-run
    
    # Actual migration
    python scripts/migrate_wallet_to_integer.py
    
    # With specific tenant
    python scripts/migrate_wallet_to_integer.py --tenant-id tenant_aurum_001
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Currency multipliers
CURRENCY_MULTIPLIERS = {
    "IDR": 1,
    "USD": 100,
    "USDT": 100,
}


def get_multiplier(currency: str) -> int:
    return CURRENCY_MULTIPLIERS.get(currency.upper(), 1)


def to_minor_units(value, currency: str) -> int:
    """Convert a float/decimal amount to integer minor units."""
    multiplier = get_multiplier(currency)
    decimal_val = Decimal(str(value))
    return int((decimal_val * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def migrate_player(db, player: dict, dry_run: bool) -> dict:
    """Migrate a single player's balance.
    
    Returns dict with migration details.
    """
    player_id = player["id"]
    tenant_id = player.get("tenant_id", "unknown")
    current_balance = player.get("wallet_balance", 0)
    currency = player.get("preferred_currency", "IDR")
    
    # Already migrated
    if player.get("wallet_balance_migrated"):
        return {
            "player_id": player_id,
            "status": "skipped",
            "reason": "already_migrated",
        }
    
    # Check if balance is float that needs conversion
    if isinstance(current_balance, float):
        new_balance = to_minor_units(current_balance, currency)
        
        if dry_run:
            return {
                "player_id": player_id,
                "tenant_id": tenant_id,
                "status": "would_migrate",
                "old_balance": current_balance,
                "new_balance": new_balance,
                "currency": currency,
            }
        
        # Perform migration
        result = await db.users.update_one(
            {"id": player_id},
            {
                "$set": {
                    "wallet_balance": new_balance,
                    "wallet_balance_migrated": True,
                    "wallet_balance_legacy": current_balance,
                    "wallet_balance_migrated_at": datetime.now(timezone.utc).isoformat(),
                }
            }
        )
        
        if result.modified_count > 0:
            return {
                "player_id": player_id,
                "tenant_id": tenant_id,
                "status": "migrated",
                "old_balance": current_balance,
                "new_balance": new_balance,
                "currency": currency,
            }
        else:
            return {
                "player_id": player_id,
                "status": "failed",
                "reason": "update_failed",
            }
    
    # Balance is already integer, just mark as migrated
    if not dry_run:
        await db.users.update_one(
            {"id": player_id},
            {"$set": {"wallet_balance_migrated": True}}
        )
    
    return {
        "player_id": player_id,
        "status": "skipped",
        "reason": "already_integer",
        "current_balance": current_balance,
    }


async def run_migration(dry_run: bool = True, tenant_id: str = None):
    """Run the migration process."""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "gaming_platform")
    
    logger.info(f"Connecting to MongoDB: {db_name}")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Build query
    query = {"role": "player"}
    if tenant_id:
        query["tenant_id"] = tenant_id
        logger.info(f"Filtering by tenant: {tenant_id}")
    
    # Get all players
    players = await db.users.find(query, {"_id": 0}).to_list(None)
    total = len(players)
    
    logger.info(f"Found {total} players to process")
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    stats = {
        "total": total,
        "migrated": 0,
        "would_migrate": 0,
        "skipped": 0,
        "failed": 0,
    }
    
    results = []
    
    for i, player in enumerate(players, 1):
        result = await migrate_player(db, player, dry_run)
        results.append(result)
        
        status = result["status"]
        if status in stats:
            stats[status] += 1
        
        # Log progress every 100 players
        if i % 100 == 0:
            logger.info(f"Processed {i}/{total} players...")
        
        # Log significant changes
        if status in ("migrated", "would_migrate"):
            logger.info(
                f"[{status.upper()}] Player {result['player_id']} ({result.get('tenant_id', 'N/A')}): "
                f"{result['old_balance']} -> {result['new_balance']} {result.get('currency', 'IDR')}"
            )
    
    # Summary
    logger.info("=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total players:    {stats['total']}")
    if dry_run:
        logger.info(f"Would migrate:    {stats['would_migrate']}")
    else:
        logger.info(f"Migrated:         {stats['migrated']}")
    logger.info(f"Skipped:          {stats['skipped']}")
    logger.info(f"Failed:           {stats['failed']}")
    logger.info("=" * 60)
    
    if dry_run and stats["would_migrate"] > 0:
        logger.info("Run without --dry-run to perform actual migration")
    
    return stats, results


def main():
    parser = argparse.ArgumentParser(description="Migrate wallet balances to integer minor units")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="Only migrate players for specific tenant"
    )
    
    args = parser.parse_args()
    
    stats, _ = asyncio.run(run_migration(dry_run=args.dry_run, tenant_id=args.tenant_id))
    
    # Exit with error if any failures
    if stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
