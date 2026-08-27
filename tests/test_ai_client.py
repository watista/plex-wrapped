from types import SimpleNamespace

import pytest

from app.ai import ClaudeAIClient, ClaudeAIError
from app.config import Settings


def _settings(**overrides) -> Settings:
    base = dict(claude_ai_enabled=False, claude_model="claude-opus-5")
    base.update(overrides)
    return Settings(**base)


def test_disabled_when_flag_off():
    client = ClaudeAIClient(_settings(claude_ai_enabled=False))
    assert client.enabled is False
    assert client.generate_text("hello") is None


def test_enabled_needs_no_api_key():
    """Auth lives in the `claude` CLI, so the flag alone enables the client."""
    client = ClaudeAIClient(_settings(claude_ai_enabled=True))
    assert client.enabled is True


def test_generate_text_returns_none_on_empty_prompt():
    client = ClaudeAIClient(_settings(claude_ai_enabled=True))
    assert client.generate_text("   ") is None


def test_generate_text_handles_missing_sdk(monkeypatch):
    client = ClaudeAIClient(_settings(claude_ai_enabled=True))
    monkeypatch.setattr(client, "_load_sdk", lambda: None)
    assert client.generate_text("hello") is None


def test_cwd_defaults_to_project_root():
    from app.config import PROJECT_ROOT

    client = ClaudeAIClient(_settings(claude_agent_cwd=""))
    assert client._cwd == str(PROJECT_ROOT)


def test_options_lock_the_agent_down():
    """The agent must not get tools or pick up on-disk CLAUDE.md/settings."""
    client = ClaudeAIClient(_settings(claude_ai_enabled=True, claude_model="sonnet"))
    sdk = SimpleNamespace(ClaudeAgentOptions=lambda **kw: kw)

    opts = client._build_options(sdk, "be brief")

    assert opts["tools"] == []
    assert opts["allowed_tools"] == []
    assert opts["setting_sources"] == []
    assert opts["max_turns"] == 1
    assert opts["system_prompt"] == "be brief"
    assert opts["model"] == "sonnet"


def test_options_omit_model_when_unset():
    """An empty CLAUDE_MODEL lets the CLI use its own configured default."""
    client = ClaudeAIClient(_settings(claude_ai_enabled=True, claude_model=""))
    sdk = SimpleNamespace(ClaudeAgentOptions=lambda **kw: kw)

    opts = client._build_options(sdk, None)

    assert "model" not in opts
    assert "system_prompt" not in opts


def test_health_check_raises_when_disabled():
    client = ClaudeAIClient(_settings(claude_ai_enabled=False))
    with pytest.raises(ClaudeAIError, match="CLAUDE_AI_ENABLED"):
        client.health_check()


def test_health_check_raises_when_sdk_missing(monkeypatch):
    client = ClaudeAIClient(_settings(claude_ai_enabled=True))
    monkeypatch.setattr(client, "_load_sdk", lambda: None)
    with pytest.raises(ClaudeAIError, match="claude-agent-sdk"):
        client.health_check()
