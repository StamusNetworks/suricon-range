#!/usr/bin/env python3
"""Tuoni discovery — drive a portscan from an agent and surface results.

Actions (default: --portscan if none given):
  --check         list active agents — hostname, user, PID, IPs (read-only)
  --portscan      submit a portscan, poll to COMPLETE, print STDOUT + Discovery API
  --show          dump /discovery/hosts and /discovery/services without scanning

Env:
  TUONI_API     base URL, e.g. https://<host>:8443       (required)
  TUONI_USER    Tuoni API user                           (required)
  TUONI_PASS    Tuoni API password                        (required)
  TUONI_AGENT   default scan agent guid (overridden by --agent-guid)
  TARGET_IPS    default --ips CIDR / list (overridden by --ips)

--check is cleanup.py's checkup (adsim.tuoni.cleanup.tuoni_check).

Importable from a notebook: tuoni_disc_show()/tuoni_disc_portscan() take the
same inputs as the matching flags as keyword arguments and return a dict
instead of only printing. They raise TuoniScriptError on failure — argparse
and sys.exit live only in main(); the core logic is in adsim.
"""
import argparse
import os
import sys

from adsim.tuoni.cleanup import tuoni_check
from adsim.tuoni.common import TuoniScriptError
from adsim.tuoni.discovery import (
    DEFAULT_PORTS,
    tuoni_disc_portscan,
    tuoni_disc_show,
)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--agent-guid", default=os.environ.get("TUONI_AGENT"),
                    help="scan agent guid (default: first active)")

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="list active agents (read-only)")
    mode.add_argument("--portscan", action="store_true",
                      help="run a portscan (default)")
    mode.add_argument("--show", action="store_true",
                      help="dump /discovery/hosts and /discovery/services")

    ap.add_argument("--ips", default=os.environ.get("TARGET_IPS"),
                    help="target CIDR or comma-list (required). "
                         "Env fallback: TARGET_IPS.")
    ap.add_argument("--ports", default=DEFAULT_PORTS,
                    help=f"port comma-list / range (default: {DEFAULT_PORTS})")
    ap.add_argument("--host-discovery", default="ICMP",
                    choices=["ICMP", "ARP", "NONE"],
                    help="host-discovery method (default: ICMP)")
    ap.add_argument("--timeout-ms", type=int, default=None,
                    help="per-port timeout in ms (default: server default)")
    ap.add_argument("--threads", type=int, default=None,
                    help="ARP-probe thread count (default: server default)")
    ap.add_argument("--max-wait", type=int, default=300,
                    help="max seconds to wait for COMPLETE (default: 300)")
    args = ap.parse_args()

    if not (args.check or args.portscan or args.show):
        args.portscan = True

    if args.portscan and not args.ips:
        ap.error("--ips required for --portscan (or set TARGET_IPS env)")

    api = os.environ.get("TUONI_API")
    user = os.environ.get("TUONI_USER")
    password = os.environ.get("TUONI_PASS")

    try:
        if not api:
            raise TuoniScriptError("TUONI_API not set")
        if not (user and password):
            raise TuoniScriptError("TUONI_USER + TUONI_PASS not set")

        if args.check:
            tuoni_check(api=api, user=user, password=password)
        elif args.show:
            tuoni_disc_show(api=api, user=user, password=password)
        else:
            tuoni_disc_portscan(api=api, user=user, password=password,
                         agent_guid=args.agent_guid, ips=args.ips, ports=args.ports,
                         host_discovery=args.host_discovery, timeout_ms=args.timeout_ms,
                         threads=args.threads, max_wait=args.max_wait)
    except TuoniScriptError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
