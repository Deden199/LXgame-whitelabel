# Architecture

## Overview
LXgame-whitelabel is a multi-tenant gaming platform with:
- FastAPI backend
- React frontend
- MongoDB persistence
- seamless provider integration for active staging catalog + launch + callbacks

## Active data path
### Player-facing catalog
- source of truth: seamless live provider/game APIs
- normalized in: `backend/seamless_live_catalog.py`
- exposed by:
  - `GET /api/games`
  - `GET /api/providers`
  - `GET /api/games/categories`

### Launch
- route: `POST /api/games/{game_id}/launch`
- adapter: `backend/providers/seamless_adapter.py`
- normalized launch fields:
  - `launch_provider_code`
  - `launch_game_code`

### Callbacks
- `/gold_api/user_balance`
- `/gold_api/game_callback`
- `/gold_api/money_callback`
- handler: `backend/providers/seamless_callbacks.py`

## Bootstrap model
`backend/bootstrap_seamless.py` ensures:
- tenants exist
- default users exist
- finance buffer exists
- live API sync is used when seamless credentials are configured
- workbook sync remains fallback-only

## Image model
### Providers
- provider source API does not return logos
- backend emits deterministic SVGs

### Games
- primary: live `banner`
- secondary: backend generated SVG asset
- final: frontend placeholder UI

## Featured sections
Flags are assigned during live API sync:
- `is_popular`
- `is_hot`
- `is_new`

Selection uses active banner-backed games only, with provider diversity.
