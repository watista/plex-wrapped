"""Thin wrapper around the Cursor Python SDK (local runtime).

This module owns the *connection* to the Cursor API only. It exposes a generic
``generate_text`` primitive that higher-level features (e.g. punchline copy)
can build on later. It is intentionally defensive: when AI is disabled, the
SDK is missing, or a run fails, it degrades to ``None`` instead of raising, so
the data-compute pipeline never breaks because of AI.
"""

from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, Settings, get_settings

logger = logging.getLogger(__name__)


class CursorAIError(Exception):
    """Raised only by explicit checks (e.g. health_check); never during compute."""


class CursorAIClient:
    """Generate text via the Cursor SDK using the local agent runtime.

    The SDK is imported lazily so the rest of the app keeps working when
    ``cursor-sdk`` is not installed or AI is turned off.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._api_key = (self.settings.cursor_api_key or "").strip()
        self._model = (self.settings.cursor_model or "auto").strip() or "auto"
        self._timeout = max(1, int(self.settings.cursor_timeout_seconds or 120))
        self._cwd = self._resolve_cwd(self.settings.cursor_agent_cwd)
        self._sdk: Any | None = None

    @staticmethod
    def _resolve_cwd(raw: str | None) -> str:
        if raw and raw.strip():
            p = Path(raw.strip())
            return str(p if p.is_absolute() else (PROJECT_ROOT / p))
        return str(PROJECT_ROOT)

    @property
    def enabled(self) -> bool:
        """True when AI is switched on and an API key is configured."""
        return bool(self.settings.cursor_ai_enabled) and bool(self._api_key)

    def _load_sdk(self) -> Any | None:
        """Import the Cursor SDK on demand; cache the module on success."""
        if self._sdk is not None:
            return self._sdk
        try:
            import cursor_sdk  # type: ignore

            self._sdk = cursor_sdk
            return self._sdk
        except Exception:  # ImportError or transitive import failure
            logger.warning(
                "Cursor SDK not available — install `cursor-sdk` and the "
                "cursor-agent runtime to enable AI generation",
                exc_info=True,
            )
            return None

    def _run_prompt(self, prompt: str) -> str | None:
        """Execute a one-shot prompt and return the final assistant text."""
        sdk = self._load_sdk()
        if sdk is None:
            return None

        Agent = sdk.Agent
        AgentOptions = sdk.AgentOptions
        LocalAgentOptions = sdk.LocalAgentOptions
        CursorAgentError = sdk.CursorAgentError

        try:
            result = Agent.prompt(
                prompt,
                AgentOptions(
                    api_key=self._api_key,
                    model=self._model,
                    local=LocalAgentOptions(cwd=self._cwd),
                ),
            )
        except CursorAgentError as exc:
            # Run never started: auth, config, network, missing runtime.
            logger.error("Cursor AI run failed to start: %s", exc)
            return None
        except Exception:
            logger.exception("Unexpected Cursor AI error while starting run")
            return None

        status = getattr(result, "status", None)
        if status == "error":
            logger.error("Cursor AI run executed but failed (status=error)")
            return None

        text = getattr(result, "result", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        logger.warning("Cursor AI run returned no usable text (status=%s)", status)
        return None

    def generate_text(self, prompt: str, *, system: str | None = None) -> str | None:
        """Generate text from a prompt.

        Returns the model's reply, or ``None`` if AI is disabled, the SDK is
        unavailable, the run fails, or the call exceeds the configured timeout.
        Never raises.
        """
        if not self.enabled:
            logger.debug("Cursor AI disabled — skipping generate_text")
            return None
        if not prompt or not prompt.strip():
            return None

        full_prompt = f"{system.strip()}\n\n{prompt.strip()}" if system else prompt.strip()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self._run_prompt, full_prompt)
            try:
                return future.result(timeout=self._timeout)
            except concurrent.futures.TimeoutError:
                logger.error("Cursor AI timed out after %ss", self._timeout)
                return None
            except Exception:
                logger.exception("Cursor AI generate_text failed")
                return None

    def health_check(self) -> str:
        """Verify connectivity by asking for a tiny fixed reply.

        Unlike ``generate_text`` this raises ``CursorAIError`` on problems so a
        CLI check can surface a clear failure. Returns the model's reply text.
        """
        if not self.settings.cursor_ai_enabled:
            raise CursorAIError("CURSOR_AI_ENABLED is false")
        if not self._api_key:
            raise CursorAIError("CURSOR_API_KEY is not set")
        if self._load_sdk() is None:
            raise CursorAIError("cursor-sdk is not installed")

        reply = self.generate_text("Reply with exactly: OK")
        if not reply:
            raise CursorAIError("No reply from Cursor AI (see logs for details)")
        return reply
