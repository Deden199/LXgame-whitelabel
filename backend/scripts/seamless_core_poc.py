#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from bootstrap_seamless import bootstrap_default_platform_data
from catalog_normalization import canonicalize_game_doc, load_catalog_from_workbook
from providers.seamless_adapter import create_seamless_adapter_for_tenant
from providers.seamless_callbacks import (
    SeamlessCallbackHandler,
    SeamlessGameCallbackRequest,
    SeamlessMoneyCallbackRequest,
    SeamlessUserBalanceRequest,
)

load_dotenv(ROOT_DIR / '.env')
WORKBOOK_PATH = "/app/downloads/EGS_Game_List_Staging.xlsx"


async def ensure_poc_player(db, tenant_id: str, currency: str) -> dict:
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    player = {
        "id": f"poc_player_{tenant_id}",
        "tenant_id": tenant_id,
        "email": f"poc+{tenant_id}@looxgame.local",
        "password_hash": "poc_only",
        "role": "player",
        "display_name": f"POC {tenant_id}",
        "wallet_balance": 5000,
        "avatar_url": None,
        "is_active": True,
        "created_at": now,
        "last_login": None,
    }
    await db.users.update_one({"id": player["id"]}, {"$set": player}, upsert=True)
    await db.player_stats.update_one(
        {"player_id": player["id"]},
        {"$set": {"tenant_id": tenant_id, "preferred_currency": currency, "wallet_currency": currency, "updated_at": now}},
        upsert=True,
    )
    return player


async def main() -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "gaming_platform")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not configured")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    try:
        bootstrap_summary = await bootstrap_default_platform_data(db, WORKBOOK_PATH)
        print("BOOTSTRAP", json.dumps(bootstrap_summary, indent=2))

        catalog = load_catalog_from_workbook(WORKBOOK_PATH, tenant_key="tenant_aurum_001")
        assert catalog["summary"]["total_source_rows"] >= 4000, "Expected workbook to contain 4000+ source rows"
        assert catalog["summary"]["provider_count"] >= 40, "Expected 40+ providers"

        sample_game = canonicalize_game_doc(catalog["games"][0])
        required_fields = [
            "id",
            "name",
            "category",
            "provider_id",
            "provider_name",
            "provider_slug",
            "provider_logo_url",
            "thumbnail_url",
            "aggregator",
            "source",
            "game_launch_id",
            "external_game_id",
            "provider_code",
            "game_code",
            "supplier",
            "platform",
            "is_active",
            "is_enabled",
            "tenant_ids",
            "tags",
            "is_hot",
            "is_new",
            "is_popular",
            "created_at",
        ]
        missing_fields = [field for field in required_fields if field not in sample_game]
        assert not missing_fields, f"Missing canonical fields: {missing_fields}"
        print("NORMALIZATION_SAMPLE", json.dumps({key: sample_game[key] for key in required_fields}, indent=2, default=str))

        tenant = await db.tenants.find_one({"slug": "aurumbet"}, {"_id": 0})
        assert tenant, "Expected aurumbet tenant after bootstrap"
        seamless_config = tenant.get("provider_config", {}).get("seamless", {})
        player = await ensure_poc_player(db, tenant["id"], seamless_config.get("default_currency", "PHP"))
        game = await db.games.find_one({"tenant_ids": tenant["id"], "is_active": True}, {"_id": 0})
        assert game, "Expected at least one imported game"

        adapter = create_seamless_adapter_for_tenant(tenant.get("provider_config", {}))
        assert adapter is not None, "Seamless adapter should be creatable from tenant config"
        launch_preview = adapter.launch_contract_preview(
            user_code=player["id"],
            user_balance=player["wallet_balance"],
            provider_code=game["provider_code"],
            game_code=game.get("game_code") or game.get("game_launch_id"),
            category=game["category"],
            language=seamless_config.get("language", "en"),
        )
        assert launch_preview["payload"]["provider_code"] == game["provider_code"]
        assert launch_preview["payload"]["game_code"] == (game.get("game_code") or game.get("game_launch_id"))
        print("LAUNCH_PREVIEW", json.dumps(launch_preview, indent=2))

        handler = SeamlessCallbackHandler(
            db,
            tenant_id=tenant["id"],
            agent_code=seamless_config["agent_code"],
            agent_secret=seamless_config["agent_secret"],
            currency=seamless_config.get("default_currency", "PHP"),
        )

        balance_req = SeamlessUserBalanceRequest(
            agent_code=seamless_config["agent_code"],
            agent_secret=seamless_config["agent_secret"],
            user_code=player["id"],
        )
        balance_response = await handler.handle_user_balance(balance_req)
        assert balance_response["status"] == 1
        starting_balance = balance_response["user_balance"]
        print("BALANCE_RESPONSE", json.dumps(balance_response, indent=2))

        callback_req = SeamlessGameCallbackRequest(
            agent_code=seamless_config["agent_code"],
            agent_secret=seamless_config["agent_secret"],
            user_code=player["id"],
            game_type="slot",
            slot={
                "provider_code": game["provider_code"],
                "game_code": game.get("game_code") or game.get("game_launch_id"),
                "round_id": "poc-round-001",
                "is_round_finished": True,
                "type": "BASE",
                "bet": 100,
                "win": 25,
                "txn_id": "poc-txn-001",
                "txn_type": "debit_credit",
                "user_before_balance": starting_balance,
                "user_after_balance": starting_balance - 75,
                "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            },
        )
        callback_response = await handler.handle_game_callback(callback_req)
        replay_response = await handler.handle_game_callback(callback_req)
        assert callback_response["status"] == 1
        assert replay_response["status"] == 1
        assert replay_response["user_balance"] == callback_response["user_balance"]
        assert replay_response.get("idempotent") is True
        print("GAME_CALLBACK_RESPONSE", json.dumps(callback_response, indent=2))
        print("GAME_CALLBACK_REPLAY", json.dumps(replay_response, indent=2))

        money_req = SeamlessMoneyCallbackRequest(
            agent_code=seamless_config["agent_code"],
            agent_secret=seamless_config["agent_secret"],
            user_code=player["id"],
            provider_code=game["provider_code"],
            game_code=game.get("game_code") or game.get("game_launch_id"),
            type="credit",
            amount=50,
            user_before_balance=callback_response["user_balance"],
            user_after_balance=callback_response["user_balance"] + 50,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        )
        money_response = await handler.handle_money_callback(money_req)
        money_replay = await handler.handle_money_callback(money_req)
        assert money_response["status"] == 1
        assert money_replay["status"] == 1
        print("MONEY_CALLBACK_RESPONSE", json.dumps(money_response, indent=2))
        print("MONEY_CALLBACK_REPLAY", json.dumps(money_replay, indent=2))

        print("POC_RESULT", json.dumps({
            "normalization": "passed",
            "launch_contract": "validated",
            "launch_mode": launch_preview["mode"],
            "callback_idempotency": "passed",
            "callback_auth": "validated_via_agent_secret",
        }, indent=2))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
