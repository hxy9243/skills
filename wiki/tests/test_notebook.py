from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from wikicli.config import WikiConfig
from wikicli.notebook import (
    Note,
    Notebook,
    NoteMetadata,
)


class NoteMetadataTests(unittest.TestCase):
    def test_parse_normalizes_title_tags_and_renders_frontmatter(self) -> None:
        metadata = NoteMetadata.parse(
            "---\n"
            "title: '  DSPy Notes  '\n"
            "tags:\n"
            "- ai\n"
            "- '#agent'\n"
            "---\n"
            "# Fallback\n\nBody text.\n"
        )

        self.assertEqual(metadata.title(Path("fallback.md")), "DSPy Notes")
        self.assertEqual(metadata.tags(), ("#agent", "#ai"))
        self.assertIn('title: "  DSPy Notes  "', metadata.render())
        self.assertIn('- "ai"', metadata.render())

    def test_write_category_creates_or_updates_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Note.md"
            path.write_text("# Note\n\nBody.\n", encoding="utf-8")

            changed = NoteMetadata.write_category(path, "A > B > C")
            unchanged = NoteMetadata.write_category(path, "A > B > C")

            self.assertTrue(changed)
            self.assertFalse(unchanged)
            self.assertIn('category: "A > B > C"', path.read_text(encoding="utf-8"))

    def test_normalize_source_rejects_absolute_and_parent_paths(self) -> None:
        self.assertEqual(Notebook.normalize_source("Notes/A.md"), "Notes/A.md")
        with self.assertRaises(ValueError):
            Notebook.normalize_source("/tmp/A.md")
        with self.assertRaises(ValueError):
            Notebook.normalize_source("../A.md")

    def test_discover_notes_excludes_generated_and_configured_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            notebook = root / "notebook"
            generated = notebook / "_WIKI"
            (notebook / "Notes").mkdir(parents=True)
            (notebook / "Templates").mkdir()
            generated.mkdir()
            (notebook / "Notes" / "A.md").write_text("# A\n", encoding="utf-8")
            (notebook / "Templates" / "T.md").write_text("# T\n", encoding="utf-8")
            (generated / "index.md").write_text("# Wiki\n", encoding="utf-8")
            config = WikiConfig(
                notebook_root=notebook,
                generated_root=generated,
                include_roots=(notebook,),
                exclude_globs=("Templates/**",),
            )

            nb = Notebook(config)
            notes = nb.discover()

            self.assertEqual([note.source for note in notes], ["Notes/A.md"])

    def test_load_note_uses_heading_fallback_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp)
            generated = notebook / "_WIKI"
            generated.mkdir()
            (notebook / "A.md").write_text(
                "# Heading Title\n\nBody.\n", encoding="utf-8"
            )
            config = WikiConfig(notebook, generated, (notebook,))

            nb = Notebook(config)
            note = nb.read("A.md")

            self.assertEqual(note.title, "Heading Title")
            self.assertEqual(note.tags, ())

    def test_note_has_created_and_last_modified_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp)
            generated = notebook / "_WIKI"
            generated.mkdir()
            (notebook / "B.md").write_text("# B\n\nBody.\n", encoding="utf-8")
            config = WikiConfig(notebook, generated, (notebook,))

            nb = Notebook(config)
            note = nb.read("B.md")

            self.assertIsNotNone(note.created)
            self.assertIsNotNone(note.last_modified)

    def test_parse_new_note_validates_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp)
            generated = notebook / "_WIKI"
            generated.mkdir()
            config = WikiConfig(notebook, generated, (notebook,))
            nb = Notebook(config)

            # Invalid JSON
            note, issues = nb.parse_new_note("not json")
            self.assertIsNone(note)
            self.assertEqual(issues[0].code, "packet_json_invalid")

            # List instead of object
            note, issues = nb.parse_new_note("[]")
            self.assertIsNone(note)
            self.assertEqual(issues[0].code, "packet_not_object")

            # Missing required fields
            note, issues = nb.parse_new_note('{"title":""}')
            self.assertIsNone(note)
            self.assertTrue(any(i.code == "packet_field_invalid" for i in issues))

    def test_parse_new_note_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp)
            generated = notebook / "_WIKI"
            generated.mkdir()
            config = WikiConfig(notebook, generated, (notebook,))
            nb = Notebook(config)

            note, issues = nb.parse_new_note(
                '{"title":"DSPy","summary":"Prompt opt","category":"CS > AI",'
                '"tags":["#ai"],"source":"Notes/DSPy.md"}'
            )
            self.assertIsNotNone(note)
            self.assertEqual(issues, [])
            self.assertEqual(note.title, "DSPy")
            self.assertEqual(note.category.display(), "CS > AI")

    def test_notebook_update_property(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            notebook = Path(tmp)
            generated = notebook / "_WIKI"
            generated.mkdir()
            (notebook / "C.md").write_text("# C\n\nBody.\n", encoding="utf-8")
            config = WikiConfig(notebook, generated, (notebook,))
            nb = Notebook(config)

            changed = nb.update_property("C.md", "status", "reviewed")
            self.assertTrue(changed)
            unchanged = nb.update_property("C.md", "status", "reviewed")
            self.assertFalse(unchanged)
            content = (notebook / "C.md").read_text(encoding="utf-8")
            self.assertIn('"reviewed"', content)

    def test_config_autodiscovers_wiki_config_in_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki_dir = root / "_WIKI"
            wiki_dir.mkdir()
            config_data = {
                "notebook_root": str(root),
                "generated_root": str(wiki_dir),
                "include_roots": ["."],
            }
            (wiki_dir / "config.json").write_text(
                json.dumps(config_data), encoding="utf-8"
            )

            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                config = WikiConfig.load()  # no config_path
            finally:
                os.chdir(old_cwd)

            self.assertEqual(config.notebook_root, root.resolve())
            self.assertEqual(config.generated_root, wiki_dir.resolve())

    def test_config_falls_back_to_default_without_wiki_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_cwd = os.getcwd()
            try:
                os.chdir(root)
                config = WikiConfig.load()  # no config_path, no _WIKI/
            finally:
                os.chdir(old_cwd)

            self.assertEqual(config.notebook_root, root.resolve())
            self.assertEqual(config.generated_root, (root / "_WIKI").resolve())


if __name__ == "__main__":
    unittest.main()
