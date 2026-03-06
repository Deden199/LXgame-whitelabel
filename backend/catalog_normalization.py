from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Any, Iterable

CANONICAL_CATEGORY_ORDER = [
    "all",
    "slots",
    "live",
    "table",
    "arcade",
    "crash",
    "fishing",
    "sports",
    "lottery",
    "poker",
    "other",
]

NON_GAME_SHEETS = {"Provider List", "All game icon"}
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
PROVIDER_GRADIENTS = [
    ("#0f172a", "#2563eb"),
    ("#111827", "#7c3aed"),
    ("#1f2937", "#0ea5e9"),
    ("#3f1d38", "#db2777"),
    ("#3f2415", "#f59e0b"),
    ("#0f3d2e", "#10b981"),
    ("#312e81", "#6366f1"),
    ("#3b0764", "#c026d3"),
]

PROVIDER_NAME_OVERRIDES = {
    "AWC_EVO": "Evolution Asia",
    "AVIATRIX": "Aviatrix",
    "BBG": "Barbarabang",
    "BOOMING": "Booming",
    "BS": "Betsolutions",
    "FC": "FA CHAI",
    "GAP_CRASH88": "Crash88",
    "GAP_MAC88": "MAC 88",
    "GAP_RG": "Royal Gaming",
    "IDNSLOTS": "IDN Slots",
    "KM": "Kingmaker",
    "LLG": "Lady Luck Games",
    "MG": "MicroGaming",
    "MS": "Micro Slot",
    "NIVO_EVO": "Nivo Games Evolution",
    "PAS": "Peter and Sons",
    "PATEPLAY": "Pate Play",
    "PP": "Pragmatic Play",
    "PPLIVE": "Pragmatic Play Live",
    "SA": "SA Gaming",
    "Sexy_Bacarrat": "Sexy Baccarat",
    "VOLTENT": "Voltent",
    "WF": "Winfinity",
    "XPG": "XProgaming",
    "ZF_ALIZE": "Alize",
    "ZF_PGSOFT": "PG Soft",
}


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u00a0", " ").replace("\t", " ").replace("\n", " ").strip()
    if text.lower() == "nan":
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def slugify(value: str, fallback: str = "other") -> str:
    text = clean_text(value).lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or fallback


def stable_uuid(*parts: Any) -> str:
    material = "::".join(clean_text(part) for part in parts if clean_text(part))
    return str(uuid.uuid5(uuid.NAMESPACE_URL, material))


def normalize_provider_code(value: Any, fallback: str = "UNKNOWN") -> str:
    code = clean_text(value).replace(" ", "_")
    code = re.sub(r"[^A-Za-z0-9_]+", "_", code)
    code = re.sub(r"_+", "_", code).strip("_")
    return code.upper() or fallback


def provider_slug(provider_code: str, provider_name: str | None = None) -> str:
    if provider_code:
        return slugify(provider_code)
    return slugify(provider_name or "provider")


def normalize_provider_name(
    provider_code: str,
    provider_name: Any = None,
    supplier: Any = None,
    provider_directory: dict[str, dict[str, Any]] | None = None,
) -> str:
    override_name = PROVIDER_NAME_OVERRIDES.get(provider_code)
    if override_name:
        return override_name
    if provider_directory and provider_code in provider_directory:
        directory_name = clean_text(provider_directory[provider_code].get("name"))
        if directory_name:
            return directory_name
    candidate = clean_text(provider_name)
    if candidate:
        return candidate
    supplier_candidate = clean_text(supplier)
    if supplier_candidate and supplier_candidate != provider_code:
        return supplier_candidate
    return provider_code.replace("_", " ").title()


