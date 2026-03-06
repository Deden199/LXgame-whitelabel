# Seamless Integration

## Contract source
Primary contract behavior:
- `POST /api/v2/game_launch`
- `POST /api/v2/provider_list`
- `POST /api/v2/game_list`
- `POST /gold_api/user_balance`
- `POST /gold_api/game_callback`
- `POST /gold_api/money_callback`

## Source behavior reflected in repo
### provider_list
Used for:
- live provider code
- live provider display name
- live provider type/backoffice

Limitation:
- no logo URL is returned by the source API

### game_list
Used for:
- `game_code`
- `game_name`
- `banner`
- `status`

These fields drive:
- active catalog membership
- launch mapping
- banner imagery

## Live launch validation
Verified successful live staging launch for:
- tenant: `tenant_aurum_001`
- player: `player_aurumbet_001`
- provider: `JILI`
- game: `Chin Shi Huang`

Verified successful featured launch for:
- provider: `CQ9`
- game: `Gold Stealer`

## Callback validation
Verified with live MORRISLITA credentials:
- balance callback success
- game callback success + replay idempotency
- money callback success + replay idempotency
