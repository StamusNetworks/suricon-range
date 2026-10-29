---
name: suricata-eve
description: Suricata EVE format — event types, timing, universal fields, detection reasoning (flow-first hierarchy, NSM-first principle, alert classification, findings template).
allowed-tools: Read
---

How to read and reason about Suricata EVE data — what to look at and
how to think about it, independent of the connector (jq, pandas,
Elasticsearch).

## Data model

EVE is **JSONL**: one self-contained JSON event per line. Suricata is
an NSM before it is an IDS — ~90% of EVE is parsed protocol metadata
logged because the parser saw it; alerts are ~10%.

### Event types and timing

| Group | event_type values | Emission |
|---|---|---|
| Security | `alert`, `anomaly`, `drop` | as observed |
| Application layer | `smb`, `dcerpc`, `krb5`, `ldap`, `dns`, `tls`, `http`, `rdp`, `ssh`, `smtp`, `quic`, … | per parsed transaction |
| Flow | `flow`, `netflow` | `flow`: at flow end, one two-sided record (both directions). `netflow`: one-sided record per direction |
| File | `fileinfo` | when a file body is transferred |

1. `alert` is emitted **early**, the instant a rule matches. Its
   embedded `flow.*` is a partial snapshot at match time — not
   authoritative.
2. `flow` is emitted **late**, at flow end, with canonical
   bytes/packets/duration both ways — present even for protocols
   Suricata doesn't parse. A connection still open at query time has
   **no `flow` record yet**: its app-layer events appear live, but
   final byte counts and `flow.state` are missing until FIN or flow
   timeout.

### Universal fields

| Field | Use |
|---|---|
| `timestamp` | ISO 8601 with timezone |
| `flow_id` | join key across all events of one flow |
| `tx_id` | transaction order *within* a flow (HTTP requests, DNS Q/A pairs, …) |
| `event_type` | discriminator; gates which per-type fields are populated |
| `src_ip` / `src_port` / `dest_ip` / `dest_port` | 5-tuple |
| `proto` | TCP / UDP / ICMP |
| `app_proto` | detected app-layer protocol on this flow |
| `community_id` | hash of the 5-tuple; cross-tool flow correlation key |

Per-type fields sit under a prefix matching the type: `alert.*`,
`flow.*`, `smb.*`, `dns.*`, …

### Protocol notes

- **DNS** emits two events per transaction (`dns.type: "request"` with
  queries, `"response"` with queries + answers). Key fields:
  `dns.queries[].rrname`, `dns.queries[].rrtype`,
  `dns.answers[].rdata`, `dns.rcode`. When the sensor sees both the
  resolver-upstream and client-facing segments, each exchange appears
  on two flows with different `community_id`s — filter by `rrname`,
  not source IP.
- **LDAP** (ports 389, 3268 Global Catalog) carries `ldap.request` /
  `ldap.response`. In a domain, DC replication and Group Policy
  refresh make it constant background noise — not evidence on its own.

## Reasoning

How to turn EVE events into a detection verdict.

### Event → flow → sequence

```
sequence  (kill chain: an ordered set of flows that together constitute a technique)
  └── flow  (one TCP/UDP connection; all events share the same flow_id)
        └── event  (one atomic protocol record: dcerpc, smb, fileinfo, alert, flow, …)
```

**Detection reasoning happens at the flow level.** The first question
is never "what do 200 smb events mean?" but "how many distinct
connections, from whom, to whom, in what order?" One connection emits
many events; raw event counts inflate apparent activity. A technique
is a sequence of connections, not of events — e.g. PsExec-style
execution: SMB file write → svcctl service creation → service start.
Events within each flow are validation or noise.

### NSM-first principle

Every protocol event (`smb`, `dcerpc`, `fileinfo`, `http`, `tls`,
`flow`, …) is primary evidence — a factual record of what the sensor
observed. Alerts are a secondary layer. **Build detections from NSM
protocol events; attach alerts as enrichments.**

1. Anchor each kill-chain step on the protocol event that records it
   (filename from `fileinfo`, interface/opnum from `dcerpc`, request
   from `http`). Don't reach for an alert to describe what the
   dissection already records. Starting from an alert and looking
   backward for corroboration is inverted.
2. Use alerts where NSM leaves a gap — opaque identifiers (DCERPC
   interface UUID, JA3 hash, DNS blob) that a rule labels.
3. Join alerts to their parent protocol event by `flow_id`. Protocol
   events that triggered an alert also carry `"alerted": true`.

If an NSM step is missing (e.g. no `fileinfo` because the payload was
pre-staged, no `http` detail because it is carried inside HTTPS),
state the gap explicitly — as evasion, or with a proposed highlight
rule to bridge it. Never silently omit the step.

### Alert tiers

The tier is how much an alert *alone* says about malicious intent.
It is independent of the rule's `priority:` field, which is
inconsistently defined across rulesets — never use it as a fidelity
proxy.

| Tier | What the alert alone tells you | Role in detection |
|---|---|---|
| `high` | Near-certain true positive. Known-bad observable with multiple anchors that make benign overlap implausible. Needs scope verification, not corroboration. | Standalone detection. IoC hits, well-anchored C2 signatures. Rare. At the end of a chain, confirmation. |
| `medium` | Legitimate feature used suspiciously — remote admin, privilege use, tool execution. Question: expected from this source at this time? | Surface to analyst for validation. |
| `low` | Noise in isolation; high standalone FP rate. ET INFO / ET POLICY / HUNT. | Never dismiss — in sequence with `medium`/`high`, low-tier alerts are often the most precise evidence of what the attacker did. |

