# Plex Wrapped

A mobile-first, Spotify Wrapped–style recap for your Plex server.

**Project plan:** [docs/PLAN.md](docs/PLAN.md) Pulls watch stats from **Tautulli**, request stats from your **Telegram bot JSON**, and supports **Plex login** plus **admin share links**.

## Quick start

1. Copy environment and config files:

```bash
cp .env.example .env
cp config/user_mapping.json.example config/user_mapping.json
cp data/telegram_requests.json.example data/telegram_requests.json
```

2. Edit `.env` with your Tautulli URL/API key, Plex client ID, and secrets.

3. Edit `config/user_mapping.json` — map Telegram IDs to Plex `user_id` (from Tautulli → Users).

4. Point `TELEGRAM_REQUESTS_PATH` at your bot's JSON export.

5. Install and run:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Pre-compute stats (required before anyone opens wrapped):**

```bash
python scripts/compute_wrapped.py --year 2025
```

The app serves cached stats only — opening `/wrapped` without a cache entry returns a “not generated yet” message.

### Local UI testing (no Tautulli batch)

Load bundled sample stats into the same SQLite cache the app reads:

```bash
python scripts/load_test_wrapped.py --user-id 1
# or every user in user_mapping.json:
python scripts/load_test_wrapped.py --all-mapped
```

Edit `data/fixtures/wrapped_test.json` to tweak numbers, slides, or persona. Then sign in with Plex as that `plex_user_id` (or use an admin share link).

Open http://localhost:8000 and sign in with Plex.

## Admin share links

```bash
curl -X POST http://localhost:8000/admin/links \
  -H "X-Admin-Secret: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"plex_user_id\": 1}"
```

Returns a signed URL like `http://localhost:8000/w/...` that opens that user's wrapped without Plex login.

## User mapping format

```json
{
  "8229502993": {
    "plex_user_id": 1,
    "plex_username": "Joe",
    "plex_email": "joe@example.com"
  }
}
```

The top-level key is the **Telegram user ID**. `plex_user_id` must match Tautulli's user id.

## Telegram requests format

```json
{
  "8229502993": {
    "logins": { "23-01-2025 15:35:49": "Joe" },
    "film_requests": { "19-05-2025 14:43:25": "Movie Title" },
    "serie_requests": { "23-01-2025 15:36:21": "Show Title" }
  }
}
```

Dates use `DD-MM-YYYY HH:MM:SS`.

## Docker

```bash
docker compose up -d --build
```

## Configuration

| Variable | Description |
|----------|-------------|
| `TAUTULLI_URL` | Tautulli base URL |
| `TAUTULLI_API_KEY` | Tautulli API key |
| `PLEX_CLIENT_ID` | UUID for Plex OAuth |
| `PUBLIC_URL` | Public URL for OAuth redirect and share links |
| `WRAPPED_YEAR` | Calendar year to summarize |
| `ADMIN_SECRET` | Header secret for `/admin/links` |
| `SHARE_LINK_SECRET` | HMAC secret for share tokens |
| `PLEX_SERVER_URL` / `PLEX_SERVER_TOKEN` | Optional poster proxy |

## License

GPL-3.0 (see LICENSE)
