import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from os import environ
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wikicli import cli
from wikicli import config as wiki_config
from wikicli import classify, log


TREE_TEXT = """## Category Tree

- layer1: [Computer Science](categories/computer-science/index.md)
  - layer2: [AI Systems](categories/computer-science/ai-systems/index.md)
    - layer3: [Agents](categories/computer-science/ai-systems/agents/index.md)
    - layer3: [Memory](categories/computer-science/ai-systems/memory/index.md)
  - layer2: [Machine Learning](categories/computer-science/machine-learning/index.md)
    - layer3: [Systems](categories/computer-science/machine-learning/systems/index.md)
  - layer2: [Knowledge Systems](categories/computer-science/knowledge-systems/index.md)
    - layer3: [Retrieval](categories/computer-science/knowledge-systems/retrieval/index.md)
    - layer3: [Wikis](categories/computer-science/knowledge-systems/wikis/index.md)
- layer1: [Culture](categories/culture/index.md)
  - layer2: [Technology](categories/culture/technology/index.md)
    - layer3: [Society](categories/culture/technology/society/index.md)
    - layer3: [Briefings](categories/culture/technology/briefings/index.md)
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
        return cli.main(["--config", str(self.config_path), *args])

    def run_cli_json(self, *args: str) -> dict[str, object]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = self.run_cli(*args)
        self.assertIn(rc, {0, 1})
        return json.loads(buffer.getvalue())

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
            with patch("os.getcwd", return_value=str(self.notebook)):
                config = wiki_config.load_config(None)

        self.assertEqual(config.generated_root, self.generated.resolve())
        self.assertEqual(config.include_roots, [self.notebook.resolve()])

    def test_add_packet_updates_log_index_and_categories(self) -> None:
        write_note(self.notebook / "Notes" / "Delegation.md", "# Delegation\n\nDelegate work to subagents when tasks are well scoped.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Delegation",
                    "summary": "Delegate work to smaller agents for bounded tasks.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents", "#delegation"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertIn('"action": "add"', self.load_text(self.generated / "log.md"))
        self.assertIn("Computer Science", self.load_text(self.generated / "index.md"))
        self.assertIn("## Category Tree", self.load_text(self.generated / "index.md"))
        self.assertIn("layer1: [Computer Science](categories/computer-science/index.md)", self.load_text(self.generated / "index.md"))
        self.assertIn("[[Notes/Delegation.md]]", self.load_text(self.generated / "index.md"))
        category_page = self.generated / "categories" / "computer-science" / "ai-systems" / "agents" / "index.md"
        self.assertTrue(category_page.exists())
        self.assertIn("[[Notes/Delegation.md]]", self.load_text(category_page))
        catalog = log.active_catalog(wiki_config.load_config(str(self.config_path)))
        self.assertIsInstance(catalog["Notes/Delegation.md"]["source_mtime_ns"], int)

    def test_add_can_extend_tree(self) -> None:
        write_note(self.notebook / "Notes" / "Odd.md", "# Odd\n\nA note with an unsupported category.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Odd",
                    "summary": "Unsupported branch.",
                    "category": "Design > Craft > Typography",
                    "tags": [],
                    "source": "Notes/Odd.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertIn("layer1: [Design]", self.load_text(self.generated / "index.md"))
        self.assertIn("[[Notes/Odd.md]]", self.load_text(self.generated / "index.md"))

    def test_add_rejects_packet_lists(self) -> None:
        write_note(self.notebook / "Notes" / "Delegation.md", "# Delegation\n\nDelegate work to subagents when tasks are well scoped.")
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(
                "add",
                "--packet",
                json.dumps(
                    [
                        {
                            "title": "Delegation",
                            "summary": "Delegate work to smaller agents for bounded tasks.",
                            "category": "Computer Science > AI Systems > Agents",
                            "tags": ["#agents", "#delegation"],
                            "source": "Notes/Delegation.md",
                        }
                    ]
                ),
            )
        self.assertEqual(str(ctx.exception), "packet payload must be a single object, not a list")

    def test_index_logs_removed_notes_and_reports_unindexed(self) -> None:
        write_note(self.notebook / "Notes" / "State.md", "# State\n\nState keeps workflows coherent.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "State",
                    "summary": "State keeps workflows coherent.",
                    "category": "Computer Science > AI Systems > Memory",
                    "tags": ["#memory"],
                    "source": "Notes/State.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        write_note(self.notebook / "Notes" / "Unindexed.md", "# Unindexed\n\nThis note has not been classified yet.")
        write_note(self.notebook / "Notes" / "Dashboard Index.md", "# Dashboard Index\n\nSystem overview note.")
        (self.notebook / "Notes" / "State.md").unlink()

        payload = self.run_cli_json("index")
        log_text = self.load_text(self.generated / "log.md")
        self.assertIn('"action": "remove"', log_text)
        self.assertIn("Notes/Unindexed.md", payload["unindexed_notes"])
        self.assertIn("Notes/Dashboard Index.md", payload["unindexed_notes"])
        self.assertNotIn("Unindexed.md", self.load_text(self.generated / "index.md"))
        self.assertNotIn("Needs Review", self.load_text(self.generated / "index.md"))
        self.assertNotIn("Indexed Notes By Category", self.load_text(self.generated / "index.md"))

    def test_reconcile_alias_still_works(self) -> None:
        rc = self.run_cli("reconcile")
        self.assertEqual(rc, 0)

    def test_search_uses_generated_docs_as_fallback_context(self) -> None:
        write_note(self.notebook / "AI" / "Retrieval.md", "# Retrieval\n\nSearch systems use retrieval and ranking.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Retrieval",
                    "summary": "Search systems use retrieval and ranking.",
                    "category": "Computer Science > Knowledge Systems > Retrieval",
                    "tags": ["#search"],
                    "source": "AI/Retrieval.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))

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
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        write_note(self.notebook / "Notes" / "Loose.md", "# Loose\n\nNo category yet.")
        (self.notebook / "Notes" / "Delegation.md").unlink()

        rc = self.run_cli("lint", "--log")
        self.assertEqual(rc, 1)
        log_text = self.load_text(self.generated / "log.md")
        self.assertIn('"action": "lint"', log_text)
        self.assertIn("Loose.md", log_text)

    def test_lint_flags_modified_notes_via_mtime(self) -> None:
        note_path = self.notebook / "Notes" / "Delegation.md"
        write_note(note_path, "# Delegation\n\nDelegate work to subagents.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Delegation",
                    "summary": "Delegate work to smaller agents.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        current_ns = note_path.stat().st_mtime_ns
        import time
        time.sleep(0.05)
        note_path.write_text("---\ncategory: Computer Science > AI Systems > Agents\n---\n# Delegation\n\nDelegate more carefully.", encoding="utf-8")

        rc = self.run_cli("lint")
        self.assertEqual(rc, 1)

    def test_search_returns_hierarchy_and_tag_matches(self) -> None:
        write_note(
            self.notebook / "Notes" / "DSPy.md",
            "---\n"
            "tags:\n"
            "- '#dspy'\n"
            "- '#agent'\n"
            "---\n"
            "# DSPy\n\nPrompt optimization for agent programs.\n",
        )
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "DSPy",
                    "summary": "Prompt optimization for agent programs.",
                    "category": "Computer Science > Artificial Intelligence > AI Agents",
                    "tags": ["#dspy", "#agent"],
                    "source": "Notes/DSPy.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))

        payload = self.run_cli_json("search", "dspy agent")
        note_matches = payload["note_matches"]
        self.assertTrue(note_matches)
        self.assertEqual(
            note_matches[0]["hierarchy"],
            ["Computer Science", "Artificial Intelligence", "AI Agents"],
        )
        self.assertIn("tags", note_matches[0]["match_reasons"])

    def test_add_supports_deeper_category_paths(self) -> None:
        write_note(self.notebook / "Notes" / "Optimizer.md", "# Optimizer\n\nA deeper category placement.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Optimizer",
                    "summary": "A deeper category placement.",
                    "category": "Computer Science > Artificial Intelligence > AI Agents > Optimization",
                    "tags": [],
                    "source": "Notes/Optimizer.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        index_text = self.load_text(self.generated / "index.md")
        self.assertIn("layer4: [Optimization]", index_text)
        self.assertTrue((self.generated / "categories" / "computer-science" / "artificial-intelligence" / "ai-agents" / "optimization" / "index.md").exists())

    def test_add_writes_category_frontmatter_property(self) -> None:
        note_path = self.notebook / "Notes" / "Delegation.md"
        write_note(note_path, "# Delegation\n\nDelegate work to subagents when tasks are well scoped.")
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "Delegation",
                    "summary": "Delegate work to smaller agents for bounded tasks.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents", "#delegation"],
                    "source": "Notes/Delegation.md",
                }
            ),
            encoding="utf-8",
        )

        rc = self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        text = self.load_text(note_path)
        self.assertIn('category: "Computer Science > AI Systems > Agents"', text)

    def test_synthesize_returns_structured_note_bundle(self) -> None:
        write_note(
            self.notebook / "Notes" / "DSPy.md",
            "---\n"
            "tags:\n"
            "- '#dspy'\n"
            "- '#agent'\n"
            "---\n"
            "# DSPy\n\nPrompt optimization for agent programs.\n",
        )
        packet_path = self.root / "packet.json"
        packet_path.write_text(
            json.dumps(
                {
                    "title": "DSPy",
                    "summary": "Prompt optimization for agent programs.",
                    "category": "Computer Science > Artificial Intelligence > AI Agents",
                    "tags": ["#dspy", "#agent"],
                    "source": "Notes/DSPy.md",
                }
            ),
            encoding="utf-8",
        )
        self.run_cli("add", "--packet", packet_path.read_text(encoding="utf-8"))

        payload = self.run_cli_json("synthesize", "--tag", "#dspy")
        self.assertEqual(payload["status"], "experimental")
        self.assertEqual(payload["notes"][0]["source"], "Notes/DSPy.md")


if __name__ == "__main__":
    unittest.main()
