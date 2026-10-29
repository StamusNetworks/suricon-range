# Postmortem — reference

## Long-lived flow timing

Long-lived TCP connections (persistent TLS sessions, long WebSockets, etc.) hold
their flow open for the connection's entire lifetime. Sensors and packet stores
emit flow-level records only at flow END. Consequences in the freeze artifacts:

- **Sensor**: per-transaction events (`tls`, `http`, `alert`, etc.) emit live,
  but the `flow` event (final byte counts, `flow.state`, app-proto resolution)
  is absent until the connection closes.
- **Packet store**: session records index at flow END. The session is invisible
  to queries until the connection closes.

Ensure live connections are closed before extracting. Once the TCP FIN
propagates, the sensor and packet store finalise the flow within minutes.

When chaining ops and connections must stay alive between steps: freeze each
intermediate run with partial artifacts (flow doc and session record missing),
then close connections once at the end and re-query ES / Arkime for each run
window — the artifacts become complete on the second pass.

## Indexer lag

- Arkime: a session not yet indexed cannot be tagged or fetched. A per-cid
  request returns 404 for recently-emitted cids (~3–5 min observed lag).
- Suricata: a late-emitted `flow` doc won't be in the EVE artifact if it lands
  after the freeze. Re-query ES for the run window to pick it up.
- Tagging (if done externally): `updated: 0` is indexer lag, not failure.
  Re-run after the lag window.

## Validation

- **EVE**: re-running with the same `run_id` and `flow_id`s produces a JSON array
  matching the prior commit up to natural ES growth (flow records emitted later by
  Suricata). Schema and ordering stable; doc count may grow.
- **cid txt**: deterministic transform of the EVE docs — same EVE input → byte-
  identical txt output.
- **PCAP**: validate with `editcap -V <file>` / `tcpdump -r <file> -c 5`. Packet
  count varies with what Arkime has indexed at query time.

## Deployment quirks

- **Index date matches `start_time` UTC date**, not the run op-slug date. A run
  starting at `2026-05-11T00:30:00Z` lands in `suricata-2026.05.11`. Cross-midnight
  runs would need both indices — not handled; emit a warning if encountered.
- **Hosts outside the mirrored segment** are absent from packet-store captures.
- **DNS runs and Arkime 431** — a bulk SPI expression with >~100 cids in an
  OR-chain hits Arkime's request-size limit. Split into per-cid requests.
- **DNS flow_id cardinality** — each UDP DNS query is a distinct flow (new
  ephemeral src-port → new 5-tuple → new flow_id). Hundreds of flow_ids collide
  with unrelated events in the same daily index. Use filter mode with a zone
  wildcard + time bounds instead.
