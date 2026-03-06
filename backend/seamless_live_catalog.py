from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
import uuid

from catalog_normalization import (
    clean_text,
    normalize_category,
    provider_logo_asset_path,
    slugify,
    utc_now_iso,
)
from providers.seamless_adapter import SeamlessAdapter

LIVE_PROVIDER_CODE_ALIASES = {
    "PP": "PRAGMATIC",
    "PPLIVE": "PPLIVE",
    "ZF_PGSOFT": "PGSOFT",
    "JILI": "JILI",
    "MG": "MICROGAMING",
    "AWC_EVO": "EVOLUTION",
}

LIVE_PROVIDER_NAME_ALIASES = {
    "PRAGMATIC PLAY": "PRAGMATIC",
    "PRAGMATIC PLAY LIVE": "PPLIVE",
    "PG SOFT": "PGSOFT",
    "PGSOFT": "PGSOFT",
    "JILI": "JILI",
    "MICROGAMING": "MICROGAMING",
    "EVOLUTION ASIA": "EVOLUTION",
    "EVOLUTION": "EVOLUTION",
}

DISPLAY_NAME_OVERRIDES = {
    "PRAGMATIC": "Pragmatic Play",
    "PGSOFT": "PG Soft",
    "MICROGAMING": "MicroGaming",
    "PPLIVE": "Pragmatic Play Live",
}

GAME_TYPES = ["slot", "casino"]


def normalize_match_name(value: str | None) -> str:
    return slugify(clean_text(value)).replace("-", "")


def prettify_provider_name(code: str, source_name: str) -> str:
    if code in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[code]
    text = clean_text(source_name)
    if not text:
        return code.title()
    for original, replacement in {
        "PragmaticPlay": "Pragmatic Play",
        "PGSoft": "PG Soft",
        "JiLi": "JILI",
        "TopTrend": "TopTrend",
        "EvoPlay": "EvoPlay",
        "DreamTech": "DreamTech",
        "PlayStar": "PlayStar",
        "RedTiger": "Red Tiger",
        "Booongo": "Booongo",
    }.items():
        if text == original:
            return replacement
    return text


def provider_category_from_type(game_type: str) -> str:
    normalized = clean_text(game_type).lower()
    if normalized == "casino":
        return "live"
    return normalize_category(normalized or "slots")


def build_live_game_id(provider_code: str, game_code: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"seamless-live::{provider_code}::{game_code}"))


def _select_featured_ids(games: list[dict[str, Any]], count: int, seen: set[str], max_per_provider: int = 2) -> set[str]:
    picked: list[str] = []
    provider_counts: dict[str, int] = defaultdict(int)
    for game in games:
        if game["id"] in seen:
            continue
        provider_code = game["provider_code"]
        if provider_counts[provider_code] >= max_per_provider:
            continue
        picked.append(game["id"])
        provider_counts[provider_code] += 1
        if len(picked) >= count:
            break
    return set(picked)


async def fetch_live_provider_catalog(adapter: SeamlessAdapter) -> dict[str, Any]:
    providers: dict[str, dict[str, Any]] = {}
    provider_order: list[str] = []
    games_by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_type in GAME_TYPES:
        provider_response = await adapter.fetch_provider_list(game_type)
        if provider_response.get("status") != 1:
            continue
        for provider in provider_response.get("providers", []):
            code = clean_text(provider.get("code")).upper()
            if not code:
                continue
            if code not in providers:
                provider_order.append(code)
            providers[code] = {
                "provider_code": code,
                "provider_name": prettify_provider_name(code, clean_text(provider.get("name")) or code),
                "game_type": clean_text(provider.get("type")) or game_type,
                "backoffice": clean_text(provider.get("backoffice")),
                "provider_logo_url": provider_logo_asset_path(code),
            }

    async def fetch_games(code: str):
        try:
            response = await adapter.fetch_game_list(code, "en")
            if response.get("status") != 1:
                return code, []
            return code, response.get("games", [])
        except Exception:
            return code, []

    results = await asyncio.gather(*(fetch_games(code) for code in provider_order))
    for code, games in results:
        games_by_provider[code] = games
    return {"providers": providers, "provider_order": provider_order, "games_by_provider": games_by_provider}


