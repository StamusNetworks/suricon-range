---
name: exercise
description: Exercise lifecycle — open run, simulate, cleanup, extract evidence, tag, close run, write findings.
allowed-tools: Read, Bash
---

Orchestrates a cyber exercise end-to-end. Each phase delegates to the
responsible skill; this skill owns the sequence and run tracking.

If `$ARGUMENTS` is provided, treat it as the op-slug and open a new run.

## Lifecycle

| Phase | What | Skill / script |
|---|---|---|
| 1. Open run | `run.py open <op-slug>` — mints run ID, creates run dir | this skill (`scripts/run.py`) |
| 2. Simulate | Execute kill-chain stages (foothold → discovery → lateral) | `/tuoni` |
| 3. Cleanup | Close live connections so sensors finalise flow records | `/tuoni` (`cleanup.py --graceful`) |
| 4. Extract | Freeze EVE docs + PCAPs for the run's flows | `/postmortem` (`eve.py`, `pcap.py`) |
| 5. Close run | `run.py close <run_id>` — stamps end time, sets status | this skill (`scripts/run.py`) |
| 6. Findings | Write `findings.md` with verdict per technique | `/postmortem` (step 4) |

## Run tracking

`scripts/run.py` manages run markers under the runs directory. Runs live in `runs/`
at the repo root: pass `--runs-root "$(git rev-parse --show-toplevel)/runs"`.

- `run.py open <op-slug>` — create run dir, write `run.json` (status: running)
- `run.py close <run_id>` — stamp `end_time`, set status
- `run.py latest` — print most recent run ID
- `run.py list` — print all run IDs

Python API: `adsim.exercise.Run` — `Run(runs_dir, op_slug, ...).open()`, `run.close()`,
`Run.load(runs_dir, run_id)`, `Run.latest(runs_dir)`. A run knows its own `dir` and `marker_path`.

### run.json format

| Field | Type | Required | Description |
|---|---|---|---|
| `run_id` | string | yes | `YYYY-MM-DD-HHMM-<op-slug>` |
| `op_slug` | string | yes | Short kebab-case operation label |
| `start_time` | datetime | yes | ISO 8601 UTC |
| `end_time` | datetime | no | Set on close |
| `status` | string | yes | `running`, `completed`, or `failed` |
| `techniques` | string[] | no | MITRE ATT&CK IDs (e.g. `T1021.002`) |
| `targets` | string[] | no | Hostnames or IPs |
| `eve_filter` | string[] | no | Kibana KQL filters for EVE fetch (all applied, results unioned) |
| `notes` | string | no | Free text |

## Reference skills (outside the lifecycle)

Not part of the phase sequence. Use them for ad-hoc data questions from the
operator, for debugging when `eve.py` / `pcap.py` fail or drift, and as a
manual fallback.

| Skill | Use for |
|---|---|
| `/elastic` | ES REST API — index patterns, `_search` / aggs, mappings. Ad-hoc EVE queries beyond the run's frozen artifacts. |
| `/arkime` | Arkime viewer API — SPI expressions, session search, PCAP download. Session lookups and PCAP pulls outside `pcap.py`. |
| `/suricata-eve` | How to read EVE — event types, flow-first reasoning, alert classification. Interpreting any EVE data. |

## Notes

- Cleanup before extraction is critical — live flows delay sensor flow records
  and packet-store indexing. Evidence frozen before cleanup is incomplete.
- When chaining ops (run A's agent drives run B), skip cleanup between steps.
  Freeze each intermediate run with partial artifacts, cleanup once at the end,
  re-run extract for each run dir (idempotent).
