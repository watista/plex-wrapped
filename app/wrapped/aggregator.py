from __future__ import annotations

import logging
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

from app.ai import CursorAIClient, build_facts, generate_ai_copy
from app.config import Settings, get_settings
from app.models.cache import WrappedCache
from app.models.schemas import GenreStat, MediaItem, ServerRankEntry, ServerStats, TelegramStats, WrappedPayload
from app.tautulli.client import TautulliClient
from app.telegram.loader import (
    TelegramData,
    count_unique_matched,
    load_telegram_data,
)
from app.wrapped.avatar import resolve_avatar_url
from app.wrapped.locale import month_number_to_dutch, to_dutch_day, to_dutch_month, weekday_number_to_dutch
from app.wrapped.posters import resolve_poster
from app.wrapped.slides import apply_persona
from app.wrapped.tmdb_actors import compute_top_actors


def _year_range(year: int) -> tuple[str, str, int]:
    after = f"{year}-01-01"
    before = f"{year}-12-31"
    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year, 12, 31)
    days = (end_dt - start_dt).days + 1
    return after, before, days


def _media_key(row: dict[str, Any], media_type: str) -> tuple[str, str | None]:
    if media_type == "episode":
        title = row.get("grandparent_title") or row.get("title") or "Unknown"
        thumb = row.get("grandparent_thumb") or row.get("thumb")
        return title, thumb
    title = row.get("full_title") or row.get("title") or "Unknown"
    return title, row.get("thumb")


def _longest_streak(play_dates: list[date]) -> tuple[int, date | None, date | None]:
    if not play_dates:
        return 0, None, None
    unique = sorted(set(play_dates))
    best_len = 1
    best_start = unique[0]
    best_end = unique[0]
    cur_start = unique[0]
    cur_len = 1
    for i in range(1, len(unique)):
        prev = unique[i - 1]
        cur = unique[i]
        if (cur - prev).days == 1:
            cur_len += 1
        else:
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
                best_end = unique[i - 1]
            cur_start = cur
            cur_len = 1
    if cur_len > best_len:
        best_len = cur_len
        best_start = cur_start
        best_end = unique[-1]
    return best_len, best_start, best_end


def _top_genres(counter: Counter[str], limit: int = 5) -> list[GenreStat]:
    return [GenreStat(name=name, plays=plays) for name, plays in counter.most_common(limit)]


def _duration_from_top10_series(series: list[dict[str, Any]], index: int) -> int:
    total = 0
    for entry in series:
        data = entry.get("data", [])
        if index < len(data):
            total += int(data[index] or 0)
    return total


def _ranked_users_from_top10(top_users: dict[str, Any]) -> list[dict[str, Any]]:
    categories = top_users.get("categories", [])
    series = top_users.get("series", [])
    if not categories or not series:
        return []
    return [
        {
            "user_id": None,
            "name": name,
            "username": "",
            "duration": _duration_from_top10_series(series, i),
        }
        for i, name in enumerate(categories)
    ]


def _ranked_users_from_server_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[int, dict[str, Any]] = {}
    for row in history:
        if row.get("media_type") not in ("movie", "episode"):
            continue
        raw_uid = row.get("user_id")
        if raw_uid is None:
            continue
        uid = int(raw_uid)
        duration = int(row.get("duration") or 0)
        if uid not in totals:
            totals[uid] = {
                "user_id": uid,
                "name": row.get("friendly_name") or row.get("user") or "",
                "username": "",
                "duration": 0,
            }
        totals[uid]["duration"] += duration
        if not totals[uid]["name"]:
            totals[uid]["name"] = row.get("friendly_name") or row.get("user") or ""
    ranked = list(totals.values())
    ranked.sort(key=lambda item: item["duration"], reverse=True)
    return ranked


def _fetch_year_ranked_users(
    tautulli: TautulliClient,
    *,
    after: str,
    before: str,
    cache: "WrappedAggregator | None" = None,
) -> list[dict[str, Any]]:
    """User watch durations for the wrapped calendar period (not all-time)."""
    if cache is not None and cache._year_ranked_users is not None:
        return cache._year_ranked_users

    ranked: list[dict[str, Any]] = []
    try:
        server_history = tautulli.fetch_server_history(after=after, before=before)
        ranked = _ranked_users_from_server_history(server_history)
        if ranked:
            logger.info(
                "Server rank source=server_history users=%s after=%s before=%s",
                len(ranked),
                after,
                before,
            )
    except Exception:
        logger.warning("Server history ranking failed", exc_info=True)

    if cache is not None:
        cache._year_ranked_users = ranked
    return ranked


