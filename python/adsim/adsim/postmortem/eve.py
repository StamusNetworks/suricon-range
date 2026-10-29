"""eve.py — freeze Suricata EVE docs for a run's signal flows."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from adsim.postmortem.common import (
    DEFAULT_PAD_SECONDS,
    ExtractError,
    parse_iso,
    read_run,
    run_window,
)

DEFAULT_SIZE = 2000


def index_for_run(run_meta: dict) -> str:
    start = run_meta.get("start_time")
    if not start:
        raise ExtractError("run.json has no start_time")
    day = parse_iso(start).strftime("%Y.%m.%d")
    return f"suricata-{day}"


def _window_query(clause: dict, start_iso: str, stop_iso: str) -> dict:
    return {"bool": {"filter": [
        clause,
        {"range": {"@timestamp": {"gte": start_iso, "lte": stop_iso}}},
    ]}}


def es_search(elk_url: str, index: str, body: dict) -> dict:
    import requests
    try:
        r = requests.post(
            f"{elk_url.rstrip('/')}/{index}/_search",
            json=body, timeout=30, verify=False,
        )
    except Exception as e:
        raise ExtractError(f"ES request failed: {e}") from e
    if r.status_code != 200:
        raise ExtractError(f"ES HTTP {r.status_code}: {r.text[:500]}")
    try:
        return r.json()
    except ValueError as e:
        raise ExtractError(f"non-JSON from ES: {r.text[:500]}") from e


def es_agg_flow_ids(elk_url: str, index: str, kql_list: list[str],
                    start_iso: str, stop_iso: str) -> list[int]:
    all_fids: set[int] = set()
    for q in kql_list:
        body = {
            "size": 0,
            "query": _window_query({"query_string": {"query": q}}, start_iso, stop_iso),
            "aggs": {"fids": {"terms": {"field": "flow_id", "size": 10000}}},
        }
        resp = es_search(elk_url, index, body)
        buckets = resp.get("aggregations", {}).get("fids", {}).get("buckets", [])
        all_fids.update(int(b["key"]) for b in buckets)
        print(f"[*] agg: {len(buckets)} flow_ids for {q!r}", file=sys.stderr)
    return sorted(all_fids)


def unique_community_ids(docs: list[dict]) -> list[str]:
    return sorted({d["community_id"] for d in docs if d.get("community_id")})


def write_cid_txt(out_path: Path, run_id: str, cids: list[str]) -> None:
    lines = [f"# community_ids for run {run_id} — {len(cids)} unique values", *cids]
    out_path.write_text("\n".join(lines) + "\n")


def pm_eve(run_dir, elk_url, resolve_flows=False, fetch_delay=0,
           pad_seconds=DEFAULT_PAD_SECONDS, index=None):
    if not elk_url:
        raise ExtractError("elk_url required")

    run_dir, run_meta = read_run(run_dir)
    # Index naming belongs to the deployment; the daily suricata-* pattern is only a default.
    index = index or index_for_run(run_meta)
    run_id = run_meta["run_id"]

    kql_list = run_meta.get("eve_filter", [])
    if not kql_list:
        raise ExtractError("run.json has no eve_filter")

    start, stop = run_window(run_meta, pad_seconds)
    start_iso, stop_iso = start.isoformat(), stop.isoformat()

    if fetch_delay > 0:
        print(f"[*] waiting {fetch_delay}s for flow flush", file=sys.stderr)
        time.sleep(fetch_delay)

    if resolve_flows:
        fids = es_agg_flow_ids(elk_url, index, kql_list, start_iso, stop_iso)
        print(f"[+] resolved {len(fids)} flow_ids", file=sys.stderr)
        body = {
            "size": DEFAULT_SIZE,
            "sort": [{"@timestamp": "asc"}],
            "query": _window_query({"terms": {"flow_id": fids}}, start_iso, stop_iso),
        }
        print(f"[*] {elk_url} -> {index} flow_ids={len(fids)} window={start_iso[:19]}..{stop_iso[:19]}",
              file=sys.stderr)
        resp = es_search(elk_url, index, body)
        hits = resp.get("hits", {}).get("hits", [])
        print(f"[+] {len(hits)} docs for {len(fids)} flow_ids", file=sys.stderr)
    else:
        all_hits = []
        for q in kql_list:
            body = {
                "size": DEFAULT_SIZE,
                "sort": [{"@timestamp": "asc"}],
                "query": _window_query({"query_string": {"query": q}}, start_iso, stop_iso),
            }
            print(f"[*] {elk_url} -> {index} kql={q!r} window={start_iso[:19]}..{stop_iso[:19]}",
                  file=sys.stderr)
            resp = es_search(elk_url, index, body)
            h = resp.get("hits", {}).get("hits", [])
            print(f"[+] {len(h)} hits for: {q!r}", file=sys.stderr)
            all_hits.extend(h)
        if not all_hits:
            raise ExtractError(f"all {len(kql_list)} KQL filter(s) returned 0 hits")
        seen = set()
        hits = []
        for h in all_hits:
            hid = h["_id"]
            if hid not in seen:
                seen.add(hid)
                hits.append(h)

    docs = [h["_source"] for h in hits]
    docs.sort(key=lambda x: x.get("@timestamp", ""))

    eve_out = run_dir / "artifacts-suricata-eve.json"
    eve_out.write_text(json.dumps(docs, indent=2, sort_keys=False))
    print(f"[+] wrote {len(docs)} docs to {eve_out}", file=sys.stderr)

    cids = unique_community_ids(docs)
    cid_path = run_dir / "artifacts-community-ids.txt"
    write_cid_txt(cid_path, run_id, cids)
    print(f"[+] wrote {len(cids)} community_ids to {cid_path}", file=sys.stderr)

    return {"eve_path": str(eve_out), "cid_path": str(cid_path), "eve_count": len(docs), "cid_count": len(cids)}
