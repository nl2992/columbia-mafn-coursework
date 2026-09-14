#!/usr/bin/env python3
"""Local refresh jobs, content-hash change detection and consistent personal backups."""
import argparse
from contextlib import contextmanager, closing
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid

import rag_pipeline as pipeline

ROOTS = ('Fall 2025', 'Spring 2026', 'Program-wide')


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.pending')
    pending.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(pending, path)


def snapshot(root):
    result = {}
    for name in ROOTS:
        for path in sorted((root/name).rglob('*')):
            if path.is_file() and not pipeline.is_ignored(path.relative_to(root)):
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError('Source links are not supported: ' + str(path))
                result[path.relative_to(root).as_posix()] = pipeline.sha256_file(path)
    return result


def changes(before, after):
    return {'added': sorted(after.keys()-before.keys()),
            'deleted': sorted(before.keys()-after.keys()),
            'changed': sorted(p for p in before.keys() & after.keys() if before[p] != after[p])}


@contextmanager
def exclusive(root):
    folder = root/'.rag/operations'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder/'refresh.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another refresh job is running') from None
        yield folder


def backup(root, destination):
    """SQLite backup includes committed WAL writes; never overwrite a backup."""
    source = root/'.rag/library.sqlite'
    if not source.is_file():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb'):
        pass
    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Backup integrity check failed')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return str(destination)


