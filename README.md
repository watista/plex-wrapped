# Plex Wrapped

A mobile-first, Spotify Wrapped–style year-in-review for your Plex server. Swipe through cinematic slides with watch time, top films and series, genres, streaks, favorite devices, server rankings, Telegram request stats, and a shareable summary card — all personalized per viewer.

Built for self-hosted Plex setups that already use **Tautulli** for watch history and optionally a **Telegram bot** for film/series requests.

**Full project plan:** [docs/PLAN.md](docs/PLAN.md)  
**Production deployment:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Python** | 3.12+ (matches the Docker image) |
| **Tautulli** | Running instance with API access (`TAUTULLI_URL`, `TAUTULLI_API_KEY`) |
| **Plex account** | Users sign in via Plex OAuth (`PLEX_CLIENT_ID`) |
| **Pre-computed cache** | Stats are batch-generated into SQLite before anyone opens `/wrapped` |
| **Optional — Telegram** | JSON export from your request bot + `config/user_mapping.json` to link Telegram IDs to Plex users |
| **Optional — Docker** | Docker Compose provided; otherwise any host with Python 3.12 |
| **Optional — posters** | `PLEX_SERVER_URL` + `PLEX_SERVER_TOKEN` for proxied poster images |
| **Production web server** | Reverse proxy (Nginx/Caddy) + HTTPS; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

**Python dependencies** (see `requirements.txt`): FastAPI, Uvicorn, httpx, Pydantic, Jinja2.

---

## Quick start

1. **Copy config templates**

```bash
cp .env.example .env
cp config/user_mapping.json.example config/user_mapping.json
cp data/telegram_requests.json.example data/telegram_requests.json
```

2. **Edit `.env`**

   - **Tautulli:** `TAUTULLI_URL`, `TAUTULLI_API_KEY`
   - **Plex login:** `PLEX_CLIENT_ID` — a stable UUID you generate once and keep
   - **Public URL:** `PUBLIC_URL` must match the **exact** URL you open in the browser (e.g. `http://192.168.1.10:8000`). Using `localhost` while browsing via a LAN IP causes Plex OAuth to fail with “We were unable to complete this request.”
   - **Secrets:** `SECRET_KEY`, `ADMIN_SECRET`, `SHARE_LINK_SECRET`

3. **Map Telegram users** (if you use request stats)

   Edit `config/user_mapping.json` — link Telegram user IDs to Plex `user_id` values from Tautulli → Users.

4. **Point at your Telegram export**

   Set `TELEGRAM_REQUESTS_PATH` to your bot's JSON file.

5. **Install and run**

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS / WSL
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Pre-compute wrapped stats** (required before anyone opens their recap)

```bash
python scripts/compute_wrapped.py --year 2025
```

The app serves **cached** stats only. Opening `/wrapped` without a cache entry shows a “not generated yet” message. Add `--force` to recompute users that are already cached. Add `-v` for verbose logging.

7. Open `http://localhost:8000` (or your `PUBLIC_URL`) and sign in with Plex.

---

## Local UI testing (no Tautulli batch)

Test data lives in a **separate** SQLite file (`data/wrapped_test.db`), not production `data/wrapped.db`.

```bash
# One user (default: user_id 1)
python scripts/load_test_wrapped.py --user-id 1

# All users listed in data/fixtures/test_users.json
python scripts/load_test_wrapped.py --all-test-users
```

In `.env`:

```env
USE_TEST_DATABASE=true
```

With `USE_TEST_DATABASE=true`, **login does not need Tautulli** — your Plex account is matched via `test_users.json`, `user_mapping.json`, or cached rows in `wrapped_test.db`.

Edit fixtures under `data/fixtures/` and register users in `test_users.json`. Each fixture must be **one** JSON object (do not paste multiple profiles into one file).

| User ID | Fixture | Scenario |
|--------|---------|----------|
| 1 | `wrapped_test.json` | Full profile (films + series + telegram) |
| 2 | `wrapped_test_user2.json` | Film-heavy mixed viewer |
| 3 | `wrapped_test_films_only.json` | Movies only, no series |
| 4 | `wrapped_test_series_only.json` | Series only, no movies |
| 5 | `wrapped_test_telegram_only.json` | Telegram only, no watch history |
| 6 | `wrapped_test_no_activity.json` | No activity at all |
| 7 | `wrapped_test_light_viewer.json` | Light viewer, minimal stats |
| 8 | `wrapped_test_mixed_low_completion.json` | Mixed + low telegram completion |
| 9 | `wrapped_test_no_telegram.json` | Full watch profile, no telegram usage |

---

## Admin endpoints

All admin routes require the `X-Admin-Secret` header (value from `ADMIN_SECRET` in `.env`).

### Share links

Create a signed URL that opens a user's wrapped **without** Plex login:

