# RS3 Discord Bot

## Setup

1. Set Railway environment variables:
   - `DISCORD_TOKEN` → your bot token
   - (Optional) `CHECK_INTERVAL` → seconds between checks, default 600

2. Deploy the folder to Railway.

3. In Discord, run:
   - `/setchannel` → to choose the notifications channel
   - `/track gimseedspoon`
   - `/track gim mythy`

## Notes
- Only posts real RuneMetrics events.
- Duplicates are prevented via seen_events.json.
