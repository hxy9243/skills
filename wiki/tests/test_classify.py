import unittest
from pathlib import Path

from wikicli.classify import normalize_packet, score_category_path
from wikicli.config import WikiConfig


class TestClassifyUtilities(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WikiConfig(
            notebook_root=Path("/tmp"),
            generated_root=Path("/tmp/_WIKI"),
            include_roots=[],
            exclude_globs=[],
        )

    def test_score_category_path_ranks_matches(self) -> None:
        score1, matched1, _ = score_category_path(
            ["Computer Science", "AI Systems"],
            title="AI Systems Overview",
            text="A review of modern AI systems and architectures.",
            source_relpath="Notes/AI.md",
            tags=["#ai"],
        )
        score2, matched2, _ = score_category_path(
            ["Biology", "Genetics"],
            title="AI Systems Overview",
            text="A review of modern AI systems and architectures.",
            source_relpath="Notes/AI.md",
            tags=["#ai"],
        )
        self.assertTrue(score1 > score2)
        self.assertTrue(matched1 > matched2)

    def test_normalize_packet_enforces_required_fields(self) -> None:
        with self.assertRaises(ValueError):
            normalize_packet({"title": "No Source"})

        with self.assertRaises(ValueError):
            normalize_packet({"source": "Note.md", "category_path": ["Too Short"]})

        packet = normalize_packet(
            {
                "source": "Note.md",
                "category_path": ["Valid", "Category"],
                "tags": [" #tag1 ", "tag2"],
            }
        )
        self.assertEqual(packet["source"], "Note.md")
        self.assertEqual(packet["title"], "Note")
        self.assertEqual(packet["category_path"], ["Valid", "Category"])
        self.assertEqual(packet["tags"], ["#tag1", "tag2"])
