import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ..exercise import Run
from .common import ExtractError, read_run, run_window


class RunWindowTest(unittest.TestCase):
    def test_closed_run_pads_end(self):
        start, stop = run_window({"start_time": "2026-11-11T10:00:00Z",
                                  "end_time": "2026-11-11T10:05:00+00:00"}, pad_seconds=60)
        self.assertEqual(start, datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc))
        self.assertEqual(stop, datetime(2026, 11, 11, 10, 6, tzinfo=timezone.utc))

    def test_open_run_ends_now(self):
        before = datetime.now(timezone.utc).replace(microsecond=0)
        _, stop = run_window({"start_time": "2026-11-11T10:00:00+00:00"}, pad_seconds=0)
        self.assertGreaterEqual(stop, before)


class ReadRunTest(unittest.TestCase):
    def test_reads_open_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Run(tmp, "lateral-wmi").open()
            run_dir, marker = read_run(run.dir)
            self.assertEqual(run_dir, run.dir)
            self.assertEqual(marker["run_id"], run.run_id)

    def test_missing_marker(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ExtractError):
            read_run(Path(tmp))


if __name__ == "__main__":
    unittest.main()
