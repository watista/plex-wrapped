"""Shared, pooled HTTP client for outbound TMDB requests.

Building a fresh ``httpx.Client`` per lookup costs a TCP + TLS handshake every
time, which dominates the runtime when a compute run resolves hundreds of
titles. One pooled client keeps connections alive between calls. ``httpx``
clients are thread-safe, so the compute pool shares this one.
"""

from __future__ import annotations

import atexit
import threading

import httpx

_lock = threading.Lock()
_client: httpx.Client | None = None


def tmdb_client() -> httpx.Client:
    """Return the process-wide TMDB client, creating it on first use."""
    global _client
    with _lock:
        if _client is None or _client.is_closed:
            _client = httpx.Client(
                timeout=httpx.Timeout(15.0, connect=10.0),
                limits=httpx.Limits(max_connections=16, max_keepalive_connections=16),
                headers={"Accept": "application/json"},
            )
        return _client


def close_tmdb_client() -> None:
    global _client
    with _lock:
        if _client is not None and not _client.is_closed:
            _client.close()
        _client = None


atexit.register(close_tmdb_client)
