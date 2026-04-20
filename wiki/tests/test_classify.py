import unittest
import tempfile
from pathlib import Path

from wikicli.classify import extract_packet_from_note, normalize_packet
from wikicli.config import WikiConfig


class TestClassifyUtilities(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WikiConfig(
            notebook_root=Path("/tmp"),
            generated_root=Path("/tmp/_WIKI"),
            include_roots=[],
            exclude_globs=[],
        )

    def test_normalize_packet_enforces_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            normalize_packet({"title": "No Source"})

        with self.assertRaises(ValueError):
            normalize_packet(
                {
                    "source": "Note.md",
                    "summary": "Missing title.",
                    "category": "Valid > Category",
                    "tags": [],
                }
            )

        with self.assertRaises(ValueError):
            normalize_packet(
                {
                    "source": "Note.md",
                    "title": "Missing Summary",
                    "category": "Valid > Category",
                    "tags": [],
                }
            )

        with self.assertRaises(ValueError):
            normalize_packet(
                {
                    "source": "Note.md",
                    "title": "No Tags",
                    "summary": "Missing explicit tags field.",
                    "category": "Valid > Category",
                }
            )

        with self.assertRaises(ValueError):
            normalize_packet(
                {
                    "source": "Note.md",
                    "title": "Too Short",
                    "summary": "Category must be explicit and deep enough.",
                    "category": "Too Short",
                    "tags": [],
                }
            )

        packet = normalize_packet(
            {
                "source": "Note.md",
                "title": "Note",
                "summary": "Explicit summary.",
                "category": "Valid > Category",
                "tags": [" #tag1 ", "tag2"],
                "search_terms": ["alpha", " Alpha ", "beta"],
            }
        )
        self.assertEqual(packet["source"], "Note.md")
        self.assertEqual(packet["title"], "Note")
        self.assertEqual(packet["summary"], "Explicit summary.")
        self.assertEqual(packet["category"], "Valid > Category")
        self.assertEqual(packet["tags"], ["#tag1", "tag2"])
        self.assertEqual(packet["search_terms"], ["alpha", "beta"])

    def test_normalize_packet_requires_category_field(self) -> None:
        with self.assertRaises(ValueError):
            normalize_packet(
                {
                    "source": "Note.md",
                    "title": "Note",
                    "summary": "Explicit summary.",
                    "category_path": "Valid > Category",
                    "tags": ["tag1"],
                }
            )

    def test_extract_packet_from_note_uses_only_explicit_frontmatter(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.config.notebook_root = root
        note_path = root / "Explicit.md"
        note_path.write_text(
            "---\n"
            "title: Explicit Note\n"
            "summary: Explicit note summary.\n"
            "category: Valid > Category\n"
            "tags:\n"
            "- tag1\n"
            "---\n"
            "# Body Title\n\nBody text that should not be summarized.\n",
            encoding="utf-8",
        )
        self.addCleanup(note_path.unlink)

        packet = extract_packet_from_note(note_path, self.config)
        self.assertEqual(
            packet,
            {
                "title": "Explicit Note",
                "summary": "Explicit note summary.",
                "category": "Valid > Category",
                "tags": ["#tag1"],
                "search_terms": [],
                "source": "Explicit.md",
            },
        )

    def test_extract_packet_from_note_rejects_missing_frontmatter_summary(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.config.notebook_root = root
        note_path = root / "Missing.md"
        note_path.write_text(
            "---\n"
            "title: Missing Summary\n"
            "category: Valid > Category\n"
            "tags:\n"
            "- tag1\n"
            "---\n"
            "# Body Title\n\nBody text that should not be summarized.\n",
            encoding="utf-8",
        )
        self.addCleanup(note_path.unlink)

        with self.assertRaises(ValueError):
            extract_packet_from_note(note_path, self.config)
