import unittest
from types import SimpleNamespace

from .common import (
    TuoniScriptError,
    active_agents,
    agent_row,
    find_template,
    pick_agent,
)


class FakeC2:
    def __init__(self, agents=(), templates=()):
        self.agents = list(agents)
        self.templates = list(templates)

    def load_agents(self, active=True):
        return self.agents

    def load_command_templates(self):
        return self.templates


def agent(guid, **meta):
    return SimpleNamespace(guid=guid, metadata=meta)


def template(name, plugin_id):
    return SimpleNamespace(name=name, plugin_id=plugin_id)


class AgentsTest(unittest.TestCase):
    def test_guid_prefix_matches(self):
        c2 = FakeC2([agent("aaaa-1"), agent("bbbb-2")])
        self.assertEqual([a.guid for a in active_agents(c2, "bbbb")], ["bbbb-2"])
        self.assertEqual(len(active_agents(c2)), 2)

    def test_unknown_guid_raises(self):
        with self.assertRaises(TuoniScriptError):
            active_agents(FakeC2([agent("aaaa-1")]), "cccc")

    def test_pick_with_no_agents_raises(self):
        with self.assertRaises(TuoniScriptError):
            pick_agent(FakeC2())

    def test_row_fills_missing_metadata(self):
        row = agent_row(SimpleNamespace(guid="g", metadata=None))
        self.assertEqual(row, {"guid": "g", "hostname": "?", "username": "?",
                               "pid": "?", "ips": "?"})


class FindTemplateTest(unittest.TestCase):
    def test_plugin_narrows_match(self):
        c2 = FakeC2(templates=[template("portscan", "other"),
                               template("portscan", "shelldot.commands.net")])
        self.assertEqual(find_template(c2, "portscan", "shelldot.commands.net").plugin_id,
                         "shelldot.commands.net")
        self.assertEqual(find_template(c2, "portscan").plugin_id, "other")

    def test_missing_raises(self):
        with self.assertRaises(TuoniScriptError):
            find_template(FakeC2(templates=[template("cmd", "x")]), "die")


if __name__ == "__main__":
    unittest.main()
