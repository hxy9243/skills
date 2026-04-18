import tempfile
import unittest
from pathlib import Path

from wikicli.tree import parse_category_tree_structure, tree_from_paths


class TestTreeUtilities(unittest.TestCase):
    def test_parse_category_tree_structure_builds_nested_dicts(self) -> None:
        text = """## Category Tree

- layer1: [Computer Science](categories/computer-science/index.md)
  - layer2: [AI Systems](categories/computer-science/ai-systems/index.md)
    - layer3: [Agents](categories/computer-science/ai-systems/agents/index.md)
- layer1: [Design](categories/design/index.md)

---
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.md"
            path.write_text(text, encoding="utf-8")
            
            tree = parse_category_tree_structure(path)
            self.assertEqual(len(tree), 2)
            self.assertEqual(tree[0]["name"], "Computer Science")
            self.assertEqual(len(tree[0]["children"]), 1)
            self.assertEqual(tree[0]["children"][0]["name"], "AI Systems")
            self.assertEqual(tree[0]["children"][0]["children"][0]["name"], "Agents")
            self.assertEqual(tree[1]["name"], "Design")

    def test_tree_from_paths_combines_flat_paths_into_hierarchy(self) -> None:
        paths = {
            ("Computer Science", "AI Systems", "Agents"),
            ("Computer Science", "AI Systems", "Memory"),
            ("Computer Science", "Databases"),
            ("Design", "Typography"),
        }
        tree = tree_from_paths(paths)
        
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0]["name"], "Computer Science")
        self.assertEqual(tree[1]["name"], "Design")
        
        cs_children = tree[0]["children"]
        self.assertEqual(len(cs_children), 2)
        self.assertEqual(cs_children[0]["name"], "AI Systems")
        self.assertEqual(cs_children[1]["name"], "Databases")
        
        ai_children = cs_children[0]["children"]
        self.assertEqual(len(ai_children), 2)
        self.assertEqual(ai_children[0]["name"], "Agents")
        self.assertEqual(ai_children[1]["name"], "Memory")
