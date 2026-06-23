#!/usr/bin/env python3
"""Optional legacy helper — genre/year music is now downloaded from YouTube at compute time.

You can still run this to create silent fallbacks, but compute_wrapped.py no longer needs it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.wrapped.music import _DEFAULT_GENRE_SLUG, _GENRE_SLUGS  # noqa: E402

GENRE_DIR = PROJECT_ROOT / "static" / "audio" / "genres"
YEAR_DIR = PROJECT_ROOT / "static" / "audio" / "year"
ASSETS_DIR = PROJECT_ROOT / "static" / "audio" / "_assets"

# Short valid MP3 (1s silence) — public blank-audio sample.
_SEED_MP3_URL = "https://raw.githubusercontent.com/anars/blank-audio/master/1-second-of-silence.mp3"
_MIN_BYTES = 4000


def _write_with_ffmpeg(path: Path, *, duration_sec: float = 3.0) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            str(duration_sec),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "6",
            str(path),
        ],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and path.is_file() and path.stat().st_size >= _MIN_BYTES


def _download_seed(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(_SEED_MP3_URL)
            response.raise_for_status()
            data = response.content
        if len(data) < _MIN_BYTES:
            return False
        path.write_bytes(data)
        return True
    except Exception:
        return False


def _ensure_seed_asset() -> Path | None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    seed = ASSETS_DIR / "seed-loop.mp3"
    if seed.is_file() and seed.stat().st_size >= _MIN_BYTES:
        return seed
    if _write_with_ffmpeg(seed):
        print(f"  seed via ffmpeg: {seed.relative_to(PROJECT_ROOT)}")
        return seed
    if _download_seed(seed):
        print(f"  seed via download: {seed.relative_to(PROJECT_ROOT)}")
        return seed
    return None


def ensure_file(path: Path, seed: Path) -> None:
    if path.is_file() and path.stat().st_size >= _MIN_BYTES:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if _write_with_ffmpeg(path):
        print(f"  created {path.relative_to(PROJECT_ROOT)} (ffmpeg)")
        return
    shutil.copy2(seed, path)
    print(f"  created {path.relative_to(PROJECT_ROOT)} (seed copy)")


def main() -> None:
    seed = _ensure_seed_asset()
    if not seed:
        print(
            "Could not create a valid seed MP3. Install ffmpeg or ensure internet access for the seed download."
        )
        sys.exit(1)

    slugs = sorted(set(_GENRE_SLUGS.values()) | {_DEFAULT_GENRE_SLUG})
    print("Genre placeholders:")
    for slug in slugs:
        ensure_file(GENRE_DIR / f"{slug}.mp3", seed)

    year = 2025
    print(f"Year placeholders ({year}):")
    for index in range(1, 6):
        ensure_file(YEAR_DIR / f"{year}_{index}.mp3", seed)

    print("Done.")


if __name__ == "__main__":
    main()
