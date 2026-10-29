"""findings.py — ask an LLM to write findings.md for a run.

The system prompt is the suricata-eve skill, which carries the findings
template. The user message is the run's run.json plus its EVE events as CSV,
trimmed to FINDINGS_COLS. Any OpenAI-compatible endpoint works.
"""
from __future__ import annotations

import json

from adsim.postmortem.common import read_run

DEFAULT_LLM_URL = "https://openrouter.ai/api/v1"
FINDINGS_HEADING = "# findings — "

FINDINGS_COLS = [
    # universal
    "timestamp", "event_type", "flow_id", "community_id",
    "src_ip", "dest_ip", "src_port", "dest_port", "proto", "app_proto",
    # protocol — dcerpc
    "dcerpc.request", "dcerpc.response", "dcerpc.req.opnum", "dcerpc.interfaces",
    # protocol — smb
    "smb.command", "smb.status", "smb.filename", "smb.share",
    # protocol — krb5
    "krb5.msg_type", "krb5.cname", "krb5.sname", "krb5.realm",
    # protocol — tls
    "tls.version", "tls.ja3.hash", "tls.ja4", "tls.subject", "tls.issuerdn",
    # protocol — dns, http, file
    "dns.type", "dns.queries",
    "http.hostname", "http.url", "http.http_method", "http.http_user_agent",
    "fileinfo.filename", "fileinfo.sha256", "fileinfo.size",
    # alerts (enrichment)
    "alert.signature", "alert.signature_id", "alert.category",
    "alert.severity", "alert.action",
    # flow close
    "flow.bytes_toserver", "flow.bytes_toclient",
    "flow.start", "flow.end", "flow.state",
]


class FindingsError(RuntimeError):
    pass


def eve_csv(df) -> tuple[str, list[str]]:
    """Project a json_normalize'd EVE frame onto FINDINGS_COLS, sorted by time."""
    available = [c for c in FINDINGS_COLS if c in df.columns]
    return df[available].sort_values("timestamp").to_csv(index=False), available


def findings_prompt(run_meta: dict, df) -> str:
    csv, available = eve_csv(df)
    return (f"Generate findings.md for this run.\n\n"
            f"Run metadata:\n{json.dumps(run_meta, indent=2)}\n\n"
            f"Suricata EVE (CSV, {len(available)} columns, {len(df)} events):\n{csv}")


def pm_findings(run_dir, df, system_prompt, llm_key, llm_model, llm_url=DEFAULT_LLM_URL):
    """Write <run_dir>/findings.md from the LLM's answer and return its path."""
    from openai import OpenAI

    run_dir, run_meta = read_run(run_dir)
    llm = OpenAI(base_url=llm_url, api_key=llm_key)
    resp = llm.chat.completions.create(
        model=llm_model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": findings_prompt(run_meta, df)}],
    )
    text = resp.choices[0].message.content or ""
    start = text.find(FINDINGS_HEADING)
    if start < 0:
        raise FindingsError(f"LLM answer has no '{FINDINGS_HEADING}' heading: {text[:300]!r}")
    # The slice drops any reasoning preamble before the template.
    path = run_dir / "findings.md"
    path.write_text(text[start:])
    return {"findings_path": str(path)}
