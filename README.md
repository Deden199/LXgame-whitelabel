# LXgame-whitelabel

LXgame-whitelabel is a FARM-stack gaming platform (FastAPI + React + MongoDB) with a **seamless provider integration** powering the active staging catalog, launch flow, callbacks, and player discovery experience.

## Current verified repo state
- Active staging catalog is rebuilt from the **live seamless source API**
- Player-facing catalog is cleaned from old workbook-only / non-API junk
- Backend launch succeeds through `/api/games/{game_id}/launch`
- Frontend launch succeeds from the player UI and opens the real remote game
- Callback routes are live and idempotent:
  - `/gold_api/user_balance`
  - `/gold_api/game_callback`
  - `/gold_api/money_callback`
- Hero / featured sections use **real active games** from the cleaned catalog

## Stack
- Backend: FastAPI, Motor, Pydantic
- Frontend: React, CRACO, Tailwind, shadcn/ui
- Database: MongoDB
- Catalog source:
  - primary staging source: seamless live API
  - fallback / compatibility source: workbook import script

## What seamless means here
The platform remains the source of truth for:
- player auth
- tenant routing
- wallet balances
- ledger / accounting
- callback idempotency

The seamless provider supplies:
- provider identity via `/api/v2/provider_list`
- game identity + banners via `/api/v2/game_list`
- launch session URLs via `/api/v2/game_launch`

## Staging setup
### Intended staging DB target
The intended staging database target is:
- `DB_NAME=loocgamedb`
- `MONGO_URL` must be provided securely through environment or local ignored `.env`

Secrets are **not** documented in tracked files.

### Required seamless env variables
- `SEAMLESS_API_BASE_URL`
- `SEAMLESS_AGENT_CODE`
- `SEAMLESS_AGENT_TOKEN`
- `SEAMLESS_AGENT_SECRET`
- `SEAMLESS_AGENT_SECRET_KEY` (accepted as alias)
- `SEAMLESS_DEFAULT_CURRENCY`
- `SEAMLESS_DEFAULT_LANGUAGE`
- `SEAMLESS_BOOTSTRAP_SOURCE=api` (optional, defaults to API when credentials exist)

## Runtime architecture
### Core backend files
- `backend/server.py` — API routes, launch, callbacks, startup
- `backend/catalog_normalization.py` — canonical game/provider/category shaping
- `backend/seamless_live_catalog.py` — live API-driven catalog rebuild and image enrichment
- `backend/catalog_sync.py` — workbook-based fallback sync path
- `backend/bootstrap_seamless.py` — tenant/user/bootstrap orchestration
- `backend/providers/seamless_adapter.py` — outbound seamless API adapter
- `backend/providers/seamless_callbacks.py` — callback auth + idempotent processing

### Core frontend files
- `frontend/src/pages/player/Games.js`
- `frontend/src/pages/player/Providers.js`
- `frontend/src/components/catalog/CatalogMedia.js`
- `frontend/src/components/ProviderFilter.js`

## Catalog / bootstrap / import / enrichment flow
### Primary staging flow (live API)
1. configure staging Mongo target in ignored env
2. configure seamless credentials in ignored env
3. bootstrap tenants/users
4. rebuild catalog from live source provider/game APIs
5. expose only active live-source games to players

### Manual commands
#### Full live catalog rebuild
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/enrich_seamless_catalog_from_api.py --tenants aurumbet,bluewave --mode sync
```

#### Workbook fallback sync
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/sync_seamless_catalog_from_excel.py --tenants aurumbet,bluewave
```

#### Legacy compatibility shim
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/replace_vd7_games_from_excel.py --tenant aurumbet --dry-run
```

#### Core POC verification
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/seamless_core_poc.py
```

## Image handling strategy
### Provider logos
Source provider API does **not** return logo URLs.
Current normalized strategy:
1. derive provider identity from source `code` + `name`
2. serve deterministic backend SVG logo at `/api/assets/providers/{provider}.svg`
3. fallback to frontend initials avatar if image render fails

### Game thumbnails
Primary source is the live seamless `game_list.banner` field.
Fallback chain:
1. live `banner`
2. backend deterministic generated asset `/api/assets/games/{provider}/{game}.svg`
3. frontend placeholder block

## Hero / featured selection strategy
Featured sections are built only from the **active cleaned live catalog**.
Selection is deterministic and banner-first:
1. use only active live-source games with real banners
2. preserve source provider ordering + source game ordering
3. diversify by provider (max 2 per provider per featured bucket)
4. assign buckets in sequence:
   - first 18 => `is_popular`
   - next 18 => `is_hot`
   - next 18 => `is_new`

This keeps hero/featured sections visually strong, real, and non-duplicative.

## Launch flow
1. player logs in through LooxGame
2. player clicks a real game card
3. backend resolves normalized launch fields:
   - `launch_provider_code`
   - `launch_game_code`
   - `lang`
   - `game_type`
4. backend calls `/api/v2/game_launch`
5. frontend opens returned launch URL in a popup/new tab

## Callback flow
- `/gold_api/user_balance`
- `/gold_api/game_callback`
- `/gold_api/money_callback`

Validation rules:
- agent auth via `agent_code + agent_secret`
- idempotency by transaction/event key
- wallet ledger remains the source of truth

## Verified state summary
- Backend launch: success
- Frontend launch: success
- Featured game launch from UI: success
- Callback auth: success
- Callback idempotency: success
- Active catalog is live-source-driven and cleaned

## Cleanup / final repo state
Removed:
- demo/evidence/test artifact clutter
- obsolete seed/scrape/catalog pipelines
- duplicate workbook
- stale generated icon dumps
- outdated docs and debug leftovers

Retained legacy compatibility shims:
- `backend/providers/vd7_adapter.py`
- `backend/providers/vd7_callbacks.py`
- `backend/providers/vd7_signature.py`
- `backend/scripts/replace_vd7_games_from_excel.py`
- operator-only `/operator/vd7/*` routes in `backend/server.py`

These are retained only for legacy compatibility and are **not** the active player path.

## Troubleshooting
### Launch returns provider error
- confirm `launch_provider_code` and `launch_game_code`
- confirm the game exists in live source provider/game list
- confirm seamless credentials are set for the tenant

### Player catalog looks wrong
- rerun live sync command
- verify active game count against latest `catalog_import_runs`
- confirm DB target points to staging Mongo (`loocgamedb`)

### Images missing
- check whether the game has `source_banner_url`
- if not, fallback asset route should still render cleanly

## Additional docs
- `docs/architecture.md`
- `docs/seamless-integration.md`
- `docs/catalog-import.md`
- `docs/testing.md`
- `docs/troubleshooting.md`
- `docs/legacy-compatibility.md`
- `docs/seamless_manual_verification.md`
