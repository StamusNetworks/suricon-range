"""checkup + cleanup for Tuoni C2 agents."""
import sys
import time

from adsim.tuoni.common import (
    TuoniScriptError,
    active_agents,
    agent_row,
    authenticate,
    find_template,
)


def checkup(agents):
    rows = [agent_row(a) for a in agents]
    if not rows:
        print("no active agents")
        print("0 active")
        return {"active": []}
    fmt = "{:<36}  {:<18}  {:<22}  {:<6}  {}"
    print(fmt.format("GUID", "HOST", "USER", "PID", "IPS"))
    print("-" * 96)
    for row in rows:
        print(fmt.format(row["guid"], row["hostname"], row["username"], row["pid"], row["ips"]))
    print(f"{len(rows)} active")
    return {"active": rows}


def deactivate(c2, agent):
    c2.request_put(f"/api/v1/agents/{agent.guid}/inactive")


def graceful_stop(c2, agent, die, erase):
    if die is None:
        deactivate(c2, agent)
        return

    print(f"  -> die {agent.guid[:8]} erase={erase}", file=sys.stderr)
    agent.send_command(die, {"erase": erase})

    time.sleep(10)
    deactivate(c2, agent)


def _cleanup_agents(c2, agents, graceful, erase):
    if not agents:
        print("no active agents — nothing to clean up", file=sys.stderr)
        print("0 deactivated")
        return {"deactivated": []}

    die = None
    if graceful:
        try:
            die = find_template(c2, "die")
        except TuoniScriptError:
            print("  [warn] 'die' template missing — fast deactivate only", file=sys.stderr)
    done = []
    for agent in agents:
        host = agent_row(agent)["hostname"]
        if graceful:
            graceful_stop(c2, agent, die, erase)
        else:
            print(f"  -> deactivate {agent.guid[:8]} ({host})", file=sys.stderr)
            deactivate(c2, agent)
        print(f"  ok {agent.guid[:8]} ({host})", file=sys.stderr)
        done.append({"guid": agent.guid, "hostname": host})

    print(f"{len(done)} deactivated")
    return {"deactivated": done}


def tuoni_check(api=None, user=None, password=None, agent_guid=None):
    c2 = authenticate(api, user, password)
    return checkup(active_agents(c2, agent_guid))


def tuoni_fast(api=None, user=None, password=None, agent_guid=None):
    c2 = authenticate(api, user, password)
    return _cleanup_agents(c2, active_agents(c2, agent_guid), graceful=False, erase=False)


def tuoni_cleanup(api=None, user=None, password=None, agent_guid=None, erase=False):
    c2 = authenticate(api, user, password)
    return _cleanup_agents(c2, active_agents(c2, agent_guid), graceful=True, erase=erase)
