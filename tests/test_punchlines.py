from app.ai.punchlines import (
    PunchlineFacts,
    build_facts,
    build_prompt,
    generate_ai_copy,
    parse_ai_copy,
)
from app.models.schemas import AICopy


def _facts() -> PunchlineFacts:
    return build_facts(
        unique_series=12,
        unique_seasons=20,
        unique_episodes=240,
        server_top_show="The Office",
        server_top_movie=None,
        user_comparison_show="Breaking Bad",
        user_comparison_movie=None,
        comparison_same_show=False,
        user_top_plays=47,
        comparison_reason="most_played",
    )


def test_build_facts_prefers_show_over_movie_and_sets_kind():
    facts = build_facts(
        unique_series=1,
        unique_seasons=1,
        unique_episodes=1,
        server_top_show=None,
        server_top_movie="Dune",
        user_comparison_show=None,
        user_comparison_movie="Inception",
        comparison_same_show=False,
    )
    assert facts.server_top_title == "Dune"
    assert facts.server_top_kind == "film"
    assert facts.user_top_title == "Inception"
    assert facts.user_top_kind == "film"


def test_build_facts_marks_shows_as_serie():
    assert _facts().server_top_kind == "serie"
    assert _facts().user_top_kind == "serie"


def test_build_prompt_includes_titles_and_counts():
    prompt = build_prompt(_facts())
    assert "The Office" in prompt
    assert "Breaking Bad" in prompt
    assert "240" in prompt
    assert "series_depth" in prompt and "server_vs_you" in prompt


def test_build_prompt_instructs_content_based_and_forbids_labels():
    prompt = build_prompt(_facts())
    # Base the joke on what the titles are about, not on type labels/numbers.
    assert "thema" in prompt.lower()
    assert "(serie)" in prompt and "GEEN labels" in prompt


def test_build_prompt_first_played_reason_phrasing():
    facts = build_facts(
        unique_series=5,
        unique_seasons=6,
        unique_episodes=30,
        server_top_show="The Office",
        server_top_movie=None,
        user_comparison_show="Severance",
        user_comparison_movie=None,
        comparison_same_show=False,
        comparison_reason="first_played",
    )
    assert "begon de gebruiker het jaar" in build_prompt(facts)


def test_parse_plain_json():
    text = '{"series_depth": "240 afleveringen, jij stopt nooit.", "server_vs_you": "Jij koos eigenwijs."}'
    copy = parse_ai_copy(text)
    assert copy.series_depth == "240 afleveringen, jij stopt nooit."
    assert copy.server_vs_you == "Jij koos eigenwijs."


def test_parse_json_in_code_fence_with_noise():
    text = 'Here you go:\n```json\n{"series_depth": "Diep gedoken.", "server_vs_you": "Eigen smaak."}\n```\nDone.'
    copy = parse_ai_copy(text)
    assert copy.series_depth == "Diep gedoken."
    assert copy.server_vs_you == "Eigen smaak."


def test_parse_rejects_overlong_value():
    long = "x" * 500
    copy = parse_ai_copy(f'{{"series_depth": "{long}", "server_vs_you": "ok"}}')
    assert copy.series_depth is None
    assert copy.server_vs_you == "ok"


def test_parse_collapses_whitespace_and_strips_quotes():
    copy = parse_ai_copy('{"series_depth": "  meerdere   spaties \\n hier  ", "server_vs_you": "\\"geciteerd\\""}')
    assert copy.series_depth == "meerdere spaties hier"
    assert copy.server_vs_you == "geciteerd"


def test_parse_garbage_returns_empty():
    assert parse_ai_copy("not json at all") == AICopy()
    assert parse_ai_copy("") == AICopy()
    assert parse_ai_copy(None) == AICopy()


class _DisabledAI:
    enabled = False

    def generate_text(self, *args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("generate_text should not run when disabled")


def test_generate_ai_copy_disabled_is_noop():
    assert generate_ai_copy(_DisabledAI(), _facts()) == AICopy()


class _StubAI:
    enabled = True

    def __init__(self, reply):
        self._reply = reply
        self.calls = 0

    def generate_text(self, prompt, *, system=None):
        self.calls = self.calls + 1
        self.last_prompt = prompt
        self.last_system = system
        return self._reply


def test_generate_ai_copy_single_batched_call():
    ai = _StubAI('{"series_depth": "a", "server_vs_you": "b"}')
    copy = generate_ai_copy(ai, _facts())
    assert ai.calls == 1
    assert copy.series_depth == "a"
    assert copy.server_vs_you == "b"


def test_generate_ai_copy_handles_none_reply():
    ai = _StubAI(None)
    assert generate_ai_copy(ai, _facts()) == AICopy()
