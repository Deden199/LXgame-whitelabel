# Testing

## Backend smoke
```bash
curl -X POST http://127.0.0.1:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"player1@aurumbet.demo","password":"player123","tenant_slug":"aurumbet"}'
```

Then:
```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/games
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/providers
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/games/categories
```

## Live launch test
Use a real enriched game such as:
- `Chin Shi Huang` (`JILI`, `launch_game_code=2`)
- or a featured CQ9 game such as `Gold Stealer`

## Frontend validation
- login through preview UI
- open Games page
- confirm banners/providers display correctly
- click a real game and verify popup/new-tab launch succeeds
- confirm at least one featured game launches successfully

## Callback tests
Use live MORRISLITA credentials against:
- `/gold_api/user_balance`
- `/gold_api/game_callback`
- `/gold_api/money_callback`

Replay the same transaction to confirm idempotency.
