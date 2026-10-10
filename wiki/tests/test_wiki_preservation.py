from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from wikicli.app import WikiCli
from wikicli.category import CategoryPath, category_page_path
from wikicli.config import WikiConfig
from wikicli.notebook import Notebook, NoteMetadata, NewNote
from wikicli.wiki import WikiIndex, IssueType


class WikiPreservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = WikiConfig.default(self.root)
        self.wiki = WikiIndex(self.config, Notebook(self.config))
        self.category = CategoryPath.parse('Engineering > Dev Environment')
        self.wiki.add_category(self.category)
        self.page = category_page_path(self.config.categories_dir, self.category)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def add(self, source='note.md', summary='Packet summary', tags=('#packet',)):
        return self.wiki.add_note(NewNote('Note', summary, self.category, tags, (), source))

    def test_authored_yaml_body_extra_sections_preserved_and_idempotent(self):
        self.page.parent.mkdir(parents=True, exist_ok=True)
        text = '---\nsummary: |\n  Uses "quoted" wording.\n  More context.\ncustom: [one, two] # retain comment\nmodified: old\n---\n# Custom title\n\n## Synthesis\n\nAuthored prose.\n\n## Details\n\nMore authored prose.\n'
        self.page.write_text(text)
        (self.root/'note.md').write_text('# Source\nBody\n')
        self.add()
        actual = self.page.read_text()
        self.assertIn(text[text.index('summary:'):], actual)
        self.assertIn('[[note.md]]', actual)
        before = self.snapshot()
        self.assertEqual(self.wiki.index()['changed_files'], [])
        self.assertEqual(before, self.snapshot())

    def test_orphan_page_survives_and_is_reported(self):
        orphan = self.config.categories_dir/'personal.md'
        orphan.write_text('# Personal\nOriginal content\n')
        result = self.wiki.index()
        self.assertEqual(orphan.read_text(), '# Personal\nOriginal content\n')
        self.assertIn('_WIKI/categories/personal.md', result['orphan_pages'])
        self.assertTrue(any(i.code == IssueType.ORPHAN_PAGE for i in self.wiki.lint()))

    def test_source_category_conflict_has_no_writes(self):
        (self.root/'note.md').write_text('---\ncategory: Different\n---\n# Source\n')
        before=self.snapshot()
        result=WikiCli(self.config).add(json.dumps({'title':'N','summary':'S','category':self.category.display(),'source':'note.md'}))
        self.assertFalse(result.ok)
        self.assertEqual(before,self.snapshot())

    def test_malformed_other_source_blocks_add_before_any_writes(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        (self.root/'note.md').write_text('---\nbroken: [\n---\n')
        (self.root/'next.md').write_text('# Next\n')
        before=self.snapshot()
        with self.assertRaises(ValueError): self.add('next.md')
        self.assertEqual(before,self.snapshot())

    def test_directory_at_category_page_blocks_add_before_any_writes(self):
        self.page.mkdir(parents=True)
        (self.root/'note.md').write_text('# Source\n')
        before=self.snapshot()
        with self.assertRaises(ValueError): self.add()
        self.assertEqual(before,self.snapshot())

    def test_add_category_collision_and_empty_slug_fail_without_writes(self):
        before=self.snapshot()
        for category in ('Engineering > Dev Environment!', 'Engineering > !!!'):
            with self.assertRaises(ValueError): self.wiki.add_category(category)
            self.assertEqual(before,self.snapshot())

    def test_tree_annotations_and_multiple_roots_are_retained(self):
        text='# My index\n\n## Category Tree\n\n- layer1: Alpha\n  - layer2: Leaf\nManual annotation\n- layer1: Beta\n\n---\n\n## Personal notes\nKeep this.\n'
        self.config.index_path.write_text(text)
        self.wiki.add_category('Alpha > New Leaf')
        after=self.config.index_path.read_text()
        self.assertIn('Manual annotation\n- layer1: Beta',after)
        self.assertTrue(after.endswith('## Personal notes\nKeep this.\n'))
        self.assertTrue(self.wiki.read_tree().contains(CategoryPath.parse('Alpha > New Leaf')))
        self.assertFalse(self.wiki.read_tree().contains(CategoryPath.parse('Beta > New Leaf')))

    def test_repeat_add_is_noop_and_catalog_metadata_accumulates(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        before=self.snapshot()
        self.assertEqual(self.add()['changed_files'],[])
        self.assertEqual(before,self.snapshot())
        self.add(summary='Additional information',tags=('#new',))
        entry=self.wiki.catalog()['note.md']
        self.assertEqual(entry.summary,'Packet summary\n\nAdditional information')
        self.assertEqual(entry.tags,('#packet','#new'))
        (self.root/'note.md').write_text((self.root/'note.md').read_text()+'More body\n')
        self.wiki.index()
        entry=self.wiki.catalog()['note.md']
        self.assertEqual(entry.tags,('#packet','#new'))
        self.assertEqual(entry.summary,'Packet summary\n\nAdditional information')

    def test_legacy_placeholder_retained_new_pages_do_not_invent_summary(self):
        self.wiki.index()
        metadata=NoteMetadata.read(self.page)
        self.assertEqual(metadata.frontmatter['summary'],'')
        old='Dev Environment is currently thin and should either be populated with real notes or folded back into a stronger neighboring category.'
        self.page.write_text(self.page.read_text()+'\n'+old+'\n')
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        self.assertIn(old,self.page.read_text())

    def test_index_preserves_crlf_without_normalizing_existing_text(self):
        original=b'# Custom index\r\n\r\n## Category Tree\r\n\r\n- layer1: Engineering\r\n  - layer2: Dev Environment\r\n\r\n---\r\n\r\n## Manual\r\nKeep me.'
        self.config.index_path.write_bytes(original)
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        self.assertTrue(self.config.index_path.read_bytes().startswith(original))
        after=self.config.index_path.read_bytes()
        self.wiki.index()
        self.assertEqual(after,self.config.index_path.read_bytes())

    def test_excluded_catalog_source_still_preflighted(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        (self.root/'note.md').write_text('---\nbroken: [\n---\n')
        visible=self.root/'Visible';visible.mkdir()
        (visible/'next.md').write_text('# Next\n')
        config=WikiConfig(self.root,self.config.generated_root,(visible,))
        wiki=WikiIndex(config,Notebook(config))
        before=self.snapshot()
        with self.assertRaises(ValueError):
            wiki.add_note(NewNote('Next','Summary',self.category,(),(),'Visible/next.md'))
        self.assertEqual(before,self.snapshot())

    def test_malformed_category_page_index_has_no_writes(self):
        self.wiki.index()
        self.page.write_text('---\nsummary: [\n---\n')
        before=self.snapshot()
        result=WikiCli(self.config).index()
        self.assertFalse(result.ok)
        self.assertEqual(before,self.snapshot())

    def test_missing_tree_heading_keeps_existing_index(self):
        text='# Existing index\nPersonal content.\n'
        self.config.index_path.write_text(text)
        self.wiki.add_category('New > Leaf')
        self.assertTrue(self.config.index_path.read_text().startswith(text))
        self.assertTrue(self.wiki.read_tree().contains(CategoryPath.parse('New > Leaf')))

    def test_excluded_note_remains_cataloged(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        visible=self.root/'Visible';visible.mkdir()
        config=WikiConfig(self.root,self.config.generated_root,(visible,))
        wiki=WikiIndex(config,Notebook(config))
        self.assertEqual(wiki.index()['removed_notes'],[])
        self.assertIn('note.md',wiki.catalog())

    def test_multiline_summary_repeat_does_not_duplicate(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        summary='First paragraph\n\nSecond paragraph'
        self.add(summary=summary)
        before=self.snapshot()
        self.assertEqual(self.add(summary=summary)['changed_files'],[])
        self.assertEqual(before,self.snapshot())

    def test_log_without_terminal_newline_keeps_previous_event(self):
        (self.root/'note.md').write_text('# Source\n')
        self.add()
        prior=self.config.log_path.read_bytes().rstrip(b'\n')
        self.config.log_path.write_bytes(prior)
        (self.root/'next.md').write_text('# Next\n')
        self.add('next.md')
        self.assertTrue(self.config.log_path.read_bytes().startswith(prior))
        self.assertEqual(set(self.wiki.catalog()),{'note.md','next.md'})

    def test_homepage_untouched(self):
        home=self.root/'HOME.md';home.write_text('# Home\nAuthored\n')
        self.wiki.index()
        self.assertEqual(home.read_text(),'# Home\nAuthored\n')

if __name__ == '__main__': unittest.main()
