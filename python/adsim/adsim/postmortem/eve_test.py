import tempfile
import unittest
from unittest import mock

from ..exercise import Run
from . import eve


class PmEveIndexTest(unittest.TestCase):
    def queried_index(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            run = Run(tmp, "lateral-wmi", eve_filter=["src_ip: 192.0.2.1"]).open()
            hit = {"_id": "1", "_source": {"@timestamp": "t", "community_id": "1:x="}}
            with mock.patch.object(eve, "es_search",
                                   return_value={"hits": {"hits": [hit]}}) as search:
                eve.pm_eve(run.dir, elk_url="http://es", **kwargs)
            return search.call_args.args[1], run.marker["start_time"][:10].replace("-", ".")

    def test_default_index_follows_run_date(self):
        index, day = self.queried_index()
        self.assertEqual(index, f"suricata-{day}")

    def test_explicit_index_wins(self):
        index, _ = self.queried_index(index="eve-*")
        self.assertEqual(index, "eve-*")


if __name__ == "__main__":
    unittest.main()
