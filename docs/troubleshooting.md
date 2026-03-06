# Troubleshooting

## Launch fails with invalid provider / invalid parameter
- confirm the game was seeded from the live API sync path
- confirm `launch_provider_code` exists and matches source provider codes
- confirm `launch_game_code` exists and comes from source `game_list.game_code`
- confirm the source provider supports that game in live provider/game responses

## Catalog count looks wrong
- confirm `MONGO_URL` points to the staging Atlas target
- confirm `DB_NAME=loocgamedb`
- rerun live sync command
- inspect the latest `catalog_import_runs` record

## Images missing
- if a game has `source_banner_url`, it should render that first
- if source banner fails, backend generated SVG should still render
- if both fail, frontend placeholder should appear instead of broken image

## Callback issues
- validate `agent_code`
- validate `agent_secret`
- inspect `callback_events` for event replay state
- inspect `transactions` for duplicated tx ids

## Legacy operator paths
Some old operator-only compatibility files/routes remain in the repo. They are not part of the active player seamless path.
