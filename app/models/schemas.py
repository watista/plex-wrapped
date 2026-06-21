from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MediaItem(BaseModel):
    title: str
    thumb: str | None = None
    plays: int = 0
    duration_seconds: int = 0


class GenreStat(BaseModel):
    name: str
    plays: int = 0


class TelegramStats(BaseModel):
    film_requests: int = 0
    serie_requests: int = 0
    total_requests: int = 0
    movies_requested: int = 0
    movies_watched: int = 0
    series_requested: int = 0
    series_watched: int = 0
    login_count: int = 0


class ServerRankEntry(BaseModel):
    rank: int
    watch_hours: int = 0
    is_you: bool = False
    position_label: str = ""


class AICopy(BaseModel):
    """AI-generated punchlines. Any field may be None -> frontend uses its default."""

    series_depth: str | None = None
    server_vs_you: str | None = None


class ServerStats(BaseModel):
    rank: int | None = None
    server_name: str | None = None
    server_top_show: str | None = None
    server_top_show_thumb: str | None = None
    server_top_movie: str | None = None
    server_top_movie_thumb: str | None = None
    more_active_than_percent: int | None = None
    rank_context: list[ServerRankEntry] = Field(default_factory=list)


class WrappedPayload(BaseModel):
    year: int
    user_id: int
    display_name: str
    username: str
    avatar_url: str | None = None

    total_watch_seconds: int = 0
    watch_hours: int = 0
    watch_days: int = 0
    total_plays: int = 0
    movie_plays: int = 0
    tv_plays: int = 0

    top_movies: list[MediaItem] = Field(default_factory=list)
    top_shows: list[MediaItem] = Field(default_factory=list)
    unique_series: int = 0
    unique_seasons: int = 0
    unique_episodes: int = 0

    busiest_month: str | None = None
    busiest_month_index: int | None = None
    busiest_month_daily_plays: list[int] = Field(default_factory=list)
    busiest_month_first_weekday: int = 0
    plays_by_weekday: list[int] = Field(default_factory=list)
    peak_day: str | None = None
    peak_hour: int | None = None
    favorite_device: str | None = None
    favorite_device_watch_percent: int | None = None
    longest_streak_days: int = 0
    longest_streak_start: str | None = None
    longest_streak_end: str | None = None

    top_movie_genres: list[GenreStat] = Field(default_factory=list)
    top_show_genres: list[GenreStat] = Field(default_factory=list)

    server: ServerStats = Field(default_factory=ServerStats)
    user_comparison_show: str | None = None
    user_comparison_show_thumb: str | None = None
    user_comparison_movie: str | None = None
    user_comparison_movie_thumb: str | None = None
    user_comparison_reason: Literal["most_played", "first_played"] | None = None
    comparison_same_show: bool | None = None
    comparison_headline_accent: str | None = None
    comparison_caption: str | None = None

    telegram: TelegramStats = Field(default_factory=TelegramStats)

    ai_copy: AICopy = Field(default_factory=AICopy)

    persona: str = "Toegewijde kijker"
    persona_tagline: str = "Stabiel en trouw."
    persona_id: str = "dedicated_viewer"
    has_watch_history: bool = True
    has_telegram_activity: bool = False

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(*args, **kwargs)
