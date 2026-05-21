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

   **Plex login:** set `PLEX_CLIENT_ID` to a stable UUID (generate once, keep it). Set `PUBLIC_URL` to the **exact** URL you open in the browser (e.g. `http://192.168.1.10:8000` — not `localhost` if you use the LAN IP). A mismatch causes Plex to show “We were unable to complete this request.”

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

Test data goes into a **separate** SQLite file (`data/wrapped_test.db`), not the production `data/wrapped.db`.

```bash
# One user (default: user_id 1)
python scripts/load_test_wrapped.py --user-id 1

# All users in data/fixtures/test_users.json
python scripts/load_test_wrapped.py --all-test-users

# Point the app at the test database (.env)
USE_TEST_DATABASE=true
```

With `USE_TEST_DATABASE=true`, **login does not need Tautulli** — your Plex account is matched via `test_users.json`, `user_mapping.json`, or cached rows in `wrapped_test.db`.

Edit fixtures under `data/fixtures/` (`wrapped_test.json`, `wrapped_test_user2.json`, …) and list users in `test_users.json`. Each fixture must be **one** JSON object (do not paste multiple profiles into one file).

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
