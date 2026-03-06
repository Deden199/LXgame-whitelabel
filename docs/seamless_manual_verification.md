# Seamless Integration Manual Verification

## Primary validation tenant
- Tenant ID: `tenant_aurum_001`
- Tenant slug: `aurumbet`
- Player: `player1@aurumbet.demo`

## Intended staging database target
- `DB_NAME=loocgamedb`
- `MONGO_URL` is supplied securely via ignored environment/local env

## Login smoke
```bash
curl -X POST http://127.0.0.1:8001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"player1@aurumbet.demo","password":"player123","tenant_slug":"aurumbet"}'
```

## Catalog smoke
```bash
TOKEN="<bearer token>"

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/games
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/providers
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8001/api/games/categories
```

## Asset fallback smoke
```bash
curl http://127.0.0.1:8001/api/assets/providers/llg.svg
curl http://127.0.0.1:8001/api/assets/games/llg/popeye96.svg
```

## Launch smoke
Expected current staging result without live outbound token:
- HTTP 503
- explicit missing seamless launch credential error

```bash
curl -X POST http://127.0.0.1:8001/api/games/<game_id>/launch \
  -H "Authorization: Bearer $TOKEN"
```

## Callback smoke
```bash
curl -X POST http://127.0.0.1:8001/gold_api/user_balance \
  -H 'Content-Type: application/json' \
  -d '{"agent_code":"aurumbet","agent_secret":"aurumbet_secret","user_code":"player_aurumbet_001"}'

curl -X POST http://127.0.0.1:8001/gold_api/game_callback \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_code":"aurumbet",
    "agent_secret":"aurumbet_secret",
    "agent_balance":99999,
    "user_code":"player_aurumbet_001",
    "user_balance":250000,
    "user_total_credit":0,
    "user_total_debit":0,
    "game_type":"slot",
    "slot":{
      "provider_code":"LLG",
      "game_code":"popeye96",
      "round_id":"manual-round-001",
      "is_round_finished":true,
      "type":"BASE",
      "bet":100,
      "win":30,
      "txn_id":"manual-txn-001",
      "txn_type":"debit_credit",
      "user_before_balance":250000,
      "user_after_balance":249930
    }
  }'

curl -X POST http://127.0.0.1:8001/gold_api/money_callback \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_code":"aurumbet",
    "agent_secret":"aurumbet_secret",
    "agent_type":"Seamless",
    "user_code":"player_aurumbet_001",
    "provider_code":"LLG",
    "game_code":"popeye96",
    "type":"credit",
    "amount":50,
    "user_before_balance":249930,
    "user_after_balance":249980,
    "msg":"manual credit"
  }'
```

## Import / migration commands
```bash
python /app/backend/scripts/sync_seamless_catalog_from_excel.py --tenants aurumbet,bluewave
python /app/backend/scripts/replace_vd7_games_from_excel.py --tenant aurumbet --dry-run
python /app/backend/scripts/seamless_core_poc.py
```
