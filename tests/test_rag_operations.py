import contextlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rag_operations import refresh, snapshot, changes, atomic, backup, exclusive
from rag_library import LibraryStore


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.course = self.root/'Fall 2025/Test/lectures'
        self.course.mkdir(parents=True)
        self.source = self.course/'one.txt'
        self.source.write_text('A precise source passage about gamma and option convexity.\n')

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, root):
        atomic(root/'.rag/search/CURRENT.json', {'generation':'fixture'})

    def run_refresh(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return refresh(self.root, builder=kwargs.pop('builder', self.build), **kwargs)

    def test_changed_deleted_and_unchanged_sources(self):
        first = self.run_refresh()
        self.assertEqual(first['cached'], 0)
        original = (self.root/'.rag/chunks.jsonl').read_text()
        second = self.run_refresh()
        self.assertEqual(second['cached'], 1)
        self.assertEqual((self.root/'.rag/chunks.jsonl').read_text(), original)
        before = snapshot(self.root)
        self.source.write_text('New material about stochastic integration.\n')
        other = self.course/'two.txt'
        other.write_text('New independent source.\n')
        self.assertEqual(len(changes(before,snapshot(self.root))['changed']),1)
        self.run_refresh()
        self.source.unlink()
        job = self.run_refresh()
        self.assertEqual(len(job['changes']['deleted']),1)
        chunks = (self.root/'.rag/chunks.jsonl').read_text()
        self.assertNotIn('stochastic integration',chunks)
        self.assertIn('independent source',chunks)

    def test_failed_build_restores_inputs_and_can_retry(self):
        self.run_refresh()
        old = (self.root/'.rag/manifest.jsonl').read_bytes()
        chunks = (self.root/'.rag/chunks.jsonl').read_bytes()
        self.source.write_text('Revised source.\n')
        def fail(root):
            raise RuntimeError('Simulated build failure')
        with self.assertRaises(RuntimeError):
            self.run_refresh(builder=fail)
        self.assertEqual((self.root/'.rag/manifest.jsonl').read_bytes(),old)
        self.assertEqual((self.root/'.rag/chunks.jsonl').read_bytes(),chunks)
        self.assertEqual(self.run_refresh()['state'],'complete')

    def test_backup_captures_wal_and_refuses_overwrite(self):
        store = LibraryStore(self.root/'.rag/library.sqlite')
        store.save('view1','view',0,{'title':'Risk lectures','query':'risk','mode':'hybrid','filters':{'course':'Risk'}})
        destination = self.root/'backup.sqlite'
        backup(self.root,destination)
        with contextlib.closing(sqlite3.connect(destination)) as db:
            self.assertEqual(db.execute('SELECT title FROM items').fetchone()[0], 'Risk lectures')
        with self.assertRaises(FileExistsError): backup(self.root,destination)
        with self.assertRaises(ValueError):
            store.save('view2','view',0,{'title':'Bad','query':'risk','mode':'hybrid','filters':{'unknown':'x'}})

    def test_job_lock_and_interrupted_recovery(self):
        with exclusive(self.root):
            with self.assertRaises(ValueError): self.run_refresh()
        abandoned = self.root/'.rag/operations/jobs/old.json'
        atomic(abandoned, {'state':'running'})
        self.run_refresh()
        self.assertEqual(json.loads(abandoned.read_text())['state'],'interrupted')


if __name__ == '__main__': unittest.main()
