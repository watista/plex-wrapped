from __future__ import annotations

import time
import uuid
from typing import Any

import httpx
from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import Settings, get_settings

PLEX_PIN_URL = "https://plex.tv/api/v2/pins"
PLEX_USER_URL = "https://plex.tv/api/v2/user"
PLEX_AUTH_URL = "https://app.plex.tv/auth"


class PlexOAuth:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client_id = self.settings.plex_client_id or str(uuid.uuid4())
        self._pending_pins: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "X-Plex-Client-Identifier": self.client_id,
            "X-Plex-Product": self.settings.plex_product,
        }

    def create_pin(self) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                PLEX_PIN_URL,
                headers={**self._headers(), "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        pin_id = str(data["id"])
        code = data["code"]
        self._pending_pins[pin_id] = {"code": code, "created": time.time()}
        from urllib.parse import quote

        forward = quote(f"{self.settings.public_url.rstrip('/')}/auth/callback", safe="")
        auth_url = (
            f"{PLEX_AUTH_URL}#?"
            f"clientID={self.client_id}"
            f"&code={code}"
            f"&context%5Bdevice%5D%5Bproduct%5D={self.settings.plex_product}"
            f"&forwardUrl={forward}"
        )
        return {"pin_id": pin_id, "code": code, "auth_url": auth_url}

    def poll_pin(self, pin_id: str) -> str | None:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{PLEX_PIN_URL}/{pin_id}",
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()
        return data.get("authToken")

    def get_plex_user(self, auth_token: str) -> dict[str, Any]:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                PLEX_USER_URL,
                headers={**self._headers(), "X-Plex-Token": auth_token},
            )
            response.raise_for_status()
            return response.json()

    def match_tautulli_user(
        self, plex_user: dict[str, Any], tautulli_users: list[dict[str, Any]], mapping: dict[str, dict[str, Any]]
    ) -> dict[str, Any] | None:
        plex_id = plex_user.get("id")
        email = (plex_user.get("email") or "").lower()
        username = (plex_user.get("username") or "").lower()

        # Check mapping overrides by email/username
        for entry in mapping.values():
            if entry.get("plex_user_id"):
                mapped_email = (entry.get("plex_email") or "").lower()
                mapped_user = (entry.get("plex_username") or "").lower()
                if mapped_email and mapped_email == email:
                    uid = int(entry["plex_user_id"])
                    return next((u for u in tautulli_users if int(u.get("user_id", 0)) == uid), None)
                if mapped_user and mapped_user == username:
                    uid = int(entry["plex_user_id"])
                    return next((u for u in tautulli_users if int(u.get("user_id", 0)) == uid), None)

        for user in tautulli_users:
            t_email = (user.get("email") or "").lower()
            t_user = (user.get("username") or "").lower()
            t_name = (user.get("friendly_name") or "").lower()
            if email and t_email == email:
                return user
            if username and (t_user == username or t_name == username):
                return user
        return None


def _serializer(settings: Settings) -> URLSafeSerializer:
    return URLSafeSerializer(settings.secret_key, salt="plex-wrapped-session")


def set_session_user_id(response: Response, user_id: int, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    token = _serializer(settings).dumps({"user_id": user_id})
    response.set_cookie(
        key="wrapped_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_max_age,
        secure=settings.public_url.startswith("https"),
    )


def get_session_user_id(request: Request, settings: Settings | None = None) -> int | None:
    settings = settings or get_settings()
    cookie = request.cookies.get("wrapped_session")
    if not cookie:
        return None
    try:
        data = _serializer(settings).loads(cookie)
        return int(data.get("user_id"))
    except (BadSignature, TypeError, ValueError):
        return None


def clear_session(response: Response) -> None:
    response.delete_cookie("wrapped_session")