def _position_label(offset: int) -> str:
    if offset == 0:
        return "Jij"
    if offset == -1:
        return "Eén plek hoger"
    if offset == 1:
        return "Eén plek lager"
    if offset < -1:
        return f"{abs(offset)} plekken hoger"
    return f"{offset} plekken lager"


def _build_rank_context(
    ranked: list[dict[str, Any]],
    user_index: int,
) -> list[ServerRankEntry]:
    if not ranked:
        return []

    indices: set[int] = set()
    for offset in (-1, 0, 1):
        idx = user_index + offset
        if 0 <= idx < len(ranked):
            indices.add(idx)

    # Always surface the server leader so everyone sees the #1 user's stats.
    indices.add(0)

    # When the viewer is the leader there is nobody above them, so show the
    # chasing pack (spots 2 and 3) instead.
    if user_index == 0:
        for idx in (1, 2):
            if idx < len(ranked):
                indices.add(idx)

    context: list[ServerRankEntry] = []
    for idx in sorted(indices):
        offset = idx - user_index
        is_you = idx == user_index
        if idx == 0 and not is_you and offset < -1:
            label = "Koploper"
        else:
            label = _position_label(offset)
        row = ranked[idx]
        context.append(
            ServerRankEntry(
                rank=idx + 1,
                watch_hours=int(round(int(row.get("duration", 0)) / 3600)),
                is_you=is_you,
                position_label=label,
            )
        )
    return context


def _match_user_index(
    ranked: list[dict[str, Any]],
    *,
    user_id: int,
    display_name: str,
    username: str,
) -> int | None:
    for i, row in enumerate(ranked):
        row_id = row.get("user_id")
        if row_id is not None and int(row_id) == user_id:
            return i
        friendly = (row.get("friendly_name") or row.get("name") or "").strip()
        row_username = (row.get("username") or "").strip()
        if friendly and (friendly == display_name or username in friendly):
            return i
        if row_username and row_username == username:
            return i
    return None


def _compute_server_stats(
    *,
    user_id: int,
    display_name: str,
    username: str,
    user_watch_seconds: int,
    year_ranked: list[dict[str, Any]] | None = None,
    users_table: dict[str, Any] | None = None,
    top_users: dict[str, Any] | None = None,
    total_users: int | None = None,
) -> ServerStats:
    stats = ServerStats()

    ranked: list[dict[str, Any]] = []

    if year_ranked:
        ranked = year_ranked
    elif users_table:
        rows = users_table.get("data", [])
        if isinstance(rows, list):
            ranked = [
                {
                    "user_id": row.get("user_id"),
                    "name": row.get("friendly_name") or row.get("username") or "",
                    "username": row.get("username") or "",
                    "duration": int(row.get("duration") or 0),
                }
                for row in rows
                if isinstance(row, dict)
            ]
            ranked.sort(key=lambda item: item["duration"], reverse=True)

    if not ranked and top_users:
        ranked = _ranked_users_from_top10(top_users)

    if not ranked:
        return stats

    user_index = _match_user_index(
        ranked,
        user_id=user_id,
        display_name=display_name,
        username=username,
    )
    if user_index is None:
        return stats

    rank = user_index + 1
    stats.rank = rank
    stats.rank_context = _build_rank_context(ranked, user_index)

    if total_users is None:
        if users_table:
            total_users = int(users_table.get("recordsTotal") or len(ranked))
        else:
            total_users = len(ranked)
    if total_users <= 0:
        total_users = len(ranked)
    if total_users > 0:
        stats.more_active_than_percent = int(
            round(max(0, min(100, (total_users - rank) / total_users * 100)))
        )

    if stats.rank_context:
        for entry in stats.rank_context:
            if entry.is_you:
                entry.watch_hours = int(round(user_watch_seconds / 3600))

    return stats


def _history_row_date(row: dict[str, Any]) -> date | None:
    ts = row.get("date")
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()