async def sync_live_catalog_to_db(db, *, tenant_ids: list[str], adapter: SeamlessAdapter) -> dict[str, Any]:
    live_catalog = await fetch_live_provider_catalog(adapter)
    providers = live_catalog["providers"]
    provider_order = live_catalog["provider_order"]
    games_by_provider = live_catalog["games_by_provider"]

    canonical_games: list[dict[str, Any]] = []
    source_total_games = 0
    source_active_games = 0

    for provider_rank, provider_code in enumerate(provider_order):
        provider = providers[provider_code]
        category = provider_category_from_type(provider["game_type"])
        for game_rank, source_game in enumerate(games_by_provider.get(provider_code, [])):
            source_total_games += 1
            status = int(source_game.get("status") or 0)
            if status != 1:
                continue
            source_active_games += 1
            game_code = clean_text(source_game.get("game_code"))
            game_name = clean_text(source_game.get("game_name")) or game_code
            banner = clean_text(source_game.get("banner"))
            canonical_games.append(
                {
                    "id": build_live_game_id(provider_code, game_code),
                    "name": game_name,
                    "category": category,
                    "provider_id": f"provider_{slugify(provider_code)}",
                    "provider_name": provider["provider_name"],
                    "provider_slug": slugify(provider_code),
                    "provider_logo_url": provider["provider_logo_url"],
                    "thumbnail_url": banner,
                    "source_banner_url": banner,
                    "aggregator": "seamless",
                    "source": "seamless_live_api",
                    "game_launch_id": game_code,
                    "external_game_id": game_code,
                    "provider_code": provider_code,
                    "game_code": game_code,
                    "launch_provider_code": provider_code,
                    "launch_game_code": game_code,
                    "supplier": provider["provider_name"],
                    "platform": "all",
                    "is_active": True,
                    "is_enabled": True,
                    "tenant_ids": tenant_ids,
                    "tags": [],
                    "is_hot": False,
                    "is_new": False,
                    "is_popular": False,
                    "created_at": utc_now_iso(),
                    "updated_at": utc_now_iso(),
                    "description": f"{provider['provider_name']} • {category.title()}",
                    "rtp": 96.0,
                    "volatility": "medium",
                    "min_bet": 0.1,
                    "max_bet": 1000.0,
                    "play_count": 0,
                    "status": "active",
                    "sort": int(source_game.get("sort") or 0),
                    "source_provider_type": provider["game_type"],
                    "source_provider_rank": provider_rank,
                    "source_game_rank": game_rank,
                }
            )

    canonical_games.sort(key=lambda item: (item["source_provider_rank"], item["source_game_rank"], item["name"].lower()))
    featured_pool = [game for game in canonical_games if game.get("source_banner_url")]
    seen_ids: set[str] = set()
    popular_ids = _select_featured_ids(featured_pool, 18, seen_ids, max_per_provider=2)
    seen_ids |= popular_ids
    hot_ids = _select_featured_ids(featured_pool, 18, seen_ids, max_per_provider=2)
    seen_ids |= hot_ids
    new_ids = _select_featured_ids(featured_pool, 18, seen_ids, max_per_provider=2)

    for game in canonical_games:
        game["is_popular"] = game["id"] in popular_ids
        game["is_hot"] = game["id"] in hot_ids
        game["is_new"] = game["id"] in new_ids
        tags = []
        if game["is_hot"]:
            tags.append("Hot")
        if game["is_new"]:
            tags.append("New")
        if game["is_popular"]:
            tags.append("Popular")
        game["tags"] = tags

    active_ids = {game["id"] for game in canonical_games}
    stale_removed = 0
    cursor = db.games.find({"tenant_ids": {"$in": tenant_ids}}, {"_id": 0, "id": 1, "tenant_ids": 1})
    async for existing in cursor:
        if existing["id"] in active_ids:
            continue
        remaining = [item for item in existing.get("tenant_ids", []) if item not in tenant_ids]
        update_payload = {"tenant_ids": remaining, "updated_at": utc_now_iso()}
        if not remaining:
            update_payload.update({"is_active": False, "is_enabled": False})
        await db.games.update_one({"id": existing["id"]}, {"$set": update_payload})
        stale_removed += 1

    inserted_games = 0
    updated_games = 0
    for provider_code, provider in providers.items():
        active_provider_games = [game for game in canonical_games if game["provider_code"] == provider_code]
        await db.providers.update_one(
            {"code": provider_code},
            {
                "$set": {
                    "id": f"provider_{slugify(provider_code)}",
                    "code": provider_code,
                    "name": provider["provider_name"],
                    "slug": slugify(provider_code),
                    "logo_url": provider["provider_logo_url"],
                    "provider_logo_url": provider["provider_logo_url"],
                    "gameCount": len(active_provider_games),
                    "categories": sorted({game["category"] for game in active_provider_games}),
                    "aggregator": "seamless",
                    "is_active": True,
                    "updated_at": utc_now_iso(),
                },
                "$setOnInsert": {"created_at": utc_now_iso()},
            },
            upsert=True,
        )

    for game in canonical_games:
        existing = await db.games.find_one({"id": game["id"]}, {"_id": 0, "id": 1, "created_at": 1})
        payload = dict(game)
        payload["updated_at"] = utc_now_iso()
        payload["created_at"] = existing.get("created_at") if existing and existing.get("created_at") else payload["created_at"]
        if existing:
            await db.games.update_one({"id": game["id"]}, {"$set": payload})
            updated_games += 1
        else:
            await db.games.insert_one(payload)
            inserted_games += 1

    category_names = sorted({game["category"] for game in canonical_games})
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
        "provider_count": len(providers),
        "source_total_games": source_total_games,
        "active_games": len(canonical_games),
        "inserted_games": inserted_games,
        "updated_games": updated_games,
        "stale_removed": stale_removed,
        "real_banner_enriched_games": sum(1 for game in canonical_games if game.get("source_banner_url")),
        "fallback_only_games": sum(1 for game in canonical_games if not game.get("source_banner_url")),
        "featured_counts": {
            "popular": len(popular_ids),
            "hot": len(hot_ids),
            "new": len(new_ids),
        },
        "tenant_ids": tenant_ids,
        "source": "seamless_live_api",
        "completed_at": utc_now_iso(),
    }
    await db.catalog_import_runs.insert_one(
        {
            "id": f"live-sync-{utc_now_iso()}",
            "tenant_ids": tenant_ids,
            "summary": summary,
            "source": "seamless_live_api",
            "created_at": utc_now_iso(),
        }
    )
    return summary


