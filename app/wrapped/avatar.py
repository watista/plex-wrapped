from __future__ import annotations

import re

# Plex default profile images (letter on colored background) are served from this path.
# Uploaded Plex profile photos use the same URL shape, so they cannot be told apart reliably.
_PLEX_AVATAR_RE = re.compile(
    r"^https?://(?:[a-z0-9-]+\.)?plex\.tv/users/[^/]+/avatar(?:\?.*)?$",
    re.IGNORECASE,
)
_PLACEHOLDER_RE = re.compile(r"gravatar-default|interfaces/default/images", re.IGNORECASE)


def _is_placeholder(url: str) -> bool:
    return bool(_PLACEHOLDER_RE.search(url))


def _is_plex_letter_avatar(url: str) -> bool:
    return bool(_PLEX_AVATAR_RE.match(url))


def resolve_avatar_url(
    thumb: str | None,
    *,
    custom_thumb: str | None = None,
) -> str | None:
    """Return a displayable custom avatar URL, or None for the app fallback.

    Tautulli stores Plex's generated letter avatar in ``thumb`` / ``user_thumb``.
    When an admin sets a separate image via Tautulli (``custom_avatar_url``), that
    URL differs from ``thumb`` and is treated as a real custom avatar.

    Standard ``plex.tv/users/.../avatar`` URLs are always treated as letter
    avatars because Plex-hosted profile photos share the same URL pattern.
    """
    custom = (custom_thumb or "").strip()
    base = (thumb or "").strip()

    if custom and base and custom != base and not _is_placeholder(custom):
        if custom.startswith(("http://", "https://")):
            return custom

    if not base:
        return None
    if _is_placeholder(base) or _is_plex_letter_avatar(base):
        return None
    if base.startswith(("http://", "https://")):
        return base
    return None
