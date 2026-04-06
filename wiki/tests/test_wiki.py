import json
import tempfile
import unittest
from pathlib import Path
from os import environ
from unittest.mock import patch

from wiki.scripts import wiki


TREE_TEXT = """## Category Tree

### Computer Science
- AI Systems
  - Agents
  - Memory
  - Research
- Knowledge Systems
  - Retrieval
  - Wikis

### Culture
- Technology
  - Society
  - Briefings
"""


def write_note(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class WikiScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.notebook = self.root / "notebook"
        self.notebook.mkdir()
        self.generated = self.notebook / "_WIKI"
        self.generated.mkdir()
        (self.generated / "index.md").write_text(
            "# Wiki Index\n\n"
            + TREE_TEXT
            + "\n\n---\n\n## Skipped System Notes\n- None\n",
            encoding="utf-8",
        )
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "include_roots": ["."],
                    "exclude_globs": ["Templates/**"],
                    "generated_root": str(self.generated),
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: str) -> int:
        return wiki.main(["--config", str(self.config_path), *args])

    def load_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_local_generated_root_config_overrides_global(self) -> None:
        global_config_dir = self.root / ".wiki"
        global_config_dir.mkdir()
        global_config_path = global_config_dir / "config.json"
        global_config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "include_roots": ["Wrong"],
                    "generated_root": str(self.generated),
                }
            ),
            encoding="utf-8",
        )
        local_config_path = self.generated / "config.json"
        local_config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "include_roots": ["."],
                    "generated_root": str(self.generated),
                }
            ),
            encoding="utf-8",
        )

        with patch.dict(environ, {"HOME": str(self.root)}):
            config = wiki.load_config(None)

        self.assertEqual(config.generated_root, self.generated.resolve())
        self.assertEqual(config.include_roots, [self.notebook.resolve()])

    def test_prefix_override_applies_to_matching_paths(self) -> None:
        local_config_path = self.generated / "config.json"
        local_config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "include_roots": ["."],
                    "generated_root": str(self.generated),
                    "category_prefix_overrides": {
                        "20_Subjects/Computer Science/Computer Systems/Distributed Systems": [
                            "Computer Science",
                            "Computer Systems",
                            "Distributed Systems",
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        write_note(
            self.notebook / "20_Subjects" / "Computer Science" / "Computer Systems" / "Distributed Systems" / "BBoltDB.md",
            "# BBoltDB\n\nEmbedded storage for system design notes.",
        )

        packet = wiki.extract_packet_from_note(
            self.notebook / "20_Subjects" / "Computer Science" / "Computer Systems" / "Distributed Systems" / "BBoltDB.md",
            wiki.load_config(str(self.config_path)),
        )
        self.assertEqual(
            packet["category_path"],
            ["Computer Science", "Computer Systems", "Distributed Systems"],
        )

    def test_add_packet_updates_log_index_and_categories(self) -> None:
        write_note(self.notebook / "Notes" / "Delegation.md", "# Delegation\n\nDelegate work to subagents when tasks are well scoped.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Delegation",
                    "summary": "Delegate work to smaller agents for bounded tasks.",
                    "category_path": ["Computer Science", "AI Systems", "Agents"],
                    "tags": ["#agents", "#delegation"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", str(packet_path))
        self.assertEqual(rc, 0)
        self.assertIn('"action": "add"', self.load_text(self.generated / "log.md"))
        self.assertIn("Computer Science", self.load_text(self.generated / "index.md"))
        self.assertIn("## Category Tree", self.load_text(self.generated / "index.md"))
        self.assertIn("layer1: [Computer Science](categories/computer-science/index.md)", self.load_text(self.generated / "index.md"))
        self.assertIn("[[Notes/Delegation.md]]", self.load_text(self.generated / "index.md"))
        category_page = self.generated / "categories" / "computer-science" / "ai-systems" / "agents" / "index.md"
        self.assertTrue(category_page.exists())
        self.assertIn("[[Notes/Delegation.md]]", self.load_text(category_page))

    def test_add_can_extend_tree(self) -> None:
        write_note(self.notebook / "Notes" / "Odd.md", "# Odd\n\nA note with an unsupported category.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Odd",
                    "summary": "Unsupported branch.",
                    "category_path": ["Design", "Craft", "Typography"],
                    "tags": [],
                    "source": "Notes/Odd.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", str(packet_path))
        self.assertEqual(rc, 0)
        self.assertIn("layer1: [Design]", self.load_text(self.generated / "index.md"))
        self.assertIn("[[Notes/Odd.md]]", self.load_text(self.generated / "index.md"))

    def test_index_logs_removed_notes_and_reports_unindexed(self) -> None:
        write_note(self.notebook / "Notes" / "State.md", "# State\n\nState keeps workflows coherent.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "State",
                    "summary": "State keeps workflows coherent.",
                    "category_path": ["Computer Science", "AI Systems", "Memory"],
                    "tags": ["#memory"],
                    "source": "Notes/State.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", str(packet_path))
        write_note(self.notebook / "Notes" / "Unindexed.md", "# Unindexed\n\nThis note has not been classified yet.")
        write_note(self.notebook / "Notes" / "Dashboard Index.md", "# Dashboard Index\n\nSystem overview note.")
        (self.notebook / "Notes" / "State.md").unlink()

        rc = self.run_cli("index")
        self.assertEqual(rc, 0)
        log_text = self.load_text(self.generated / "log.md")
        self.assertIn('"action": "remove"', log_text)
        self.assertIn("Unindexed.md", self.load_text(self.generated / "index.md") or "")
        self.assertIn("Unsorted", self.load_text(self.generated / "index.md"))
        self.assertIn("Dashboard Index.md", self.load_text(self.generated / "index.md"))
        self.assertIn("Unindexed.md", self.load_text(self.generated / "index.md"))
        self.assertNotIn("Indexed Notes By Category", self.load_text(self.generated / "index.md"))

    def test_search_uses_generated_docs_as_fallback_context(self) -> None:
        write_note(self.notebook / "AI" / "Retrieval.md", "# Retrieval\n\nSearch systems use retrieval and ranking.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Retrieval",
                    "summary": "Search systems use retrieval and ranking.",
                    "category_path": ["Computer Science", "Knowledge Systems", "Retrieval"],
                    "tags": ["#search"],
                    "source": "AI/Retrieval.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", str(packet_path))

        rc = self.run_cli("search", "ranking")
        self.assertEqual(rc, 0)
        index_text = self.load_text(self.generated / "index.md")
        self.assertIn("layer3: [Retrieval]", index_text)
        category_page = self.load_text(self.generated / "categories" / "computer-science" / "knowledge-systems" / "retrieval" / "index.md")
        self.assertIn("## Brief Intro", category_page)
        self.assertIn("## Search Cues", category_page)

    def test_lint_flags_unindexed_and_missing_sources(self) -> None:
        write_note(self.notebook / "Notes" / "Delegation.md", "# Delegation\n\nDelegate work to subagents.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Delegation",
                    "summary": "Delegate work to smaller agents.",
                    "category_path": ["Computer Science", "AI Systems", "Agents"],
                    "tags": ["#agents"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", str(packet_path))
        write_note(self.notebook / "Notes" / "Loose.md", "# Loose\n\nNo category yet.")
        (self.notebook / "Notes" / "Delegation.md").unlink()

        rc = self.run_cli("lint", "--log")
        self.assertEqual(rc, 1)
        log_text = self.load_text(self.generated / "log.md")
        self.assertIn('"action": "lint"', log_text)
        self.assertIn("Loose.md", log_text)


if __name__ == "__main__":
    unittest.main()
