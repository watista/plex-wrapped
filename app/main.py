from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.admin.links import ShareLinkManager
from app.auth.login_resolve import resolve_login_user_id
from app.auth.plex_oauth import PlexOAuth, clear_session, get_session_user_id, set_session_user_id
from app.config import PROJECT_ROOT, Settings, get_settings
from app.logging_setup import configure_logging
from app.models.cache import WrappedCache
from app.tautulli.client import TautulliClient, TautulliError
from app.models.schemas import WrappedPayload

STATIC_DIR = PROJECT_ROOT / "static"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

logger = logging.getLogger(__name__)


def _request_origin(request: Request) -> str:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host.split(',')[0].strip()}"
    return f"{request.url.scheme}://{request.url.netloc}"


def _pin_cookie_kwargs(request: Request, settings: Settings) -> dict[str, Any]:
    secure = request.url.scheme == "https" or settings.public_url.startswith("https")
    return {"httponly": True, "max_age": 1800, "samesite": "lax", "secure": secure}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "Starting Plex Wrapped (public_url=%s, test_db=%s)",
        settings.public_url,
        settings.use_test_database,
    )
    app.state.settings = settings
    app.state.tautulli = TautulliClient(settings)
    app.state.cache = WrappedCache(settings, database_path=settings.active_database_path())
    app.state.plex_oauth = PlexOAuth(settings)
    app.state.share_links = ShareLinkManager(settings, app.state.cache)
    yield
    app.state.tautulli.close()


app = FastAPI(title="Plex Wrapped", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def get_tautulli(request: Request) -> TautulliClient:
    return request.app.state.tautulli


def require_user_id(request: Request) -> int:
    user_id = get_session_user_id(request, request.app.state.settings)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


class AdminLinkBody(BaseModel):
    plex_user_id: int
    year: int | None = None
    max_views: int | None = None


def _format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


@app.get("/health")
def health(tautulli: TautulliClient = Depends(get_tautulli)):
    try:
        users = tautulli.get_users()
        return {"status": "ok", "users": len(users)}
    except TautulliError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=503)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user_id = get_session_user_id(request, request.app.state.settings)
    if user_id:
        return RedirectResponse("/wrapped")
    return templates.TemplateResponse(request, "login.html", {"request": request})


@app.get("/auth/start")
def auth_start(request: Request):
    settings: Settings = request.app.state.settings
    oauth: PlexOAuth = request.app.state.plex_oauth
    request_origin = _request_origin(request)
    configured_origin = oauth._public_origin()
    if urlparse(request_origin).netloc != urlparse(configured_origin).netloc:
        logger.warning(
            "PUBLIC_URL host mismatch: browser=%s configured=%s — Plex OAuth may fail; "
            "set PUBLIC_URL to the exact URL you use in the browser",
            request_origin,
            configured_origin,
        )

    pin = oauth.create_pin()
    cookie_kwargs = _pin_cookie_kwargs(request, settings)
    response = RedirectResponse(pin["auth_url"])
    response.set_cookie("plex_pin_id", pin["pin_id"], **cookie_kwargs)
    response.set_cookie("plex_pin_code", pin["code"], **cookie_kwargs)
    logger.info("Auth started: redirecting to Plex (pin_id=%s)", pin["pin_id"])
    return response


