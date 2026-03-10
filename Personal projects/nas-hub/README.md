# NAS Calendar + Thesis Hub (FastAPI)

MVP web app for:
- Viewing all Google calendars/events
- Creating/deleting events
- Logging thesis work sessions (hours + notes)

## Run on NAS (Docker)

```bash
cd "Personal projects/nas-hub"
cp /path/to/your/google-client.json ./secrets/client.json
# choose a strong session secret in docker-compose.yml first
docker compose up -d --build
```

Open:
- `http://192.168.50.165:3180`

## First-time Google auth
1. Click **Connect Google**
2. Complete OAuth
3. App stores token in SQLite settings table (`data/app.db`)

## Notes
- Uses SQLite (`./data/app.db`) for persistence.
- Keep `./secrets/client.json` private.
- Behind Twingate is recommended for remote access.

## Next improvements
- Edit existing events
- Calendar filtering toggles
- Thesis timer (start/stop)
- Basic login for app UI
