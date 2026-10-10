from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from wikicli.app import WikiCli
from wikicli.category import CategoryPath,category_page_path
from wikicli.config import WikiConfig
from wikicli.notebook import Notebook,NewNote,NoteMetadata
from wikicli.wiki import WikiIndex,IssueType


class LiveMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.config=WikiConfig.default(self.root)
        self.w=WikiIndex(self.config,Notebook(self.config));self.cat=CategoryPath.parse('Root > Topic')
        self.w.add_category(self.cat)
        self.page=category_page_path(self.config.categories_dir,self.cat)
        self.parent=category_page_path(self.config.categories_dir,CategoryPath.parse('Root'))

    def add(self):
        (self.root/'note.md').write_text('# Note\nOriginal body\n')
        return self.w.add_note(NewNote('Note','Authored catalog summary',self.cat,(),(),'note.md'))

    def meta(self,path=None):return NoteMetadata.read(path or self.page).frontmatter
    def snapshot(self):return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def test_counts_status_modified_add_remove_and_noop(self):
        with patch('wikicli.wiki._utc_now',return_value='2026-01-01T00:00:00Z'):self.w.index()
        self.assertEqual((self.meta()['wiki_note_count'],self.meta()['wiki_status']),(0,'empty'))
        with patch('wikicli.wiki._utc_now',return_value='2026-01-02T00:00:00Z'):self.add()
        for path in (self.page,self.parent):
            self.assertEqual((self.meta(path)['wiki_note_count'],self.meta(path)['wiki_status']),(1,'active'))
            self.assertEqual(self.meta(path)['modified'],'2026-01-02T00:00:00Z')
        before=self.snapshot()
        with patch('wikicli.wiki._utc_now',return_value='2026-01-03T00:00:00Z'):self.w.index()
        self.assertEqual(before,self.snapshot())
        (self.root/'note.md').unlink()
        with patch('wikicli.wiki._utc_now',return_value='2026-01-04T00:00:00Z'):self.w.index()
        self.assertEqual((self.meta()['wiki_note_count'],self.meta()['wiki_status']),(0,'empty'))
        self.assertEqual(self.meta()['modified'],'2026-01-04T00:00:00Z')
        self.assertIn('[[note.md]]',self.page.read_text())

    def test_source_content_change_bumps_timestamp_but_touch_does_not(self):
        self.add();before=self.meta()['modified']
        note=self.root/'note.md';os.utime(note,ns=(note.stat().st_atime_ns,note.stat().st_mtime_ns+10000000))
        self.w.index();self.assertEqual(before,self.meta()['modified'])
        note.write_text(note.read_text()+'New sourced fact.\n')
        with patch('wikicli.wiki._utc_now',return_value='2026-02-01T00:00:00Z'):self.w.index()
        self.assertEqual(self.meta()['modified'],'2026-02-01T00:00:00Z')
        self.assertEqual(self.meta(self.parent)['modified'],'2026-02-01T00:00:00Z')
        before=self.page.read_bytes();self.w.index();self.assertEqual(before,self.page.read_bytes())

    def test_source_edit_with_restored_mtime_still_updates_modified(self):
        self.add();note=self.root/'note.md';stamp=note.stat()
        note.write_text(note.read_text()+'Changed despite restored mtime.\n')
        os.utime(note,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        with patch('wikicli.wiki._utc_now',return_value='2026-04-01T00:00:00Z'):self.w.index()
        self.assertEqual(self.meta()['modified'],'2026-04-01T00:00:00Z')
        before=self.page.read_bytes();self.w.index();self.assertEqual(before,self.page.read_bytes())

    def test_authored_page_change_bumps_modified_and_preserves_text(self):
        self.add()
        self.page.write_text(self.page.read_text()+'\n## Authored details\nKeep this wording.\n')
        with patch('wikicli.wiki._utc_now',return_value='2026-03-01T00:00:00Z'):self.w.index()
        self.assertEqual(self.meta()['modified'],'2026-03-01T00:00:00Z')
        self.assertIn('## Authored details\nKeep this wording.\n',self.page.read_text())
        before=self.snapshot();self.w.index();self.assertEqual(before,self.snapshot())

    def test_child_count_kind_tracks_tree_without_deleting_old_pages(self):
        self.w.index();self.w.add_category('Root > Topic > Child');self.w.index()
        self.assertEqual((self.meta()['wiki_child_count'],self.meta()['wiki_kind']),(1,'branch'))
        child=category_page_path(self.config.categories_dir,CategoryPath.parse('Root > Topic > Child'))
        self.config.index_path.write_text('# Index\n\n## Category Tree\n\n- layer1: Root\n  - layer2: Topic\n\n---\n')
        self.w.index();self.assertEqual((self.meta()['wiki_child_count'],self.meta()['wiki_kind']),(0,'leaf'))
        self.assertTrue(child.exists())

    def test_legacy_baseline_preserves_timestamp_when_nothing_else_changes(self):
        self.w.index()
        text=self.page.read_text();text='\n'.join(line for line in text.split('\n') if not line.startswith('wiki_content_hash:'))
        text=text.replace('modified: '+__import__('json').dumps(self.meta()['modified']),'modified: "2001-01-01T00:00:00Z"')
        self.page.write_text(text)
        self.w.index();self.assertEqual(self.meta()['modified'],'2001-01-01T00:00:00Z')
        before=self.page.read_bytes();self.w.index();self.assertEqual(before,self.page.read_bytes())

    def test_custom_status_and_authored_yaml_survive(self):
        self.w.index();text=self.page.read_text().replace('wiki_status: "empty"','wiki_status: "draft" # custom')
        text=text.replace('summary: ""','summary: |\n  Authored "summary".\n  Second line.\nstatus: review # personal\ncustom: [one, two]')
        self.page.write_text(text);self.add()
        actual=self.page.read_text()
        self.assertIn('wiki_status: "draft" # custom',actual)
        self.assertIn('summary: |\n  Authored "summary".\n  Second line.\nstatus: review # personal\ncustom: [one, two]',actual)
        self.assertEqual(self.meta()['wiki_note_count'],1)

    def test_lint_empty_summaries_is_readonly_and_filterable(self):
        self.w.index()
        for summary in (None,'null','""','"   "'):
            text=self.page.read_text();lines=[line for line in text.splitlines() if not line.startswith('summary:')]
            if summary is not None:lines.insert(1,'summary: '+summary)
            self.page.write_text('\n'.join(lines)+'\n')
            before=self.snapshot();result=WikiCli(self.config).lint(filters=('empty_summary',))
            self.assertTrue(result.ok);self.assertTrue(any(i.path=='_WIKI/categories/root/topic/index.md' for i in result.issues))
            self.assertTrue(all(i.severity=='warning' for i in result.issues));self.assertEqual(before,self.snapshot())
        self.page.write_text(self.page.read_text().replace('summary: "   "','summary: Meaningful authored summary'))
        self.assertFalse(any(i.path=='_WIKI/categories/root/topic/index.md' for i in self.w.lint() if i.code==IssueType.EMPTY_SUMMARY))

    def test_flow_mapping_rejected_before_add_mutations(self):
        import json
        self.w.index()
        metadata=self.meta();metadata.pop('wiki_content_hash')
        self.page.write_text('---\n'+json.dumps(metadata)+'\n---\n# Authored\n')
        (self.root/'note.md').write_text('# Source\n');before=self.snapshot()
        with self.assertRaises(ValueError):self.w.add_note(NewNote('Note','Summary',self.cat,(),(),'note.md'))
        self.assertEqual(before,self.snapshot())

    def test_invalid_owned_metadata_fails_before_source_or_log_changes(self):
        self.w.index();self.page.write_text(self.page.read_text().replace('wiki_note_count: 0','wiki_note_count: [bad]'))
        (self.root/'note.md').write_text('# Source\n');before=self.snapshot()
        with self.assertRaises(ValueError):self.w.add_note(NewNote('Note','Summary',self.cat,(),(),'note.md'))
        self.assertEqual(before,self.snapshot())

if __name__=='__main__':unittest.main()
