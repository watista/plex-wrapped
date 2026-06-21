from app.ai import CursorAIClient
from app.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(cursor_ai_enabled=False, cursor_api_key="", cursor_model="auto")
    base.update(overrides)
    return Settings(**base)


def test_disabled_when_flag_off():
    client = CursorAIClient(_settings(cursor_ai_enabled=False, cursor_api_key="key"))
    assert client.enabled is False
    assert client.generate_text("hello") is None


def test_disabled_when_no_api_key():
    client = CursorAIClient(_settings(cursor_ai_enabled=True, cursor_api_key=""))
    assert client.enabled is False
    assert client.generate_text("hello") is None


def test_enabled_when_flag_and_key_present():
    client = CursorAIClient(_settings(cursor_ai_enabled=True, cursor_api_key="cursor_abc"))
    assert client.enabled is True


def test_generate_text_returns_none_on_empty_prompt():
    client = CursorAIClient(_settings(cursor_ai_enabled=True, cursor_api_key="cursor_abc"))
    assert client.generate_text("   ") is None


def test_generate_text_handles_missing_sdk(monkeypatch):
    client = CursorAIClient(_settings(cursor_ai_enabled=True, cursor_api_key="cursor_abc"))
    monkeypatch.setattr(client, "_load_sdk", lambda: None)
    assert client.generate_text("hello") is None


def test_cwd_defaults_to_project_root():
    from app.config import PROJECT_ROOT

    client = CursorAIClient(_settings(cursor_agent_cwd=""))
    assert client._cwd == str(PROJECT_ROOT)
