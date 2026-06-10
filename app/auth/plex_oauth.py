from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

PLEX_PIN_URL = "https://plex.tv/api/v2/pins"
PLEX_USER_URL = "https://plex.tv/api/v2/user"
PLEX_AUTH_URL = "https://app.plex.tv/auth"


class PlexOAuth:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client_id = (self.settings.plex_client_id or "").strip()
        if not self.client_id:
            raise ValueError(
                "PLEX_CLIENT_ID is required for Plex login (use a stable UUID in .env)"
            )
        self._pending_pins: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-Plex-Client-Identifier": self.client_id,
            "X-Plex-Product": self.settings.plex_product,
        }

    def _public_origin(self) -> str:
        parsed = urlparse(self.settings.public_url.strip())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return self.settings.public_url.rstrip("/")

    def _callback_url(self, pin_id: str) -> str:
        base = self._public_origin()
        return f"{base}/auth/callback?pin_id={pin_id}"

    def create_pin(self) -> dict[str, Any]:
        origin = self._public_origin()
        form = {
            "strong": "true",
            "X-Plex-Product": self.settings.plex_product,
            "X-Plex-Client-Identifier": self.client_id,
        }
        headers = {
            **self._headers(),
            "Origin": origin,
        }
        logger.info(
            "Creating Plex pin (client_id=%s…%s, origin=%s, product=%s)",
            self.client_id[:8],
            self.client_id[-4:] if len(self.client_id) > 12 else "",
            origin,
            self.settings.plex_product,
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(PLEX_PIN_URL, headers=headers, data=form)
            if response.status_code >= 400:
                logger.error(
                    "Plex pin creation failed: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()

        pin_id = str(data["id"])
        code = str(data["code"])
        forward = self._callback_url(pin_id)
        self._pending_pins[pin_id] = {"code": code, "created": time.time()}

        params = urlencode(
            {
                "clientID": self.client_id,
                "code": code,
                "forwardUrl": forward,
                "context[device][product]": self.settings.plex_product,
            }
        )
        auth_url = f"{PLEX_AUTH_URL}#?{params}"
        logger.info(
            "Plex pin created: pin_id=%s forward_url=%s",
            pin_id,
            forward,
        )
        return {"pin_id": pin_id, "code": code, "auth_url": auth_url, "forward_url": forward}

    def resolve_pin_code(self, pin_id: str, pin_code: str | None = None) -> str | None:
        if pin_code:
            return pin_code
        pending = self._pending_pins.get(pin_id)
        if pending:
            return str(pending.get("code") or "")
        return None

    def poll_pin(
        self,
        pin_id: str,
        pin_code: str | None = None,
        *,
        max_attempts: int = 20,
        interval_seconds: float = 1.0,
    ) -> str | None:
        code = self.resolve_pin_code(pin_id, pin_code)
        if not code:
            logger.warning(
                "Cannot poll Plex pin %s: missing pin code (restart login from /auth/start)",
                pin_id,
            )
            return None

        logger.info("Polling Plex pin pin_id=%s (max_attempts=%s)", pin_id, max_attempts)
        for attempt in range(1, max_attempts + 1):
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{PLEX_PIN_URL}/{pin_id}",
                    headers=self._headers(),
                    params={"code": code},
                )
                if response.status_code >= 400:
                    logger.error(
                        "Plex pin poll failed: pin_id=%s attempt=%s status=%s body=%s",
                        pin_id,
                        attempt,
                        response.status_code,
                        response.text[:500],
                    )
                    response.raise_for_status()
                data = response.json()

            auth_token = data.get("authToken")
            if auth_token:
                logger.info(
                    "Plex pin claimed: pin_id=%s attempt=%s",
                    pin_id,
                    attempt,
                )
                return str(auth_token)

            logger.debug(
                "Plex pin not ready: pin_id=%s attempt=%s authToken=null",
                pin_id,
                attempt,
            )
            if attempt < max_attempts:
                time.sleep(interval_seconds)

        logger.warning(
            "Plex pin not claimed after polling: pin_id=%s attempts=%s",
            pin_id,
            max_attempts,
        )
        return None

    def get_plex_user(self, auth_token: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                PLEX_USER_URL,
                headers={**self._headers(), "X-Plex-Token": auth_token},
            )
            if response.status_code >= 400:
                logger.error(
                    "Plex user fetch failed: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
            response.raise_for_status()
            return response.json()

    def match_tautulli_user(
        self, plex_user: dict[str, Any], tautulli_users: list[dict[str, Any]], mapping: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        plex_id = plex_user.get("id")
        email = (plex_user.get("email") or "").lower()
        username = (plex_user.get("username") or "").lower()

        for entry in mapping.values():
            if entry.get("plex_user_id"):
                mapped_email = (entry.get("plex_email") or "").lower()
                mapped_user = (entry.get("plex_username") or "").lower()
                if mapped_email and mapped_email == email:
                    uid = int(entry["plex_user_id"])
                    matched = next((u for u in tautulli_users if int(u.get("user_id", 0)) == uid), None)
                    if matched:
                        logger.info(
                            "Matched via user_mapping email -> tautulli user_id=%s",
                            uid,
                        )
                    return matched
                if mapped_user and mapped_user == username:
                    uid = int(entry["plex_user_id"])
                    matched = next((u for u in tautulli_users if int(u.get("user_id", 0)) == uid), None)
                    if matched:
                        logger.info(
                            "Matched via user_mapping username -> tautulli user_id=%s",
                            uid,
                        )
                    return matched

        for user in tautulli_users:
            t_email = (user.get("email") or "").lower()
            t_user = (user.get("username") or "").lower()
            t_name = (user.get("friendly_name") or "").lower()
            if email and t_email == email:
                logger.info(
                    "Matched Plex user to Tautulli user_id=%s by email",
                    user.get("user_id"),
                )
                return user
            if username and (t_user == username or t_name == username):
                logger.info(
                    "Matched Plex user to Tautulli user_id=%s by username",
                    user.get("user_id"),
                )
                return user

        logger.warning(
            "No Tautulli match for Plex account: plex_id=%s username=%s email=%s",
            plex_id,
            plex_user.get("username"),
            plex_user.get("email"),
        )
        return None


def _serializer(settings: Settings) -> URLSafeSerializer:
    return URLSafeSerializer(settings.secret_key, salt="plex-wrapped-session")


def set_session_user_id(
    response: Response,
    user_id: int,
    settings: Settings | None = None,
    *,
    username: str | None = None,
) -> None:
    settings = settings or get_settings()
    payload: dict[str, Any] = {"user_id": user_id}
    if username:
        payload["username"] = username
    token = _serializer(settings).dumps(payload)
    response.set_cookie(
        key="wrapped_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_max_age,
        secure=settings.public_url.startswith("https"),
    )


def _load_session(request: Request, settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    cookie = request.cookies.get("wrapped_session")
    if not cookie:
        return None
    try:
        data = _serializer(settings).loads(cookie)
        if not isinstance(data, dict):
            return None
        return data
    except (BadSignature, TypeError, ValueError):
        return None


def get_session_user_id(request: Request, settings: Settings | None = None) -> int | None:
    data = _load_session(request, settings)
    if not data:
        return None
    try:
        return int(data.get("user_id"))
    except (TypeError, ValueError):
        return None


def get_session_username(request: Request, settings: Settings | None = None) -> str | None:
    data = _load_session(request, settings)
    if not data:
        return None
    username = data.get("username")
    if isinstance(username, str) and username.strip():
        return username.strip()
    return None


def clear_session(response: Response) -> None:
    response.delete_cookie("wrapped_session")