def refresh(root, retry=False, ocr=False, builder=None):
    root = root.resolve()
    with exclusive(root) as folder:
        # An abandoned running state is recoverable once the OS lock is released.
        for path in folder.glob('jobs/*.json'):
            previous = json.loads(path.read_text())
            if previous['state'] == 'running':
                previous.update(state='interrupted', finished_at=pipeline.utc_now())
                atomic(path, previous)
        job_id = uuid.uuid4().hex
        path = folder/'jobs'/f'{job_id}.json'
        job = {'id': job_id, 'state': 'running', 'stage': 'scan',
               'started_at': pipeline.utc_now(), 'retry_errors': retry, 'ocr': ocr}
        def progress(stage, **fields):
            job.update(stage=stage, **fields)
            atomic(path, job)
            print(json.dumps(job), flush=True)
        progress('scan')
        rag = root/'.rag'
        # Save rebuild inputs, not the embedding cache or personal data.
        recovery = folder/'recovery'/job_id
        recovery.mkdir(parents=True)
        names = ['manifest.jsonl', 'chunks.jsonl', 'inventory-report.json',
                 'review-queue.jsonl', 'extraction-report.json', 'normalization-report.json',
                 'rich-extraction-report.json']
        existed = {name for name in names if (rag/name).exists()}
        for name in existed:
            shutil.copy2(rag/name, recovery/name)
        old_globals = pipeline.ROOT, pipeline.RAG_DIR, pipeline.EXTRACTED_DIR
        published = False
        try:
            before = {r['source_path']: r['content_hash'] for r in pipeline.jsonl_read(rag/'manifest.jsonl')
                      if Path(r['source_path']).parts[0] in ROOTS}
            after = snapshot(root)
            job['changes'] = changes(before, after)
            job['backup'] = backup(root, folder/'backups'/f'{job_id}.sqlite')
            pipeline.ROOT, pipeline.RAG_DIR, pipeline.EXTRACTED_DIR = root, rag, rag/'extracted'
            progress('inventory')
            pipeline.inventory()
            # Keep internal application files out of extraction as well as retrieval.
            records = [r for r in pipeline.jsonl_read(rag/'manifest.jsonl') if r['source_path'] in after]
            # Recompute aliases after excluding internal content.
            groups = {}
            for record in records:
                groups.setdefault(record['content_hash'], []).append(record['source_path'])
            for record in records:
                aliases = groups[record['content_hash']]
                record.update(source_paths=aliases, duplicate_of=aliases[0] if record['source_path'] != aliases[0] else None)
            pipeline.jsonl_write(rag/'manifest.jsonl', records)
            pipeline.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
            canonical = [r for r in records if not r['duplicate_of']]
            report = []
            from rag_rich import image_records, archive_records
            for i, record in enumerate(canonical):
                progress('extract', completed=i, total=len(canonical), source=record['source_path'])
                output = pipeline.EXTRACTED_DIR/(record['content_hash']+'.jsonl')
                rows = list(pipeline.jsonl_read(output)) if output.exists() else []
                bad = not rows or any(r.get('record_type') in ('error', 'unsupported') for r in rows)
                empty = not any(r.get('text', '').strip() for r in rows)
                rich_missing = (record['route'] == 'image' and not any(r.get('record_type') == 'image_ocr' for r in rows))
                rich_missing |= record['route'] == 'archive' and not any('archive_members' in r or 'extraction_issues' in r for r in rows)
                cached = output.exists() and not (retry and (bad or empty)) and not rich_missing
                if not cached:
                    source = root/record['source_path']
                    try:
                        if record['route'] == 'image':
                            rows = list(image_records(source, record))
                        elif record['route'] == 'archive':
                            rows = list(pipeline.extract_archive(source, record)) + list(archive_records(source, record))
                        else:
                            rows = list(pipeline.extract_records(source, record, ocr))
                        if pipeline.sha256_file(source) != record['content_hash']:
                            raise ValueError('Source changed during extraction')
                    except Exception as exc:
                        rows = [pipeline.base_record(record, record_type='error', text='', error=str(exc),
                                                     locator_type='document', locator_value='', extraction_method='refresh')]
                    pending = output.with_suffix('.pending')
                    pipeline.jsonl_write(pending, rows)
                    pending.replace(output)
                errors = sum(r.get('record_type') in ('error', 'unsupported') for r in rows)
                report.append({'source_path': record['source_path'], 'cached': cached, 'errors': errors,
                               'records': len(rows), 'empty': not any(r.get('text', '').strip() for r in rows),
                               'issues': [issue for r in rows for issue in r.get('extraction_issues', [])],
                               'ocr_confidence': next((r['ocr_confidence'] for r in rows if 'ocr_confidence' in r), None)})
            pipeline.json_dump(rag/'extraction-report.json', {'generated_at': pipeline.utc_now(), 'documents': report})
            pipeline.json_dump(rag/'rich-extraction-report.json', {'generated_at': pipeline.utc_now(),
                'documents': [r for r in report if Path(r['source_path']).suffix.lower() in ('.zip','.png','.jpg','.jpeg','.gif')]})
            pipeline.jsonl_write(rag/'operations-review.jsonl', [r for r in report if r['errors'] or r['empty'] or r['issues'] or (r['ocr_confidence'] is not None and r['ocr_confidence'] < 70)])
            progress('normalize', completed=len(canonical), cached=sum(r['cached'] for r in report),
                     extraction_errors=sum(bool(r['errors']) for r in report))
            pipeline.normalize(argparse.Namespace())
            if snapshot(root) != after:
                raise ValueError('Sources changed during refresh; retry with a stable archive')
            progress('build')
            if builder is None:
                from rag_search import build
                builder = build
            builder(root=root)
            published = True
            pointer = json.loads((rag/'search/CURRENT.json').read_text())
            progress('done', state='complete', generation=pointer['generation'], finished_at=pipeline.utc_now(),
                     restart_required=True)
            return job
        except BaseException as exc:
            if not published:
                for name in names:
                    if name in existed:
                        shutil.copy2(recovery/name, rag/name)
                    else:
                        (rag/name).unlink(missing_ok=True)
            progress('failed', state='failed', error=str(exc), finished_at=pipeline.utc_now())
            raise
        finally:
            pipeline.ROOT, pipeline.RAG_DIR, pipeline.EXTRACTED_DIR = old_globals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=pipeline.ROOT)
    sub = parser.add_subparsers(dest='command', required=True)
    refresh_parser = sub.add_parser('refresh')
    refresh_parser.add_argument('--retry-errors', action='store_true')
    refresh_parser.add_argument('--ocr', action='store_true')
    sub.add_parser('status')
    sub.add_parser('scan')
    sub.add_parser('backup').add_argument('destination', type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == 'refresh':
        refresh(root, args.retry_errors, args.ocr)
    elif args.command == 'backup':
        print(backup(root, args.destination.resolve()) or 'No personal database exists yet')
    elif args.command == 'status':
        for path in sorted((root/'.rag/operations/jobs').glob('*.json'), key=lambda p: p.stat().st_mtime):
            print(path.read_text())
    else:
        before = {r['source_path']:r['content_hash'] for r in pipeline.jsonl_read(root/'.rag/manifest.jsonl')
                  if Path(r['source_path']).parts[0] in ROOTS}
        print(json.dumps(changes(before, snapshot(root)), indent=2))


if __name__ == '__main__':
    main()
