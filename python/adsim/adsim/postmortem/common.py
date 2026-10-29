"""Shared by the postmortem modules."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from adsim.exercise import RUN_MARKER, now_iso

DEFAULT_PAD_SECONDS = 120


class ExtractError(RuntimeError):
    pass


def parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def read_run(run_dir) -> tuple[Path, dict]:
    run_dir = Path(run_dir).resolve()
    path = run_dir / RUN_MARKER
    if not path.is_file():
        raise ExtractError(f"{RUN_MARKER} not found: {path}")
    return run_dir, json.loads(path.read_text())


def run_window(marker: dict, pad_seconds=DEFAULT_PAD_SECONDS) -> tuple[datetime, datetime]:
    """The run's start, and its end (now, if still open) plus the pad."""
    start = parse_iso(marker["start_time"])
    end = parse_iso(marker.get("end_time") or now_iso())
    return start, end + timedelta(seconds=pad_seconds)
