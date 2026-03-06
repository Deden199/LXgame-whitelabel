# Catalog Import and Cleanup

## Intended staging target
- `DB_NAME=loocgamedb`
- `MONGO_URL` must be injected securely

## Final active catalog strategy
The final player-facing staging catalog is rebuilt from the live seamless API, not from historical workbook-only leftovers.

## Commands
### Live source rebuild
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/enrich_seamless_catalog_from_api.py --tenants aurumbet,bluewave --mode sync
```

### Workbook fallback import
```bash
PYTHONPATH=/app/backend /root/.venv/bin/python /app/backend/scripts/sync_seamless_catalog_from_excel.py --tenants aurumbet,bluewave
```

## Cleanup behavior
During live sync:
- only source-active (`status == 1`) live API games are kept active
- non-live-source / stale rows are removed from tenant-visible active catalog
- providers are rebuilt from live provider source
- category set is rebuilt from live provider types (`slots`, `live`)

## Final count model
See latest `catalog_import_runs` for:
- source total games
- active games
- stale removed
- banner enriched count
- fallback only count
