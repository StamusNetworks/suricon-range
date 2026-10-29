# Arkime API — reference

## Response-shape quirks

- **Content-Type is `application/vnd.tcpdump.pcap`** on the
  `/api/sessions/pcap/...` endpoint, not `application/pcap`. Filename in the
  URL path is the suggested download name only — it does NOT filter the query.

## Empty-result behavior

- **Single-cid query that matches nothing returns HTTP 404**, not HTTP 200 with
  an empty PCAP. A consumer building a per-cid PCAP set should treat 404 as
  "Arkime has no session for this cid (yet)" — possibly indexer lag, possibly
  capture loss — not a hard failure.
- **OR-chained multi-cid query silently drops non-matching cids.** The consumer
  cannot tell from the response which cids contributed. Useful for bulk fetches;
  use single-cid calls when per-cid completeness needs verification.
- **Indexer lag is real.** Sessions visible in Elasticsearch may not yet be
  queryable in Arkime (~3–5 min observed). Symptom: per-flow `communityId`
  query returns 404, then 200 a few minutes later.

## addTags by explicit session IDs

The reliable path is **two-step**:

1. `GET /api/sessions` with the same `expression` + time bound +
   `fields=id` → collect explicit session IDs that match.
2. `POST /api/sessions/addTags` with `ids=<comma-separated>` +
   `tags=<value>` and **no** `expression` or time bound.

## Time-bound parameter names: `startTime` / `stopTime`, NOT `start` / `stop`

The time-bound params on `/api/sessions` and `/api/sessions/pcap/...` are
**`startTime`** and **`stopTime`** (epoch seconds). With the wrong names, the
response carries the correct `recordsFiltered` count but the **`data[]` array
is silently empty**.

Symptom signature:
```
recordsFiltered = 3       # expression matched 3 sessions
data            = []      # but no rows returned
```

Always use `startTime`/`stopTime`.

## removeTags requires `removeEnabled` user permission

`POST /api/sessions/removeTags` returns permission denied for the default admin
user — `admin: true` is **not** sufficient. The user must also have
`removeEnabled: true`. Until granted, a misapplied tag cannot be cleanly
reverted via the API.

## Indexer lag

Sessions visible in Elasticsearch may take ~3–5 minutes to appear in Arkime's
index. The lag affects per-cid completeness more than the bulk OR endpoint,
because the bulk endpoint silently drops misses while per-flow surfaces them as
explicit 404s.
