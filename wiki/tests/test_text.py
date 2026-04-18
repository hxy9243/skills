import unittest

from wikicli.text import safe_title, slugify, split_sentences, tokenize


class TestTextUtilities(unittest.TestCase):
    def test_slugify_handles_special_characters(self) -> None:
        self.assertEqual(slugify("Hello World!"), "hello-world")
        self.assertEqual(slugify("  Lots   of    Spaces  "), "lots-of-spaces")
        self.assertEqual(slugify("Layer 1: Artificial Intelligence"), "layer-1-artificial-intelligence")
        self.assertEqual(slugify("!@#$$%^&*()"), "untitled")

    def test_safe_title_collapses_whitespace(self) -> None:
        self.assertEqual(safe_title("  A    title   with \n spaces  "), "A title with spaces")
        self.assertEqual(safe_title("   "), "Untitled")

    def test_tokenize_extracts_alphanumeric_words(self) -> None:
        tokens = tokenize("This is a test-case for 100% accurate tokenization.")
        self.assertEqual(tokens, ["this", "is", "test-case", "for", "accurate", "tokenization"])

    def test_split_sentences_respects_punctuation(self) -> None:
        text = "This is the first sentence. And this is the second one! Is this the third sentence? Yes."
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "This is the first sentence.")
        self.assertEqual(sentences[1], "And this is the second one!")
        self.assertEqual(sentences[2], "Is this the third sentence?")
        # 'Yes.' is too short (< 25 chars) and gets filtered out.