@app.get("/auth/callback")
def auth_callback(
    request: Request,
    pin_id: str | None = None,
    pin_code: str | None = None,
):
    settings: Settings = request.app.state.settings
    oauth: PlexOAuth = request.app.state.plex_oauth
    tautulli: TautulliClient = request.app.state.tautulli

    pin_id = pin_id or request.query_params.get("pin_id") or request.cookies.get("plex_pin_id")
    pin_code = pin_code or request.query_params.get("pin_code") or request.cookies.get("plex_pin_code")

    logger.info(
        "Auth callback: pin_id=%s pin_code_present=%s client_host=%s public_url=%s",
        pin_id,
        bool(pin_code),
        request.client.host if request.client else None,
        settings.public_url,
    )

    if not pin_id:
        logger.error("Auth callback missing pin_id (query=%s cookies=%s)", dict(request.query_params), list(request.cookies))
        raise HTTPException(400, "Missing pin_id. Start login from /auth/start")

    try:
        auth_token = oauth.poll_pin(pin_id, pin_code)
    except Exception as exc:
        logger.exception("Auth callback poll failed for pin_id=%s: %s", pin_id, exc)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Plex login failed. Check server logs and try again."},
        )

    if not auth_token:
        logger.warning(
            "Auth callback: no authToken for pin_id=%s (Plex auth may not have finished, or Origin/PUBLIC_URL mismatch)",
            pin_id,
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Login not completed. Please try again."},
        )

    try:
        plex_user = oauth.get_plex_user(auth_token)
    except Exception as exc:
        logger.exception("Failed to fetch Plex user after pin_id=%s: %s", pin_id, exc)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Could not load your Plex profile. Try again."},
        )

    logger.info(
        "Plex account authenticated: plex_id=%s username=%s email=%s title=%s",
        plex_user.get("id"),
        plex_user.get("username"),
        plex_user.get("email"),
        plex_user.get("title"),
    )

    cache: WrappedCache = request.app.state.cache
    try:
        user_id = resolve_login_user_id(settings, cache, oauth, plex_user, tautulli)
    except Exception:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Server stats unavailable. Try again later."},
        )

    if user_id is None:
        if settings.use_test_database:
            error = (
                "No test profile for this Plex account. "
                "Run: python scripts/load_test_wrapped.py --user-id "
                f"{plex_user.get('id')} (or add yourself to data/fixtures/test_users.json)."
            )
        else:
            error = "Your Plex account is not linked to this server. Contact the admin."
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": error},
        )

    logger.info(
        "Login success: session user_id=%s (plex_id=%s, test_mode=%s)",
        user_id,
        plex_user.get("id"),
        settings.use_test_database,
    )
    response = RedirectResponse("/wrapped", status_code=303)
    set_session_user_id(response, user_id, settings)
    response.delete_cookie("plex_pin_id")
    response.delete_cookie("plex_pin_code")
    return response


@app.get("/auth/logout")
def logout():
    response = RedirectResponse("/")
    clear_session(response)
    return response


@app.get("/w/{token}", response_class=HTMLResponse)
def share_wrapped(request: Request, token: str):
    share: ShareLinkManager = request.app.state.share_links
    result = share.validate_token(token)
    if not result:
        raise HTTPException(404, "Invalid or expired link")
    user_id, year = result
    response = templates.TemplateResponse(
        request,
        "wrapped.html",
        {
            "request": request,
            "year": year,
            "user_id": user_id,
            "share_mode": True,
        },
    )
    set_session_user_id(response, user_id, request.app.state.settings)
    return response


@app.get("/wrapped", response_class=HTMLResponse)
def wrapped_page(request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is None:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        request,
        "wrapped.html",
        {
            "request": request,
            "year": settings.wrapped_year,
            "user_id": user_id,
            "share_mode": False,
        },
    )


@app.get("/api/wrapped")
def api_wrapped(request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is None:
        raise HTTPException(401, "Not authenticated")

    cache: WrappedCache = request.app.state.cache
    cached = cache.get(user_id, settings.wrapped_year)
    if not cached:
        raise HTTPException(
            503,
            detail={
                "ready": False,
                "message": "Wrapped not generated yet. Run compute_wrapped.py first.",
            },
        )

    payload = WrappedPayload(**cached)

    data = payload.model_dump()
    data["total_watch_time_formatted"] = _format_duration(payload.total_watch_seconds)
    return data


@app.post("/admin/links")
def admin_create_link(
    body: AdminLinkBody,
    request: Request,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    settings: Settings = request.app.state.settings
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(403, "Forbidden")

    share: ShareLinkManager = request.app.state.share_links
    url = share.create_link(body.plex_user_id, body.year, body.max_views)
    return {"url": url, "plex_user_id": body.plex_user_id, "year": body.year or settings.wrapped_year}


@app.get("/api/poster")
def poster_proxy(path: str, request: Request):
    settings: Settings = request.app.state.settings
    if not path.startswith("/"):
        raise HTTPException(400, "Invalid path")
    if not settings.plex_server_url or not settings.plex_server_token:
        raise HTTPException(501, "Poster proxy not configured")

    import httpx

    url = f"{settings.plex_server_url.rstrip('/')}{path}"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, params={"X-Plex-Token": settings.plex_server_token})
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, "Poster unavailable")
    return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))


# Jinja filters
templates.env.filters["format_duration"] = _format_duration
