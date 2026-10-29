import json
import os
import tempfile
import unittest
from pathlib import Path

from .exercise import Run, RunError


class RunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name).resolve() / "runs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_close_roundtrip(self):
        run = Run(self.runs, "lateral-wmi", techniques=["T1047"], targets=["dc"],
                  eve_filter=["src_ip: 1.2.3.4"]).open()
        self.assertTrue(run.run_id.endswith("-lateral-wmi"))
        self.assertEqual(run.dir, self.runs / run.run_id)
        self.assertEqual(run.marker["status"], "running")

        run.close()
        marker = json.loads(run.marker_path.read_text())
        self.assertEqual(marker["status"], "completed")
        self.assertIn("end_time", marker)
        self.assertEqual(marker["eve_filter"], ["src_ip: 1.2.3.4"])

    def test_load_and_latest_see_the_written_run(self):
        run = Run(self.runs, "op").open()
        self.assertEqual(Run.load(self.runs, run.run_id).marker, run.marker)
        self.assertEqual(Run.latest(self.runs).run_id, run.run_id)

    def test_latest_filters_by_op_and_file(self):
        old = Run(self.runs, "jump-wmi").open()
        (old.dir / "findings.md").write_text("# findings")
        other = Run(self.runs, "jump-service").open()
        new = Run(self.runs, "jump-wmi").open()
        self.assertEqual(Run.latest(self.runs).run_id, new.run_id)
        self.assertEqual(Run.latest(self.runs, op_slug="jump-service").run_id, other.run_id)
        self.assertEqual(Run.latest(self.runs, op_slug="jump-wmi", with_file="findings.md").run_id,
                         old.run_id)
        with self.assertRaises(RunError):
            Run.latest(self.runs, op_slug="jump-winrm")

    def test_relative_runs_dir_survives_chdir(self):
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            run = Run("runs", "op")
            os.chdir(cwd)
            run.open()
        finally:
            os.chdir(cwd)
        self.assertTrue((self.runs / run.run_id / "run.json").is_file())

    def test_rejects_bad_input(self):
        with self.assertRaises(RunError):
            Run(self.runs, "Bad_Slug")
        with self.assertRaises(RunError):
            Run(self.runs, "op", techniques=["1047"])
        with self.assertRaises(RunError):
            Run(self.runs, "op").close()
        with self.assertRaises(RunError):
            Run.load(self.runs, "missing")


if __name__ == "__main__":
    unittest.main()
