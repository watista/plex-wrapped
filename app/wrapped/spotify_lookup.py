from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

import httpx

from app.wrapped.theme_lookup import ThemeTrack, _title_overlap

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SEARCH_URL = "https://api.spotify.com/v1/search"


@dataclass(frozen=True)
class SpotifyCredentials:
    client_id: str
    client_secret: str

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


class SpotifyClient:
    def __init__(self, credentials: SpotifyCredentials) -> None:
        self._credentials = credentials
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    @classmethod
    def from_settings(cls, settings) -> SpotifyClient | None:
        creds = SpotifyCredentials(
            client_id=(getattr(settings, "spotify_client_id", "") or "").strip(),
            client_secret=(getattr(settings, "spotify_client_secret", "") or "").strip(),
        )
        if not creds.configured:
            return None
        return cls(creds)

    def _ensure_token(self, client: httpx.Client) -> str | None:
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token
        try:
            response = client.post(
                _TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self._credentials.client_id, self._credentials.client_secret),
            )
            response.raise_for_status()
            payload = response.json()
            self._token = payload.get("access_token")
            expires_in = int(payload.get("expires_in") or 3600)
            self._token_expires_at = time.time() + expires_in
            return self._token
        except Exception:
            logger.debug("Spotify token request failed", exc_info=True)
            return None

    def _search_tracks(self, client: httpx.Client, query: str, *, limit: int = 8) -> list[dict]:
        token = self._ensure_token(client)
        if not token:
            return []
        try:
            response = client.get(
                _SEARCH_URL,
                params={"q": query, "type": "track", "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            items = response.json().get("tracks", {}).get("items") or []
            return [row for row in items if isinstance(row, dict)]
        except Exception:
            logger.debug("Spotify search failed for %r", query, exc_info=True)
            return []

    def _score_track_row(
        self,
        row: dict,
        *,
        media_title: str,
        media_kind: str,
        seed: ThemeTrack | None,
    ) -> float:
        track = (row.get("name") or "").strip()
        album = ""
        album_obj = row.get("album")
        if isinstance(album_obj, dict):
            album = (album_obj.get("name") or "").strip()
        artists = [
            (a.get("name") or "").strip()
            for a in (row.get("artists") or [])
            if isinstance(a, dict) and (a.get("name") or "").strip()
        ]
        artist = artists[0] if artists else ""
        if not track:
            return -999.0

        blob = f"{track} {artist} {album}".lower()
        score = 0.0
        if "soundtrack" in blob or "score" in blob or "ost" in blob:
            score += 30
        if media_kind == "show" and ("series" in blob or "television" in blob):
            score += 10
        if media_kind == "movie" and ("motion picture" in blob or "film" in blob):
            score += 8
        score += _title_overlap(media_title, album) * 10
        score += _title_overlap(media_title, track) * 4

        if seed:
            if _normalize_match(seed.track_name, track):
                score += 35
            if seed.artist_name and any(_normalize_match(seed.artist_name, a) for a in artists):
                score += 25
            if seed.album_name and _normalize_match(seed.album_name, album):
                score += 15

        if row.get("track_number") == 1:
            score += 8

        return score

    def refine_theme_track(
        self,
        *,
        media_title: str,
        year: int | None,
        media_kind: str,
        seed: ThemeTrack | None,
    ) -> ThemeTrack | None:
        queries: list[str] = []
        if seed and seed.track_name and seed.artist_name:
            queries.append(f'track:"{seed.track_name}" artist:"{seed.artist_name}"')
            queries.append(f"{seed.track_name} {seed.artist_name}")
        if seed and seed.track_name:
            queries.append(f"{seed.track_name} soundtrack")
        if year:
            queries.append(f"{media_title} {year} soundtrack")
        queries.append(f"{media_title} soundtrack")

        best: ThemeTrack | None = None
        best_score = -999.0

        try:
            with httpx.Client(timeout=12.0) as client:
                for query in queries:
                    for row in self._search_tracks(client, query, limit=10):
                        score = self._score_track_row(
                            row,
                            media_title=media_title,
                            media_kind=media_kind,
                            seed=seed,
                        )
                        if score <= best_score:
                            continue
                        track = (row.get("name") or "").strip()
                        artists = [
                            (a.get("name") or "").strip()
                            for a in (row.get("artists") or [])
                            if isinstance(a, dict)
                        ]
                        artist = artists[0] if artists else ""
                        album = ""
                        album_obj = row.get("album")
                        if isinstance(album_obj, dict):
                            album = (album_obj.get("name") or "").strip()
                        if not track:
                            continue
                        best_score = score
                        best = ThemeTrack(
                            track_name=track,
                            artist_name=artist,
                            album_name=album,
                            source="spotify",
                        )
                    if best and best_score >= 45:
                        break
        except Exception:
            logger.debug("Spotify refine failed for %r", media_title, exc_info=True)
            return seed

        if best and best_score >= 35:
            logger.info(
                "Theme track (Spotify) media=%r track=%r artist=%r score=%.1f",
                media_title,
                best.track_name,
                best.artist_name,
                best_score,
            )
            return best
        return seed


def _normalize_match(a: str, b: str) -> bool:
    aa = re.sub(r"\s+", " ", (a or "").strip().lower())
    bb = re.sub(r"\s+", " ", (b or "").strip().lower())
    return bool(aa and bb and (aa == bb or aa in bb or bb in aa))
