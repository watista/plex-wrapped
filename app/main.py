from __future__ import annotations

import json
import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.activity.schemas import ActivityEventBody
from app.activity.service import ActivityService
from app.admin.links import ShareLinkManager
from app.auth.login_resolve import resolve_login_user_id
from app.auth.plex_oauth import PlexOAuth, clear_session, get_session_user_id, set_session_user_id
from app.config import PROJECT_ROOT, Settings, get_settings
from app.i18n import get_translator, localize_wrapped_payload
from app.logging_setup import configure_logging
from app.models.cache import WrappedCache
from app.tautulli.client import TautulliClient, TautulliError
from app.wrapped.posters import plex_poster_paths, rating_key_from_poster_path
from app.tautulli.devices import collect_unique_devices
from app.models.schemas import WrappedPayload

from app.wrapped.youtube_audio import is_valid_video_id

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
    app.state.activity = ActivityService(settings, app.state.cache)
    yield
    app.state.tautulli.close()


app = FastAPI(title="Plex Wrapped", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _translator_for(request: Request) -> Any:
    settings: Settings = request.app.state.settings
    return get_translator(settings.language)


def _i18n_context(request: Request) -> dict[str, Any]:
    translator = _translator_for(request)
    return {
        "t": translator.t,
        "html_lang": translator.html_lang(),
        "i18n_json": json.dumps(translator.client_bundle()),
    }


def get_tautulli(request: Request) -> TautulliClient:
    return request.app.state.tautulli


def require_user_id(request: Request) -> int:
    user_id = get_session_user_id(request, request.app.state.settings)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


def _login_context(
    request: Request,
    *,
    error: str | None = None,
    logged_in: bool = False,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    ctx: dict[str, Any] = {
        "request": request,
        "plex_client_id": (settings.plex_client_id or "").strip(),
        "plex_product": settings.plex_product,
        "use_test_database": settings.use_test_database,
        "logged_in": logged_in,
        **_i18n_context(request),
    }
    if error:
        ctx["error"] = error
    return ctx


def _wrapped_template_context(request: Request, *, year: int, user_id: int, share_mode: bool) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    return {
        "request": request,
        "year": year,
        "user_id": user_id,
        "share_mode": share_mode,
        "google_analytics_id": (settings.google_analytics_id or "").strip(),
        **_i18n_context(request),
    }


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
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    translator = get_translator(settings.language)
    return templates.TemplateResponse(
        request,
        "login.html",
        _login_context(request, logged_in=user_id is not None),
        headers={"Content-Language": translator.html_lang()},
    )


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
    translator = get_translator(settings.language)

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
            _login_context(request, error=translator.t("auth.plex_login_failed")),
        )

    if not auth_token:
        logger.warning(
            "Auth callback: no authToken for pin_id=%s (Plex auth may not have finished, or Origin/PUBLIC_URL mismatch)",
            pin_id,
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            _login_context(request, error=translator.t("auth.login_not_completed")),
        )

    try:
        plex_user = oauth.get_plex_user(auth_token)
    except Exception as exc:
        logger.exception("Failed to fetch Plex user after pin_id=%s: %s", pin_id, exc)
        return templates.TemplateResponse(
            request,
            "login.html",
            _login_context(request, error=translator.t("auth.profile_load_failed")),
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
            _login_context(request, error=translator.t("auth.server_unavailable")),
        )

    if user_id is None:
        if settings.use_test_database:
            error = translator.t(
                "auth.test_profile_missing",
                plex_id=plex_user.get("id"),
            )
        else:
            error = translator.t("auth.account_not_linked")
        return templates.TemplateResponse(
            request,
            "login.html",
            _login_context(request, error=error),
        )

    plex_username = (plex_user.get("username") or plex_user.get("title") or "").strip()
    activity: ActivityService = request.app.state.activity
    activity.log_login(
        request,
        user_id=user_id,
        username=plex_username or f"user_{user_id}",
        login_method="login_portal",
        year=settings.wrapped_year,
    )

    response = RedirectResponse("/wrapped", status_code=303)
    set_session_user_id(response, user_id, settings, username=plex_username or None)
    response.delete_cookie("plex_pin_id")
    response.delete_cookie("plex_pin_code")
    return response


@app.get("/auth/logout")
def logout(request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is not None:
        activity: ActivityService = request.app.state.activity
        username = activity.resolve_username(request, user_id)
        activity.logger.log(username, "logout", user_id=user_id, year=settings.wrapped_year)
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
    settings: Settings = request.app.state.settings
    activity: ActivityService = request.app.state.activity
    cached = request.app.state.cache.get(user_id, year)
    username = (
        (cached or {}).get("username")
        or (cached or {}).get("display_name")
        or f"user_{user_id}"
    )

    activity.log_login(
        request,
        user_id=user_id,
        username=username,
        login_method="share_link",
        year=year,
    )

    response = templates.TemplateResponse(
        request,
        "wrapped.html",
        _wrapped_template_context(request, year=year, user_id=user_id, share_mode=True),
    )
    set_session_user_id(response, user_id, settings, username=username)
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
        _wrapped_template_context(
            request,
            year=settings.wrapped_year,
            user_id=user_id,
            share_mode=False,
        ),
    )


@app.get("/api/wrapped")
def api_wrapped(request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is None:
        raise HTTPException(401, "Not authenticated")

    cache: WrappedCache = request.app.state.cache
    cached = cache.get(user_id, settings.wrapped_year)
    translator = get_translator(settings.language)
    if not cached:
        raise HTTPException(
            503,
            detail={
                "ready": False,
                "message": translator.t("api.wrapped_not_ready"),
            },
        )

    payload = WrappedPayload(**cached)

    data = payload.model_dump()
    data["total_watch_time_formatted"] = _format_duration(payload.total_watch_seconds)
    localize_wrapped_payload(data, translator)
    return data


@app.post("/api/activity")
def api_activity(body: ActivityEventBody, request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is None:
        raise HTTPException(401, "Not authenticated")

    activity: ActivityService = request.app.state.activity
    activity.record_client_event(request, user_id, body)
    return {"ok": True}


def _require_admin_secret(settings: Settings, x_admin_secret: str) -> None:
    if not settings.admin_secret or x_admin_secret != settings.admin_secret:
        raise HTTPException(403, "Forbidden")


@app.get("/admin/devices")
def admin_list_devices(
    request: Request,
    tautulli: TautulliClient = Depends(get_tautulli),
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    settings: Settings = request.app.state.settings
    _require_admin_secret(settings, x_admin_secret)
    try:
        return collect_unique_devices(tautulli)
    except TautulliError as exc:
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=503)


@app.post("/admin/links")
def admin_create_link(
    body: AdminLinkBody,
    request: Request,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
):
    settings: Settings = request.app.state.settings
    _require_admin_secret(settings, x_admin_secret)

    share: ShareLinkManager = request.app.state.share_links
    url = share.create_link(body.plex_user_id, body.year, body.max_views)
    return {"url": url, "plex_user_id": body.plex_user_id, "year": body.year or settings.wrapped_year}


def _is_image_response(resp: httpx.Response) -> bool:
    content_type = (resp.headers.get("content-type") or "").lower()
    return resp.status_code == 200 and content_type.startswith("image/")


_ALLOWED_EXTERNAL_IMAGE_HOSTS = frozenset({"image.tmdb.org"})


@app.get("/api/image")
def external_image_proxy(url: str):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(400, "Invalid URL")
    if parsed.hostname not in _ALLOWED_EXTERNAL_IMAGE_HOSTS:
        raise HTTPException(403, "Image host not allowed")

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        resp = client.get(url)
    if not _is_image_response(resp):
        status = resp.status_code if resp is not None else 502
        raise HTTPException(status, "Image unavailable")
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/api/poster")
def poster_proxy(
    path: str,
    request: Request,
    rating_key: str | None = None,
):
    settings: Settings = request.app.state.settings
    tautulli: TautulliClient = request.app.state.tautulli
    if not path.startswith("/"):
        raise HTTPException(400, "Invalid path")

    resolved_rating_key = rating_key or rating_key_from_poster_path(path)
    resp: httpx.Response | None = None

    if settings.plex_server_url and settings.plex_server_token:
        base = settings.plex_server_url.rstrip("/")
        with httpx.Client(timeout=15.0) as client:
            for candidate in plex_poster_paths(path):
                attempt = client.get(
                    f"{base}{candidate}",
                    params={"X-Plex-Token": settings.plex_server_token},
                )
                if _is_image_response(attempt):
                    resp = attempt
                    break
                resp = attempt

    if resp is None or not _is_image_response(resp):
        for attempt in (
            tautulli.fetch_pms_image(img=path, rating_key=resolved_rating_key, refresh=True),
            tautulli.fetch_pms_image(rating_key=resolved_rating_key, refresh=True)
            if resolved_rating_key
            else None,
        ):
            if attempt is None:
                continue
            if _is_image_response(attempt):
                resp = attempt
                break
            resp = attempt

    if resp is None or not _is_image_response(resp):
        status = resp.status_code if resp is not None else 502
        raise HTTPException(status, "Poster unavailable")
    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
    )


_AUDIO_FILE_RE = re.compile(r"^[A-Za-z0-9_-]+\.(mp3|m4a|aac)$", re.IGNORECASE)


@app.get("/api/audio/{filename}")
def audio_file(filename: str, request: Request):
    settings: Settings = request.app.state.settings
    user_id = get_session_user_id(request, settings)
    if user_id is None:
        raise HTTPException(401, "Not authenticated")
    if not _AUDIO_FILE_RE.match(filename):
        raise HTTPException(400, "Invalid filename")

    cache_dir = settings.resolve_path(settings.audio_cache_path)
    direct = cache_dir / filename
    if direct.is_file():
        return FileResponse(direct, media_type="audio/mpeg")

    stem = Path(filename).stem
    if is_valid_video_id(stem):
        for path in cache_dir.glob(f"{stem}.*"):
            if path.is_file() and path.stat().st_size > 0:
                media = "audio/mpeg" if path.suffix.lower() == ".mp3" else "audio/mp4"
                return FileResponse(path, media_type=media)

    raise HTTPException(404, "Audio not found")


# Jinja filters
templates.env.filters["format_duration"] = _format_duration
