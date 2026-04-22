from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from wikicli.config import WikiConfig
from wikicli.notebook import (
    NoteMetadata,
    discover_notes,
    load_note,
    normalize_source,
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
        self.assertEqual(normalize_source("Notes/A.md"), "Notes/A.md")
        with self.assertRaises(ValueError):
            normalize_source("/tmp/A.md")
        with self.assertRaises(ValueError):
            normalize_source("../A.md")

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

            notes = discover_notes(config)

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

            note = load_note(config, "A.md")

            self.assertEqual(note.title, "Heading Title")
            self.assertEqual(note.tags, ())


if __name__ == "__main__":
    unittest.main()
