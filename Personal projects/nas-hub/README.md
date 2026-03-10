# NAS Calendar + Thesis Hub (FastAPI)

MVP web app for:
- Viewing all Google calendars/events
- Creating/deleting events
- Logging thesis work sessions (hours + notes)

## Run on NAS (Docker)

```bash
cd "Personal projects/nas-hub"
cp /path/to/your/google-client.json ./secrets/client.json
cp /path/to/your/google-token.json ./secrets/token.json
# choose a strong session secret in docker-compose.yml first
docker compose up -d --build
```

Open:
- `http://192.168.50.165:3180`

## Google auth model (no web callback required)
- The app reads OAuth files directly from:
  - `./secrets/client.json`
  - `./secrets/token.json`
- It refreshes the token automatically and writes the updated token back to `./secrets/token.json`.

## Notes
- Uses SQLite (`./data/app.db`) for persistence.
- Keep `./secrets/client.json` and `./secrets/token.json` private.
- Behind Twingate is recommended for remote access.

## Next improvements
- Edit existing events
- Calendar filtering toggles
- Thesis timer (start/stop)
- Basic login for app UI