def _compute_watch_timing(
    media_history: list[dict[str, Any]],
    year: int,
) -> dict[str, Any]:
    """Per-month activity, busiest-month calendar, and weekday play counts from history."""
    month_play_counts: Counter[int] = Counter()
    month_day_play_counts: dict[int, Counter[int]] = defaultdict(Counter)
    weekday_play_counts: Counter[int] = Counter()

    for row in media_history:
        row_date = _history_row_date(row)
        if not row_date or row_date.year != year:
            continue
        month_play_counts[row_date.month] += 1
        month_day_play_counts[row_date.month][row_date.day] += 1
        weekday_play_counts[row_date.weekday()] += 1

    busiest_month_index: int | None = None
    busiest_month: str | None = None
    busiest_month_daily_plays: list[int] = []
    busiest_month_first_weekday = 0
    plays_by_weekday = [weekday_play_counts.get(i, 0) for i in range(7)]

    if month_play_counts:
        busiest_month_index = max(month_play_counts, key=month_play_counts.get)
        busiest_month = month_number_to_dutch(busiest_month_index)
        days_in_month = monthrange(year, busiest_month_index)[1]
        day_counts = month_day_play_counts[busiest_month_index]
        busiest_month_daily_plays = [day_counts.get(day, 0) for day in range(1, days_in_month + 1)]
        busiest_month_first_weekday = date(year, busiest_month_index, 1).weekday()

    return {
        "busiest_month": busiest_month,
        "busiest_month_index": busiest_month_index,
        "busiest_month_daily_plays": busiest_month_daily_plays,
        "busiest_month_first_weekday": busiest_month_first_weekday,
        "plays_by_weekday": plays_by_weekday,
        "peak_day": weekday_number_to_dutch(max(range(7), key=lambda i: weekday_play_counts.get(i, 0)))
        if weekday_play_counts
        else None,
    }


_COMPARISON_HEADLINE_ACCENTS = ("eigenzinnige", "verfijnde", "unieke", "eigen")


def _comparison_headline_accent(server_title: str, user_title: str) -> str:
    key = f"{server_title.lower()}|{user_title.lower()}"
    idx = sum(ord(c) for c in key) % len(_COMPARISON_HEADLINE_ACCENTS)
    return _COMPARISON_HEADLINE_ACCENTS[idx]


def _build_comparison_caption(
    server_title: str,
    user_title: str,
    *,
    same_show: bool,
    reason: str | None,
) -> str:
    if same_show:
        return (
            f"Iedereen op de server draaide {server_title} — jij inclusief. "
            "Great minds think alike."
        )
    if reason == "first_played":
        return (
            f"Terwijl de server massaal naar {server_title} keek, "
            f"startte jij het jaar met {user_title}."
        )
    return (
        f"Terwijl de server naar {server_title} keek, "
        f"was {user_title} jouw nummer één."
    )


