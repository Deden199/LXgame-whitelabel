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

from catalog_sync import sync_catalog_to_db

load_dotenv(ROOT_DIR / '.env')
DEFAULT_WORKBOOK_PATH = "/app/downloads/EGS_Game_List_Staging.xlsx"


async def resolve_tenant_ids(db, tenant_identifiers: list[str]) -> list[str]:
    tenant_ids: list[str] = []
    for identifier in tenant_identifiers:
        tenant = await db.tenants.find_one(
            {"$or": [{"id": identifier}, {"slug": identifier}]},
            {"_id": 0, "id": 1},
        )
        if not tenant:
            raise ValueError(f"Tenant not found: {identifier}")
        tenant_ids.append(tenant["id"])
    return tenant_ids


async def main_async(args: argparse.Namespace) -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gaming_platform")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not configured")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    try:
        tenant_ids = await resolve_tenant_ids(db, [item.strip() for item in args.tenants.split(",") if item.strip()])
        summary = await sync_catalog_to_db(
            db,
            workbook_path=args.file,
            tenant_ids=tenant_ids,
            replace_existing=not args.no_replace,
            source="seamless_cli_sync",
        )
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync seamless catalog from Excel into MongoDB")
    parser.add_argument("--tenants", required=True, help="Comma-separated tenant ids or slugs (e.g. aurumbet,bluewave)")
    parser.add_argument("--file", default=DEFAULT_WORKBOOK_PATH, help=f"Workbook path (default: {DEFAULT_WORKBOOK_PATH})")
    parser.add_argument("--no-replace", action="store_true", help="Do not remove stale tenant catalog entries")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args)))
