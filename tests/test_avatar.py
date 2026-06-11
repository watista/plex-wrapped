from app.wrapped.avatar import resolve_avatar_url


def test_plex_letter_avatar_uses_fallback():
    assert (
        resolve_avatar_url("https://plex.tv/users/568gwwoib5t98a3a/avatar")
        is None
    )
    assert (
        resolve_avatar_url("https://plex.tv/users/abc123/avatar?c=1720981098")
        is None
    )


def test_tautulli_placeholder_uses_fallback():
    assert (
        resolve_avatar_url("interfaces/default/images/gravatar-default-80x80.png")
        is None
    )


def test_tautulli_custom_thumb_when_different_from_plex_thumb():
    url = resolve_avatar_url(
        "https://plex.tv/users/abc/avatar",
        custom_thumb="https://example.com/my-face.jpg",
    )
    assert url == "https://example.com/my-face.jpg"


def test_external_custom_url_is_kept():
    url = "https://cdn.example.com/avatars/user42.png"
    assert resolve_avatar_url(url) == url


def test_empty_uses_fallback():
    assert resolve_avatar_url(None) is None
    assert resolve_avatar_url("") is None
