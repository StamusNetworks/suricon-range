---
name: elastic
description: Elasticsearch REST API — auth, search/agg shape, _update_by_query. Tool-API reference for any skill that talks to ES.
allowed-tools: Read
---

What you need to know to talk to Elasticsearch: auth scheme, endpoints,
the query/aggregation shape, and the `_update_by_query` write path.

## Authentication

- ES may expose the API **without xpack security** — no auth required.
- xpack state is configurable. Probe `GET /` on session start; if
  the response is `401`, obtain credentials and retry.

## Endpoints

| Purpose | Method + path | Notes |
|---|---|---|
| Engine identity | `GET /` | Confirm version on session start. |
| Index enumeration | `GET /_cat/indices?v` | Index patterns are deployment-specific — find the Suricata and Windows indices here. |
| Search / aggregate | `POST /<index>/_search` | Standard `query` + `aggs` body. Add `size: 0` for aggs, `track_total_hits: true` for exact totals. |
| Field mapping | `GET /<index>/_mapping` | Probe field shapes — dynamically mapped strings are `text` with a `.keyword` multi-field. |
| Bulk update by query | `POST /<index>/_update_by_query` | Mutating endpoint. Same `query` shape as `_search`, plus a `script` that runs on every matching doc. Used for tagging. |
| Count | `POST /<index>/_count` | Cheap exact count for sanity checks; takes a `query` body. |

## Aggregations — the read path

ES computes over the whole index, server-side. Never rename an
aggregation, add a key, reshape the object, or reformat ES's numbers
— `1.6052081E7`, `"Infinity"`, `"NaN"` are what the server said.
Deriving a table or summary from a response is fine when asked for
one; a number computed anywhere but the server is not a query result.

### Native metric aggregations

| Need | Aggregation |
|---|---|
| count / min / max / avg / sum in one call | `stats` |
| plus variance, std-dev, bounds | `extended_stats` |
| median and tail percentiles | `percentiles` (`percents`) |
| where a value sits in the distribution | `percentile_ranks` (`values`) |
| spread robust to outliers | `median_absolute_deviation` |
| quartiles and whiskers | `boxplot` |
| docs carrying the field | `value_count` |
| **distinct** values (approximate) | `cardinality` (`precision_threshold`) |
| the doc at an extreme | `top_metrics` (with `sort`) |
| keyword length / entropy | `string_stats` |

Pair with `terms`, `rare_terms`, `date_histogram`, `histogram`,
`range`, `filters`. `boxplot`, `top_metrics`, `string_stats` and
`rare_terms` come from the analytics feature; if one errors as
unknown, check `GET /_xpack`.

### Canonical grouped-statistics query

Group by a keyword field, describe a numeric field per group.

```http
POST /<index>/_search
Content-Type: application/json

{
  "size": 0,
  "track_total_hits": true,
  "query": {"bool": {"filter": [
    {"range": {"@timestamp": {"gte": "<start>", "lte": "<stop>"}}}
  ]}},
  "aggs": {
    "by_group": {
      "terms": {"field": "<group_field>.keyword", "size": 50,
                "order": {"_count": "desc"}},
      "aggs": {
        "num_stats": {"stats": {"field": "<numeric_field>"}},
        "num_pct":   {"percentiles": {"field": "<numeric_field>",
                                      "percents": [50, 95, 99]}},
        "distinct":  {"cardinality": {"field": "<distinct_field>.keyword",
                                      "precision_threshold": 1000}},
        "sample":    {"terms": {"field": "<distinct_field>.keyword",
                                "size": 10}}
      }
    }
  }
}
```

Use `size: 0`, time-bound with `range` on `@timestamp`, `.keyword`
on string fields. Swap `stats` for `extended_stats` or add rows from
the metric table as needed, but keep the distinct-count and sample.

## `_update_by_query` — append a tag to matching docs

Appends a keyword value to an array field on every doc matching a filter.
The Painless script initialises the array on first write and uses `contains`
for idempotency.

**Request shape:**

```http
POST /<index>/_update_by_query?conflicts=proceed
Content-Type: application/json

{
  "query": {
    "bool": {
      "filter": [
        {"terms": {"<match_field>.keyword": ["val1", "val2", ...]}},
        {"range": {"@timestamp": {"gte": "<start>", "lte": "<stop>"}}}
      ]
    }
  },
  "script": {
    "lang": "painless",
    "params": {"tag": "<tag-value>"},
    "source": "if (ctx._source.<tag_field> == null) { ctx._source.<tag_field> = new ArrayList(); } if (!ctx._source.<tag_field>.contains(params.tag)) { ctx._source.<tag_field>.add(params.tag); }"
  }
}
```

**Behavior notes:**

- `.keyword` subfield is mandatory on dynamically mapped string match
  fields — the bare field is analyzed `text`; confirm with `_mapping`.
- The `range` filter bounds the operation to a time window. Without a time
  bound, `_update_by_query` walks the whole index.
- `?conflicts=proceed` skips docs updated concurrently. Re-running
  closes gaps.
- Painless script appends idempotently: re-running is a no-op for
  already-tagged docs; newly arrived docs get tagged on re-run.
- Response reports `total`, `updated`, `version_conflicts`,
  `failures`. `total != updated` is fine on re-tag.
- `?refresh=true` makes modifications visible immediately; otherwise
  wait for the index refresh interval (default 1 s).

## Reading Windows event docs

If the cluster also holds Windows event docs, find their index with
`_cat/indices`. Same auth, same `.keyword` rule.

Canonical bridge query: take a `community_id` value, find matching
Sysmon 3 (Network Connection) docs, and return `process.entity_id`
for per-process correlation:

```http
POST /<windows-index>/_search
Content-Type: application/json

{
  "size": 1000,
  "_source": ["@timestamp", "host.hostname", "process.entity_id",
              "network.community_id", "event.code"],
  "query": {"bool": {"filter": [
    {"term":  {"event.code.keyword": "3"}},
    {"terms": {"network.community_id.keyword": ["1:abc=", "1:def=", ...]}},
    {"range": {"@timestamp": {"gte": "<start>", "lte": "<stop>"}}}
  ]}}
}
```

A second `_search` with `terms` on `process.entity_id.keyword` (no
`event.code` filter) returns every event sharing the entity_ids —
the full per-process trail.

The example assumes ECS fields (`network.community_id`,
`process.entity_id`, `event.code`); check `_mapping` for what the
deployment carries.

## Field-shape and mapping notes

Dynamically mapped string fields are `text` with a `.keyword`
multi-field. Always use `.keyword` for `term`/`terms`
filters and `terms` aggregations — bare string fields hit the
analyzed `text` mapping and produce wrong or empty results.

`community_id` is top-level on most EVE events (alert, smb, dcerpc,
flow, tls, http, dns, krb5).
