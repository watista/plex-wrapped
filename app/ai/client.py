"""Thin wrapper around the Claude Agent SDK (local `claude` CLI).

This module owns the *connection* to Claude only. It exposes a generic
``generate_text`` primitive that higher-level features (e.g. punchline copy)
can build on later. Authentication comes from the CLI's own login on the
compute host, so runs are billed against that Claude subscription — no API
key is read or sent by this module.

It is intentionally defensive: when AI is disabled, the SDK is missing, the
`claude` binary is absent, or a run fails, it degrades to ``None`` instead of
raising, so the data-compute pipeline never breaks because of AI.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import threading
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, Settings, get_settings

logger = logging.getLogger(__name__)

_gate_guard = threading.Lock()
_gate: threading.Semaphore | None = None


def _concurrency_gate(limit: int) -> threading.Semaphore:
    """Process-wide cap on simultaneous `claude` CLI runs.

    Each generation spawns a CLI subprocess, so a parallel compute run would
    otherwise start one per worker and hammer the subscription's rate limits.
    """
    global _gate
    with _gate_guard:
        if _gate is None:
            _gate = threading.Semaphore(max(1, limit))
        return _gate


class ClaudeAIError(Exception):
    """Raised only by explicit checks (e.g. health_check); never during compute."""


class ClaudeAIClient:
    """Generate text via the Claude Agent SDK, which drives the local `claude` CLI.

    The SDK is imported lazily so the rest of the app keeps working when
    ``claude-agent-sdk`` is not installed or AI is turned off.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = (self.settings.claude_model or "").strip()
        self._timeout = max(1, int(self.settings.claude_timeout_seconds or 120))
        self._cwd = self._resolve_cwd(self.settings.claude_agent_cwd)
        self._sdk: Any | None = None

    @staticmethod
    def _resolve_cwd(raw: str | None) -> str:
        if raw and raw.strip():
            p = Path(raw.strip())
            return str(p if p.is_absolute() else (PROJECT_ROOT / p))
        return str(PROJECT_ROOT)

    @property
    def enabled(self) -> bool:
        """True when AI is switched on. Auth lives in the CLI, not in settings."""
        return bool(self.settings.claude_ai_enabled)

    def _load_sdk(self) -> Any | None:
        """Import the Claude Agent SDK on demand; cache the module on success."""
        if self._sdk is not None:
            return self._sdk
        try:
            import claude_agent_sdk  # type: ignore

            self._sdk = claude_agent_sdk
            return self._sdk
        except Exception:  # ImportError or transitive import failure
            logger.warning(
                "Claude Agent SDK not available — install `claude-agent-sdk` and "
                "the `claude` CLI to enable AI generation",
                exc_info=True,
            )
            return None

    def _build_options(self, sdk: Any, system: str | None) -> Any:
        """Lock the agent down to plain text generation.

        No tools means no filesystem access and exactly one assistant turn;
        empty ``setting_sources`` keeps a CLAUDE.md or local settings file in
        ``cwd`` from leaking into the prompt.
        """
        options: dict[str, Any] = {
            "cwd": self._cwd,
            "tools": [],
            "allowed_tools": [],
            "setting_sources": [],
            "max_turns": 1,
            "permission_mode": "default",
        }
        if system:
            options["system_prompt"] = system
        if self._model:
            options["model"] = self._model
        return sdk.ClaudeAgentOptions(**options)

    async def _collect(self, sdk: Any, prompt: str, system: str | None) -> str | None:
        """Run one query and return the final assistant text."""
        result: str | None = None
        texts: list[str] = []
        terminal_reason: str | None = None
        is_error = False

        options = self._build_options(sdk, system)
        async for message in sdk.query(prompt=prompt, options=options):
            if isinstance(message, sdk.ResultMessage):
                result = getattr(message, "result", None)
                terminal_reason = getattr(message, "terminal_reason", None)
                is_error = bool(getattr(message, "is_error", False))
            elif isinstance(message, sdk.AssistantMessage):
                for block in message.content:
                    if isinstance(block, sdk.TextBlock):
                        texts.append(block.text)

        if is_error:
            logger.error("Claude AI run failed (terminal_reason=%s)", terminal_reason)
            return None

        # ResultMessage.result is the final answer; the collected TextBlocks are
        # a fallback for SDK versions that leave it unset.
        text = result if isinstance(result, str) and result.strip() else "\n".join(texts)
        if text and text.strip():
            return text.strip()
        logger.warning(
            "Claude AI run returned no usable text (terminal_reason=%s)", terminal_reason
        )
        return None

    def _run_prompt(self, prompt: str, system: str | None) -> str | None:
        """Execute a one-shot prompt from a worker thread."""
        sdk = self._load_sdk()
        if sdk is None:
            return None

        CLINotFoundError = sdk.CLINotFoundError

        async def _runner() -> str | None:
            return await asyncio.wait_for(
                self._collect(sdk, prompt, system), timeout=self._timeout
            )

        try:
            return asyncio.run(_runner())
        except asyncio.TimeoutError:
            logger.error("Claude AI timed out after %ss", self._timeout)
            return None
        except CLINotFoundError as exc:
            logger.error(
                "`claude` CLI not found — install it and log in on this host: %s", exc
            )
            return None
        except Exception:
            logger.exception("Unexpected Claude AI error while running prompt")
            return None

    def generate_text(self, prompt: str, *, system: str | None = None) -> str | None:
        """Generate text from a prompt.

        Returns the model's reply, or ``None`` if AI is disabled, the SDK or CLI
        is unavailable, the run fails, or the call exceeds the configured
        timeout. Never raises.
        """
        if not self.enabled:
            logger.debug("Claude AI disabled — skipping generate_text")
            return None
        if not prompt or not prompt.strip():
            return None

        if os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning(
                "ANTHROPIC_API_KEY is set in the environment — the `claude` CLI "
                "will bill this run to API credits instead of the subscription. "
                "Unset it on the compute host to use subscription auth."
            )

        # The SDK is async-only; run it on a worker thread so callers stay sync.
        # The inner asyncio timeout does the real work; this one is a backstop
        # for a subprocess that never yields.
        gate = _concurrency_gate(self.settings.claude_max_concurrency)
        with gate, concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._run_prompt, prompt.strip(), system)
            try:
                return future.result(timeout=self._timeout + 30)
            except concurrent.futures.TimeoutError:
                logger.error("Claude AI thread did not return after %ss", self._timeout + 30)
                return None
            except Exception:
                logger.exception("Claude AI generate_text failed")
                return None

    def health_check(self) -> str:
        """Verify connectivity by asking for a tiny fixed reply.

        Unlike ``generate_text`` this raises ``ClaudeAIError`` on problems so a
        CLI check can surface a clear failure. Returns the model's reply text.
        """
        if not self.settings.claude_ai_enabled:
            raise ClaudeAIError("CLAUDE_AI_ENABLED is false")
        if self._load_sdk() is None:
            raise ClaudeAIError("claude-agent-sdk is not installed")

        reply = self.generate_text("Reply with exactly: OK")
        if not reply:
            raise ClaudeAIError(
                "No reply from Claude AI — check that `claude` is on PATH and "
                "logged in (`claude login`); see logs for details"
            )
        return reply
