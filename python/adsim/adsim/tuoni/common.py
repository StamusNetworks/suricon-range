"""Shared by the tuoni modules."""
import sys

import urllib3
from tuoni.TuoniC2 import TuoniC2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class TuoniScriptError(RuntimeError):
    pass


def authenticate(api, user, password):
    print(f"[*] Authenticating to {api}")
    c2 = TuoniC2()
    c2.login(api, user, password)
    return c2


def agent_row(agent):
    meta = agent.metadata or {}
    return {"guid": agent.guid, "hostname": meta.get("hostname", "?"),
            "username": meta.get("username", "?"), "pid": meta.get("pid", "?"),
            "ips": meta.get("ips", "?")}


def active_agents(c2, guid=None):
    """Active agents; with guid, only those whose guid starts with it."""
    agents = c2.load_agents(active=True)
    if not guid:
        return agents
    matched = [a for a in agents if a.guid.startswith(guid)]
    if not matched:
        raise TuoniScriptError(f"agent {guid} not in /agents/active")
    return matched


def pick_agent(c2, guid=None):
    agents = active_agents(c2, guid)
    if not agents:
        raise TuoniScriptError("no active agents")
    return agents[0]


def active_agent_guids(c2):
    return {a.guid for a in c2.load_agents(active=True)}


def find_template(c2, name, plugin=None):
    for t in c2.load_command_templates():
        if t.name == name and plugin in (None, t.plugin_id):
            return t
    where = f" in plugin {plugin}" if plugin else ""
    raise TuoniScriptError(f"{name} template not found{where}")


def submit_and_wait(agent, tpl, cfg, max_wait):
    print(f"[*] Submitting {tpl.name} from agent {agent.guid[:8]} "
          f"({agent_row(agent)['hostname']})", file=sys.stderr)
    print(f"    config: {cfg}", file=sys.stderr)
    cmd = agent.send_command(tpl, cfg)
    print(f"[*] Command sent (id={cmd.command_id}) — waiting up to {max_wait}s",
          file=sys.stderr)
    cmd.wait_done(interval=3, maxWait=max_wait)
    return cmd
