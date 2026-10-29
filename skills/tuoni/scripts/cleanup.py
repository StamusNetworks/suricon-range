#!/usr/bin/env python3
"""checkup + cleanup for Tuoni C2 agents.

Actions (default: --check if none given):
  --check     list active agents — hostname, user, PID, IPs, OS (read-only)
  --fast      PUT /inactive for each target — no die, connection left open
  --graceful  send die → wait → PUT /inactive — the agent closes its connection

Env:
  TUONI_API     base URL, e.g. https://<host>:8443       (required)
  TUONI_USER    Tuoni API user                           (required)
  TUONI_PASS    Tuoni API password                        (required)
  TUONI_AGENT   target agent guid (overridden by --agent-guid)

Importable from a notebook: tuoni_check()/tuoni_fast()/tuoni_cleanup() take the
same inputs as the matching flags as keyword arguments and return a dict
instead of only printing. They raise TuoniScriptError on failure — argparse
and sys.exit live only in main(); the core logic is in adsim.
"""
import argparse
import os
import sys

from adsim.tuoni.cleanup import (
    tuoni_check,
    tuoni_cleanup,
    tuoni_fast,
)
from adsim.tuoni.common import TuoniScriptError


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent-guid", default=os.environ.get("TUONI_AGENT"),
                    help="target a single agent (default: all active)")

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="list active agents (read-only; default if no action given)")
    mode.add_argument("--fast", action="store_true",
                      help="PUT /inactive without die; connection left open")
    mode.add_argument("--graceful", action="store_true",
                      help="die → wait → PUT /inactive; agent closes its connection")

    ap.add_argument("--erase", action="store_true",
                    help="delete payload binary from disk (--graceful only)")
    args = ap.parse_args()

    if args.erase and not args.graceful:
        ap.error("--erase requires --graceful")

    if not (args.check or args.fast or args.graceful):
        args.check = True

    api = os.environ.get("TUONI_API")
    user = os.environ.get("TUONI_USER")
    password = os.environ.get("TUONI_PASS")

    try:
        if not api:
            raise TuoniScriptError("TUONI_API not set")
        if not (user and password):
            raise TuoniScriptError("TUONI_USER + TUONI_PASS not set")

        if args.check:
            tuoni_check(api=api, user=user, password=password, agent_guid=args.agent_guid)
        elif args.fast:
            tuoni_fast(api=api, user=user, password=password, agent_guid=args.agent_guid)
        else:
            tuoni_cleanup(api=api, user=user, password=password,
                        agent_guid=args.agent_guid, erase=args.erase)
    except TuoniScriptError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
