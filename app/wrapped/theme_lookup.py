from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import httpx

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

MediaKind = Literal["movie", "show"]
_LOOKUP_VERSION = 3

_THEME_TRACK_WORDS = (
    "main title",
    "main theme",
    "opening theme",
    "opening titles",
    "end titles",
    "theme",
    "overture",
    "prologue",
)
_SOUNDTRACK_WORDS = ("soundtrack", "original score", "ost", "score")
_BAD_YT_WORDS = (
    "bhojpuri",
    "bollywood",
    "bollywood",
    "telugu",
    "tamil",
    "hindi",
    "punjabi",
    "marathi",
    "gujarati",
    "bengali",
    "urdu",
    "remix",
    "cover version",
    "karaoke",
    "lyrics video",
    "with lyrics",
    "reaction",
    "tutorial",
    "full movie",
    "full film",
    "trailer",
    "nightcore",
    "bass boosted",
    "1 hour",
    "10 hours",
    "8 hours",
    "lofi",
    "mashup",
    "violin cover",
    "piano cover",
    "guitar cover",
    "flute",
    "ringtone",
    "tiktok",
    "dj ",
    "punjabi",
    "desi",
    "item song",
    "devotional",
    "wedding",
    "status video",
    "shorts",
    "slowed",
    "reverb",
)
_GOOD_YT_WORDS = (
    "official",
    "soundtrack",
    "ost",
    "theme",
    "score",
    "main title",
    "original",
    "composer",
    "extended",
)

# Minimum score to accept a YouTube candidate.
_MIN_SCORE_STRICT = 55.0
_MIN_SCORE_RELAXED = 30.0
_MIN_SCORE_FALLBACK = 22.0

# Fixed background track per slide (non-theme slides). Slide id -> YouTube video id.
FIXED_SLIDE_VIDEO_IDS: dict[str, str] = {
    "welcome": "dW9xbFLaatU",
    "watch-time": "U9FzgsF2T-s",
    "total-plays": "AJgE_dLWsuQ",
    "movies-vs-tv": "AdQ3JDLlmPI",
    "series-depth": "uyIVAm9PVrI",
    "when-you-watch": "s2TyVQGoCYo",
    "favorite-device": "ilfYnhXD-bE",
    "longest-streak": "-RcPZdihrp4",
    "server-rank": "9UaJAnnipkY",
    "telegram-requests": "zNPXnAVyAUA",
    "persona": "KPhqU--Mq1A",
}

_INSTRUMENTAL_QUERY_SUFFIX = " instrumental only"

_GENRE_YT_QUERIES: dict[str, list[str]] = {
    "action": [
        "epic action movie soundtrack orchestral theme official",
        "action film score main theme instrumental",
    ],
    "adventure": [
        "adventure film soundtrack orchestral theme official",
        "adventure movie score instrumental",
    ],
    "animation": [
        "animated film soundtrack theme official instrumental",
        "animation movie score main theme",
    ],
    "comedy": [
        "comedy film soundtrack theme official instrumental",
        "lighthearted movie score theme",
    ],
    "crime": [
        "crime drama soundtrack theme official instrumental",
        "noir film score theme",
    ],
    "documentary": [
        "documentary soundtrack piano theme instrumental",
        "documentary film score ambient",
    ],
    "drama": [
        "drama film soundtrack piano theme official instrumental",
        "emotional movie score theme orchestral",
    ],
    "family": [
        "family film soundtrack theme official instrumental",
        "family movie score theme",
    ],
    "fantasy": [
        "fantasy film soundtrack orchestral theme official",
        "fantasy movie score main theme",
    ],
    "history": [
        "historical film soundtrack orchestral theme official",
        "period drama score theme instrumental",
    ],
    "horror": [
        "horror film soundtrack theme official instrumental",
        "horror movie score ambient theme",
    ],
    "music": [
        "musical film soundtrack theme official",
        "music biopic score theme instrumental",
    ],
    "mystery": [
        "mystery thriller soundtrack theme official instrumental",
        "suspense film score theme",
    ],
    "romance": [
        "romance film soundtrack piano theme official instrumental",
        "romantic movie score theme",
    ],
    "sci_fi": [
        "science fiction film soundtrack theme official instrumental",
        "sci-fi movie score orchestral theme",
    ],
    "thriller": [
        "thriller film soundtrack theme official instrumental",
        "suspense movie score theme",
    ],
    "war": [
        "war film soundtrack orchestral theme official",
        "war movie score theme instrumental",
    ],
    "western": [
        "western film soundtrack theme official instrumental",
        "cowboy movie score theme",
    ],
    "cinematic": [
        "cinematic orchestral film score theme official instrumental",
        "movie soundtrack main theme piano orchestral",
    ],
}