```bash
curl -X POST http://localhost:8000/admin/links \
  -H "X-Admin-Secret: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d "{\"plex_user_id\": 1}"
```

Returns a URL like `http://localhost:8000/w/...`.

Optional body fields: `year`, `max_views`.

### List unique devices

Collect every distinct Plex **player name** seen across all Tautulli users. Use this to discover which device icons you need (e.g. for the “Jouw scherm” slide) before adding custom artwork:

```bash
curl http://localhost:8000/admin/devices \
  -H "X-Admin-Secret: your-admin-secret"
```

Example response:

```json
{
  "count": 8,
  "names": ["Apple TV", "Chrome", "iPhone", "LG webOS TV", "NVIDIA SHIELD Android TV", "Samsung TV", "iPad", "Plex Web"],
  "devices": [
    {
      "name": "Apple TV",
      "platform": "tvOS",
      "platform_name": "Apple TV",
      "total_plays": 450,
      "users": ["Alice", "Bob"]
    }
  ]
}
```

- `names` — flat list sorted by popularity (handy to paste into a design brief)
- `devices` — per-device metadata: Tautulli `platform`, which users use it, and total play counts

Player names match the `favorite_device` value shown in each user's wrapped recap.

Device icons for the *Jouw scherm* slide are resolved in `static/js/device-icons.js` from `data/known_devices.json`. Regenerate after adding new players:

```bash
python scripts/generate_device_icons.py
```

Similar devices share one icon (for example all LG and Samsung TVs use `tv`, all iPhones use `phone_iphone`).

### Health check

```bash
curl http://localhost:8000/health
```

Returns `200` when Tautulli is reachable, or `503` with an error message when it is not.

---

## Data formats

### User mapping (`config/user_mapping.json`)

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

### Telegram requests (`data/telegram_requests.json`)

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

---

## Running on a web server

For production (HTTPS, reverse proxy, systemd, scheduled cache rebuilds), see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

Quick summary:

1. Set `PUBLIC_URL` to your public `https://` URL (required for Plex OAuth and share links).
2. Run Uvicorn on `127.0.0.1:8000` — do not expose it directly to the internet.
3. Put **Nginx** or **Caddy** in front for TLS (example configs in `deploy/`).
4. Run `compute_wrapped.py` after deploy and on a schedule (cron example in `deploy/`).

Example files in [`deploy/`](deploy/):

| File | Purpose |
|------|---------|
| `nginx.conf.example` | Reverse proxy to Uvicorn |
| `plex-wrapped.service.example` | systemd service (no `--reload`) |
| `compute-wrapped.cron.example` | Nightly cache rebuild |
| `env.production.example` | Production `.env` starting point |

### Docker

```bash
docker compose up -d --build
docker compose exec plex-wrapped python scripts/compute_wrapped.py --year 2025
```

Mount `.env`, `data/`, and `config/user_mapping.json` as in `docker-compose.yml`. Put a reverse proxy in front for HTTPS — details in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Configuration

| Variable | Description |
|----------|-------------|
| `PUBLIC_URL` | Public URL for OAuth redirects and share links (must match browser URL) |
| `WRAPPED_YEAR` | Calendar year to summarize |
| `SECRET_KEY` | Session signing secret |
| `SESSION_MAX_AGE` | Session cookie lifetime (seconds) |
| `LOG_LEVEL` | Application log level |
| `TAUTULLI_URL` | Tautulli base URL |
| `TAUTULLI_API_KEY` | Tautulli API key |
| `PLEX_CLIENT_ID` | Stable UUID for Plex OAuth |
| `PLEX_PRODUCT` | Product name sent to Plex (default: `PlexWrapped`) |
| `ADMIN_SECRET` | Header secret for `/admin/*` endpoints |
| `SHARE_LINK_SECRET` | HMAC secret for share tokens |
| `SHARE_LINK_EXPIRY_DAYS` | Share link validity (days) |
| `USER_MAPPING_PATH` | Path to Telegram ↔ Plex mapping JSON |
| `TELEGRAM_REQUESTS_PATH` | Path to Telegram bot request export |
| `DATABASE_PATH` | Production SQLite cache path |
| `TEST_DATABASE_PATH` | Test SQLite cache path |
| `USE_TEST_DATABASE` | `true` to use test DB and relaxed login |
| `TELEGRAM_BOT_TOKEN` | Optional — bot token for login/share alerts |
| `TELEGRAM_CHANNEL_ID` | Optional — channel/chat ID for alerts |
| `GOOGLE_ANALYTICS_ID` | Optional — GA4 measurement ID for slide tracking |
| `PLEX_SERVER_URL` / `PLEX_SERVER_TOKEN` | Optional poster proxy |

---

## License

GPL-3.0 (see [LICENSE](LICENSE))