## Method

0. **Orientation** — total event count, `event_type` distribution,
   timestamp min/max per type.
1. **Flow index** — group all events by `flow_id` into the Flow index
   table defined in the findings template. Collapses event counts to
   connection counts.
2. **Sequence check** — on the flow index, find the flows matching
   each kill-chain phase (e.g. delivery, execution, C2).
3. **Alert enrichment** — attach alert SIDs to flows; what
   service/interface do they label?
4. **`flow_id` pivot** — only to resolve ambiguity within a flow: take
   the `flow_id`, pull *all* its events sorted by `tx_id` (or
   `timestamp` across protocols), read the detail (e.g.
   `dcerpc.interfaces[].uuid`, or `tls.ja3` / `http.url` on a suspected
   C2 flow). Repeat with any
   new interesting values.

When unsure where to look, let field cardinality pick the strategy:

| Cardinality | Examples | Strategy |
|---|---|---|
| Low | `event_type`, `proto`, `http.http_method`, `smb.command` | enumerate uniques; anything outside the expected set is an anomaly |
| Medium | `tls.sni`, `dns.queries[].rrname`, `krb5.sname`, `alert.signature` | uniques + counts; outliers stand out |
| High | `http.url`, `http.http_user_agent`, `fileinfo.sha256` | drop frequent patterns; the tail is interesting |

## Findings template

Write `findings.md` using this structure. The section order is deliberate —
it mirrors the event → flow → sequence hierarchy above. Do not reorder,
merge, or invent sections. Output only the document, starting with the
`# findings — <run_id>` line: no preamble, no working notes, no reasoning.
Output raw markdown. Do not wrap in code fences.

```markdown
# findings — <run_id>

## Run

| Field | Value |
|---|---|
| run_id | `<run_id>` |
| op_slug | `<op_slug>` |
| start_time | `<start_time>` |
| end_time | `<end_time>` |
| status | `<status>` |
| techniques | `<techniques>` |
| targets | `<targets>` |

---

## Flow index

`<N>` events across `<N>` flows in window.

| # | First seen | Source | Destination | Port | Proto | Events | Traffic | Alert SIDs | Key metadata |
|---|---|---|---|---|---|---|---|---|---|

One row per distinct `flow_id`, ordered by first timestamp. `Proto` is
`app_proto` when available, else `proto`. `Alert SIDs` lists attached
alert signature_ids (`—` when none fired on this flow). `Traffic`
summarizes volume from `flow.bytes_toserver`/`flow.bytes_toclient` in
human-readable units (e.g. `30 MB↑ 1.2 KB↓`); write `—` when no `flow`
record exists in window. Every row has exactly 10 cells; use `—` for any
empty value. This table is the primary analytical view — raw event counts
belong here, not in a separate alert section.

`Key metadata` picks the most distinctive protocol field values from the
flow's events — what this connection *did*, not just what protocol it spoke:

- **smb**: filename, share, command (e.g. `TREE_CONNECT ADMIN$`, `CREATE+WRITE svc.exe`)
- **dcerpc**: interface name or UUID, opnum (e.g. `drsuapi DRSGetNCChanges`)
- **krb5**: cname, sname (e.g. `TGS-REQ MSSQLSvc/db01 RC4`)
- **tls**: SNI, subject/CN, JA3/JA4 hash (missing SNI = scripted tooling)
- **dns**: queried name (e.g. `A wdcp.microsoft.com`)
- **http**: method + hostname + URL (e.g. `POST /upload.php`); IP-literal
  or missing Host = scripted tooling; non-browser user agent
- **ldap**: operation, base DN or filter (e.g. `searchRequest DC=corp,DC=example`)
- **fileinfo**: filename, sha256 prefix, size, magic (delivered side
  is higher signal than the request)

Keep it terse — a few tokens per flow, not a sentence. Omit when Port and
Proto already say everything.

---

## Timeline

Chronological narrative at flow level. First separate relevant flows from
background. A flow is relevant when it is a step of the activity under
analysis or is caused by one — directly, or as a side effect (a remote
logon triggering ticket requests and name lookups). Traffic that looks
routine is still relevant when timing and endpoints tie it to a step;
attach it to that step's phase and say it is a side effect. Background is
traffic with no such tie — it would have happened anyway. Group only
relevant flows into kill-chain phases. For each phase:

- Name the phase and time window.
- List the flows involved (by `flow_id` or row number from the flow index).
- Describe what the NSM protocol events record — filenames, interfaces,
  service principals, URIs, command names. This is primary evidence.
- Note alerts inline as enrichments: "alert 2025701 fired on this flow,
  labeling the file transfer." Alerts explain opaque values; they do not
  replace the protocol record.

Do not create a separate section for alerts. They appear here, attached
to their parent flows.

After the phases, list background flows once under `### Background` — row
numbers and why each has no tie to the activity. Background never forms a
phase and never counts as evidence in the Verdict.

---

## Verdict

### `<technique_id>` — <technique_name>

- **NSM evidence**: which protocol events (by type and flow) anchor this technique
- **Alert enrichment**: which alerts fired on those flows, what they labeled
- **Gaps**: NSM steps with no protocol event or alert coverage
- **Verdict**: `covered` / `partial` / `missing` / `noisy`

---

## Notes

<free text — IoCs, anomalies, out-of-scope observations, recommendations>
```
