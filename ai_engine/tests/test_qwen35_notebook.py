"""Validate that executable Kaggle notebook cells remain syntactically valid Python."""
import ast
import json
import unittest
from pathlib import Path


class Qwen35NotebookTests(unittest.TestCase):
    def test_notebook_json_and_python_cells_are_valid(self):
        repo_root = Path(__file__).resolve().parents[2]
        notebook_path = repo_root / "notebooks" / "Jon2_Qwen35_GPU_Inference_Training_Evaluation.ipynb"
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        self.assertEqual(notebook.get("nbformat"), 4)
        code_cells = [cell for cell in notebook["cells"] if cell.get("cell_type") == "code"]
        self.assertGreaterEqual(len(code_cells), 8)
        for index, cell in enumerate(code_cells):
            source = "".join(cell.get("source", []))
            if source.lstrip().startswith("%pip "):
                continue
            with self.subTest(cell=index):
                ast.parse(source, filename=f"{notebook_path.name}:cell-{index}")


if __name__ == "__main__":
    unittest.main()