@dataclass(frozen=True)
class ThemeTrack:
    track_name: str
    artist_name: str
    album_name: str
    source: str


@dataclass(frozen=True)
class YoutubeQuery:
    text: str
    min_score: float
    require_track_match: bool
    require_media_overlap: bool
    require_instrumental: bool = False


@dataclass(frozen=True)
class ThemeSearchPlan:
    queries: list[YoutubeQuery]
    track: ThemeTrack | None
    media_title: str


def cache_key(title: str, *, year: int | None, media_kind: MediaKind) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.strip().lower()).strip("_")[:72]
    return f"v{_LOOKUP_VERSION}_{media_kind}_{slug}_{year or 'na'}"


def genre_cache_key(slug: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "_", slug.strip().lower()).strip("_")[:48]
    return f"v{_LOOKUP_VERSION}_genre_{clean}"


def fixed_slide_cache_key(slide_id: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", slide_id.strip().lower()).strip("_")[:48]
    return f"v3_slide_{safe}"


def default_pool_cache_key(index: int, video_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", video_id)[:24]
    return f"v{_LOOKUP_VERSION}_default_{index:02d}_{safe_id}"


def genre_youtube_queries(slug: str) -> list[str]:
    base = _GENRE_YT_QUERIES.get(slug, _GENRE_YT_QUERIES["cinematic"])
    return [f"{q}{_INSTRUMENTAL_QUERY_SUFFIX}" for q in base]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _title_overlap(media_title: str, text: str) -> int:
    words = [w for w in re.findall(r"[a-z0-9]{3,}", _normalize(media_title))]
    if not words:
        return 0
    hay = _normalize(text)
    return sum(1 for w in words if w in hay)


def _score_itunes_track(
    row: dict,
    *,
    media_title: str,
    media_kind: MediaKind,
) -> float:
    track = (row.get("trackName") or "").strip()
    artist = (row.get("artistName") or "").strip()
    album = (row.get("collectionName") or "").strip()
    if not track:
        return -999.0

    score = 0.0
    blob = f"{track} {artist} {album}".lower()
    if any(w in blob for w in _SOUNDTRACK_WORDS):
        score += 25
    if media_kind == "show" and "television" in blob:
        score += 8
    if media_kind == "movie" and "motion picture" in blob:
        score += 8

    track_lower = track.lower()
    if any(w in track_lower for w in _THEME_TRACK_WORDS):
        score += 20
    if row.get("trackNumber") == 1:
        score += 12

    score += _title_overlap(media_title, album) * 6
    score += _title_overlap(media_title, track) * 3

    if row.get("kind") == "song":
        score += 5
    return score


def lookup_itunes_theme_track(
    title: str,
    *,
    year: int | None,
    media_kind: MediaKind,
) -> ThemeTrack | None:
    queries: list[str] = []
    if year:
        queries.append(f"{title} {year} soundtrack")
    queries.append(f"{title} soundtrack")
    if media_kind == "show":
        queries.append(f"{title} television soundtrack")

    best: ThemeTrack | None = None
    best_score = -999.0

    try:
        with httpx.Client(timeout=12.0) as client:
            for query in queries:
                response = client.get(
                    "https://itunes.apple.com/search",
                    params={"term": query, "entity": "song", "limit": 12},
                )
                response.raise_for_status()
                for row in response.json().get("results") or []:
                    if not isinstance(row, dict):
                        continue
                    score = _score_itunes_track(row, media_title=title, media_kind=media_kind)
                    if score <= best_score:
                        continue
                    track = (row.get("trackName") or "").strip()
                    artist = (row.get("artistName") or "").strip()
                    album = (row.get("collectionName") or "").strip()
                    if not track:
                        continue
                    best_score = score
                    best = ThemeTrack(
                        track_name=track,
                        artist_name=artist,
                        album_name=album,
                        source="itunes",
                    )
                if best and best_score >= 35:
                    break
    except Exception:
        logger.debug("iTunes theme lookup failed for %r", title, exc_info=True)

    if best:
        logger.info(
            "Theme track (iTunes) media=%r track=%r artist=%r",
            title,
            best.track_name,
            best.artist_name,
        )
    return best


def lookup_musicbrainz_theme_track(
    title: str,
    *,
    year: int | None,
    media_kind: MediaKind,
) -> ThemeTrack | None:
    kind_tag = "film" if media_kind == "movie" else "television"
    query = f'recording:"{title}" AND tag:{kind_tag} AND (tag:soundtrack OR releasegroup:soundtrack)'
    if year:
        query += f" AND date:{year}"

    headers = {"User-Agent": "PlexWrapped/1.0 (https://github.com/plex-wrapped)"}
    try:
        with httpx.Client(timeout=12.0, headers=headers) as client:
            response = client.get(
                "https://musicbrainz.org/ws/2/recording",
                params={"query": query, "fmt": "json", "limit": 8},
            )
            response.raise_for_status()
            recordings = response.json().get("recordings") or []
    except Exception:
        logger.debug("MusicBrainz theme lookup failed for %r", title, exc_info=True)
        return None

    best: ThemeTrack | None = None
    best_score = -999.0
    for row in recordings:
        if not isinstance(row, dict):
            continue
        track = (row.get("title") or "").strip()
        if not track:
            continue
        artist = ""
        for ac in row.get("artist-credit") or []:
            if isinstance(ac, dict) and isinstance(ac.get("artist"), dict):
                artist = (ac["artist"].get("name") or "").strip()
                if artist:
                    break
        score = 0.0
        track_lower = track.lower()
        if any(w in track_lower for w in _THEME_TRACK_WORDS):
            score += 25
        score += _title_overlap(title, track) * 5
        if score > best_score:
            best_score = score
            best = ThemeTrack(
                track_name=track,
                artist_name=artist,
                album_name="",
                source="musicbrainz",
            )

    if best:
        logger.info(
            "Theme track (MusicBrainz) media=%r track=%r artist=%r",
            title,
            best.track_name,
            best.artist_name,
        )
    return best


def lookup_theme_track(
    title: str,
    *,
    year: int | None,
    media_kind: MediaKind,
    settings: Settings | None,
) -> ThemeTrack | None:
    """Resolve theme via iTunes → MusicBrainz → Spotify refinement."""
    track = lookup_itunes_theme_track(title, year=year, media_kind=media_kind)
    if not track:
        time.sleep(0.35)
        track = lookup_musicbrainz_theme_track(title, year=year, media_kind=media_kind)

    if settings is None:
        return track

    from app.wrapped.spotify_lookup import SpotifyClient

    spotify = SpotifyClient.from_settings(settings)
    if spotify is None:
        return track

    refined = spotify.refine_theme_track(
        media_title=title,
        year=year,
        media_kind=media_kind,
        seed=track,
    )
    return refined or track


def build_youtube_search_plan(
    title: str,
    *,
    year: int | None,
    media_kind: MediaKind,
    settings: Settings | None = None,
) -> ThemeSearchPlan:
    queries: list[YoutubeQuery] = []
    track = lookup_theme_track(title, year=year, media_kind=media_kind, settings=settings)

    def add(
        text: str,
        *,
        min_score: float,
        require_track_match: bool = False,
        require_media_overlap: bool = False,
    ) -> None:
        cleaned = " ".join(text.split()).strip()
        if not cleaned:
            return
        if any(q.text.lower() == cleaned.lower() for q in queries):
            return
        queries.append(
            YoutubeQuery(
                text=cleaned,
                min_score=min_score,
                require_track_match=require_track_match,
                require_media_overlap=require_media_overlap,
            )
        )

    if track and track.artist_name:
        add(
            f'"{track.track_name}" "{track.artist_name}" official soundtrack',
            min_score=_MIN_SCORE_STRICT,
            require_track_match=True,
        )
        add(
            f"{track.artist_name} - {track.track_name} official audio soundtrack",
            min_score=_MIN_SCORE_STRICT,
            require_track_match=True,
        )
        add(
            f"{track.artist_name} {track.track_name} ost theme",
            min_score=_MIN_SCORE_STRICT,
            require_track_match=True,
        )
    if track:
        add(
            f'"{track.track_name}" official soundtrack theme',
            min_score=_MIN_SCORE_STRICT,
            require_track_match=True,
        )
        if track.album_name:
            add(
                f'"{track.track_name}" "{track.album_name}"',
                min_score=_MIN_SCORE_RELAXED,
                require_track_match=True,
            )

    kind_label = "TV series" if media_kind == "show" else "film"
    if year:
        add(
            f'"{title}" {year} {kind_label} main theme official soundtrack',
            min_score=_MIN_SCORE_RELAXED,
            require_media_overlap=True,
        )
    add(
        f'"{title}" {kind_label} main theme official soundtrack',
        min_score=_MIN_SCORE_FALLBACK,
        require_media_overlap=True,
    )

    return ThemeSearchPlan(queries=queries, track=track, media_title=title)


def score_youtube_candidate(
    *,
    video_title: str,
    duration: int | None,
    media_title: str,
    theme_track: ThemeTrack | None,
    require_track_match: bool = False,
    require_media_overlap: bool = False,
    require_instrumental: bool = False,
) -> float:
    title_lower = video_title.lower()
    score = 0.0

    for bad in _BAD_YT_WORDS:
        if bad in title_lower:
            score -= 50

    for good in _GOOD_YT_WORDS:
        if good in title_lower:
            score += 7

    overlap = _title_overlap(media_title, video_title)
    score += overlap * 10

    if require_media_overlap and overlap == 0:
        score -= 40

    track_match = False
    artist_match = False
    if theme_track:
        track_norm = _normalize(theme_track.track_name)
        if track_norm and track_norm in title_lower:
            track_match = True
            score += 40
        if theme_track.artist_name:
            artist_norm = _normalize(theme_track.artist_name)
            if artist_norm and artist_norm in title_lower:
                artist_match = True
                score += 28
            last_name = artist_norm.split()[-1] if artist_norm else ""
            if len(last_name) > 3 and last_name in title_lower:
                score += 10
        for word in re.findall(r"[a-z0-9]{4,}", track_norm):
            if word in title_lower:
                score += 3

    if require_track_match and not (track_match or artist_match):
        score -= 60

    if require_instrumental:
        instrumental_markers = (
            "instrumental",
            "orchestral",
            "orchestra",
            "score",
            "ost",
            "ambient",
            "piano instrumental",
            "strings",
            "soundtrack",
        )
        vocal_markers = (
            "vocal",
            "vocals",
            "with lyrics",
            "lyrics",
            "singing",
            " feat ",
            " ft ",
            "official music video",
            "music video",
            "live performance",
            "concert",
            "acoustic version",
        )
        if any(marker in title_lower for marker in instrumental_markers):
            score += 25
        else:
            score -= 35
        if any(marker in title_lower for marker in vocal_markers):
            score -= 50

    if duration is not None:
        if 50 <= duration <= 360:
            score += 20
        elif duration > 480:
            score -= 30
        elif duration < 35:
            score -= 20

    return score
