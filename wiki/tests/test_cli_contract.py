from __future__ import annotations

import json
import sys
import tempfile
import time
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
            rc = cli.main(["--config", str(self.config_path), "--format", "json", *args])
        return rc, json.loads(buffer.getvalue())

    def run_cli_text(self, *args: str) -> tuple[int, str]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(["--config", str(self.config_path), *args])
        return rc, buffer.getvalue()

    def run_cli_json_with_root(self, *args: str) -> tuple[int, dict[str, object]]:
        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(["--root", str(self.notebook), "--format", "json", *args])
        return rc, json.loads(buffer.getvalue())

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

    def test_add_rejects_packet_lists_as_json_issue(self) -> None:
        rc, payload = self.run_cli_json("add", "--json", "[]")

        self.assertEqual(rc, 1)
        self.assertEqual(payload["ok"], False)
        self.assertEqual(payload["issues"][0]["code"], "packet_not_object")

    def test_add_indexes_note_and_renders_generated_files(self) -> None:
        self.write_note("Notes/DSPy.md", "# DSPy\n\nPrompt optimization for agents.")

        rc, payload = self.run_cli_json(
            "add",
            "--json",
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
        category_text = category_page.read_text(encoding="utf-8")
        self.assertIn("Prompt optimization", category_text)
        self.assertIn('wiki_role: "synthesis"', category_text)
        self.assertIn('wiki_note_count: 1', category_text)
        self.assertIn('tags:', category_text)

    def test_add_allow_undeclared_expands_tree_before_rebuild(self) -> None:
        self.write_note("Notes/Tools.md", "# Tools\n\nTool use for agents.")
        packet = json.dumps(
            {
                "title": "Tools",
                "summary": "Tool use for agents.",
                "category": "Computer Science > AI Systems > Tools",
                "tags": ["#agents"],
                "source": "Notes/Tools.md",
            }
        )

        rejected_rc, rejected_payload = self.run_cli_json("add", "--json", packet)
        accepted_rc, accepted_payload = self.run_cli_json(
            "add", "--json", packet, "--allow-undeclared"
        )

        self.assertEqual(rejected_rc, 1)
        self.assertEqual(
            rejected_payload["issues"][0]["code"], "category_not_approved"
        )
        self.assertEqual(accepted_rc, 0)
        self.assertEqual(accepted_payload["ok"], True)
        self.assertIn(
            "- layer3: [Tools](categories/computer-science/ai-systems/tools/index.md)",
            (self.generated / "index.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            (
                self.generated
                / "categories"
                / "computer-science"
                / "ai-systems"
                / "tools"
                / "index.md"
            ).exists()
        )

    def test_lint_flags_catalog_category_outside_tree(self) -> None:
        note = self.write_note("Notes/Tools.md", "# Tools\n\nTool use for agents.")
        self.generated.joinpath("log.md").write_text(
            "# Wiki Log\n\n"
            "- "
            + json.dumps(
                {
                    "timestamp": "2026-05-23T00:00:00Z",
                    "action": "add",
                    "title": "Tools",
                    "summary": "Tool use for agents.",
                    "category": "Computer Science > AI Systems > Tools",
                    "tags": ["#agents"],
                    "source": "Notes/Tools.md",
                    "source_mtime_ns": note.stat().st_mtime_ns,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        rc, payload = self.run_cli_json("lint", "--filter", "invalid_category")

        self.assertEqual(rc, 1)
        self.assertEqual(payload["issues"][0]["code"], "invalid_category")
        self.assertIn("not present", payload["issues"][0]["message"])

    def test_rebuild_preserves_rich_category_synthesis(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()
        category_page = (
            self.generated
            / "categories"
            / "computer-science"
            / "ai-systems"
            / "agents"
            / "index.md"
        )
        original = category_page.read_text(encoding="utf-8")
        compact = (
            "Agents is a focused leaf under AI Systems. This page collects the notes "
            "that most directly define this topic in the current wiki."
        )
        rich_synthesis = (
            "Agents pages track runtime design for model-backed workers.\n\n"
            "They emphasize how memory, tools, and prompt programs turn isolated "
            "model calls into maintained systems."
        )
        category_page.write_text(
            original.replace(f"\n{compact}\n", f"\n{rich_synthesis}\n", 1),
            encoding="utf-8",
        )
        self.write_note("Notes/Reflexion.md", "# Reflexion\n\nSelf-critique loops.")

        rc, payload = self.run_cli_json(
            "add",
            "--json",
            json.dumps(
                {
                    "title": "Reflexion",
                    "summary": "Self-critique loops for agents.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#agents"],
                    "source": "Notes/Reflexion.md",
                }
            ),
        )

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        category_text = category_page.read_text(encoding="utf-8")
        self.assertIn(rich_synthesis, category_text)
        self.assertNotIn(f"\n{compact}\n", category_text)
        self.assertIn(
            "[[Notes/DSPy.md]] - Prompt optimization for agents.",
            category_text,
        )
        self.assertIn(
            "[[Notes/Reflexion.md]] - Self-critique loops for agents.",
            category_text,
        )

    def test_search_finds_indexed_note_content_and_metadata(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json("search", "optimization agents")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["data"]["results"][0]["source"], "Notes/DSPy.md")
        self.assertIn("content", payload["data"]["results"][0]["match_reasons"])

    def test_list_root_shows_subcategories(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json("list")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["command"], "list")
        self.assertIn("Computer Science", payload["data"]["subcategories"])
        # Root has no direct entries, only subcategories
        self.assertEqual(len(payload["data"]["entries"]), 0)

    def test_root_flag_loads_notebook_wiki_config(self) -> None:
        (self.generated / "config.json").write_text(
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
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json_with_root("list", "Computer Science")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["command"], "list")
        self.assertIn("AI Systems", payload["data"]["subcategories"])

    def test_path_alias_works_after_subcommand(self) -> None:
        (self.generated / "config.json").write_text(
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
        self.test_add_indexes_note_and_renders_generated_files()

        buffer = StringIO()
        with redirect_stdout(buffer):
            rc = cli.main(
                [
                    "--format",
                    "json",
                    "list",
                    "Computer Science",
                    "--path",
                    str(self.notebook),
                ]
            )
        payload = json.loads(buffer.getvalue())

        self.assertEqual(rc, 0)
        self.assertIn("AI Systems", payload["data"]["subcategories"])

    def test_list_branch_shows_children(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json(
            "list", "Computer Science > AI Systems"
        )
        self.assertEqual(rc, 0)
        self.assertIn("Agents", payload["data"]["subcategories"])
        self.assertIn("Memory", payload["data"]["subcategories"])

    def test_list_leaf_shows_entries(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json(
            "list", "Computer Science > AI Systems > Agents"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(payload["data"]["entries"]), 1)
        self.assertEqual(payload["data"]["entries"][0]["source"], "Notes/DSPy.md")
        self.assertEqual(payload["data"]["subcategories"], [])

    def test_list_recursive_flattens_all_entries(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json(
            "list", "Computer Science", "--recursive"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(payload["data"]["entries"]), 1)
        self.assertEqual(payload["data"]["subcategories"], [])

    def test_list_with_include_body(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json(
            "list", "Computer Science > AI Systems > Agents", "--include-body"
        )

        self.assertEqual(rc, 0)
        self.assertIn("body", payload["data"]["entries"][0])
        self.assertIn("Prompt optimization", payload["data"]["entries"][0]["body"])

    def test_list_nonmatching_leaf(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json(
            "list", "Computer Science > AI Systems > Memory"
        )
        self.assertEqual(rc, 0)
        self.assertEqual(len(payload["data"]["entries"]), 0)
        self.assertEqual(payload["data"]["subcategories"], [])

    def test_search_with_tags(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json("search", "--tag", "#agents")

        self.assertEqual(rc, 0)
        self.assertEqual(len(payload["data"]["results"]), 1)

    def test_index_reports_unindexed_and_removed_notes(self) -> None:
        note = self.write_note("Notes/State.md", "# State\n\nMemory state.")
        rc, _ = self.run_cli_json(
            "add",
            "--json",
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

    def test_index_does_not_rewrite_unchanged_generated_pages(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()
        time.sleep(1.1)

        first_rc, first_payload = self.run_cli_json("index")
        time.sleep(1.1)
        second_rc, second_payload = self.run_cli_json("index")

        self.assertEqual(first_rc, 0)
        self.assertEqual(second_rc, 0)
        self.assertEqual(first_payload["data"]["changed_files"], ["_WIKI/index.md"])
        self.assertEqual(second_payload["data"]["changed_files"], [])

    def test_add_and_index_refresh_homepage(self) -> None:
        self.write_note("Notes/DSPy.md", "# DSPy\n\nPrompt optimization for agents.")

        rc, payload = self.run_cli_json(
            "add",
            "--json",
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
        self.assertIn("HOME.md", payload["data"]["changed_files"])
        homepage = (self.notebook / "HOME.md").read_text(encoding="utf-8")
        self.assertIn("## Category Tree", homepage)
        self.assertIn("[layer1: Computer Science]", homepage)
        self.assertIn("[layer3: Agents]", homepage)

        original = homepage
        time.sleep(1.1)
        rc, payload = self.run_cli_json("index")
        self.assertEqual(rc, 0)
        self.assertEqual(payload["data"]["changed_files"], ["_WIKI/index.md"])
        self.assertEqual((self.notebook / "HOME.md").read_text(encoding="utf-8"), original)

    def test_lint_is_read_only_and_reports_unindexed_notes(self) -> None:
        self.write_note("Notes/Loose.md", "# Loose\n\nUnindexed.")

        rc, payload = self.run_cli_json("lint")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["issues"][0]["code"], "unindexed")

    def test_lint_reports_empty_leaf_categories(self) -> None:
        rc, payload = self.run_cli_json("lint", "--filter", "empty_category")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(
            [issue["code"] for issue in payload["issues"]],
            ["empty_category", "empty_category"],
        )

    def test_tree_returns_deterministic_structure(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, payload = self.run_cli_json("tree")

        self.assertEqual(rc, 0)
        self.assertEqual(payload["command"], "tree")
        roots = payload["data"]["roots"]
        self.assertEqual(roots[0]["name"], "Computer Science")
        ai_systems = roots[0]["children"][0]
        self.assertEqual(ai_systems["name"], "AI Systems")
        agents = ai_systems["children"][0]
        self.assertEqual(agents["name"], "Agents")
        self.assertTrue(agents["leaf"])
        self.assertEqual(agents["note_count"], 1)
        self.assertEqual(agents["notes"][0]["source"], "Notes/DSPy.md")

    def test_tree_and_category_pages_follow_current_note_frontmatter_when_log_is_stale(self) -> None:
        self.generated.joinpath("index.md").write_text(
            "# Wiki Index\n\n"
            "## Category Tree\n\n"
            "- layer1: [Computer Science](categories/computer-science/index.md)\n"
            "  - layer2: [AI Systems](categories/computer-science/ai-systems/index.md)\n"
            "    - layer3: [Agents](categories/computer-science/ai-systems/agents/index.md)\n"
            "  - layer2: [Operating System](categories/computer-science/operating-system/index.md)\n"
            "\n---\n\n"
            "## Skipped System Notes\n- None\n",
            encoding="utf-8",
        )
        stale_note = self.write_note(
            "Notes/Homelab.md",
            "---\ncategory: \"Computer Science > Operating System\"\nsummary: \"Homelab setup ideas.\"\ntags:\n- homelab\n---\n# Homelab\n\nMachines.\n",
        )
        self.generated.joinpath("log.md").write_text(
            "# Wiki Log\n\n"
            + "- "
            + json.dumps(
                {
                    "action": "add",
                    "title": "Homelab",
                    "summary": "Wrong old category.",
                    "category": "Computer Science > AI Systems > Agents",
                    "tags": ["#homelab"],
                    "search_terms": [],
                    "source": "Notes/Homelab.md",
                    "source_mtime_ns": stale_note.stat().st_mtime_ns - 1,
                    "timestamp": "2026-05-01T00:00:00Z",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        rc, tree_payload = self.run_cli_json("tree")
        self.assertEqual(rc, 0)
        roots = tree_payload["data"]["roots"]
        computer_science = roots[0]
        operating_system = next(
            child for child in computer_science["children"] if child["name"] == "Operating System"
        )
        ai_systems = next(
            child for child in computer_science["children"] if child["name"] == "AI Systems"
        )
        self.assertEqual(operating_system["note_count"], 1)
        self.assertEqual(operating_system["notes"][0]["source"], "Notes/Homelab.md")
        self.assertEqual(ai_systems["note_count"], 0)

        rc, index_payload = self.run_cli_json("index")
        self.assertEqual(rc, 0)
        self.assertIn("Notes/Homelab.md", index_payload["data"]["modified_notes"])

        category_page = (
            self.generated
            / "categories"
            / "computer-science"
            / "operating-system"
            / "index.md"
        )
        category_text = category_page.read_text(encoding="utf-8")
        self.assertIn("[[Notes/Homelab.md]] - Homelab setup ideas.", category_text)
        self.assertNotIn("Wrong old category.", category_text)

    def test_removed_commands_fail(self) -> None:
        """Removed commands (show, status, synthesize, reconcile) should not parse."""
        for cmd in ("show", "status", "synthesize", "reconcile"):
            with self.assertRaises(SystemExit):
                cli.main(
                    ["--config", str(self.config_path), "--format", "json", cmd]
                )

    def test_format_json_returns_stable_envelope(self) -> None:
        """--format json always produces the CommandResult envelope."""
        rc, payload = self.run_cli_json("lint")

        self.assertIn("ok", payload)
        self.assertIn("command", payload)
        self.assertIn("data", payload)
        self.assertIn("issues", payload)
        self.assertIn("fixes", payload)

    def test_wikicli_method_surface_exists(self) -> None:
        app = WikiCli(WikiConfig(self.notebook, self.generated, (self.notebook,)))

        self.assertEqual(app.lint().command, "lint")
        self.assertEqual(app.index().command, "index")
        self.assertEqual(app.list().command, "list")
        self.assertEqual(
            app.search(query="test", limit=5).command, "search"
        )
        self.assertEqual(app.tree().command, "tree")

    def test_default_text_output_for_list(self) -> None:
        self.test_add_indexes_note_and_renders_generated_files()

        rc, output = self.run_cli_text("list")

        self.assertEqual(rc, 0)
        # Root list shows subcategory names with trailing slash
        self.assertIn("Computer Science/", output)


if __name__ == "__main__":
    unittest.main()
