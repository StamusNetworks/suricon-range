---
name: postmortem
description: Freeze a completed run's evidence — EVE docs and PCAPs.
allowed-tools: Read, Bash
---

Evidence freeze for a completed run. Assumes the run is already open and live
flows are closed (see `/exercise` for the full lifecycle).

If `$ARGUMENTS` is provided as `<run_id>`, run extraction directly.
Otherwise apply Step 1.

Scripts: `eve.py` (EVE fetch), `pcap.py` (Arkime PCAP).

## Step 1 — Prerequisites

Connection params are always passed explicitly — no hidden env-var fallback in
the Python API. CLI wrappers accept env defaults via argparse.

- **ES endpoint** (`elk_url`) — e.g. `http://<elk_ip>:9200`.
- **Arkime endpoint** (`arkime_url`) — e.g. `http://<arkime_ip>:8005`.
- **Arkime credentials** (`arkime_user`, `arkime_pass`) — HTTP Digest auth.
- **Runs directory** — runs live in `runs/` at the repo root: pass `--runs-root "$(git rev-parse --show-toplevel)/runs"`.
  Notebooks pass `run.dir` from the `Run` object.

If a value is missing, ask the operator.

## Step 2 — Extract EVE (eve.py)

Ensure live flows are closed before extracting — open connections delay `flow`
doc emission and PCAP session indexing.

Query modes (mutually exclusive):

| Mode | When | ES anchor |
|---|---|---|
| **Flow-ID** | Lateral movement, C2, TLS, SMB, DCERPC | `terms` on `flow_id` |
| **Filter** (`--filter`) | DNS, high-cardinality flows | `term`/`wildcard` + time bounds |
| **KQL** (`--kql`) | Ground-truth filters from `eve_filter` in run.json | `query_string` + time bounds |

When called from a notebook with no explicit query, `pm_eve` auto-reads
`eve_filter` from `run.json`.

Writes under `<run_dir>/`:
1. `artifacts-suricata-eve.json` — full EVE docs, `@timestamp` asc.
2. `artifacts-community-ids.txt` — unique `community_id` values, sorted.

Returns `{"docs": [...], "eve_count": int, "cids": [...]}`.

## Step 3 — Fetch PCAP (pcap.py)

Reads community IDs from `artifacts-community-ids.txt` (or accepts explicit `cids`).

```bash
pcap.py <run_id> --runs-root <path> --arkime-url <url> --arkime-user <u> --arkime-pass <p>
```

Writes `artifacts-arkime.pcap` (bulk) or `arkime-pcaps/<cid>.pcap` (`--per-flow`).

Returns `{"pcap_path": str|None}`.

## Step 4 — Write findings.md

Write `<run_dir>/findings.md` using the findings template from the
`suricata-eve` skill.
