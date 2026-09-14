"""Document intake validation and publish orchestration tests."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from rag_import import ImportService


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, command, root):
        self.calls.append(command)
        if command[:3] == ['git', 'branch', '--show-current']:
            return 'main\n'
        if command[:3] == ['git', 'remote', 'get-url']:
            return 'git@github.com:example/archive.git\n'
        if command[:2] == ['git', 'rev-parse']:
            return 'abc1234\n'
        return ''


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rag-import-test-')
        self.root = Path(self.tmp.name)
        for folder in ['Fall 2025/MATH5000/lectures', 'Spring 2026/MATH5001/readings', 'Program-wide/syllabi']:
            (self.root / folder).mkdir(parents=True)
        self.runner = FakeRunner()
        self.service = ImportService(self.root, runner=self.runner, start_threads=False)

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, name='new-notes.txt', content=b'Gamma measures delta changes.'):
        return {'folder': 'Fall 2025/MATH5000/lectures', 'files': [{
            'name': name, 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
            'data': base64.b64encode(content).decode(),
        }]}

    def test_lists_only_existing_archive_folders_and_repository_target(self):
        folders = self.service.status()['folders']
        self.assertIn('Fall 2025/MATH5000/lectures', folders)
        self.assertNotIn('.rag', folders)
        self.assertIn('.pdf', self.service.supported_extensions)
        self.assertEqual(self.service.repository()['branch'], 'main')

    def test_accept_verifies_and_atomically_saves_new_file(self):
        job = self.service.accept(self.payload())
        target = self.root / job['files'][0]
        self.assertEqual(target.read_bytes(), b'Gamma measures delta changes.')
        persisted = json.loads((self.root / '.rag/imports/jobs' / f"{job['id']}.json").read_text())
        self.assertEqual(persisted['state'], 'queued')

    def test_rejects_traversal_unsupported_collision_and_bad_hash(self):
        cases = [self.payload('../escape.txt'), self.payload('malware.exe')]
        bad_hash = self.payload('bad.txt'); bad_hash['files'][0]['sha256'] = '0' * 64; cases.append(bad_hash)
        for payload in cases:
            with self.subTest(name=payload['files'][0]['name']):
                service = ImportService(self.root, runner=self.runner, start_threads=False)
                with self.assertRaises(ValueError): service.accept(payload)
        existing = self.root / 'Fall 2025/MATH5000/lectures/already.txt'; existing.write_text('old')
        with self.assertRaises(FileExistsError):
            ImportService(self.root, runner=self.runner, start_threads=False).accept(self.payload('already.txt', b'new'))

    def test_publish_runs_refresh_gate_scoped_commit_and_push(self):
        job = self.service.accept(self.payload())
        self.service._publish(job['id'])
        commands = self.runner.calls
        self.assertTrue(any(command[1:3] == ['scripts/rag_operations.py', '--root'] for command in commands))
        self.assertTrue(any(command[1] == 'scripts/evaluate_rag_release.py' for command in commands if len(command) > 1))
        commit = next(command for command in commands if command[:3] == ['git', 'commit', '--only'])
        self.assertIn(job['files'][0], commit)
        self.assertIn(['git', 'push', 'origin', 'HEAD'], commands)
        final = json.loads((self.root / '.rag/imports/jobs' / f"{job['id']}.json").read_text())
        self.assertEqual(final['state'], 'complete')
        self.assertEqual(final['commit'], 'abc1234')

    def test_restart_marks_an_unfinished_job_interrupted(self):
        job = self.service.accept(self.payload())
        replacement = ImportService(self.root, runner=self.runner, start_threads=False)
        persisted = next(item for item in replacement.status()['jobs'] if item['id'] == job['id'])
        self.assertEqual(persisted['state'], 'interrupted')
        self.assertIn('remain local', persisted['message'])


if __name__ == '__main__':
    unittest.main()