def normalize_category(raw_category: Any) -> str:
    raw = clean_text(raw_category).lower()
    if not raw:
        return "other"

    normalized = raw.replace("&", " and ")
    checks: list[tuple[tuple[str, ...], str]] = [
        (("fish", "fishing", "\u6355\u9c7c"), "fishing"),
        (("crash", "aviator"), "crash"),
        (("sport", "bookmaker", "exchange", "fancy bet", "virtual sports"), "sports"),
        (("lottery", "bingo", "keno", "number game"), "lottery"),
        (("poker",), "poker"),
        (("live", "hall"), "live"),
        (("roulette", "blackjack", "baccarat", "sicbo", "dragon tiger", "andar bahar", "table", "card game", "card", "casino"), "table"),
        (("arcade", "mini", "virtual", "casual", "instaplay", "pachinko", "lobby", "scratch", "provably fair", "color game", "indian games"), "arcade"),
        (("slot", "video", "cascading", "megaways", "\u8001\u864e\u673a", "3*3"), "slots"),
    ]

    for keywords, category in checks:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other"


def derive_game_type(category: str) -> str:
    if category in {"live", "table", "poker"}:
        return "casino"
    if category == "sports":
        return "sports"
    if category == "lottery":
        return "lottery"
    return "slot"


def normalize_platform(raw_platform: Any) -> str:
    raw = clean_text(raw_platform).lower()
    if not raw:
        return "all"
    has_desktop = "desktop" in raw or "pc" in raw or "web" in raw
    has_mobile = "mobile" in raw or "h5" in raw or "android" in raw or "ios" in raw
    if has_desktop and has_mobile:
        return "all"
    if has_mobile:
        return "mobile"
    if has_desktop:
        return "desktop"
    return "all"


def normalize_rtp(value: Any) -> float | None:
    raw = clean_text(value).replace("%", "")
    if not raw:
        return None
    try:
        numeric = float(raw)
    except ValueError:
        return None
    if numeric <= 1.0:
        numeric *= 100
    return round(numeric, 2)


def normalize_volatility(value: Any) -> str | None:
    raw = clean_text(value)
    if not raw:
        return None
    return raw.lower()


