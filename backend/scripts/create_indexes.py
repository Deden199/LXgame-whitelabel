#!/usr/bin/env python3
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    mongo_url = os.environ.get('MONGO_URL') or os.environ.get('MONGO_URI') or 'mongodb://127.0.0.1:27017'
    db_name = os.environ.get('DB_NAME', 'gaming_platform')
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print(f"Creating indexes on {db_name}...")

    await db.transactions.create_index([('tenant_id', 1), ('tx_id', 1)], unique=True, name='uniq_tenant_tx_id')
    await db.transactions.create_index([('tenant_id', 1), ('player_id', 1)], name='idx_tx_tenant_player')

    await db.users.create_index([('tenant_id', 1), ('role', 1)], name='idx_users_tenant_role')
    await db.users.create_index([('id', 1)], unique=True, name='uniq_user_id')

    await db.games.create_index([('provider_slug', 1)], name='idx_games_provider_slug')
    await db.games.create_index([('tenant_ids', 1)], name='idx_games_tenant_ids')
    await db.games.create_index([('is_enabled', 1)], name='idx_games_is_enabled')

    await db.api_keys.create_index([('key_hash', 1)], unique=True, name='uniq_api_key_hash')
    await db.api_keys.create_index([('tenant_id', 1), ('is_active', 1)], name='idx_api_key_tenant_active')

    # Tenant settings indexes
    try:
        await db.tenant_settings.create_index([('tenant_id', 1)], unique=True, name='uniq_tenant_settings_tenant_id')
        await db.tenant_settings.create_index([('domain.primary_domain', 1)], name='idx_tenant_settings_primary_domain')
        await db.tenant_settings.create_index([('domain.allowed_domains', 1)], name='idx_tenant_settings_allowed_domains')
        print("ok tenant_settings indexes")
    except Exception as exc:
        print(f"skip tenant_settings: {exc}")

    # Risk flags indexes
    try:
        await db.risk_flags.create_index([('tenant_id', 1), ('player_id', 1)], unique=True, name='uniq_risk_flag')
        await db.risk_flags.create_index([('tenant_id', 1), ('flagged', 1)], name='idx_risk_flags_tenant_flagged')
        print("ok risk_flags indexes")
    except Exception as exc:
        print(f"skip risk_flags: {exc}")

    for coll, idx in (
        ('withdrawals', [('tenant_id', 1), ('status', 1)]),
        ('deposits', [('tenant_id', 1), ('status', 1)]),
        ('payment_events', [('event_id', 1)]),
        ('withdrawal_orders', [('tenant_id', 1), ('status', 1)]),
        ('deposit_orders', [('tenant_id', 1), ('status', 1)]),
    ):
        try:
            await db[coll].create_index(idx, name=f'idx_{coll}_main')
            print(f"ok placeholder index {coll}")
        except Exception as exc:
            print(f"skip {coll}: {exc}")

    print('Index creation complete')
    client.close()


if __name__ == '__main__':
    asyncio.run(main())
