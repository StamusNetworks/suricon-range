#!/usr/bin/env python3
"""pcap.py — download PCAPs from Arkime for a run's community IDs.

Reads community IDs from `artifacts-community-ids.txt` (written by
eve.py) or accepts them explicitly via pm_pcap(). Fetches session
PCAPs from Arkime's API and writes:

  artifacts-arkime.pcap       — single merged PCAP (default)
  arkime-pcaps/<cid>.pcap     — per-session PCAPs (--per-flow)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from adsim.postmortem.common import DEFAULT_PAD_SECONDS, ExtractError
from adsim.postmortem.pcap import (
    pm_pcap,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_id")
    p.add_argument("--runs-root", required=True)
    p.add_argument("--arkime-url", default=os.environ.get("ARKIME_URL"))
    p.add_argument("--arkime-user", default=os.environ.get("ARKIME_USER"))
    p.add_argument("--arkime-pass", default=os.environ.get("ARKIME_PASS"))
    p.add_argument("--per-flow", action="store_true")
    p.add_argument("--pad-seconds", type=int, default=DEFAULT_PAD_SECONDS)
    args = p.parse_args()

    if not all([args.arkime_url, args.arkime_user, args.arkime_pass]):
        sys.exit("error: pass --arkime-url/user/pass or set ARKIME_URL/USER/PASS")

    run_dir = Path(args.runs_root).resolve() / args.run_id
    try:
        pm_pcap(run_dir=run_dir, arkime_url=args.arkime_url,
                arkime_user=args.arkime_user, arkime_pass=args.arkime_pass,
                per_flow=args.per_flow, pad_seconds=args.pad_seconds)
    except ExtractError as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
