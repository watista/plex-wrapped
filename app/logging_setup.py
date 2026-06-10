from __future__ import annotations

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(log_level)
        return
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("plex.wrapped.activity").setLevel(log_level)
