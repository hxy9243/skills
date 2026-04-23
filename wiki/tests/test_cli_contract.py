from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wikicli import cli
from wikicli.app import CommandResult, Issue, WikiCli
from wikicli.config import WikiConfig


class CliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.notebook = self.root / "notebook"
        self.generated = self.notebook / "_WIKI"
        self.generated.mkdir(parents=True)
        self.write_index()
        self.config_path = self.root / "config.json"
        self.config_path.write_text(
            json.dumps(
                {
                    "notebook_root": str(self.notebook),
                    "generated_root": str(self.generated),
                    "include_roots": ["."],
                    "exclude_globs": ["Templates/**"],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_index(self) -> None:
        self.generated.joinpath("log.md").write_text("# Wiki Log\n\n", encoding="utf-8")
        self.generated.joinpath("index.md").write_text(
            "# Wiki Index\n\n"
            "## Category Tree\n\n"
            "- layer1: [Computer Science](categories/computer-science/index.md)\n"
            "  - layer2: [AI Systems](categories/computer-science/ai-systems/index.md)\n"
            "    - layer3: [Agents](categories/computer-science/ai-systems/agents/index.md)\n"
            "    - layer3: [Memory](categories/computer-science/ai-systems/memory/index.md)\n"
            "\n---\n\n"
            "## Skipped System Notes\n- None\n",
            encoding="utf-8",
        )

    def write_note(self, source: str, text: str) -> Path:
        path = self.notebook / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_cli_json(self, *args: str) -> tuple[int, dict[str, object]]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(["--config", str(self.config_path), *args])
        return rc, json.loads(buffer.getvalue())

    def run_cli_text(self, *args: str) -> tuple[int, str]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(["--config", str(self.config_path), *args])
        return rc, buffer.getvalue()

    def test_command_result_envelope_is_stable_json(self) -> None:
        result = CommandResult(
            False,
            "lint",
            data={"checked": True},
            issues=(Issue("missing", "missing thing", path="/tmp/x"),),
            exit_code=1,
        )

        self.assertEqual(
            result.to_json(),
            {
                "ok": False,
                "command": "lint",
                "data": {"checked": True},
                "issues": [
                    {
                        "code": "missing",
                        "message": "missing thing",
                        "severity": "error",
                        "path": "/tmp/x",
                    }
                ],
                "fixes": [],
            },
        )

    def test_status_prints_json(self) -> None:
        rc, payload = self.run_cli_json("status")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["command"], "status")
        self.assertEqual(
            payload["data"]["generated_root"], str(self.generated.resolve())
        )

    def test_add_rejects_packet_lists_as_json_issue(self) -> None:
        rc, payload = self.run_cli_json("add", "--packet", "[]")

        self.assertEqual(rc, 1)
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["issues"][0]["code"], "packet_not_object")

    def test_add_indexes_note_and_renders_generated_files(self) -> None:
        self.write_note("Notes/DSPy.md", "# DSPy\n\nPrompt optimization for agents.")

        rc, payload = self.run_cli_json(
            "add",
            "--packet",
            json.dumps(
                {
                    "title": "DSPy",
                    "summary": "Prompt optimization for agents.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents"],
                    "source": "Notes/DSPy.md",
                }
            ),
        )

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertIn(
            "[[Notes/DSPy.md]]",
            (self.generated / "index.md").read_text(encoding="utf-8"),
        )
        category_page = (
            self.generated
            / "categories"
            / "computer-science"
            / "ai-systems"
            / "agents"
            / "index.md"
        )
        self.assertTrue(category_page.exists())
        self.assertIn("Prompt optimization", category_page.read_text(encoding="utf-8"))

    def test_search_finds_indexed_note_content_and_metadata(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json("search", "optimization agents")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["data"]["results"][0]["source"], "Notes/DSPy.md")
        self.assertIn("content", payload["data"]["results"][0]["match_reasons"])

    def test_show_and_synthesize_return_indexed_catalog_entries(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        show_rc, show_payload = self.run_cli_json("show", "Notes/DSPy.md")
        synth_rc, synth_payload = self.run_cli_json("synthesize", "--tag", "#agents")

        self.assertEqual(show_rc, 0)
        self.assertEqual(show_payload["data"]["note"]["title"], "DSPy")
        self.assertEqual(synth_rc, 0)
        self.assertEqual(synth_payload["data"]["notes"][0]["source"], "Notes/DSPy.md")

    def test_index_reports_unindexed_and_removed_notes(self) -> None:
        note = self.write_note("Notes/State.md", "# State\n\nMemory state.")
        rc, _ = self.run_cli_json(
            "add",
            "--packet",
            json.dumps(
                {
                    "title": "State",
                    "summary": "Memory state.",
                    "category": "Computer Science > AI Systems > Memory",
                    "tags": [],
                    "source": "Notes/State.md",
                }
            ),
        )
        self.assertEqual(rc, 0)
        self.write_note("Notes/Loose.md", "# Loose\n\nUnindexed.")
        note.unlink()

        rc, payload = self.run_cli_json("index")

        self.assertEqual(rc, 0)
        self.assertIn("Notes/State.md", payload["data"]["removed_notes"])
        self.assertIn("Notes/Loose.md", payload["data"]["unindexed_notes"])

    def test_lint_is_read_only_and_reports_unindexed_notes(self) -> None:
        self.write_note("Notes/Loose.md", "# Loose\n\nUnindexed.")

        rc, payload = self.run_cli_json("lint")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["issues"][0]["code"], "source_unindexed")

    def test_tree_defaults_to_plain_markdown_output(self) -> None:
        rc, output = self.run_cli_text("tree")

        self.assertEqual(rc, 0)
        self.assertEqual(
            output,
            "- Computer Science\n"
            "  - AI Systems\n"
            "    - Agents\n"
            "    - Memory\n",
        )

    def test_tree_json_format_preserves_nested_categories(self) -> None:
        rc, payload = self.run_cli_json("tree", "--format", "json")

        self.assertEqual(rc, 0)
        self.assertEqual(
            payload["data"]["categories"],
            [
                {
                    "name": "Computer Science",
                    "children": [
                        {
                            "name": "AI Systems",
                            "children": [
                                {"name": "Agents", "children": []},
                                {"name": "Memory", "children": []},
                            ],
                        }
                    ],
                }
            ],
        )

    def test_thin_reconcile_alias_uses_index_command(self) -> None:
        rc, payload = self.run_cli_json("reconcile")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["command"], "index")

    def test_wikicli_method_surface_exists(self) -> None:
        app = WikiCli(WikiConfig(self.notebook, self.generated, (self.notebook,)))

        self.assertEqual(app.tree().command, "tree")
        self.assertEqual(app.show("Notes/A.md").command, "show")
        self.assertEqual(app.synthesize_bundle(tags=("x",)).command, "synthesize")


if __name__ == "__main__":
    unittest.main()
