import tempfile
import unittest
from pathlib import Path

from compute_core.storage import ComputeStorage


class StorageTests(unittest.TestCase):
    def test_values_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "test.sqlite3")
            first = ComputeStorage(path)
            first.set("hello", {"arabic": "مرحبا", "n": 7})
            second = ComputeStorage(path)
            self.assertEqual(second.get("hello"), {"arabic": "مرحبا", "n": 7})
            self.assertEqual(second.count(), 1)
            self.assertTrue(second.delete("hello"))
            self.assertIsNone(second.get("hello"))


if __name__ == "__main__":
    unittest.main()
