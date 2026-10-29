---
name: arkime
description: Arkime REST API — auth, endpoints, SPI expression syntax, and version quirks. Tool-API reference for any skill that talks to Arkime.
allowed-tools: Read
---

Arkime viewer API reference: auth, endpoints, SPI expression language, and
version quirks. This captures the API knowledge as a manual fallback for
debugging or when scripts drift.

## Authentication

- **HTTP Digest** auth. Python: `requests.auth.HTTPDigestAuth(user, password)`.
  Curl: `curl --digest -u <user>:<password>`.
- Basic auth also supported; digest preferred.
- Credentials needed: Arkime viewer URL, username, password. Ask the operator
  if not available.

## Endpoints

Viewer (default port `8005`). Prefer the `/api/` prefix.

| Purpose | Method + path | Notes |
|---|---|---|
| Session search (JSON) | `GET /api/sessions` | Returns session objects (5-tuple, packet/byte counts, timestamps). |
| Bulk PCAP download | `GET /api/sessions/pcap/<filename>.pcap` | Streams multi-session PCAP. Filename is operator-supplied (download name only). Content-Type: `application/vnd.tcpdump.pcap`. |
| Single-session PCAP | `GET /pcap/{sessionId}.pcap?node=<name>` | Less common; bulk endpoint with `id=="..."` is more uniform. |
| Add session tags | `POST /api/sessions/addTags` | Idempotent (re-adding same tag is a no-op). |
| Remove session tags | `POST /api/sessions/removeTags` | Same shape; requires `removeEnabled` user permission. |

Required query params on bulk PCAP: `expression` (URL-encoded SPI), `startTime` + `stopTime` (epoch seconds).

## SPI expression syntax

Arkime's query language. Field names are **Arkime's**, not Suricata's.

- String literals: double-quoted. Escape `"` with `\"`.
- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`. Glob (`*`, `?`) on text fields.
- Boolean: `&&` (AND), `||` (OR), `!` (NOT). Parentheses group.
- OR-of-values: `field == "a" || field == "b"` (no `IN` shortcut).

### Field-name translations from Suricata EVE

| Suricata EVE field | Arkime SPI field |
|---|---|
| `community_id` | **`communityId`** (camelCase) |
| `src_ip` / `dest_ip` | `ip.src` / `ip.dst` (or `ip` for both) |
| `src_port` / `dest_port` | `port.src` / `port.dst` |
| `flow_id` | (no Arkime equivalent — Suricata-only) |

The `community_id` → `communityId` rename is the most important translation
when piping cids from Suricata into Arkime queries.

## Time-range parameters

- `startTime` / `stopTime`: **Unix epoch seconds** (preferred) or ISO 8601.
- Pad the upper edge by `+120 s` — Suricata and Arkime both emit records at
  flow END; a tight bound misses them.

## Bulk-PCAP behavior

- **Empty match → HTTP 200 with a valid but empty PCAP** (global header only).
  Check packet count; don't assume 200 = data.
- **URL length cap ~8 KB** — large OR-chain expressions hit `414 Request-URI
  Too Long`. For >50 cids, chunk into multiple calls and stitch with `mergecap`.
- Multi-cid expressions silently drop non-matching cids — useful for bulk
  fetches but not for per-cid completeness verification.

## Session tagging (two-step shape)

Tag by explicit session IDs, not by `expression`. Reliable shape:

1. `GET /api/sessions` with `expression` + `startTime`/`stopTime` + `fields=id`
   + `length=10000` → collect session IDs.
2. `POST /api/sessions/addTags` with `ids=<comma-separated>` + `tags=<value>`
   (no `expression` or time bound) → tags exactly those sessions.

Idempotent. Indexer lag (~3–5 min) applies — re-run after lag clears.
