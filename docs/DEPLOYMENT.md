# Deploying Plex Wrapped on a web server

This guide covers running Plex Wrapped in production behind a reverse proxy (HTTPS), with persistent data, scheduled cache rebuilds, and optional Docker.

For local development and first-time setup, start with [README.md](../README.md).

---

## Overview

```
Internet → Nginx/Caddy (443, TLS) → Uvicorn (127.0.0.1:8000) → FastAPI app
                                         ↓
                              SQLite cache (data/wrapped.db)
                                         ↓
                              Tautulli API (LAN or Docker network)
```

The app is a standard ASGI application. In production you typically:

1. Run Uvicorn bound to localhost (not exposed directly to the internet).
2. Put Nginx or Caddy in front for HTTPS and static buffering.
3. Set `PUBLIC_URL` to your public `https://` URL (required for Plex OAuth and share links).
4. Pre-compute wrapped stats with `scripts/compute_wrapped.py` before users visit.
5. Schedule cache rebuilds (cron/systemd timer) when watch history changes or a new year starts.

---

## Production checklist

| Item | Action |
|------|--------|
| `PUBLIC_URL` | Set to the exact public URL, e.g. `https://wrapped.example.com` |
| `SECRET_KEY` | Long random string (session signing) |
| `ADMIN_SECRET` | Long random string (admin API header) |
| `SHARE_LINK_SECRET` | Long random string (share token HMAC) |
| `USE_TEST_DATABASE` | `false` |
| `PLEX_CLIENT_ID` | Stable UUID — never rotate after users have logged in |
| `TAUTULLI_URL` | Reachable from the app host (see [Tautulli connectivity](#tautulli-connectivity)) |
| HTTPS | Required for secure session cookies when `PUBLIC_URL` uses `https://` |
| Cache | Run `compute_wrapped.py` after deploy and on a schedule |
| Firewall | Expose 443 (proxy only); keep port 8000 on localhost |

Generate secrets (Linux/macOS/WSL):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Option A — Bare metal / VM (systemd + Nginx)

### 1. Install the application

```bash
sudo useradd --system --home /opt/plex-wrapped --shell /usr/sbin/nologin plexwrapped
sudo mkdir -p /opt/plex-wrapped
sudo chown $USER:plexwrapped /opt/plex-wrapped

# Clone or copy the project into /opt/plex-wrapped
cd /opt/plex-wrapped
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
cp config/user_mapping.json.example config/user_mapping.json
# Edit .env — see deploy/env.production.example
```

Ensure the `plexwrapped` user can read `.env`, `config/`, and write to `data/`:

```bash
sudo chown -R plexwrapped:plexwrapped /opt/plex-wrapped/data
sudo chown plexwrapped:plexwrapped /opt/plex-wrapped/.env
```

### 2. Pre-compute stats

```bash
cd /opt/plex-wrapped
source .venv/bin/activate
python scripts/compute_wrapped.py --year 2025
```

### 3. Systemd service

Copy and edit the example unit file:

```bash
sudo cp deploy/plex-wrapped.service.example /etc/systemd/system/plex-wrapped.service
sudo systemctl daemon-reload
sudo systemctl enable --now plex-wrapped
sudo systemctl status plex-wrapped
```

The service runs Uvicorn on `127.0.0.1:8000` without `--reload`.

### 4. Nginx reverse proxy

Copy and adapt the example config:

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/plex-wrapped
sudo ln -s /etc/nginx/sites-available/plex-wrapped /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Obtain a TLS certificate with [Certbot](https://certbot.eff.org/) (Let's Encrypt) and uncomment the SSL lines in the Nginx config, or terminate TLS at Cloudflare/your load balancer and forward `X-Forwarded-Proto: https`.

**Important:** `PUBLIC_URL` in `.env` must match what users type in the browser (`https://wrapped.example.com`), not the internal `127.0.0.1:8000` address.

### 5. Scheduled cache rebuild

Wrapped stats are read from SQLite; they do not update automatically when someone watches more Plex.

Copy the cron example:

```bash
sudo cp deploy/compute-wrapped.cron.example /etc/cron.d/plex-wrapped-compute
```

Or use a systemd timer — run the same command as in the cron file on a schedule that fits your server (e.g. nightly, or weekly during the wrapped season).

Force a full refresh after major Tautulli history imports:

```bash
cd /opt/plex-wrapped && .venv/bin/python scripts/compute_wrapped.py --year 2025 --force
```

---

## Option B — Docker Compose

Best when you already run other services in Docker.

### 1. Configure environment

```bash
cp .env.example .env
# Set PUBLIC_URL=https://wrapped.example.com and production secrets
```

### 2. Start the container

```bash
docker compose up -d --build
```

`docker-compose.yml` mounts:

- `./data` → persistent SQLite cache
- `./config/user_mapping.json` → Telegram ↔ Plex mapping

Also mount your Telegram export if it lives outside the image:

```yaml
volumes:
  - ./data/telegram_requests.json:/app/data/telegram_requests.json:ro
```

### 3. Pre-compute inside the container

```bash
docker compose exec plex-wrapped python scripts/compute_wrapped.py --year 2025
```

### 4. Reverse proxy

Point Nginx/Caddy at `http://127.0.0.1:8000` (published port from Compose). Do not expose port 8000 publicly if the proxy runs on the same host — bind to `127.0.0.1:8000:8000` in Compose for stricter setups:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

### Tautulli connectivity

| Setup | `TAUTULLI_URL` example |
|-------|-------------------------|
| Tautulli on same host, app in Docker | `http://host.docker.internal:8181` (Docker Desktop) or host LAN IP |
| Both in Docker, same Compose network | `http://tautulli:8181` (service name) |
| App on host, Tautulli on host | `http://127.0.0.1:8181` |

The app only needs outbound HTTP access to Tautulli; Tautulli does not need to be public on the internet.

---

## Option C — Caddy (automatic HTTPS)

Minimal `Caddyfile` example:

```caddy
wrapped.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

Set `PUBLIC_URL=https://wrapped.example.com`. Caddy sets `X-Forwarded-Proto` automatically.

---

## Verifying the deployment

```bash
# App health (Tautulli must be reachable)
curl -sS https://wrapped.example.com/health

# Admin device list (replace secret)
curl -sS https://wrapped.example.com/admin/devices \
  -H "X-Admin-Secret: your-admin-secret"
```

Open `https://wrapped.example.com` in a browser and complete Plex login. If OAuth fails:

- Confirm `PUBLIC_URL` matches the browser URL exactly (scheme, host, no trailing path).
- Check server logs: `journalctl -u plex-wrapped -f` or `docker compose logs -f`.
- Ensure cookies work over HTTPS (`secure` flag is set when `PUBLIC_URL` starts with `https://`).

---

## Updating the application

**Bare metal:**

```bash
cd /opt/plex-wrapped
git pull   # or copy new files
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart plex-wrapped
python scripts/compute_wrapped.py --year 2025 --force   # if data schema changed
```

**Docker:**

```bash
docker compose up -d --build
docker compose exec plex-wrapped python scripts/compute_wrapped.py --year 2025 --force
```

---

## File permissions and backups

Back up regularly:

- `data/wrapped.db` — all pre-computed wrapped payloads and share-link metadata
- `config/user_mapping.json`
- `data/telegram_requests.json`
- `.env` (store securely; not in git)

The `data/` directory must be writable by the process user (`plexwrapped` or the container user).

---

## Troubleshooting

| Symptom | Likely cause |
|---------|----------------|
| Plex OAuth “unable to complete request” | `PUBLIC_URL` mismatch vs browser URL |
| `/health` returns 503 | Tautulli down or wrong `TAUTULLI_URL` / API key |
| “Not generated yet” on `/wrapped` | Cache empty — run `compute_wrapped.py` |
| Share links use `http://localhost` | `PUBLIC_URL` not updated for production |
| Posters missing | Set `PLEX_SERVER_URL` and `PLEX_SERVER_TOKEN` |
| Login works but wrong user stats | `user_mapping.json` Telegram ID ↔ `plex_user_id` incorrect |

---

## Example files in `deploy/`

| File | Purpose |
|------|---------|
| [nginx.conf.example](../deploy/nginx.conf.example) | Nginx reverse proxy |
| [plex-wrapped.service.example](../deploy/plex-wrapped.service.example) | systemd unit for Uvicorn |
| [compute-wrapped.cron.example](../deploy/compute-wrapped.cron.example) | Scheduled cache rebuild |
| [env.production.example](../deploy/env.production.example) | Production `.env` template |
