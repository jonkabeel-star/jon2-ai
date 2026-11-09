"""Tests for the conservative Jon2 Auto Repair Engine."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import jon2_auto_repair


class AutoRepairTests(unittest.TestCase):
    def test_only_python_trailing_whitespace_is_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ai_engine").mkdir()
            (root / "tests").mkdir()
            source = root / "ai_engine" / "sample.py"
            source.write_bytes(b"value = 1  \nprint(value)\t")
            other = root / "ai_engine" / "notes.txt"
            other.write_bytes(b"keep this  ")
            changed = jon2_auto_repair.normalize_python_whitespace(root)
            self.assertEqual(changed, ["ai_engine/sample.py"])
            self.assertEqual(source.read_bytes(), b"value = 1\nprint(value)\n")
            self.assertEqual(other.read_bytes(), b"keep this  ")

    def test_crlf_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "ai_engine").mkdir()
            (root / "tests").mkdir()
            source = root / "ai_engine" / "windows.py"
            source.write_bytes(b"a = 1  \r\nb = 2\r\n")
            jon2_auto_repair.normalize_python_whitespace(root)
            self.assertEqual(source.read_bytes(), b"a = 1\r\nb = 2\r\n")

    def test_check_commands_are_fixed_and_do_not_use_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(jon2_auto_repair.subprocess, "run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "ok"
                results = jon2_auto_repair.run_checks(root)
            self.assertTrue(all(item["passed"] for item in results))
            self.assertTrue(run.call_args.kwargs["shell"] is False if "shell" in run.call_args.kwargs else True)
            self.assertTrue(all(isinstance(item["command"], list) for item in results))

    def test_check_stops_after_first_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(jon2_auto_repair.subprocess, "run") as run:
                run.return_value.returncode = 1
                run.return_value.stdout = "failure"
                results = jon2_auto_repair.run_checks(root)
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0]["passed"])


if __name__ == "__main__":
    unittest.main()