async def enrich_catalog_with_live_api(db, *, tenant_ids: list[str], adapter: SeamlessAdapter) -> dict[str, Any]:
    live_catalog = await fetch_live_provider_catalog(adapter)
    providers = live_catalog["providers"]
    games_by_provider = live_catalog["games_by_provider"]

    provider_game_indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for provider_code, games in games_by_provider.items():
        index: dict[str, dict[str, Any]] = {}
        for game in games:
            code_key = clean_text(game.get("game_code"))
            if code_key:
                index[code_key.lower()] = game
            name_key = normalize_match_name(game.get("game_name"))
            if name_key and name_key not in index:
                index[name_key] = game
        provider_game_indexes[provider_code] = index

    updated_games = 0
    updated_providers = 0
    unmatched_games = 0

    for provider_code, provider in providers.items():
        result = await db.providers.update_many(
            {"$or": [{"code": provider_code}, {"live_provider_code": provider_code}]},
            {"$set": {
                "live_provider_code": provider_code,
                "live_provider_name": provider["provider_name"],
                "provider_logo_url": provider["provider_logo_url"],
                "logo_url": provider["provider_logo_url"],
                "updated_at": utc_now_iso(),
            }},
        )
        updated_providers += result.modified_count

    query = {"is_active": True, "tenant_ids": {"$in": tenant_ids}}
    cursor = db.games.find(query, {"_id": 0})
    async for game in cursor:
        live_provider_code = resolve_live_provider_code(game)
        if not live_provider_code or live_provider_code not in provider_game_indexes:
            unmatched_games += 1
            continue
        index = provider_game_indexes[live_provider_code]
        direct_code_key = clean_text(game.get("game_code") or game.get("game_launch_id") or game.get("external_game_id")).lower()
        name_key = normalize_match_name(game.get("name"))
        live_game = index.get(direct_code_key) or index.get(name_key)
        if not live_game:
            unmatched_games += 1
            continue

        update_payload = {
            "live_provider_code": live_provider_code,
            "live_provider_name": providers[live_provider_code]["provider_name"],
            "launch_provider_code": live_provider_code,
            "launch_game_code": clean_text(live_game.get("game_code")) or direct_code_key,
            "thumbnail_url": clean_text(live_game.get("banner")) or game.get("thumbnail_url"),
            "source_banner_url": clean_text(live_game.get("banner")) or None,
            "provider_logo_url": providers[live_provider_code]["provider_logo_url"],
            "updated_at": utc_now_iso(),
        }
        await db.games.update_one({"id": game["id"]}, {"$set": update_payload})
        updated_games += 1

    summary = {
        "updated_games": updated_games,
        "updated_providers": updated_providers,
        "unmatched_games": unmatched_games,
        "live_provider_count": len(providers),
        "provider_codes": sorted(providers.keys()),
    }
    await db.catalog_import_runs.insert_one(
        {
            "id": f"live-enrichment-{utc_now_iso()}",
            "tenant_ids": tenant_ids,
            "summary": summary,
            "source": "seamless_live_api",
            "created_at": utc_now_iso(),
        }
    )
    return summary


def resolve_live_provider_code(game: dict[str, Any]) -> str | None:
    provider_code = clean_text(game.get("provider_code")).upper()
    if provider_code in LIVE_PROVIDER_CODE_ALIASES:
        return LIVE_PROVIDER_CODE_ALIASES[provider_code]
    provider_name = clean_text(game.get("provider_name")).upper()
    return LIVE_PROVIDER_NAME_ALIASES.get(provider_name)
