from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from catalog_normalization import canonicalize_game_doc, load_catalog_from_workbook, utc_now_iso


async def _deactivate_stale_games(db, tenant_ids: list[str], active_game_ids: set[str]) -> int:
    affected = 0
    for tenant_id in tenant_ids:
        cursor = db.games.find({"tenant_ids": tenant_id}, {"_id": 0, "id": 1, "tenant_ids": 1})
        async for game in cursor:
            if game["id"] in active_game_ids:
                continue
            remaining_tenants = [item for item in game.get("tenant_ids", []) if item != tenant_id]
            update_payload: dict[str, Any] = {
                "tenant_ids": remaining_tenants,
                "updated_at": utc_now_iso(),
            }
            if not remaining_tenants:
                update_payload.update({"is_active": False, "is_enabled": False})
            await db.games.update_one({"id": game["id"]}, {"$set": update_payload})
            affected += 1
    return affected


async def sync_catalog_to_db(
    db,
    *,
    workbook_path: str,
    tenant_ids: list[str],
    replace_existing: bool = True,
    source: str = "seamless_excel",
) -> dict[str, Any]:
    if not tenant_ids:
        raise ValueError("tenant_ids is required for catalog sync")

    catalog = load_catalog_from_workbook(workbook_path, tenant_key=",".join(tenant_ids))
    games = [canonicalize_game_doc({**game, "tenant_ids": tenant_ids, "source": source}) for game in catalog["games"]]
    providers = catalog["providers"]

    inserted_games = 0
    updated_games = 0
    inserted_providers = 0
    updated_providers = 0
    active_game_ids = {game["id"] for game in games}

    if replace_existing:
        deactivated_games = await _deactivate_stale_games(db, tenant_ids, active_game_ids)
    else:
        deactivated_games = 0

    for provider in providers:
        provider_doc = {
            "id": provider.get("id") or f"provider_{provider['slug']}",
            "code": provider["code"],
            "name": provider["name"],
            "slug": provider["slug"],
            "logo_url": provider["logo_url"],
            "source_logo_ref": provider.get("source_logo_ref"),
            "source_icon_ref": provider.get("source_icon_ref"),
            "wallet_type": provider.get("wallet_type", "Seamless"),
            "supported_currencies": provider.get("supported_currencies", []),
            "aggregator": provider.get("aggregator", "seamless"),
            "is_active": True,
            "updated_at": utc_now_iso(),
        }
        existing = await db.providers.find_one({"code": provider["code"]}, {"_id": 0, "id": 1})
        if existing:
            await db.providers.update_one({"code": provider["code"]}, {"$set": provider_doc})
            updated_providers += 1
        else:
            await db.providers.insert_one({**provider_doc, "created_at": utc_now_iso()})
            inserted_providers += 1

    for game in games:
        existing = await db.games.find_one({"id": game["id"]}, {"_id": 0, "id": 1, "tenant_ids": 1, "created_at": 1})
        if existing:
            merged_tenants = sorted(set(existing.get("tenant_ids", [])) | set(tenant_ids))
            game_doc = {
                **game,
                "tenant_ids": merged_tenants,
                "created_at": existing.get("created_at") or game.get("created_at") or utc_now_iso(),
                "updated_at": utc_now_iso(),
            }
            await db.games.update_one({"id": game["id"]}, {"$set": game_doc})
            updated_games += 1
        else:
            game_doc = {**game, "tenant_ids": tenant_ids, "created_at": game.get("created_at") or utc_now_iso(), "updated_at": utc_now_iso()}
            await db.games.insert_one(game_doc)
            inserted_games += 1

    category_names = sorted({game["category"] for game in games})
    for index, category in enumerate(category_names, start=1):
        await db.game_categories.update_one(
            {"slug": category},
            {
                "$set": {
                    "id": category,
                    "name": category.title(),
                    "slug": category,
                    "order": index,
                    "is_active": True,
                    "updated_at": utc_now_iso(),
                },
                "$setOnInsert": {"created_at": utc_now_iso()},
            },
            upsert=True,
        )

    summary = {
        **catalog["summary"],
        "tenant_ids": tenant_ids,
        "inserted_games": inserted_games,
        "updated_games": updated_games,
        "deactivated_games": deactivated_games,
        "inserted_providers": inserted_providers,
        "updated_providers": updated_providers,
        "source": source,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.catalog_import_runs.insert_one(
        {
            "id": f"import_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "workbook_path": workbook_path,
            "tenant_ids": tenant_ids,
            "summary": summary,
            "created_at": utc_now_iso(),
        }
    )

    return summary
