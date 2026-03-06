#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from providers.seamless_adapter import SeamlessAdapter
from seamless_live_catalog import enrich_catalog_with_live_api

load_dotenv(ROOT_DIR / '.env')


async def resolve_tenant_ids(db, raw_tenants: str) -> list[str]:
    tenant_ids = []
    for identifier in [item.strip() for item in raw_tenants.split(',') if item.strip()]:
        tenant = await db.tenants.find_one({"$or": [{"id": identifier}, {"slug": identifier}]}, {"_id": 0, "id": 1})
        if not tenant:
            raise ValueError(f"Tenant not found: {identifier}")
        tenant_ids.append(tenant["id"])
    return tenant_ids


async def main_async(args: argparse.Namespace) -> int:
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME', 'gaming_platform')
    if not mongo_url:
        raise RuntimeError('MONGO_URL is not configured')

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    try:
        tenant_ids = await resolve_tenant_ids(db, args.tenants)
        adapter = SeamlessAdapter()
        summary = await enrich_catalog_with_live_api(db, tenant_ids=tenant_ids, adapter=adapter)
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Enrich seamless catalog from live provider API')
    parser.add_argument('--tenants', required=True, help='Comma-separated tenant slugs or ids')
    return parser


if __name__ == '__main__':
    parser = build_parser()
    raise SystemExit(asyncio.run(main_async(parser.parse_args())))
