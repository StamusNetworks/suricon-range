"""adsim.exercise"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

RUN_MARKER = "run.json"

SLUG_RE = re.compile(r"^[a-z0-9-]+$")

TECHNIQUE_RE = re.compile(r"^T\d{4}(\.\d{3})?$")


class RunError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_run_id(root: Path, slug: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    base = f"{stamp}-{slug}"
    if not (root / base).exists():
        return base
    for n in range(2, 100):
        candidate = f"{base}-{n}"
        if not (root / candidate).exists():
            return candidate
    raise RunError(f"cannot mint a run id: {base} and every -N variant already exist")


def read_marker(root: Path, run_id: str) -> dict:
    path = root / run_id / RUN_MARKER
    if not path.is_file():
        raise RunError(f"{run_id} is not a run: no {RUN_MARKER} under {root / run_id}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RunError(f"{path} is not readable JSON: {exc}") from exc


def write_marker(root: Path, run_id: str, marker: dict) -> None:
    path = root / run_id
    path.mkdir(parents=True, exist_ok=True)
    (path / RUN_MARKER).write_text(json.dumps(marker, indent=2) + "\n",
                                  encoding="utf-8")


def list_runs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / RUN_MARKER).is_file())


class Run:
    """A simulation run: a directory under runs_dir holding run.json and the run's artifacts.

    The runs directory is resolved to an absolute path once, here, so later
    changes of the working directory do not move the run.
    """

    def __init__(self, runs_dir, op_slug, techniques=(), targets=(), notes="", eve_filter=()):
        if not SLUG_RE.match(op_slug):
            raise RunError(f"op slug {op_slug!r} must be lowercase kebab-case")
        for t in techniques:
            if not TECHNIQUE_RE.match(t):
                raise RunError(f"technique {t!r} is not an ATT&CK id")
        self.runs_dir = Path(runs_dir).expanduser().resolve()
        self.run_id = None
        self.marker = {
            "op_slug": op_slug,
            "techniques": list(techniques),
            "targets": list(targets),
        }
        if notes:
            self.marker["notes"] = notes
        if eve_filter:
            self.marker["eve_filter"] = list(eve_filter)

    def __repr__(self):
        return f"Run({self.run_id or self.marker['op_slug']!r}, {self.marker.get('status', 'new')})"

    @property
    def dir(self) -> Path:
        if self.run_id is None:
            raise RunError("run is not open yet")
        return self.runs_dir / self.run_id

    @property
    def marker_path(self) -> Path:
        return self.dir / RUN_MARKER

    def open(self) -> Run:
        if self.run_id is not None:
            raise RunError(f"run {self.run_id} is already open")
        self.run_id = make_run_id(self.runs_dir, self.marker["op_slug"])
        self.marker = {"run_id": self.run_id, **self.marker,
                       "start_time": now_iso(), "status": "running"}
        write_marker(self.runs_dir, self.run_id, self.marker)
        print(f"[+] opened run {self.run_id} at {self.dir}", file=sys.stderr)
        return self

    def close(self, status="completed", notes="") -> Run:
        if status not in ("completed", "failed"):
            raise RunError(f"status must be completed or failed, got {status!r}")
        # Re-read so edits made to run.json while the run was open are kept.
        self.marker = read_marker(self.runs_dir, self.dir.name)
        self.marker["status"] = status
        self.marker["end_time"] = now_iso()
        if notes:
            existing = self.marker.get("notes", "")
            self.marker["notes"] = f"{existing} {notes}".strip()
        write_marker(self.runs_dir, self.run_id, self.marker)
        print(f"[+] closed run {self.run_id} ({status})", file=sys.stderr)
        return self

    @classmethod
    def load(cls, runs_dir, run_id) -> Run:
        root = Path(runs_dir).expanduser().resolve()
        marker = read_marker(root, run_id)
        run = cls.__new__(cls)
        run.runs_dir = root
        run.run_id = run_id
        run.marker = marker
        return run

    @classmethod
    def latest(cls, runs_dir, op_slug=None, with_file=None) -> Run:
        """Newest run, optionally only those of op_slug and those holding with_file."""
        root = Path(runs_dir).expanduser().resolve()
        for run_id in reversed(list_runs(root)):
            run = cls.load(root, run_id)
            if op_slug is not None and run.marker.get("op_slug") != op_slug:
                continue
            if with_file is not None and not (run.dir / with_file).is_file():
                continue
            return run
        wanted = " ".join(filter(None, [op_slug and f"of {op_slug}", with_file and f"with {with_file}"]))
        raise RunError(f"no runs {wanted}".strip() + f" under {root}")
