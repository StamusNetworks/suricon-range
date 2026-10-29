"""Tuoni discovery — drive a portscan from an agent and surface results."""
import sys

from adsim.tuoni.common import (
    TuoniScriptError,
    authenticate,
    find_template,
    pick_agent,
    submit_and_wait,
)

PORTSCAN_PLUGIN = "shelldot.commands.net"

DEFAULT_PORTS = "22,80,135,139,389,443,445,3389,5985,5986,8080"


def _api_get(c2, path):
    return c2.request_get(f"/api/v1{path}")


def show_discovery(c2):
    hosts = _api_get(c2, "/discovery/hosts")
    services = _api_get(c2, "/discovery/services")
    h_items = hosts.get("items", []) if isinstance(hosts, dict) else hosts
    s_items = services.get("items", []) if isinstance(services, dict) else services

    print(f"-- /discovery/hosts ({len(h_items)}) --")
    for h in h_items:
        addr = h.get("address", "?")
        note = h.get("note", "")
        print(f"  {addr:<16}  {note}")

    print(f"-- /discovery/services ({len(s_items)}) --")
    for s in s_items:
        addr = s.get("address", "?")
        port = s.get("port", "?")
        proto = s.get("protocol", "?")
        note = s.get("note", "")
        print(f"  {addr:<16}  {port}/{proto:<3}  {note}")

    return {"hosts": h_items, "services": s_items}


def portscan(c2, agent, ips, ports, host_discovery, timeout_ms, threads, max_wait):
    tpl = find_template(c2, "portscan", PORTSCAN_PLUGIN)
    cfg = {"ips": ips, "ports": ports, "hostDiscovery": host_discovery}
    if timeout_ms is not None:
        cfg["timeout"] = timeout_ms
    if threads is not None:
        cfg["threads"] = threads

    cmd = submit_and_wait(agent, tpl, cfg, max_wait)

    if cmd.is_failed():
        raise TuoniScriptError(f"portscan FAILED — command id={cmd.command_id}")
    if not cmd.is_done():
        raise TuoniScriptError(f"portscan did not finish within {max_wait}s — "
                                f"command id={cmd.command_id}, status still ongoing")

    print(f"[+] Portscan done (cmd id={cmd.command_id})", file=sys.stderr)

    print("-- portscan STDOUT --")
    result = cmd.get_result()
    stdout_text = result.get_text() if result is not None else None
    print(stdout_text.strip() if stdout_text else ("(empty)" if result is not None else "(no result)"))

    discovery = show_discovery(c2)
    return {"command_id": cmd.command_id, "stdout": stdout_text, **discovery}


def tuoni_disc_show(api=None, user=None, password=None):
    c2 = authenticate(api, user, password)
    return show_discovery(c2)


def tuoni_disc_portscan(api=None, user=None, password=None, agent_guid=None,
                  ips=None, ports=DEFAULT_PORTS, host_discovery="ICMP",
                  timeout_ms=None, threads=None, max_wait=300):
    c2 = authenticate(api, user, password)
    agent = pick_agent(c2, agent_guid)
    return portscan(c2, agent, ips, ports, host_discovery, timeout_ms, threads, max_wait)
