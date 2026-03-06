# LXgame-whitelabel

Lean FastAPI + React + MongoDB gaming platform wired to a normalized seamless game source.

## What this repo contains
- Full tenant bootstrap for staging/testing
- Canonical seamless catalog import from the attached workbook source
- Normalized provider/category APIs
- Stable SVG fallbacks for provider logos and game thumbnails
- Seamless wallet callback endpoints with idempotent ledger handling
- Updated player Games and Providers pages

## Runtime overview
- Backend: `backend/server.py`
- Frontend: `frontend/src/App.js`
- Catalog normalization: `backend/catalog_normalization.py`
- Catalog sync/import: `backend/catalog_sync.py`
- Seamless adapter: `backend/providers/seamless_adapter.py`
- Seamless callbacks: `backend/providers/seamless_callbacks.py`
- Bootstrap: `backend/bootstrap_seamless.py`

## Primary scripts
```bash
python /app/backend/scripts/sync_seamless_catalog_from_excel.py --tenants aurumbet,bluewave
python /app/backend/scripts/seamless_core_poc.py
python /app/backend/scripts/replace_vd7_games_from_excel.py --tenant aurumbet --dry-run
```

## Default local staging users
- Super admin: `admin@platform.com` / `admin123`
- Tenant admin: `admin@aurumbet.com` / `admin123`
- Player: `player1@aurumbet.demo` / `player123` with tenant slug `aurumbet`

## Live launch credentials
The seamless outbound launch flow is fully wired, but live launch requires tenant/provider credentials in `backend/.env` / `tenant.provider_config.seamless`:
- `SEAMLESS_API_BASE_URL`
- `SEAMLESS_AGENT_CODE`
- `SEAMLESS_AGENT_TOKEN`
- `SEAMLESS_AGENT_SECRET`

## Verification
See `docs/seamless_manual_verification.md` for smoke commands.
