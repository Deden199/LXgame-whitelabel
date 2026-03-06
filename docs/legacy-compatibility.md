# Legacy Compatibility

## Retained compatibility-only files
- `backend/providers/vd7_adapter.py`
- `backend/providers/vd7_callbacks.py`
- `backend/providers/vd7_signature.py`
- `backend/scripts/replace_vd7_games_from_excel.py`
- operator-only `/operator/vd7/*` routes in `backend/server.py`

## Why they were kept
They may still support:
- historical operator workflows
- backward-compatible diagnostics
- migration-time safety for old data references

## What is NOT legacy anymore
The active player-facing path is now:
- seamless live-source catalog
- seamless launch mapping
- seamless callback routes
- player Games / Providers UI built on the normalized seamless data model

## Important rule
These retained legacy files must not be treated as the main setup path for staging.
The main staging path is the seamless live API rebuild and launch flow.