def looks_like_direct_image_url(value: Any) -> bool:
    url = clean_text(value)
    if not url:
        return False
    lowered = url.lower()
    if lowered.startswith("/api/assets/"):
        return True
    if lowered.startswith("/") and any(lowered.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    if not lowered.startswith(("http://", "https://")):
        return False
    if any(ext in lowered for ext in IMAGE_EXTENSIONS):
        return True
    if "drive.google.com/drive/folders" in lowered or "docs.google.com/spreadsheets" in lowered:
        return False
    if "canto.global/v/" in lowered:
        return False
    return False


def _gradient_for(provider_code: str) -> tuple[str, str]:
    code = normalize_provider_code(provider_code)
    index = int(hashlib.sha256(code.encode("utf-8")).hexdigest(), 16) % len(PROVIDER_GRADIENTS)
    return PROVIDER_GRADIENTS[index]


def provider_logo_asset_path(provider_code: str) -> str:
    return f"/api/assets/providers/{slugify(provider_code)}.svg"


def game_thumbnail_asset_path(provider_code: str, game_code: str) -> str:
    return f"/api/assets/games/{slugify(provider_code)}/{slugify(game_code)}.svg"


def render_provider_logo_svg(provider_code: str, provider_name: str | None = None) -> str:
    start, end = _gradient_for(provider_code)
    code = escape(normalize_provider_code(provider_code)[:12])
    name = escape(normalize_provider_name(normalize_provider_code(provider_code), provider_name)[:26])
    initials = escape("".join(part[0] for part in name.split()[:2]).upper() or code[:2])
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="0 0 240 240" fill="none">
  <defs>
    <linearGradient id="logoGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{start}" />
      <stop offset="100%" stop-color="{end}" />
    </linearGradient>
  </defs>
  <rect width="240" height="240" rx="40" fill="url(#logoGradient)" />
  <rect x="18" y="18" width="204" height="204" rx="32" fill="rgba(255,255,255,0.06)" />
  <circle cx="120" cy="90" r="42" fill="rgba(255,255,255,0.12)" />
  <text x="120" y="104" fill="#ffffff" font-size="32" font-weight="800" text-anchor="middle" font-family="Inter, Arial, sans-serif">{initials}</text>
  <text x="120" y="162" fill="#ffffff" font-size="16" font-weight="700" text-anchor="middle" font-family="Inter, Arial, sans-serif">{name}</text>
  <text x="120" y="188" fill="rgba(255,255,255,0.72)" font-size="12" font-weight="600" text-anchor="middle" font-family="Inter, Arial, sans-serif">{code}</text>
</svg>
""".strip()


def render_game_thumbnail_svg(provider_code: str, game_code: str, game_name: str, category: str) -> str:
    start, end = _gradient_for(provider_code)
    code = escape(normalize_provider_code(provider_code)[:16])
    title = escape(clean_text(game_name)[:34] or clean_text(game_code)[:34])
    category_label = escape(normalize_category(category).upper())
    provider_short = escape(PROVIDER_NAME_OVERRIDES.get(code, code).replace("_", " ")[:22])
    return f"""
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360" fill="none">
  <defs>
    <linearGradient id="gameGradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{start}" />
      <stop offset="100%" stop-color="{end}" />
    </linearGradient>
  </defs>
  <rect width="640" height="360" rx="28" fill="url(#gameGradient)" />
  <rect x="20" y="20" width="600" height="320" rx="24" fill="rgba(15,23,42,0.32)" />
  <g opacity="0.16">
    <circle cx="548" cy="86" r="72" fill="#ffffff" />
    <circle cx="80" cy="286" r="92" fill="#ffffff" />
  </g>
  <rect x="34" y="34" width="122" height="34" rx="17" fill="rgba(15,23,42,0.58)" />
  <text x="95" y="56" fill="#ffffff" font-size="15" font-weight="700" text-anchor="middle" font-family="Inter, Arial, sans-serif">{category_label}</text>
  <text x="42" y="170" fill="#ffffff" font-size="32" font-weight="800" font-family="Inter, Arial, sans-serif">{title}</text>
  <text x="42" y="206" fill="rgba(255,255,255,0.82)" font-size="18" font-weight="600" font-family="Inter, Arial, sans-serif">{provider_short}</text>
  <text x="42" y="236" fill="rgba(255,255,255,0.64)" font-size="15" font-weight="600" font-family="Inter, Arial, sans-serif">Code: {escape(clean_text(game_code)[:28])}</text>
  <text x="598" y="328" fill="rgba(255,255,255,0.52)" font-size="13" font-weight="700" text-anchor="end" font-family="Inter, Arial, sans-serif">LooxGame seamless catalog</text>
</svg>
""".strip()


def _split_currencies(value: Any) -> list[str]:
    raw = clean_text(value)
    if not raw:
        return []
    return [clean_text(item).upper() for item in raw.split(",") if clean_text(item)]


def _match_provider_row(code: str, name: str, supplier: str, rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    normalized_code = normalize_provider_code(code)
    normalized_name = slugify(name)
    supplier_tokens = {normalize_provider_code(supplier), normalized_code.split("_")[0], slugify(name).upper()}
    for row in rows:
        row_supplier = normalize_provider_code(row.get("Game Supplier") or row.get("Supplier") or row.get("Provider") or "")
        row_name = slugify(row.get("Provider Name") or row.get("Provider") or "")
        if row_supplier and row_supplier in supplier_tokens:
            return row
        if row_name and row_name == normalized_name:
            return row
    return None


@lru_cache(maxsize=8)
def build_provider_directory_from_workbook(workbook_path: str) -> dict[str, dict[str, Any]]:
    import pandas as pd

    xls = pd.ExcelFile(workbook_path)
    provider_rows = []
    icon_rows = []
    if "Provider List" in xls.sheet_names:
        provider_rows = pd.read_excel(workbook_path, sheet_name="Provider List").fillna("").to_dict("records")
    if "All game icon" in xls.sheet_names:
        icon_rows = pd.read_excel(workbook_path, sheet_name="All game icon").fillna("").to_dict("records")

    directory: dict[str, dict[str, Any]] = {}
    for sheet_name in xls.sheet_names:
        if sheet_name in NON_GAME_SHEETS:
            continue
        frame = pd.read_excel(workbook_path, sheet_name=sheet_name).fillna("")
        if frame.empty:
            continue
        sample = frame.iloc[0].to_dict()
        code = normalize_provider_code(sample.get("Provider Code") or sample.get("Provider") or sheet_name)
        supplier = clean_text(sample.get("Supplier") or sample.get("Column 1") or code)
        raw_name = clean_text(sample.get("Provider Name") or sheet_name)
        provider_reference = _match_provider_row(code, raw_name, supplier, provider_rows)
        icon_reference = _match_provider_row(code, raw_name, supplier, icon_rows)
        display_name = normalize_provider_name(code, raw_name, supplier)
        directory[code] = {
            "id": f"provider_{slugify(code)}",
            "code": code,
            "name": display_name,
            "slug": provider_slug(code, display_name),
            "wallet_type": clean_text(provider_reference.get("Wallet Type") if provider_reference else "Seamless") or "Seamless",
            "supported_currencies": _split_currencies(provider_reference.get("Currency") if provider_reference else ""),
            "source_logo_ref": clean_text(icon_reference.get("Company Logo") if icon_reference else ""),
            "source_icon_ref": clean_text(icon_reference.get("Game Icon") if icon_reference else ""),
            "logo_url": provider_logo_asset_path(code),
            "supplier": supplier or code,
            "aggregator": "seamless",
        }
    return directory


def _first_non_empty(row: dict[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = clean_text(row.get(key))
        if value:
            return value
    return ""


def normalize_game_row(
    row: dict[str, Any],
    *,
    sheet_name: str,
    provider_directory: dict[str, dict[str, Any]],
    tenant_ids: list[str],
    source: str = "seamless_excel",
) -> dict[str, Any] | None:
    provider_code = normalize_provider_code(_first_non_empty(row, ["Provider Code", "Provider", sheet_name]))
    provider_meta = provider_directory.get(provider_code, {})
    supplier = clean_text(_first_non_empty(row, ["Supplier", "Column 1", "Game Supplier"])) or provider_meta.get("supplier") or provider_code
    provider_name = normalize_provider_name(provider_code, row.get("Provider Name"), supplier, provider_directory)
    game_name = clean_text(_first_non_empty(row, ["Game Name", "Game name", "Name"]))
    if not game_name:
        return None
    status = clean_text(row.get("Status")).lower() or "active"
    game_launch_id = clean_text(_first_non_empty(row, ["Game launch Id", "Game Launch ID", "Game Launch Id", "game_launch_id", "Game launch id"]))
    game_code = clean_text(_first_non_empty(row, ["Game Code", "Game code", "game_code"]))
    external_game_id = game_code or game_launch_id or game_name
    game_launch_id = game_launch_id or external_game_id
    if not game_launch_id and not external_game_id:
        return None
    platform = normalize_platform(row.get("Platform"))
    category_raw = _first_non_empty(row, ["Category", "Game Type", "Type"]) or sheet_name
    category = normalize_category(category_raw)
    rtp = normalize_rtp(_first_non_empty(row, ["RTP", "RTP %", "RTP (%)"]))
    volatility = normalize_volatility(row.get("Volatility"))
    direct_thumbnail = _first_non_empty(row, ["Banner", "Game Icon", "Mobile Image", "PC Image", "Image", "Thumbnail"])
    thumbnail_url = direct_thumbnail if looks_like_direct_image_url(direct_thumbnail) else game_thumbnail_asset_path(provider_code, external_game_id)
    provider_logo_url = provider_meta.get("logo_url") or provider_logo_asset_path(provider_code)
    created_at = utc_now_iso()
    stable_game_id = stable_uuid("game", provider_code, external_game_id, game_launch_id, platform)
    tags: list[str] = []

    return {
        "id": stable_game_id,
        "name": game_name,
        "category": category,
        "provider_id": provider_meta.get("id") or f"provider_{slugify(provider_code)}",
        "provider_name": provider_name,
        "provider_slug": provider_meta.get("slug") or provider_slug(provider_code, provider_name),
        "provider_logo_url": provider_logo_url,
        "thumbnail_url": thumbnail_url,
        "aggregator": "seamless",
        "source": source,
        "game_launch_id": game_launch_id,
        "external_game_id": external_game_id,
        "provider_code": provider_code,
        "game_code": game_code or external_game_id,
        "supplier": supplier,
        "platform": platform,
        "is_active": status == "active",
        "is_enabled": status == "active",
        "tenant_ids": list(dict.fromkeys(tenant_ids)),
        "tags": tags,
        "is_hot": False,
        "is_new": False,
        "is_popular": False,
        "created_at": created_at,
        "updated_at": created_at,
        "description": f"{provider_name} • {category.title()}",
        "rtp": rtp,
        "volatility": volatility or "medium",
        "min_bet": 0.1,
        "max_bet": 1000.0,
        "status": status,
        "wallet_type": provider_meta.get("wallet_type", "Seamless"),
        "supported_currencies": provider_meta.get("supported_currencies", []),
        "provider_logo_source": provider_meta.get("source_logo_ref"),
        "thumbnail_source": direct_thumbnail,
    }


def dedupe_games(games: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for game in games:
        dedupe_key = "::".join(
            [
                game.get("provider_code", ""),
                game.get("game_code", ""),
                game.get("game_launch_id", ""),
                game.get("platform", "all"),
            ]
        )
        existing = deduped.get(dedupe_key)
        if not existing:
            deduped[dedupe_key] = game
            continue
        duplicates += 1
        current_score = sum(bool(existing.get(field)) for field in ("thumbnail_url", "rtp", "volatility", "provider_logo_url"))
        new_score = sum(bool(game.get(field)) for field in ("thumbnail_url", "rtp", "volatility", "provider_logo_url"))
        if new_score > current_score:
            deduped[dedupe_key] = game
    return list(deduped.values()), {"dedupe_key": "provider_code + game_code + game_launch_id + platform", "duplicates_removed": duplicates}


@lru_cache(maxsize=8)
def load_catalog_from_workbook(workbook_path: str, tenant_key: str = "default") -> dict[str, Any]:
    import pandas as pd

    workbook = str(Path(workbook_path))
    provider_directory = build_provider_directory_from_workbook(workbook)
    xls = pd.ExcelFile(workbook)
    games: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_source_rows = 0
    skipped_rows = 0
    for sheet_name in xls.sheet_names:
        frame = pd.read_excel(workbook, sheet_name=sheet_name).fillna("")
        if sheet_name in NON_GAME_SHEETS:
            continue
        total_source_rows += len(frame)
        if "Provider Code" not in frame.columns and "Provider" not in frame.columns:
            warnings.append(f"Skipped sheet '{sheet_name}' because provider code column is missing")
            skipped_rows += len(frame)
            continue
        for _, raw_row in frame.iterrows():
            row = raw_row.to_dict()
            normalized = normalize_game_row(
                row,
                sheet_name=sheet_name,
                provider_directory=provider_directory,
                tenant_ids=tenant_key.split(",") if tenant_key else [],
            )
            if normalized is None:
                skipped_rows += 1
                continue
            games.append(normalized)
    deduped_games, duplicate_summary = dedupe_games(games)
    provider_codes = {game["provider_code"] for game in deduped_games}
    categories = Counter(game["category"] for game in deduped_games)
    provider_docs = [provider_directory[code] for code in sorted(provider_codes) if code in provider_directory]
    return {
        "games": deduped_games,
        "providers": provider_docs,
        "summary": {
            "total_source_rows": total_source_rows,
            "imported_games": len(deduped_games),
            "skipped_rows": skipped_rows,
            "provider_count": len(provider_docs),
            "category_count": len(categories),
            "categories": dict(categories),
            "duplicate_handling": duplicate_summary,
            "warnings": warnings,
        },
    }


def canonicalize_game_doc(doc: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(doc)
    provider_code = normalize_provider_code(normalized.get("provider_code") or normalized.get("provider_id"))
    provider_name = normalize_provider_name(provider_code, normalized.get("provider_name"), normalized.get("supplier"))
    provider_slug_value = normalized.get("provider_slug") or provider_slug(provider_code, provider_name)
    game_code = clean_text(normalized.get("game_code") or normalized.get("external_game_id") or normalized.get("game_launch_id") or normalized.get("id"))
    category = normalize_category(normalized.get("category"))
    normalized.update(
        {
            "provider_id": normalized.get("provider_id") or f"provider_{slugify(provider_code)}",
            "provider_code": provider_code,
            "provider_name": provider_name,
            "provider_slug": provider_slug_value,
            "provider_logo_url": normalized.get("provider_logo_url") or provider_logo_asset_path(provider_code),
            "thumbnail_url": normalized.get("thumbnail_url") if looks_like_direct_image_url(normalized.get("thumbnail_url")) else game_thumbnail_asset_path(provider_code, game_code),
            "aggregator": clean_text(normalized.get("aggregator")) or "seamless",
            "source": clean_text(normalized.get("source")) or "seamless_catalog",
            "game_launch_id": clean_text(normalized.get("game_launch_id") or game_code),
            "external_game_id": clean_text(normalized.get("external_game_id") or game_code),
            "game_code": game_code,
            "category": category,
            "platform": normalize_platform(normalized.get("platform")),
            "is_active": bool(normalized.get("is_active", True)),
            "is_enabled": bool(normalized.get("is_enabled", True)),
            "tenant_ids": normalized.get("tenant_ids") or [],
            "tags": list(normalized.get("tags") or []),
            "is_hot": bool(normalized.get("is_hot", False)),
            "is_new": bool(normalized.get("is_new", False)),
            "is_popular": bool(normalized.get("is_popular", False)),
        }
    )
    return normalized


def aggregate_provider_rows(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    provider_map: dict[str, dict[str, Any]] = {}
    for raw_game in games:
        game = canonicalize_game_doc(raw_game)
        code = game["provider_code"]
        if code not in provider_map:
            provider_map[code] = {
                "id": game["provider_id"],
                "name": game["provider_name"],
                "slug": game["provider_slug"],
                "code": code,
                "logo_url": game["provider_logo_url"],
                "logoUrl": game["provider_logo_url"],
                "gameCount": 0,
                "categories": set(),
                "provider_code": code,
            }
        provider_map[code]["gameCount"] += 1
        provider_map[code]["categories"].add(game["category"])
    providers = []
    for provider in provider_map.values():
        provider["categories"] = sorted(provider["categories"], key=lambda item: CANONICAL_CATEGORY_ORDER.index(item) if item in CANONICAL_CATEGORY_ORDER else 999)
        providers.append(provider)
    providers.sort(key=lambda item: item["name"].lower())
    return providers


def aggregate_category_counts(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(canonicalize_game_doc(game)["category"] for game in games)
    total = sum(counts.values())
    rows = [{"name": "all", "count": total}]
    for category in CANONICAL_CATEGORY_ORDER:
        if category == "all":
            continue
        count = counts.get(category, 0)
        if count > 0:
            rows.append({"name": category, "count": count})
    return rows
