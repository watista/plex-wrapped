from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any

from app.config import Settings, get_settings
from app.models.cache import WrappedCache
from app.models.schemas import GenreStat, MediaItem, ServerStats, TelegramStats, WrappedPayload
from app.tautulli.client import TautulliClient
from app.telegram.loader import (
    TelegramData,
    count_unique_matched,
    load_telegram_data,
)
from app.wrapped.locale import to_dutch_day, to_dutch_month
from app.wrapped.slides import apply_persona


def _year_range(year: int) -> tuple[str, str, int]:
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year, 12, 31)
    days = (end_dt - start_dt).days + 1
    return start, end, days


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


def _history_row_date(row: dict[str, Any]) -> date | None:
    ts = row.get("date")
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()


class WrappedAggregator:
    def __init__(
        self,
        tautulli: TautulliClient,
        settings: Settings | None = None,
        telegram: TelegramData | None = None,
        cache: WrappedCache | None = None,
        year: int | None = None,
    ):
        self.tautulli = tautulli
        self.settings = settings or get_settings()
        self.year = year if year is not None else self.settings.wrapped_year
        self.telegram = telegram if telegram is not None else load_telegram_data(self.settings, self.year)
        self.cache = cache or WrappedCache(self.settings)
        self._metadata_cache: dict[str, list[str]] = {}
        self._server_top_show: str | None = None

    def get_cached(self, user_id: int) -> WrappedPayload | None:
        cached = self.cache.get(user_id, self.year)
        if not cached:
            return None
        return WrappedPayload(**cached)

    def get_or_compute(self, user_id: int, *, force: bool = False) -> WrappedPayload:
        if not force:
            cached = self.get_cached(user_id)
            if cached:
                return cached
        payload = self.compute(user_id)
        self.cache.set(user_id, self.year, payload.model_dump())
        return payload

    def _get_metadata_genres(self, rating_key: str | int) -> list[str]:
        key = str(rating_key)
        if key in self._metadata_cache:
            return self._metadata_cache[key]
        try:
            meta = self.tautulli.get_metadata(rating_key=key)
            genres = meta.get("genres") or []
            names = [g if isinstance(g, str) else str(g) for g in genres if g]
        except Exception:
            names = []
        self._metadata_cache[key] = names
        return names

    def _get_server_top_show(self, time_range_days: int) -> str | None:
        if self._server_top_show is not None:
            return self._server_top_show
        title: str | None = None
        try:
            stats = self.tautulli.get_home_stats(
                time_range=time_range_days,
                stat_id="top_tv",
                stats_count=1,
            )
            for block in stats:
                if block.get("stat_id") != "top_tv":
                    continue
                rows = block.get("rows") or []
                if rows:
                    row = rows[0]
                    title = row.get("grandparent_title") or row.get("title") or row.get("full_title")
                break
        except Exception:
            pass
        self._server_top_show = title
        return title

    def compute(self, user_id: int) -> WrappedPayload:
        user = self.tautulli.get_user(user_id)
        start_date, end_date, time_range_days = _year_range(self.year)

        history = self.tautulli.fetch_all_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
        media_history = [r for r in history if r.get("media_type") in ("movie", "episode")]

        display_name = user.get("friendly_name") or user.get("username") or "Viewer"
        username = user.get("username") or ""
        avatar = user.get("user_thumb")

        total_seconds = 0
        movie_plays = tv_plays = 0
        movie_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"plays": 0, "duration": 0, "thumb": None, "rating_key": None}
        )
        show_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"plays": 0, "duration": 0, "thumb": None}
        )
        history_titles: list[str] = []
        play_dates: list[date] = []
        series_keys: set[str] = set()
        season_keys: set[tuple[str, str]] = set()
        episode_keys: set[str] = set()
        movie_genre_counter: Counter[str] = Counter()
        show_genre_counter: Counter[str] = Counter()

        sorted_episodes = sorted(
            [r for r in media_history if r.get("media_type") == "episode"],
            key=lambda r: r.get("date") or 0,
        )

        for row in media_history:
            media_type = row.get("media_type", "")
            duration = int(row.get("duration") or 0)
            total_seconds += duration
            history_titles.append(
                row.get("grandparent_title") or row.get("title") or row.get("full_title") or ""
            )
            row_date = _history_row_date(row)
            if row_date:
                play_dates.append(row_date)

            if media_type == "movie":
                movie_plays += 1
                title, thumb = _media_key(row, media_type)
                movie_stats[title]["plays"] += 1
                movie_stats[title]["duration"] += duration
                movie_stats[title]["thumb"] = movie_stats[title]["thumb"] or thumb
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
                gp = row.get("grandparent_rating_key")
                if gp is not None:
                    series_keys.add(str(gp))
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

        def to_media_items(stats: dict[str, dict[str, Any]], limit: int = 5) -> list[MediaItem]:
            ranked = sorted(stats.items(), key=lambda x: (-x[1]["plays"], -x[1]["duration"]))
            return [
                MediaItem(
                    title=title,
                    thumb=data.get("thumb"),
                    plays=data["plays"],
                    duration_seconds=data["duration"],
                )
                for title, data in ranked[:limit]
            ]

        top_movies = to_media_items(movie_stats, 5)
        top_shows = to_media_items(show_stats, 5)

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

        busiest_month = peak_day = None
        peak_hour = None
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
        try:
            players = self.tautulli.get_user_player_stats(user_id=user_id)
            if players:
                favorite_device = max(players, key=lambda p: p.get("total_plays", 0)).get("player_name")
        except Exception:
            pass

        server_stats = ServerStats()
        try:
            top_users = self.tautulli.get_plays_by_top_10_users(time_range=time_range_days)
            categories = top_users.get("categories", [])
            series = top_users.get("series", [])
            user_name = display_name
            if categories and series:
                for i, name in enumerate(categories):
                    if name == user_name or username in name:
                        server_stats.rank = i + 1
                        break
        except Exception:
            pass
        server_stats.server_top_show = self._get_server_top_show(time_range_days)

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
            peak_day=peak_day,
            peak_hour=peak_hour,
            favorite_device=favorite_device,
            longest_streak_days=streak_days,
            longest_streak_start=streak_start.isoformat() if streak_start else None,
            longest_streak_end=streak_end.isoformat() if streak_end else None,
            top_movie_genres=_top_genres(movie_genre_counter),
            top_show_genres=_top_genres(show_genre_counter),
            server=server_stats,
            user_comparison_show=user_comparison_show,
            user_comparison_reason=user_comparison_reason,  # type: ignore[arg-type]
            telegram=telegram_stats,
            has_watch_history=total_plays > 0,
            has_telegram_activity=has_telegram,
        )
        apply_persona(payload)
        return payload
