#!/usr/bin/env python3
"""Safe local document intake followed by refresh, release validation, and Git publish."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import uuid

import rag_pipeline as pipeline

ROOTS = ('Fall 2025', 'Spring 2026', 'Program-wide')
MAX_FILES = 20
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_BATCH_BYTES = 128 * 1024 * 1024
SAFE_NAME = re.compile(r'^[^/\\\x00-\x1f:]+$')


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(pending, path)


def run(command, root: Path):
    return subprocess.run(command, cwd=root, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


class ImportService:
    def __init__(self, root: Path, runner=run, start_threads=True):
        self.root = root.resolve()
        self.runner = runner
        self.start_threads = start_threads
        self.jobs = self.root / '.rag' / 'imports' / 'jobs'
        self._lock = threading.Lock()
        self._active = None
        self._recover_interrupted()

    def _recover_interrupted(self):
        for path in self.jobs.glob('*.json'):
            job = json.loads(path.read_text(encoding='utf-8'))
            if job.get('state') in ('queued', 'running'):
                job.update(state='interrupted', stage='interrupted', finished_at=pipeline.utc_now(),
                           message='The app stopped during this job. The files remain local; run the documented recovery commands.')
                atomic_json(path, job)

    @property
    def supported_extensions(self):
        return sorted(ext for ext, route in pipeline.SUPPORTED_ROUTES.items() if route != 'unsupported')

    def folders(self):
        rows = []
        for root_name in ROOTS:
            source_root = (self.root / root_name).resolve()
            if not source_root.is_dir() or not source_root.is_relative_to(self.root):
                continue
            for folder in [source_root, *sorted(source_root.rglob('*'))]:
                if not folder.is_dir() or folder.is_symlink():
                    continue
                resolved = folder.resolve()
                if resolved.is_relative_to(source_root):
                    rows.append(resolved.relative_to(self.root).as_posix())
        return rows

    def repository(self):
        try:
            branch = self.runner(['git', 'branch', '--show-current'], self.root).strip()
            remote = self.runner(['git', 'remote', 'get-url', 'origin'], self.root).strip()
        except (subprocess.CalledProcessError, OSError):
            branch, remote = '', ''
        return {'branch': branch, 'remote': remote, 'automatic_publish': bool(branch and remote)}

    def status(self):
        paths = sorted(self.jobs.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
        return {'folders': self.folders(), 'extensions': self.supported_extensions,
                'limits': {'files': MAX_FILES, 'file_bytes': MAX_FILE_BYTES, 'batch_bytes': MAX_BATCH_BYTES},
                'repository': self.repository(),
                'jobs': [json.loads(path.read_text(encoding='utf-8')) for path in paths]}

    def _destination(self, folder: str, name: str):
        if folder not in self.folders():
            raise ValueError('Choose an existing course archive folder')
        if (not isinstance(name, str) or not name or name.startswith('.') or name.endswith('.')
                or len(name) > 240 or not SAFE_NAME.fullmatch(name)):
            raise ValueError('Each file must have a safe filename without folders or control characters')
        if Path(name).name != name or Path(name).suffix.lower() not in self.supported_extensions:
            raise ValueError(f'Unsupported document type: {Path(name).suffix or "no extension"}')
        destination = (self.root / folder / name).resolve()
        target_root = (self.root / folder).resolve()
        if not destination.is_relative_to(target_root):
            raise ValueError('Upload path leaves the selected archive folder')
        if destination.exists():
            raise FileExistsError(f'{name} already exists in this folder; rename the new file first')
        return destination

    def accept(self, payload: dict):
        if not isinstance(payload, dict) or set(payload) != {'folder', 'files'}:
            raise ValueError('Upload requires a folder and files')
        files = payload['files']
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
            raise ValueError(f'Choose between 1 and {MAX_FILES} files')
        with self._lock:
            if self._active:
                raise RuntimeError('Another document intake job is already running')
            repository = self.repository()
            if not repository['automatic_publish']:
                raise RuntimeError('Automatic publishing requires a checked-out Git branch and origin remote')
            try:
                conflicts = self.runner(['git', 'diff', '--name-only', '--diff-filter=U'], self.root).strip()
            except (subprocess.CalledProcessError, OSError) as exc:
                raise RuntimeError('Could not verify the Git working tree before import') from exc
            if conflicts:
                raise RuntimeError('Resolve Git merge conflicts before importing documents')
            prepared, total = [], 0
            for item in files:
                if not isinstance(item, dict) or set(item) != {'name', 'size', 'sha256', 'data'}:
                    raise ValueError('Invalid uploaded file record')
                destination = self._destination(payload['folder'], item['name'])
                if not isinstance(item['size'], int) or not 0 <= item['size'] <= MAX_FILE_BYTES:
                    raise ValueError(f'{item["name"]} exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB file limit')
                if not re.fullmatch(r'[0-9a-f]{64}', str(item['sha256'])):
                    raise ValueError(f'Invalid checksum for {item["name"]}')
                try:
                    content = base64.b64decode(item['data'], validate=True)
                except (ValueError, binascii.Error):
                    raise ValueError(f'Invalid file data for {item["name"]}') from None
                if len(content) != item['size'] or hashlib.sha256(content).hexdigest() != item['sha256']:
                    raise ValueError(f'Upload verification failed for {item["name"]}')
                total += len(content)
                if total > MAX_BATCH_BYTES:
                    raise ValueError(f'The upload exceeds the {MAX_BATCH_BYTES // (1024 * 1024)} MB batch limit')
                prepared.append((destination, content))

            created = []
            try:
                for destination, content in prepared:
                    pending = destination.with_name('.' + destination.name + '.uploading')
                    with pending.open('xb') as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(pending, destination)
                    created.append(destination)
            except BaseException:
                for path in created:
                    path.unlink(missing_ok=True)
                for destination, _ in prepared:
                    destination.with_name('.' + destination.name + '.uploading').unlink(missing_ok=True)
                raise

            job_id = uuid.uuid4().hex
            relative = [path.relative_to(self.root).as_posix() for path in created]
            job = {'id': job_id, 'state': 'queued', 'stage': 'uploaded',
                   'started_at': pipeline.utc_now(), 'folder': payload['folder'],
                   'files': relative, 'bytes': total,
                   'message': 'Files saved locally; verification is queued.'}
            atomic_json(self.jobs / f'{job_id}.json', job)
            self._active = job_id
            if self.start_threads:
                threading.Thread(target=self._publish, args=(job_id,), daemon=True,
                                 name=f'archive-import-{job_id[:8]}').start()
            return job

    def _update(self, job: dict, stage: str, **fields):
        job.update(stage=stage, **fields)
        atomic_json(self.jobs / f'{job["id"]}.json', job)

    def _publish(self, job_id: str):
        path = self.jobs / f'{job_id}.json'
        job = json.loads(path.read_text(encoding='utf-8'))
        try:
            self._update(job, 'refresh', state='running', message='Running incremental extraction, OCR, and index refresh…')
            self.runner([sys.executable, 'scripts/rag_operations.py', '--root', str(self.root),
                         'refresh', '--retry-errors', '--ocr'], self.root)
            self._update(job, 'release_gate', message='Running the Stage 8 release gate…')
            self.runner([sys.executable, 'scripts/evaluate_rag_release.py', '--root', str(self.root)], self.root)
            branch = self.runner(['git', 'branch', '--show-current'], self.root).strip()
            remote = self.runner(['git', 'remote', 'get-url', 'origin'], self.root).strip()
            if not branch or not remote:
                raise RuntimeError('Git origin and a checked-out branch are required for automatic publishing')
            self._update(job, 'commit', message=f'Adding verified documents to {branch}…')
            self.runner(['git', 'add', '--', *job['files']], self.root)
            message = f"Add {len(job['files'])} course document" + ('s' if len(job['files']) != 1 else '')
            self.runner(['git', 'commit', '--only', '-m', message, '--', *job['files']], self.root)
            commit = self.runner(['git', 'rev-parse', '--short', 'HEAD'], self.root).strip()
            self._update(job, 'push', commit=commit, message=f'Pushing commit {commit} to origin/{branch}…')
            self.runner(['git', 'push', 'origin', 'HEAD'], self.root)
            self._update(job, 'done', state='complete', finished_at=pipeline.utc_now(),
                         message=f'Indexed and published as commit {commit} on origin/{branch}.')
        except BaseException as exc:
            detail = str(exc)
            if isinstance(exc, subprocess.CalledProcessError) and exc.stdout:
                detail = exc.stdout.strip()[-2000:]
            self._update(job, 'failed', state='failed', finished_at=pipeline.utc_now(),
                         error=detail, message='The files remain safely stored locally. Resolve the error, then retry the intake.')
        finally:
            with self._lock:
                if self._active == job_id:
                    self._active = None
