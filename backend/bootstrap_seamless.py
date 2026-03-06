from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from auth import hash_password
from catalog_sync import sync_catalog_to_db
from finance.models import DEFAULT_BUFFER_MIN_THRESHOLD_MINOR

DEFAULT_WORKBOOK_PATH = "/app/downloads/EGS_Game_List_Staging.xlsx"


def _env_or_fallback(*values: str | None) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _seamless_config(agent_code: str, default_currency: str = "PHP") -> dict:
    resolved_agent_code = _env_or_fallback(
        os.environ.get(f"SEAMLESS_AGENT_CODE_{agent_code.upper()}"),
        os.environ.get("SEAMLESS_AGENT_CODE"),
        agent_code,
    )
    resolved_agent_token = _env_or_fallback(
        os.environ.get(f"SEAMLESS_AGENT_TOKEN_{agent_code.upper()}"),
        os.environ.get("SEAMLESS_AGENT_TOKEN"),
    )
    resolved_agent_secret = _env_or_fallback(
        os.environ.get(f"SEAMLESS_AGENT_SECRET_{agent_code.upper()}"),
        os.environ.get("SEAMLESS_AGENT_SECRET"),
        f"{agent_code}_secret",
    )
    return {
        "enabled": True,
        "api_base_url": _env_or_fallback(os.environ.get("SEAMLESS_API_BASE_URL"), "https://svc-v1.lunexa.to"),
        "agent_code": resolved_agent_code,
        "agent_token": resolved_agent_token or "",
        "agent_secret": resolved_agent_secret,
        "default_currency": _env_or_fallback(os.environ.get("SEAMLESS_DEFAULT_CURRENCY"), default_currency) or default_currency,
        "language": _env_or_fallback(os.environ.get("SEAMLESS_DEFAULT_LANGUAGE"), "en") or "en",
        "timeout_seconds": int(_env_or_fallback(os.environ.get("SEAMLESS_TIMEOUT_SECONDS"), "20") or "20"),
    }


async def bootstrap_default_platform_data(db, workbook_path: str = DEFAULT_WORKBOOK_PATH) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    tenants = [
        {
            "id": "tenant_aurum_001",
            "name": "AurumBet",
            "slug": "aurumbet",
            "theme_preset": "royal_gold",
            "branding": {},
            "status": "active",
            "is_active": True,
            "provider_config": {"seamless": _seamless_config("aurumbet")},
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "tenant_bluewave_001",
            "name": "BlueWave Gaming",
            "slug": "bluewave",
            "theme_preset": "midnight_blue",
            "branding": {},
            "status": "active",
            "is_active": True,
            "provider_config": {"seamless": _seamless_config("bluewave")},
            "created_at": now,
            "updated_at": now,
        },
    ]
    for tenant in tenants:
        await db.tenants.update_one({"id": tenant["id"]}, {"$set": tenant}, upsert=True)
    initial_buffer = DEFAULT_BUFFER_MIN_THRESHOLD_MINOR * 2
    for tenant in tenants:
        await db.tenant_finance.update_one(
            {"tenant_id": tenant["id"]},
            {
                "$set": {
                    "tenant_id": tenant["id"],
                    "buffer_balance_minor": initial_buffer,
                    "buffer_min_threshold_minor": DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
                    "is_frozen": False,
                    "frozen_reason": None,
                    "frozen_at": None,
                    "ggr_share_percent": 15.0,
                    "infra_fee_monthly_minor": 5_000_000,
                    "setup_fee_minor": DEFAULT_BUFFER_MIN_THRESHOLD_MINOR,
                    "setup_fee_mode": "ACTIVATION_DEPOSIT",
                    "setup_fee_paid": True,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )


    users = [
        {
            "id": "user_superadmin_001",
            "tenant_id": "system",
            "email": "admin@platform.com",
            "password_hash": hash_password("admin123"),
            "role": "super_admin",
            "display_name": "Platform Admin",
            "wallet_balance": 0,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        {
            "id": "user_admin_aurum_001",
            "tenant_id": "tenant_aurum_001",
            "email": "admin@aurumbet.com",
            "password_hash": hash_password("admin123"),
            "role": "tenant_admin",
            "display_name": "Aurum Admin",
            "wallet_balance": 0,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        {
            "id": "user_admin_bluewave_001",
            "tenant_id": "tenant_bluewave_001",
            "email": "admin@bluewave.com",
            "password_hash": hash_password("admin123"),
            "role": "tenant_admin",
            "display_name": "BlueWave Admin",
            "wallet_balance": 0,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        {
            "id": "player_aurumbet_001",
            "tenant_id": "tenant_aurum_001",
            "email": "player1@aurumbet.demo",
            "password_hash": hash_password("player123"),
            "role": "player",
            "display_name": "Aurum Player",
            "wallet_balance": 250000,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
        {
            "id": "player_bluewave_001",
            "tenant_id": "tenant_bluewave_001",
            "email": "player1@bluewave.demo",
            "password_hash": hash_password("player123"),
            "role": "player",
            "display_name": "BlueWave Player",
            "wallet_balance": 250000,
            "avatar_url": None,
            "is_active": True,
            "created_at": now,
            "last_login": None,
        },
    ]
    for user in users:
        await db.users.update_one({"id": user["id"]}, {"$set": user}, upsert=True)

    for player in [user for user in users if user["role"] == "player"]:
        preferred_currency = (tenants[0]["provider_config"]["seamless"].get("default_currency") if player["tenant_id"] == "tenant_aurum_001" else tenants[1]["provider_config"]["seamless"].get("default_currency"))
        await db.player_stats.update_one(
            {"player_id": player["id"]},
            {
                "$set": {
                    "tenant_id": player["tenant_id"],
                    "total_bets": 0,
                    "total_wins": 0,
                    "games_played": 0,
                    "total_sessions": 0,
                    "recent_games": [],
                    "favorite_category": None,
                    "deposit_limit": None,
                    "session_reminder_enabled": True,
                    "preferred_currency": preferred_currency,
                    "wallet_currency": preferred_currency,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    summary = await sync_catalog_to_db(
        db,
        workbook_path=workbook_path,
        tenant_ids=[tenant["id"] for tenant in tenants],
        replace_existing=True,
        source="seamless_bootstrap",
    )
    return {
        "tenants": [tenant["slug"] for tenant in tenants],
        "players": [user["email"] for user in users if user["role"] == "player"],
        "summary": summary,
        "workbook_path": workbook_path,
    }
