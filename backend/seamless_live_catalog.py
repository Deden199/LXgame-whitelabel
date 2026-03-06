from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from catalog_normalization import clean_text, provider_logo_asset_path, slugify, utc_now_iso
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

GAME_TYPES = ["slot", "casino"]


def normalize_match_name(value: str | None) -> str:
    return slugify(clean_text(value)).replace('-', '')


def resolve_live_provider_code(game: dict[str, Any]) -> str | None:
    provider_code = clean_text(game.get("provider_code")).upper()
    if provider_code in LIVE_PROVIDER_CODE_ALIASES:
        return LIVE_PROVIDER_CODE_ALIASES[provider_code]
    provider_name = clean_text(game.get("provider_name")).upper()
    return LIVE_PROVIDER_NAME_ALIASES.get(provider_name)


async def fetch_live_provider_catalog(adapter: SeamlessAdapter) -> dict[str, Any]:
    providers: dict[str, dict[str, Any]] = {}
    games_by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for game_type in GAME_TYPES:
        provider_response = await adapter.fetch_provider_list(game_type)
        if provider_response.get("status") != 1:
            continue
        for provider in provider_response.get("providers", []):
            code = clean_text(provider.get("code")).upper()
            if not code:
                continue
            providers[code] = {
                "provider_code": code,
                "provider_name": clean_text(provider.get("name")) or code,
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

    results = await asyncio.gather(*(fetch_games(code) for code in providers.keys()))
    for code, games in results:
        games_by_provider[code] = games
    return {"providers": providers, "games_by_provider": games_by_provider}


async def enrich_catalog_with_live_api(db, *, tenant_ids: list[str], adapter: SeamlessAdapter) -> dict[str, Any]:
    live_catalog = await fetch_live_provider_catalog(adapter)
    providers = live_catalog["providers"]
    games_by_provider = live_catalog["games_by_provider"]

    # Build per-provider lookup by code and normalized name.
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
