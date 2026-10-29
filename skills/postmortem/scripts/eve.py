#!/usr/bin/env python3
"""eve.py — freeze Suricata EVE docs for a run's signal flows.

Reads run.json for the ES index, time window, and KQL patterns
(eve_filter), queries Elasticsearch, and writes two artifacts:

  artifacts-suricata-eve.json   — full EVE documents (sorted by @timestamp)
  artifacts-community-ids.txt   — unique community_id values, one per line

Two fetch modes:

  Direct KQL (default):  query each pattern, merge deduplicated results.
  Flow-resolve:          aggregate unique flow_ids from patterns, then
                         fetch all docs matching those flow_ids.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from adsim.postmortem.common import DEFAULT_PAD_SECONDS, ExtractError
from adsim.postmortem.eve import (
    pm_eve,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_id")
    p.add_argument("--kql", action="append", dest="kql_list",
                   metavar="KQL", help="override eve_filter from run.json")
    p.add_argument("--elk-url", default=os.environ.get("ELK_URL"))
    p.add_argument("--runs-root", required=True)
    p.add_argument("--pad-seconds", type=int, default=DEFAULT_PAD_SECONDS)
    p.add_argument("--index", default=os.environ.get("EVE_INDEX"),
                   help="ES index to query (default: env EVE_INDEX, else "
                        "suricata-<run start date>)")
    p.add_argument("--resolve-flows", action="store_true",
                   help="aggregate flow_ids first, then fetch by flow_id")
    p.add_argument("--fetch-delay", type=int, default=0,
                   help="seconds to wait before fetching")
    args = p.parse_args()

    if not args.elk_url:
        sys.exit("error: pass --elk-url or set ELK_URL")

    run_dir = Path(args.runs_root).resolve() / args.run_id

    if args.kql_list:
        run_json = run_dir / "run.json"
        run_meta = json.loads(run_json.read_text())
        run_meta["eve_filter"] = args.kql_list
        run_json.write_text(json.dumps(run_meta, indent=2) + "\n")

    try:
        pm_eve(
            run_dir=run_dir,
            elk_url=args.elk_url,
            resolve_flows=args.resolve_flows,
            fetch_delay=args.fetch_delay,
            pad_seconds=args.pad_seconds,
            index=args.index,
        )
    except ExtractError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
