"""pcap.py — download PCAPs from Arkime for a run's community IDs."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from adsim.postmortem.common import (
    DEFAULT_PAD_SECONDS,
    ExtractError,
    read_run,
    run_window,
)

_PCAP_GLOBAL_HEADER_LEN = 24

_ARKIME_CID_BATCH = 50


def _sanitize_cid(cid: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", cid)


def _arkime_fetch(session, url: str, params: dict) -> tuple[bool, bytes, str]:
    try:
        r = session.get(url, params=params, stream=True, timeout=60, verify=False)
    except Exception as e:
        return False, b"", str(e)
    if r.status_code != 200:
        return False, b"", f"HTTP {r.status_code}: {r.text[:200]}"
    data = b"".join(r.iter_content(64 * 1024))
    return True, data, ""


def _arkime_download(arkime_url, user, password, cids,
                     start_epoch, stop_epoch, run_dir, per_flow):
    import requests
    from requests.auth import HTTPDigestAuth

    url = f"{arkime_url.rstrip('/')}/api/sessions/pcap/sessions.pcap"
    session = requests.Session()
    session.auth = HTTPDigestAuth(user, password)
    errors = []

    if per_flow:
        out_dir = run_dir / "arkime-pcaps"
        out_dir.mkdir(parents=True, exist_ok=True)
        ok_count = 0
        for cid in cids:
            expr = f'communityId=="{cid}"'
            params = {"expression": expr, "startTime": start_epoch, "stopTime": stop_epoch}
            ok, data, err = _arkime_fetch(session, url, params)
            if not ok:
                errors.append(f"{cid}: {err}")
                continue
            if not data:
                continue
            (out_dir / f"{_sanitize_cid(cid)}.pcap").write_bytes(data)
            ok_count += 1
        print(f"[+] wrote {ok_count}/{len(cids)} per-cid PCAPs to {out_dir}", file=sys.stderr)
        for e in errors:
            print(f"[!] {e}", file=sys.stderr)
        return True, str(out_dir)

    pcap_out = run_dir / "artifacts-arkime.pcap"
    written = 0
    first_batch = True
    with pcap_out.open("wb") as f:
        for i in range(0, len(cids), _ARKIME_CID_BATCH):
            batch = cids[i:i + _ARKIME_CID_BATCH]
            expr = " || ".join(f'communityId=="{c}"' for c in batch)
            params = {"expression": expr, "startTime": start_epoch, "stopTime": stop_epoch}
            ok, data, err = _arkime_fetch(session, url, params)
            if not ok:
                errors.append(err)
                continue
            if not data:
                continue
            if first_batch:
                f.write(data)
                written += len(data)
                first_batch = False
            else:
                f.write(data[_PCAP_GLOBAL_HEADER_LEN:])
                written += len(data) - _PCAP_GLOBAL_HEADER_LEN

    if errors and written == 0:
        pcap_out.unlink(missing_ok=True)
        print(f"[!] PCAP fetch failed: {errors[0]}", file=sys.stderr)
        return False, None
    msg = f"{written} bytes"
    if errors:
        msg += f" ({len(errors)} batch errors: {errors[0]})"
    print(f"[+] wrote PCAP to {pcap_out} ({msg})", file=sys.stderr)
    return True, str(pcap_out)


def _read_cids_from_file(path: Path) -> list[str]:
    lines = path.read_text().strip().splitlines()
    return [l for l in lines if l and not l.startswith("#")]


def pm_pcap(run_dir, arkime_url, arkime_user, arkime_pass,
            cids=None, per_flow=False, pad_seconds=DEFAULT_PAD_SECONDS):
    if not all([arkime_url, arkime_user, arkime_pass]):
        raise ExtractError("arkime_url, arkime_user, and arkime_pass required")

    run_dir, run_meta = read_run(run_dir)

    if cids is None:
        cid_file = run_dir / "artifacts-community-ids.txt"
        if not cid_file.is_file():
            raise ExtractError(f"no cids passed and {cid_file} not found — run eve.py first")
        cids = _read_cids_from_file(cid_file)

    if not cids:
        print("[!] no community_ids — nothing to fetch", file=sys.stderr)
        return {"pcap_path": None}

    start, stop = run_window(run_meta, pad_seconds)

    ok, path = _arkime_download(
        arkime_url, arkime_user, arkime_pass,
        cids, int(start.timestamp()), int(stop.timestamp()), run_dir, per_flow)
    return {"pcap_path": path if ok else None}
