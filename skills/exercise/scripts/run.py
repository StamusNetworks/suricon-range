#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adsim.exercise import Run, RunError, list_runs


def die(msg: str) -> None:
    sys.exit(f"error: {msg}")


def cmd_open(args: argparse.Namespace) -> None:
    run = Run(args.runs_root, args.op_slug, techniques=args.techniques,
              targets=args.targets, notes=args.notes, eve_filter=args.eve_filter).open()
    print(run.run_id)


def cmd_close(args: argparse.Namespace) -> None:
    Run.load(args.runs_root, args.run_id).close(status=args.status, notes=args.notes)
    print(f"{args.run_id} {args.status}")


def cmd_dir(args: argparse.Namespace) -> None:
    print(args.runs_root.resolve())


def cmd_list(args: argparse.Namespace) -> None:
    for run_id in list_runs(args.runs_root.resolve()):
        print(run_id)


def cmd_latest(args: argparse.Namespace) -> None:
    print(Run.latest(args.runs_root).run_id)


def cmd_path(args: argparse.Namespace) -> None:
    print(Run.load(args.runs_root, args.run_id).dir)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--runs-root", required=True, type=Path,
                   help="path to the runs directory")
    sub = p.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("open", help="open a run, print the run id")
    o.add_argument("op_slug", help="lowercase kebab-case op label, e.g. lateral-smb")
    o.add_argument("--technique", action="append", dest="techniques", default=[],
                   metavar="T1234[.001]", help="ATT&CK id, repeatable")
    o.add_argument("--target", action="append", dest="targets", default=[],
                   metavar="HOST", help="target hostname or IP, repeatable")
    o.add_argument("--notes", default="", help="free-text notes")
    o.add_argument("--eve-filter", action="append", dest="eve_filter", default=[],
                   metavar="KQL", help="Kibana KQL filter for EVE fetch, repeatable")
    o.set_defaults(func=cmd_open)

    c = sub.add_parser("close", help="close a run")
    c.add_argument("run_id")
    c.add_argument("--status", default="completed", help="completed (default) or failed")
    c.add_argument("--notes", default="", help="appended to the marker's notes")
    c.set_defaults(func=cmd_close)

    sub.add_parser("dir", help="print the resolved runs dir").set_defaults(func=cmd_dir)
    sub.add_parser("list", help="print recorded run ids, oldest first").set_defaults(func=cmd_list)
    sub.add_parser("latest", help="print the most recent run id").set_defaults(func=cmd_latest)

    q = sub.add_parser("path", help="print a run's directory")
    q.add_argument("run_id")
    q.set_defaults(func=cmd_path)

    return p.parse_args()


if __name__ == "__main__":
    try:
        parsed = parse_args()
        parsed.func(parsed)
    except RunError as exc:
        die(str(exc))
