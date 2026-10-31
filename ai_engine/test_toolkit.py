"""Unit tests for Jon2's project-owned tool catalog."""
import unittest

from toolkit import available_tools, get_tool_prompt


class ToolCatalogTests(unittest.TestCase):
    def test_all_tools_have_names_and_prompts(self):
        tools = available_tools()
        self.assertGreaterEqual(len(tools), 7)
        self.assertEqual(len({item["id"] for item in tools}), len(tools))
        for item in tools:
            self.assertTrue(item["name"].strip())
            self.assertTrue(get_tool_prompt(item["id"]).strip())

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            get_tool_prompt("shell_or_unapproved_tool")


if __name__ == "__main__":
    unittest.main()
