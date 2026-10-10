from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from wikicli.config import WikiConfig
from wikicli.notebook import Notebook, NoteMetadata


class MetadataPreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'note.md'
        self.notebook = Notebook(WikiConfig.default(self.root))

    def put(self, text: str) -> None:
        self.path.write_bytes(text.encode('utf-8'))

    def test_complex_yaml_is_preserved_byte_for_byte(self) -> None:
        text = (
            '---\n# Keep this comment\n'
            'title: "My: title" # inline comment\n'
            'description: |\n  first line\n  second line\n'
            'folded: >-\n  many\n  words\n'
            'nested:\n  enabled: true\n  count: 3\n  ratio: 1.5\n  empty: null\n'
            'tags: [one, "two words", "#three"]\n'
            "quoted: 'it''s safe'\n"
            '---\n\n# Body\n\nKeep trailing spaces.  \n'
        )
        self.put(text)
        before = NoteMetadata.parse(text)
        self.assertEqual(before.frontmatter['nested'], {'enabled': True, 'count': 3, 'ratio': 1.5, 'empty': None})
        self.assertEqual(before.frontmatter['description'], 'first line\nsecond line\n')
        self.assertEqual(before.frontmatter['folded'], 'many words')
        self.assertEqual(before.frontmatter['quoted'], "it's safe")
        self.assertEqual(before.tags(), ('#one', '#three', '#two words'))
        self.assertTrue(NoteMetadata.write_category(self.path, 'A > B'))
        self.assertEqual(self.path.read_bytes(), text.replace('---\n', '---\ncategory: "A > B"\n', 1).encode())
        after = NoteMetadata.read(self.path)
        self.assertEqual(after.frontmatter, {**before.frontmatter, 'category': 'A > B'})
        self.assertEqual(after.body, before.body)

    def test_crlf_bom_and_missing_final_newline_preserved(self) -> None:
        for text in ('---\r\ntitle: Hello\r\n---\r\n\r\nBody', '\ufeff---\r\ntitle: Hello\r\n---', '\ufeff# Body\r\n\r\n'):
            with self.subTest(text=text):
                self.put(text)
                self.assertTrue(NoteMetadata.write_category(self.path, 'Test'))
                result = self.path.read_bytes().decode()
                if 'title:' in text:
                    self.assertEqual(result, text.replace('---\r\n', '---\r\ncategory: "Test"\r\n', 1))
                else:
                    self.assertEqual(result, '\ufeff---\r\ncategory: "Test"\r\n---\r\n' + text[1:])

    def test_idempotence_does_not_touch_file(self) -> None:
        original = "---\ncategory: 'A > B' # hand-maintained\n---\nBody\n"
        self.put(original)
        before = self.path.stat().st_mtime_ns
        self.assertFalse(NoteMetadata.write_category(self.path, 'A > B'))
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        self.assertEqual(self.path.read_bytes(), original.encode())

    def test_conflict_does_not_write(self) -> None:
        for value in ('Other', '', None, [], False):
            with self.subTest(value=value):
                import json
                original = '---\ncategory: ' + json.dumps(value) + '\n---\nBody\n'
                self.put(original)
                with self.assertRaisesRegex(ValueError, 'overwrite'):
                    NoteMetadata.write_category(self.path, 'New')
                self.assertEqual(self.path.read_bytes(), original.encode())

    def test_unsafe_yaml_fails_closed(self) -> None:
        fixtures = [
            'title: "unterminated',
            'category: first\ncategory: second',
            'nested: {key: first, key: second}',
            'value: !!python/object/apply:os.system [echo bad]',
            'base: &base {key: value}\ncopy: *base',
            '- list\n- instead of mapping',
            '1: nonstring key',
            'nested:\n  <<: {key: value}',
        ]
        for raw in fixtures:
            with self.subTest(raw=raw):
                original = '---\n' + raw + '\n---\nBody'
                self.put(original)
                with self.assertRaises(ValueError):
                    NoteMetadata.write_category(self.path, 'New')
                self.assertEqual(self.path.read_bytes(), original.encode())
        original = '---\ntitle: no closing delimiter\nBody'
        self.put(original)
        with self.assertRaises(ValueError):
            NoteMetadata.write_category(self.path, 'New')
        self.assertEqual(self.path.read_bytes(), original.encode())

    def test_flow_root_is_rejected_without_writing(self) -> None:
        original = '---\n{title: Title, tags: [one, two]}\n---\nBody'
        self.put(original)
        with self.assertRaises(ValueError):
            NoteMetadata.write_category(self.path, 'New')
        self.assertEqual(self.path.read_bytes(), original.encode())

    def test_update_property_is_add_only_and_type_sensitive(self) -> None:
        original = '---\nflag: true\ncount: 1\n---\nBody\n'
        self.put(original)
        self.assertFalse(self.notebook.update_property('note.md', 'flag', True))
        for key, value in [('flag', 1), ('count', 1.0), ('flag', False)]:
            with self.assertRaises(ValueError):
                self.notebook.update_property('note.md', key, value)
            self.assertEqual(self.path.read_bytes(), original.encode())
        self.assertTrue(self.notebook.update_property('note.md', 'extra', {'values': [True, None, 'test']}))
        self.assertEqual(NoteMetadata.read(self.path).frontmatter['extra'], {'values': [True, None, 'test']})

    def test_write_is_create_only(self) -> None:
        self.assertTrue(self.notebook.write('note.md', 'Original\r\n'))
        self.assertFalse(self.notebook.write('note.md', 'Original\r\n'))
        with self.assertRaises(ValueError):
            self.notebook.write('note.md', 'Replacement\n')
        self.assertEqual(self.path.read_bytes(), b'Original\r\n')

    def test_atomic_update_preserves_permissions(self) -> None:
        self.put("Body\r\n")
        self.path.chmod(0o640)
        self.assertTrue(NoteMetadata.write_category(self.path, "New"))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(list(self.root.glob(".note.md.*")), [])

    def test_concurrent_edit_is_not_replaced(self) -> None:
        import wikicli.notebook as notebook_module

        self.put("Original")
        real_read = notebook_module._read_text
        calls = 0

        def read_with_concurrent_edit(path: Path) -> str:
            nonlocal calls
            calls += 1
            if calls == 2:
                self.put("User's new edit")
            return real_read(path)

        with patch.object(notebook_module, "_read_text", side_effect=read_with_concurrent_edit):
            with self.assertRaisesRegex(ValueError, "changed while preparing"):
                NoteMetadata.write_category(self.path, "New")
        self.assertEqual(self.path.read_bytes(), b"User's new edit")
        self.assertEqual(list(self.root.glob(".note.md.*")), [])

    def test_source_and_parent_symlinks_rejected(self) -> None:
        target = self.root / 'target.md'
        target.write_text('Untouched')
        self.path.symlink_to(target)
        for action in [lambda: NoteMetadata.write_category(self.path, 'New'), lambda: self.notebook.update_property('note.md', 'key', 'value'), lambda: self.notebook.write('note.md', 'New')]:
            with self.assertRaisesRegex(ValueError, 'symlink'):
                action()
        actual = self.root / 'actual'
        actual.mkdir()
        (self.root / 'linked').symlink_to(actual, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.notebook.write('linked/new.md', 'New')
        self.assertFalse((actual / 'new.md').exists())
        self.assertEqual(target.read_text(), 'Untouched')


if __name__ == '__main__':
    unittest.main()
