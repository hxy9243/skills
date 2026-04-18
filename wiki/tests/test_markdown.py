import unittest

from wikicli.markdown import clean_note_text, parse_frontmatter, upsert_frontmatter_property


class TestMarkdownUtilities(unittest.TestCase):
    def test_parse_frontmatter_extracts_yaml_and_body(self) -> None:
        text = "---\ntitle: Hello\ntags:\n- '#test'\n---\n\n# Body\nText."
        metadata, body = parse_frontmatter(text)
        self.assertEqual(metadata["title"], "Hello")
        self.assertEqual(metadata["tags"], ["#test"])
        self.assertEqual(body, "\n# Body\nText.")

    def test_parse_frontmatter_handles_no_frontmatter(self) -> None:
        text = "# Just body\nText."
        metadata, body = parse_frontmatter(text)
        self.assertEqual(metadata, {})
        self.assertEqual(body, text)

    def test_upsert_frontmatter_property_adds_or_updates_key(self) -> None:
        text = "---\ncategory: Old Category\n---\n# Body"
        updated = upsert_frontmatter_property(text, "category", "New Category")
        self.assertIn('category: "New Category"', updated)
        self.assertNotIn("Old Category", updated)

        text_no_frontmatter = "# Just body"
        updated2 = upsert_frontmatter_property(text_no_frontmatter, "category", "New Category")
        self.assertTrue(updated2.startswith("---\n"))
        self.assertIn('category: "New Category"', updated2)

    def test_clean_note_text_strips_markdown_formatting(self) -> None:
        text = "---\ntitle: Hello\n---\n# Heading\n\nSome **bold** and *italic* text.\n\n```python\nprint('code')\n```\n\n[Link](http://example.com)\n![Image](image.png)\nhttps://example.com"
        cleaned = clean_note_text(text)
        self.assertNotIn("Heading", cleaned)
        self.assertNotIn("```python", cleaned)
        self.assertNotIn("![Image]", cleaned)
        self.assertNotIn("\nhttps://example.com", cleaned)
        self.assertIn("Some **bold** and *italic* text.", cleaned)
        self.assertIn("[Link](http://example.com)", cleaned)
