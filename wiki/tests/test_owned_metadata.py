from __future__ import annotations

import unittest

from wikicli.notebook import NoteMetadata


class OwnedMetadataTests(unittest.TestCase):
    def test_scalar_updates_preserve_authored_bytes(self) -> None:
        original = (
            '---\n# authored metadata\n'
            'summary: |\n  Carefully written\n  multiline summary.\n'
            'wiki_note_count: 1  # hand-counted\n'
            "wiki_status: 'old' # keep this\n"
            'wiki_kind: "old"\n'
            'custom: {nested: [1, two]}\n'
            '---\n\n# Body\n\nTrailing spaces.  \n'
        )
        updated = NoteMetadata.update_generated_properties(original, {
            'wiki_note_count': 5, 'wiki_status': "it's ready", 'wiki_kind': 'category',
        })
        self.assertEqual(updated, original.replace('count: 1', 'count: 5')
                         .replace("'old'", "'it''s ready'")
                         .replace('"old"', '"category"'))

    def test_crlf_and_bom_preserved(self) -> None:
        original = '\ufeff---\r\nwiki_note_count: 1 # comment\r\n---\r\n\r\nBody'
        self.assertEqual(NoteMetadata.update_generated_properties(original, {'wiki_note_count': 2}),
                         original.replace('count: 1', 'count: 2'))
        updated = NoteMetadata.update_generated_properties(original, {'wiki_depth': 0})
        self.assertEqual(updated, original.replace('---\r\n', '---\r\nwiki_depth: 0\r\n', 1))

    def test_equal_values_are_byte_identical(self) -> None:
        original = '---\nwiki_note_count: 01 # unchanged\nwiki_status: "ready"\n---\nBody'
        self.assertEqual(NoteMetadata.update_generated_properties(original, {
            'wiki_note_count': 1, 'wiki_status': 'ready',
        }), original)

    def test_missing_properties_are_added_without_body_changes(self) -> None:
        original = '\ufeffBody\r\n'
        updated = NoteMetadata.update_generated_properties(original, {'wiki_note_count': 1})
        self.assertEqual(updated, '\ufeff---\r\nwiki_note_count: 1\r\n---\r\nBody\r\n')

    def test_unowned_keys_are_rejected(self) -> None:
        for key in ('title', 'summary', 'tags', 'category', 'created', 'wiki_unknown'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'not a generated'):
                NoteMetadata.update_generated_properties('Body', {key: 'new'})

    def test_unsafe_existing_metadata_is_rejected_before_any_edits(self) -> None:
        for raw in (
            'wiki_note_count: [1, 2]', 'wiki_status: {nested: yes}',
            'wiki_status:\n  nested: value', 'wiki_note_count: 1\nwiki_note_count: 2',
            'wiki_status: "unterminated', 'wiki_status: &status ready',
            'wiki_status: |\n  complex\n  scalar', 'wiki_status: !!str ready',
            'wiki_status: &status ready\nother: *status',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                NoteMetadata.update_generated_properties('---\n' + raw + '\n---\nBody', {'wiki_depth': 1})

    def test_replacement_must_be_finite_scalar(self) -> None:
        for value in ([], {}, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                NoteMetadata.update_generated_properties('---\nwiki_depth: 1\n---\nBody', {'wiki_depth': value})

    def test_empty_value_keeps_inline_comment(self) -> None:
        original = '---\nwiki_note_count: # fill this\n---\nBody'
        updated = NoteMetadata.update_generated_properties(original, {'wiki_note_count': 3})
        self.assertEqual(updated, original.replace('count:', 'count: 3'))

    def test_plain_strings_are_quoted_when_yaml_would_change_the_type(self) -> None:
        original = '---\nwiki_status: old # preserved\n---\nBody'
        for value in ('true', 'null', '1', 'line\nbreak', '# comment', 'a: b'):
            with self.subTest(value=value):
                updated = NoteMetadata.update_generated_properties(original, {'wiki_status': value})
                self.assertEqual(NoteMetadata.parse(updated).frontmatter['wiki_status'], value)
                self.assertIn(' # preserved\n', updated)

    def test_fingerprint_ignores_tracking_values_but_keeps_other_bytes(self) -> None:
        original = '---\nmodified: "yesterday" # date\nwiki_content_hash: "old"\nsummary: keep\n---\nBody'
        updated = NoteMetadata.update_generated_properties(original, {'modified': 'today', 'wiki_content_hash': 'new'})
        self.assertEqual(NoteMetadata.fingerprint_text(original), NoteMetadata.fingerprint_text(updated))
        self.assertNotEqual(NoteMetadata.fingerprint_text(original), NoteMetadata.fingerprint_text(original + '\n'))
        self.assertNotEqual(NoteMetadata.fingerprint_text(original), NoteMetadata.fingerprint_text(original.replace('keep', 'edited')))

    def test_fingerprint_normalizes_missing_tracking_fields(self) -> None:
        original = '---\nsummary: keep\n---\nBody'
        updated = NoteMetadata.update_generated_properties(original, {'modified': 'today', 'wiki_content_hash': 'hash'})
        self.assertEqual(NoteMetadata.fingerprint_text(original), NoteMetadata.fingerprint_text(updated))

    def test_fingerprint_ignores_tracking_scalar_type_and_quotes(self) -> None:
        original = "---\nmodified: 2025-01-01 # date\nwiki_content_hash: 'old'\n---\nBody"
        updated = NoteMetadata.update_generated_properties(original, {'modified': '2026-10-10', 'wiki_content_hash': 'new'})
        self.assertEqual(NoteMetadata.fingerprint_text(original), NoteMetadata.fingerprint_text(updated))

    def test_quoted_numeric_count_is_replaced_with_numeric_scalar(self) -> None:
        original = '---\nwiki_note_count: "1" # original string\n---\nBody'
        updated = NoteMetadata.update_generated_properties(original, {'wiki_note_count': 2})
        self.assertEqual(updated, original.replace('"1"', '2'))
        self.assertIs(type(NoteMetadata.parse(updated).frontmatter['wiki_note_count']), int)
