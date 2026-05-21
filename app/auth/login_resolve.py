from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.plex_oauth import PlexOAuth
from app.config import Settings
from app.fixtures.test_wrapped import load_test_user_entries
from app.models.cache import WrappedCache
from app.telegram.loader import load_user_mapping
from app.tautulli.client import TautulliClient, TautulliError

logger = logging.getLogger(__name__)


def _mapping_user_id(plex_user: dict[str, Any], mapping: dict[str, dict[str, Any]]) -> int | None:
    plex_id = plex_user.get("id")
    email = (plex_user.get("email") or "").lower()
    username = (plex_user.get("username") or "").lower()

    for entry in mapping.values():
        mapped_id = entry.get("plex_user_id")
        if mapped_id is None:
            continue
        uid = int(mapped_id)
        if plex_id is not None and int(plex_id) == uid:
            logger.info("Test login: matched plex_id=%s via user_mapping plex_user_id", uid)
            return uid
        mapped_email = (entry.get("plex_email") or "").lower()
        mapped_user = (entry.get("plex_username") or "").lower()
        if mapped_email and mapped_email == email:
            logger.info("Test login: matched email -> user_id=%s via user_mapping", uid)
            return uid
        if mapped_user and mapped_user == username:
            logger.info("Test login: matched username -> user_id=%s via user_mapping", uid)
            return uid
    return None


def _test_users_user_id(plex_user: dict[str, Any]) -> int | None:
    plex_id = plex_user.get("id")
    if plex_id is None:
        return None
    plex_id_int = int(plex_id)
    for entry in load_test_user_entries():
        if entry.plex_user_id == plex_id_int:
            logger.info(
                "Test login: matched plex_id=%s via test_users.json",
                entry.plex_user_id,
            )
            return entry.plex_user_id
    return None


def _cached_test_user_id(
    cache: WrappedCache,
    plex_user: dict[str, Any],
    year: int,
) -> int | None:
    plex_id = plex_user.get("id")
    if plex_id is not None:
        uid = int(plex_id)
        if cache.get(uid, year):
            logger.info(
                "Test login: using cached wrapped data for user_id=%s (plex_id)",
                uid,
            )
            return uid

    for entry in load_test_user_entries():
        if cache.get(entry.plex_user_id, year):
            if plex_id is not None and int(plex_id) == entry.plex_user_id:
                logger.info(
                    "Test login: using cached wrapped for test_users entry user_id=%s",
                    entry.plex_user_id,
                )
                return entry.plex_user_id

    cached_ids = []
    for entry in load_test_user_entries():
        if cache.get(entry.plex_user_id, year):
            cached_ids.append(entry.plex_user_id)
    if plex_id is not None and int(plex_id) in cached_ids:
        return int(plex_id)

    logger.warning(
        "Test login: no cached wrapped for plex_id=%s; cached test user_ids=%s",
        plex_id,
        cached_ids,
    )
    return None


def resolve_login_user_id(
    settings: Settings,
    cache: WrappedCache,
    oauth: PlexOAuth,
    plex_user: dict[str, Any],
    tautulli: TautulliClient,
) -> int | None:
    """
    Map an authenticated Plex account to a Tautulli/wrapped user_id.

    In test mode (USE_TEST_DATABASE), Tautulli is not required.
    """
    mapping = load_user_mapping(settings)
    year = settings.wrapped_year

    if settings.use_test_database:
        logger.info(
            "Resolving login in test mode (plex_id=%s, year=%s)",
            plex_user.get("id"),
            year,
        )
        for resolver in (
            lambda: _mapping_user_id(plex_user, mapping),
            lambda: _test_users_user_id(plex_user),
            lambda: _cached_test_user_id(cache, plex_user, year),
        ):
            user_id = resolver()
            if user_id is not None:
                return user_id
        return None

    try:
        tautulli_users = tautulli.get_users()
    except (TautulliError, httpx.HTTPError, OSError) as exc:
        logger.exception(
            "Tautulli unavailable during login for plex_id=%s: %s",
            plex_user.get("id"),
            exc,
        )
        raise

    tautulli_ids = [int(u.get("user_id", 0)) for u in tautulli_users if u.get("user_id") is not None]
    logger.info("Tautulli users available for matching: %s", tautulli_ids)

    matched = oauth.match_tautulli_user(plex_user, tautulli_users, mapping)
    if not matched:
        logger.warning(
            "Login rejected — no Tautulli match: plex_id=%s username=%s email=%s; "
            "tautulli_user_ids=%s mapping_plex_ids=%s",
            plex_user.get("id"),
            plex_user.get("username"),
            plex_user.get("email"),
            tautulli_ids,
            [entry.get("plex_user_id") for entry in mapping.values()],
        )
        return None

    return int(matched["user_id"])
