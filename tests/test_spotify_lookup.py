from unittest.mock import MagicMock, patch

from app.config import Settings
from app.wrapped.spotify_lookup import SpotifyClient, SpotifyCredentials
from app.wrapped.theme_lookup import ThemeTrack


def test_spotify_refine_prefers_soundtrack_match(monkeypatch):
    client = SpotifyClient(
        SpotifyCredentials(client_id="id", client_secret="secret"),
    )

    def fake_search(_self, _client, query, *, limit=8):
        return [
            {
                "name": "The Avengers",
                "artists": [{"name": "Alan Silvestri"}],
                "album": {"name": "The Avengers (Original Motion Picture Soundtrack)"},
                "track_number": 1,
            }
        ]

    monkeypatch.setattr(client, "_search_tracks", fake_search)
    monkeypatch.setattr(client, "_ensure_token", lambda _c: "token")

    seed = ThemeTrack(
        track_name="Main Theme",
        artist_name="Alan Silvestri",
        album_name="",
        source="musicbrainz",
    )
    refined = client.refine_theme_track(
        media_title="The Avengers",
        year=2012,
        media_kind="movie",
        seed=seed,
    )
    assert refined is not None
    assert refined.source == "spotify"
    assert refined.track_name == "The Avengers"
    assert refined.artist_name == "Alan Silvestri"
