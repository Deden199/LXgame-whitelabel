#!/usr/bin/env python3
"""
Compatibility shim for the legacy VD7/EGS Excel replacement command.

This script remains only so older operator runbooks do not break.
It now delegates to the normalized seamless catalog sync flow backed by
`catalog_sync.sync_catalog_to_db` and the attached source workbook.

Preferred command for new operations:
    python /app/backend/scripts/sync_seamless_catalog_from_excel.py --tenants aurumbet,bluewave
"""

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

from catalog_normalization import load_catalog_from_workbook
from catalog_sync import sync_catalog_to_db

load_dotenv(ROOT_DIR / '.env')
DEFAULT_EXCEL_PATH = "/app/downloads/EGS_Game_List_Staging.xlsx"


async def resolve_tenant_id(db, identifier: str) -> str:
    tenant = await db.tenants.find_one({"$or": [{"id": identifier}, {"slug": identifier}]}, {"_id": 0, "id": 1})
    if not tenant:
        raise ValueError(f"Tenant not found: {identifier}")
    return tenant["id"]


async def main_async(args: argparse.Namespace) -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gaming_platform")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not configured")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    try:
        tenant_id = await resolve_tenant_id(db, args.tenant)
        if args.dry_run:
            summary = load_catalog_from_workbook(args.file, tenant_key=tenant_id)["summary"]
            print(json.dumps({"mode": "dry_run", "tenant_id": tenant_id, **summary}, indent=2))
            return 0

        summary = await sync_catalog_to_db(
            db,
            workbook_path=args.file,
            tenant_ids=[tenant_id],
            replace_existing=True,
            source="legacy_vd7_shim",
        )
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compatibility shim for legacy VD7/EGS catalog replacement")
    parser.add_argument("--tenant", required=True, help="Tenant id or slug")
    parser.add_argument("--file", default=DEFAULT_EXCEL_PATH, help=f"Workbook path (default: {DEFAULT_EXCEL_PATH})")
    parser.add_argument("--dry-run", action="store_true", help="Print normalized import summary without writing to DB")
    return parser


if __name__ == "__main__":
    parser = build_parser()
    raise SystemExit(asyncio.run(main_async(parser.parse_args())))