class WrappedAggregator:
    def __init__(
        self,
        tautulli: TautulliClient,
        settings: Settings | None = None,
        telegram: TelegramData | None = None,
        cache: WrappedCache | None = None,
        year: int | None = None,
        ai: CursorAIClient | None = None,
    ):
        self.tautulli = tautulli
        self.settings = settings or get_settings()
        self.year = year if year is not None else self.settings.wrapped_year
        self.telegram = telegram if telegram is not None else load_telegram_data(self.settings, self.year)
        self.cache = cache or WrappedCache(self.settings)
        # Connection to Cursor AI. Available during compute() so future features
        # (e.g. dynamic punchlines) can call self.ai.generate_text(...).
        self.ai = ai or CursorAIClient(self.settings)
        self._metadata_cache: dict[str, dict[str, Any]] = {}
        self._tmdb_poster_cache: dict[tuple[str, str], str | None] = {}
        self._tmdb_credits_cache: dict[tuple[str, int], list[dict[str, Any]]] = {}
        self._tmdb_search_cache: dict[tuple[str, str], int | None] = {}
        self._server_top_show: tuple[str | None, str | None] | None = None
        self._server_top_movie: tuple[str | None, str | None] | None = None
        self._home_stats: list[dict[str, Any]] | None = None
        self._year_ranked_users: list[dict[str, Any]] | None = None

    def get_cached(self, user_id: int) -> WrappedPayload | None:
        cached = self.cache.get(user_id, self.year)
        if not cached:
            return None
        return WrappedPayload(**cached)

    def get_or_compute(self, user_id: int, *, force: bool = False) -> WrappedPayload:
        if not force:
            cached = self.get_cached(user_id)
            if cached:
                logger.info(
                    "Cache hit user_id=%s year=%s plays=%s watch_hours=%s",
                    user_id,
                    self.year,
                    cached.total_plays,
                    cached.watch_hours,
                )
                return cached
        logger.info("Computing wrapped user_id=%s year=%s force=%s", user_id, self.year, force)
        payload = self.compute(user_id)
        self.cache.set(user_id, self.year, payload.model_dump())
        return payload

    def _get_metadata(self, rating_key: str | int) -> dict[str, Any]:
        key = str(rating_key)
        if key in self._metadata_cache:
            return self._metadata_cache[key]
        try:
            meta = self.tautulli.get_metadata(rating_key=key)
            cached = meta if isinstance(meta, dict) else {}
        except Exception:
            cached = {}
        self._metadata_cache[key] = cached
        return cached

    def _get_metadata_genres(self, rating_key: str | int) -> list[str]:
        meta = self._get_metadata(rating_key)
        genres = meta.get("genres") or []
        return [g if isinstance(g, str) else str(g) for g in genres if g]

    def _resolve_poster(
        self,
        *,
        thumb: str | None,
        rating_key: str | int | None,
        title: str,
        media_kind: Literal["movie", "show"],
    ) -> str | None:
        return resolve_poster(
            settings=self.settings,
            thumb=thumb,
            rating_key=rating_key,
            title=title,
            media_kind=media_kind,
            get_metadata=self._get_metadata,
            tmdb_cache=self._tmdb_poster_cache,
        )

    def _get_home_stats(self, time_range_days: int) -> list[dict[str, Any]]:
        if self._home_stats is not None:
            return self._home_stats
        blocks: list[dict[str, Any]] = []
        try:
            # NOTE: passing stat_id makes some Tautulli versions return nothing,
            # so we fetch every block and filter by stat_id ourselves.
            blocks = self.tautulli.get_home_stats(
                time_range=time_range_days,
                stat_id=None,
                stats_count=5,
            )
        except Exception:
            logger.warning("get_home_stats failed", exc_info=True)
        self._home_stats = blocks
        return blocks

    def _home_stat_rows(self, time_range_days: int, stat_id: str) -> list[dict[str, Any]]:
        for block in self._get_home_stats(time_range_days):
            if block.get("stat_id") == stat_id:
                return block.get("rows") or []
        return []

    def _get_server_top_show(self, time_range_days: int) -> tuple[str | None, str | None]:
        if self._server_top_show is not None:
            return self._server_top_show
        title: str | None = None
        thumb: str | None = None
        rows = self._home_stat_rows(time_range_days, "top_tv")
        if rows:
            row = rows[0]
            title = row.get("grandparent_title") or row.get("title") or row.get("full_title")
            thumb = row.get("grandparent_thumb") or row.get("thumb")
        self._server_top_show = (title, thumb)
        return title, thumb

    def _get_server_top_movie(self, time_range_days: int) -> tuple[str | None, str | None]:
        if self._server_top_movie is not None:
            return self._server_top_movie
        title: str | None = None
        thumb: str | None = None
        rows = self._home_stat_rows(time_range_days, "top_movies")
        if rows:
            row = rows[0]
            title = row.get("title") or row.get("full_title")
            thumb = row.get("thumb")
        self._server_top_movie = (title, thumb)
        return title, thumb

    def compute(self, user_id: int) -> WrappedPayload:
        user = self.tautulli.get_user(user_id)
        after, before, time_range_days = _year_range(self.year)
        logger.debug("Cursor AI enabled=%s for user_id=%s", self.ai.enabled, user_id)
        logger.info(
            "Fetching history user_id=%s after=%s before=%s time_range_days=%s",
            user_id,
            after,
            before,
            time_range_days,
        )

        history = self.tautulli.fetch_all_history(
            user_id=user_id,
            after=after,
            before=before,
        )
        media_history = [r for r in history if r.get("media_type") in ("movie", "episode")]
        media_types = Counter(row.get("media_type") or "unknown" for row in history)
        logger.info(
            "History rows user_id=%s total=%s movie_episode=%s by_media_type=%s",
            user_id,
            len(history),
            len(media_history),
            dict(media_types),
        )
        if not history:
            logger.warning(
                "No Tautulli history rows for user_id=%s between %s and %s",
                user_id,
                after,
                before,
            )
        elif not media_history:
            logger.warning(
                "History rows present but none are movie/episode for user_id=%s: %s",
                user_id,
                dict(media_types),
            )

        display_name = user.get("friendly_name") or user.get("username") or "Viewer"
        username = user.get("username") or ""
        avatar = resolve_avatar_url(
            user.get("user_thumb"),
            custom_thumb=user.get("custom_avatar_url") or user.get("custom_thumb"),
        )

        total_seconds = 0
        movie_plays = tv_plays = 0
        movie_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"plays": 0, "duration": 0, "thumb": None, "rating_key": None, "last_ts": 0}
        )
        show_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"plays": 0, "duration": 0, "thumb": None, "rating_key": None, "last_ts": 0}
        )
        history_titles: list[str] = []
        play_dates: list[date] = []
        series_keys: set[str] = set()
        season_keys: set[tuple[str, str]] = set()
        episode_keys: set[str] = set()
        movie_genre_counter: Counter[str] = Counter()
        show_genre_counter: Counter[str] = Counter()
        player_durations: Counter[str] = Counter()

        sorted_episodes = sorted(
            [r for r in media_history if r.get("media_type") == "episode"],
            key=lambda r: r.get("date") or 0,
        )

        for row in media_history:
            media_type = row.get("media_type", "")
            duration = int(row.get("duration") or 0)
            row_ts = int(row.get("date") or 0)
            total_seconds += duration
            history_titles.append(
                row.get("grandparent_title") or row.get("title") or row.get("full_title") or ""
            )
            row_date = _history_row_date(row)
            if row_date:
                play_dates.append(row_date)

            player = row.get("player")
            if player:
                player_durations[str(player)] += duration

            if media_type == "movie":
                movie_plays += 1
                title, thumb = _media_key(row, media_type)
                movie_stats[title]["plays"] += 1
                movie_stats[title]["duration"] += duration
                movie_stats[title]["thumb"] = movie_stats[title]["thumb"] or thumb
                if row_ts > movie_stats[title]["last_ts"]:
                    movie_stats[title]["last_ts"] = row_ts
                rk = row.get("rating_key")
                if rk is not None:
                    movie_stats[title]["rating_key"] = movie_stats[title]["rating_key"] or str(rk)
                if rk is not None:
                    for genre in self._get_metadata_genres(rk):
                        movie_genre_counter[genre] += 1
            elif media_type == "episode":
                tv_plays += 1
                title, thumb = _media_key(row, media_type)
                show_stats[title]["plays"] += 1
                show_stats[title]["duration"] += duration
                show_stats[title]["thumb"] = show_stats[title]["thumb"] or thumb
                if row_ts > show_stats[title]["last_ts"]:
                    show_stats[title]["last_ts"] = row_ts
                gp = row.get("grandparent_rating_key")
                if gp is not None:
                    series_keys.add(str(gp))
                    show_stats[title]["rating_key"] = show_stats[title]["rating_key"] or str(gp)
                    season_idx = row.get("parent_media_index")
                    season_keys.add((str(gp), str(season_idx if season_idx is not None else "")))
                    for genre in self._get_metadata_genres(gp):
                        show_genre_counter[genre] += 1
                ep_rk = row.get("rating_key")
                if ep_rk is not None:
                    episode_keys.add(str(ep_rk))

        total_plays = movie_plays + tv_plays
        watch_hours = total_seconds // 3600
        watch_days = watch_hours // 24

        def to_media_items(
            stats: dict[str, dict[str, Any]],
            limit: int,
            media_kind: Literal["movie", "show"],
        ) -> list[MediaItem]:
            entries = list(stats.items())
            # When nothing was rewatched, "top" by plays is arbitrary, so surface
            # the most recently watched titles instead (newest first).
            all_watched_once = bool(entries) and all(d["plays"] <= 1 for _, d in entries)
            if all_watched_once:
                ranked = sorted(entries, key=lambda x: (-(x[1].get("last_ts") or 0), x[0]))
            else:
                ranked = sorted(entries, key=lambda x: (-x[1]["plays"], -x[1]["duration"]))
            items: list[MediaItem] = []
            for title, data in ranked[:limit]:
                items.append(
                    MediaItem(
                        title=title,
                        thumb=self._resolve_poster(
                            thumb=data.get("thumb"),
                            rating_key=data.get("rating_key"),
                            title=title,
                            media_kind=media_kind,
                        ),
                        plays=data["plays"],
                        duration_seconds=data["duration"],
                    )
                )
            return items

        top_movies = to_media_items(movie_stats, 5, "movie")
        top_shows = to_media_items(show_stats, 5, "show")

        top_actors = compute_top_actors(
            movie_stats=movie_stats,
            show_stats=show_stats,
            get_metadata=self._get_metadata,
            api_key=self.settings.tmdb_api_key,
            credits_cache=self._tmdb_credits_cache,
            search_cache=self._tmdb_search_cache,
        )
        if top_actors:
            logger.info(
                "Top actors user_id=%s leader=%s plays=%s titles=%s",
                user_id,
                top_actors[0].name,
                top_actors[0].plays,
                top_actors[0].title_count,
            )

        streak_days, streak_start, streak_end = _longest_streak(play_dates)

        user_comparison_show: str | None = None
        user_comparison_reason: str | None = None
        if show_stats:
            has_repeat = any(d["plays"] > 1 for d in show_stats.values())
            if has_repeat:
                best_title = max(show_stats.items(), key=lambda x: x[1]["plays"])[0]
                user_comparison_show = best_title
                user_comparison_reason = "most_played"
            elif sorted_episodes:
                first_row = sorted_episodes[0]
                user_comparison_show = _media_key(first_row, "episode")[0]
                user_comparison_reason = "first_played"

        # Movie equivalent — used as a fallback for the "server vs you" slide when
        # the user (or the server) has no series activity.
        user_comparison_movie: str | None = None
        if movie_stats:
            movie_has_repeat = any(d["plays"] > 1 for d in movie_stats.values())
            if movie_has_repeat:
                user_comparison_movie = max(movie_stats.items(), key=lambda x: x[1]["plays"])[0]
            else:
                user_comparison_movie = max(
                    movie_stats.items(), key=lambda x: x[1].get("last_ts") or 0
                )[0]

        watch_timing = _compute_watch_timing(media_history, self.year)
        busiest_month = watch_timing["busiest_month"]
        busiest_month_index = watch_timing["busiest_month_index"]
        busiest_month_daily_plays = watch_timing["busiest_month_daily_plays"]
        busiest_month_first_weekday = watch_timing["busiest_month_first_weekday"]
        plays_by_weekday = watch_timing["plays_by_weekday"]
        peak_day = watch_timing["peak_day"]
        peak_hour = None

        if not busiest_month:
            try:
                month_data = self.tautulli.get_plays_per_month(user_id=user_id, time_range=time_range_days)
                categories = month_data.get("categories", [])
                series = month_data.get("series", [])
                if categories and series:
                    totals = [
                        sum(s.get("data", [0])[i] if i < len(s.get("data", [])) else 0 for s in series)
                        for i in range(len(categories))
                    ]
                    if totals:
                        idx = totals.index(max(totals))
                        busiest_month = to_dutch_month(categories[idx])
            except Exception:
                pass

        if not peak_day:
            try:
                dow_data = self.tautulli.get_plays_by_dayofweek(user_id=user_id, time_range=time_range_days)
                categories = dow_data.get("categories", [])
                series = dow_data.get("series", [])
                if categories and series:
                    totals = [
                        sum(s.get("data", [0])[i] if i < len(s.get("data", [])) else 0 for s in series)
                        for i in range(len(categories))
                    ]
                    if totals:
                        peak_day = to_dutch_day(categories[totals.index(max(totals))])
            except Exception:
                pass

        try:
            hour_data = self.tautulli.get_plays_by_hourofday(user_id=user_id, time_range=time_range_days)
            categories = hour_data.get("categories", [])
            series = hour_data.get("series", [])
            if categories and series:
                totals = [
                    sum(s.get("data", [0])[i] if i < len(s.get("data", [])) else 0 for s in series)
                    for i in range(len(categories))
                ]
                if totals:
                    peak_hour = int(categories[totals.index(max(totals))])
        except Exception:
            pass

        favorite_device = None
        favorite_device_watch_percent = None
        if player_durations and total_seconds > 0:
            favorite_device, favorite_duration = player_durations.most_common(1)[0]
            favorite_device_watch_percent = int(round(favorite_duration / total_seconds * 100))

        if not favorite_device:
            try:
                players = self.tautulli.get_user_player_stats(user_id=user_id)
                if players:
                    top_player = max(players, key=lambda p: p.get("total_plays", 0))
                    favorite_device = top_player.get("player_name")
                    if favorite_device_watch_percent is None:
                        total_times = sum(int(p.get("total_time") or 0) for p in players)
                        top_time = int(top_player.get("total_time") or 0)
                        if total_times > 0 and top_time > 0:
                            favorite_device_watch_percent = int(round(top_time / total_times * 100))
                        else:
                            total_player_plays = sum(int(p.get("total_plays") or 0) for p in players)
                            top_plays = int(top_player.get("total_plays") or 0)
                            if total_player_plays > 0 and top_plays > 0:
                                favorite_device_watch_percent = int(
                                    round(top_plays / total_player_plays * 100)
                                )
            except Exception:
                pass

        year_ranked = _fetch_year_ranked_users(
            self.tautulli,
            after=after,
            before=before,
            cache=self,
        )
        server_user_count: int | None = None
        try:
            server_user_count = len(self.tautulli.get_users())
        except Exception:
            pass
        server_stats = _compute_server_stats(
            user_id=user_id,
            display_name=display_name,
            username=username,
            user_watch_seconds=total_seconds,
            year_ranked=year_ranked or None,
            total_users=server_user_count,
        )
        try:
            server_stats.server_name = self.tautulli.get_server_friendly_name()
        except Exception:
            pass
        server_top_title, server_top_thumb = self._get_server_top_show(time_range_days)
        server_stats.server_top_show = server_top_title
        if server_top_title:
            server_stats.server_top_show_thumb = self._resolve_poster(
                thumb=server_top_thumb,
                rating_key=None,
                title=server_top_title,
                media_kind="show",
            )
        else:
            server_stats.server_top_show_thumb = server_top_thumb

        server_top_movie_title, server_top_movie_thumb = self._get_server_top_movie(time_range_days)
        server_stats.server_top_movie = server_top_movie_title
        if server_top_movie_title:
            server_stats.server_top_movie_thumb = self._resolve_poster(
                thumb=server_top_movie_thumb,
                rating_key=None,
                title=server_top_movie_title,
                media_kind="movie",
            )
        else:
            server_stats.server_top_movie_thumb = server_top_movie_thumb

        user_comparison_show_thumb: str | None = None
        if user_comparison_show and user_comparison_show in show_stats:
            show_data = show_stats[user_comparison_show]
            user_comparison_show_thumb = self._resolve_poster(
                thumb=show_data.get("thumb"),
                rating_key=show_data.get("rating_key"),
                title=user_comparison_show,
                media_kind="show",
            )
        if not user_comparison_show_thumb and user_comparison_show:
            for item in top_shows:
                if item.title == user_comparison_show:
                    user_comparison_show_thumb = item.thumb
                    break

        user_comparison_movie_thumb: str | None = None
        if user_comparison_movie and user_comparison_movie in movie_stats:
            movie_data = movie_stats[user_comparison_movie]
            user_comparison_movie_thumb = self._resolve_poster(
                thumb=movie_data.get("thumb"),
                rating_key=movie_data.get("rating_key"),
                title=user_comparison_movie,
                media_kind="movie",
            )
        if not user_comparison_movie_thumb and user_comparison_movie:
            for item in top_movies:
                if item.title == user_comparison_movie:
                    user_comparison_movie_thumb = item.thumb
                    break

        comparison_same_show: bool | None = None
        comparison_headline_accent: str | None = None
        comparison_caption: str | None = None
        if server_top_title and user_comparison_show:
            comparison_same_show = server_top_title.lower() == user_comparison_show.lower()
            if not comparison_same_show:
                comparison_headline_accent = _comparison_headline_accent(
                    server_top_title,
                    user_comparison_show,
                )
            comparison_caption = _build_comparison_caption(
                server_top_title,
                user_comparison_show,
                same_show=comparison_same_show,
                reason=user_comparison_reason,
            )

        tg = self.telegram.by_plex_user_id.get(user_id)
        telegram_stats = TelegramStats()
        has_telegram = False
        if tg:
            unique_films = list(dict.fromkeys(tg.film_requests))
            unique_series = list(dict.fromkeys(tg.serie_requests))
            film_count = len(tg.film_requests)
            serie_count = len(tg.serie_requests)
            telegram_stats = TelegramStats(
                film_requests=film_count,
                serie_requests=serie_count,
                total_requests=film_count + serie_count,
                movies_requested=len(unique_films),
                movies_watched=count_unique_matched(unique_films, history_titles),
                series_requested=len(unique_series),
                series_watched=count_unique_matched(unique_series, history_titles),
                login_count=tg.login_count,
            )
            has_telegram = (
                telegram_stats.film_requests > 0
                or telegram_stats.serie_requests > 0
                or telegram_stats.login_count > 0
            )

        if user_comparison_show and user_comparison_show in show_stats:
            user_top_plays = show_stats[user_comparison_show]["plays"]
        elif user_comparison_movie and user_comparison_movie in movie_stats:
            user_top_plays = movie_stats[user_comparison_movie]["plays"]
        else:
            user_top_plays = None

        ai_copy = generate_ai_copy(
            self.ai,
            build_facts(
                unique_series=len(series_keys),
                unique_seasons=len(season_keys),
                unique_episodes=len(episode_keys),
                server_top_show=server_top_title,
                server_top_movie=server_top_movie_title,
                user_comparison_show=user_comparison_show,
                user_comparison_movie=user_comparison_movie,
                comparison_same_show=comparison_same_show,
                user_top_plays=user_top_plays,
                comparison_reason=user_comparison_reason,
            ),
        )

        payload = WrappedPayload(
            year=self.year,
            user_id=user_id,
            display_name=display_name,
            username=username,
            avatar_url=avatar,
            total_watch_seconds=total_seconds,
            watch_hours=watch_hours,
            watch_days=watch_days,
            total_plays=total_plays,
            movie_plays=movie_plays,
            tv_plays=tv_plays,
            top_movies=top_movies,
            top_shows=top_shows,
            unique_series=len(series_keys),
            unique_seasons=len(season_keys),
            unique_episodes=len(episode_keys),
            busiest_month=busiest_month,
            busiest_month_index=busiest_month_index,
            busiest_month_daily_plays=busiest_month_daily_plays,
            busiest_month_first_weekday=busiest_month_first_weekday,
            plays_by_weekday=plays_by_weekday,
            peak_day=peak_day,
            peak_hour=peak_hour,
            favorite_device=favorite_device,
            favorite_device_watch_percent=favorite_device_watch_percent,
            longest_streak_days=streak_days,
            longest_streak_start=streak_start.isoformat() if streak_start else None,
            longest_streak_end=streak_end.isoformat() if streak_end else None,
            top_movie_genres=_top_genres(movie_genre_counter),
            top_show_genres=_top_genres(show_genre_counter),
            top_actors=top_actors,
            server=server_stats,
            user_comparison_show=user_comparison_show,
            user_comparison_show_thumb=user_comparison_show_thumb,
            user_comparison_movie=user_comparison_movie,
            user_comparison_movie_thumb=user_comparison_movie_thumb,
            user_comparison_reason=user_comparison_reason,  # type: ignore[arg-type]
            comparison_same_show=comparison_same_show,
            comparison_headline_accent=comparison_headline_accent,
            comparison_caption=comparison_caption,
            telegram=telegram_stats,
            ai_copy=ai_copy,
            has_watch_history=total_plays > 0,
            has_telegram_activity=has_telegram,
        )
        apply_persona(payload)
        logger.info(
            "Wrapped result user_id=%s plays=%s movies=%s tv=%s watch_hours=%s device=%s",
            user_id,
            payload.total_plays,
            payload.movie_plays,
            payload.tv_plays,
            payload.watch_hours,
            payload.favorite_device,
        )
        return payload
