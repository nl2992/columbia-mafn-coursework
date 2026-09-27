#!/usr/bin/env python3
"""Build the static GitHub Pages edition of the archive into _site/.

Search runs in the browser through a Pagefind index built from the published chunks, the
Copilot runs Qwen3 in the browser through WebLLM, and Data reads workbooks with SheetJS.
Source files are copied into the site until the Pages size budget is reached; anything
larger is fetched from GitHub's LFS media host instead.
"""
import argparse
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rag_search import source_metadata  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_TYPES = {'xlsx', 'xls', 'xlsm', 'csv', 'tsv'}
# Hosting priority when the budget is tight: readable documents first, then data, then the rest.
HOST_PRIORITY = {'pdf': 0, 'xlsx': 1, 'xlsm': 1, 'csv': 1, 'tsv': 1, 'xls': 1, 'ipynb': 2, 'md': 2, 'txt': 2,
                 'py': 2, 'm': 2, 'c': 2, 'r': 2, 'tex': 2, 'png': 3, 'jpg': 3, 'jpeg': 3, 'gif': 3,
                 'docx': 4, 'pptx': 4}


def jsonl(path):
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def locator_label(chunk):
    kind, value = chunk['locator_type'], str(chunk.get('locator_value') or '')
    return {'pdf_page': f'p. {value}', 'pptx_slide': f'slide {value}', 'notebook_cell': f'cell {value}',
            'line_range': f'lines {value}', 'docx_block': f'block {value}', 'spreadsheet_range': value,
            'image_asset': value, 'archive_member': value, 'archive_member_catalog': 'archive contents',
            'dataset_schema': 'columns'}.get(kind, value)


def repository_slug(root):
    if os.environ.get('GITHUB_REPOSITORY'):
        return os.environ['GITHUB_REPOSITORY']
    url = subprocess.run(['git', '-C', str(root), 'remote', 'get-url', 'origin'],
                         capture_output=True, text=True, check=True).stdout.strip()
    return url.removeprefix('git@github.com:').removeprefix('https://github.com/').removesuffix('.git')


def directory_bytes(path):
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file())


def write_index(records, output):
    """Index the records with Pagefind's native CLI via one HTML stub each (its Python API costs ~0.1 s per record)."""
    with tempfile.TemporaryDirectory() as tmp:
        for i, record in enumerate(records):
            meta = ''.join(f'<span data-pagefind-meta="{k}">{html.escape(v)}</span>' for k, v in record['meta'].items())
            filters = ''.join(f'<span data-pagefind-filter="{k}">{html.escape(v)}</span>'
                              for k, values in record['filters'].items() for v in values)
            page = (f'<!doctype html><html lang="en"><head><title>{html.escape(record["meta"]["title"])}</title></head>'
                    f'<body><div>{meta}{filters}</div><main data-pagefind-body>{html.escape(record["content"])}</main></body></html>')
            target = Path(tmp) / f'{i // 1000:03d}' / f'{i}.html'
            target.parent.mkdir(exist_ok=True)
            target.write_text(page, encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'pagefind', '--site', tmp, '--output-path', str(output),
                        '--force-language', 'en', '--quiet'], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, default=ROOT / '_site')
    parser.add_argument('--ref', default='main')
    parser.add_argument('--budget-mb', type=int, default=960)
    args = parser.parse_args()
    root, out, rag = args.root.resolve(), args.out.resolve(), args.root.resolve() / '.rag'
    slug = repository_slug(root)
    media = f'https://media.githubusercontent.com/media/{slug}/{args.ref}/'
    blob = f'https://github.com/{slug}/blob/{args.ref}/'

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(root / 'site', out)
    for name in ('maf-logo.png', 'course-archive-icon.png'):
        shutil.copy2(root / 'viewer' / name, out / name)
    (out / '.nojekyll').write_text('')

    documents = {}
    for row in jsonl(rag / 'manifest.jsonl'):
        if row.get('duplicate_of'):
            continue
        aliases = [source_metadata({**row, 'source_path': path}) for path in row.get('source_paths') or [row['source_path']]]
        documents[row['document_id']] = aliases

    # Choose which files to host before writing records, so each record knows its URL.
    candidates = sorted({a['path'] for aliases in documents.values() for a in aliases
                         if a['file_type'] in HOST_PRIORITY and (root / a['path']).is_file()},
                        key=lambda p: (HOST_PRIORITY[Path(p).suffix.lstrip('.').lower()], (root / p).stat().st_size))
    index_allowance = 220 * 1024 * 1024  # measured Pagefind output is well under this
    budget = args.budget_mb * 1024 * 1024 - index_allowance - directory_bytes(out)
    hosted = set()
    for path in candidates:
        size = (root / path).stat().st_size
        if size <= budget:
            hosted.add(path)
            budget -= size

    def urls(path):
        encoded = quote(path)
        return {'file': 'files/' + encoded if path in hosted else '',
                'media': media + encoded, 'github': blob + encoded}

    records = []
    for chunk in jsonl(rag / 'chunks.jsonl'):
        aliases = documents.get(chunk['document_id'])
        if not aliases:
            continue
        first = aliases[0]
        links = urls(first['path'])
        records.append({
            'content': chunk['text'],
            'meta': {'title': Path(first['path']).name, 'path': first['path'], 'course_label': first['course_label'],
                     'term': first['term'], 'material': first['content_type'], 'file_type': first['file_type'],
                     'review': first['review'], 'locator_type': chunk['locator_type'],
                     'locator_value': str(chunk.get('locator_value') or ''), 'locator': locator_label(chunk),
                     'chunk': chunk['chunk_id'], **links},
            'filters': {'course': sorted({a['course'] for a in aliases if a['course']}) or ['Program-wide'],
                        'term': sorted({a['term'] for a in aliases if a['term']}),
                        'material': sorted({a['content_type'] for a in aliases}),
                        'file_type': [first['file_type']],
                        'review': [first['review']]},
        })
    write_index(records, out / 'pagefind')

    for path in hosted:
        target = out / 'files' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, target)

    datasets = [{**{k: a[k] for k in ('path', 'course', 'course_label', 'term', 'file_type', 'review')},
                 'url': urls(a['path'])['file'] or urls(a['path'])['media'], 'github': urls(a['path'])['github']}
                for aliases in documents.values() for a in aliases if a['file_type'] in DATA_TYPES]
    generation = json.loads((rag / 'search' / 'CURRENT.json').read_text())['generation']
    commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    (out / 'data').mkdir(exist_ok=True)
    (out / 'data' / 'datasets.json').write_text(json.dumps(sorted(datasets, key=lambda d: d['path'])))
    stats = {'generation': generation, 'commit': commit, 'repository': slug, 'chunks': len(records),
             'documents': len(documents), 'source_paths': sum(len(a) for a in documents.values()),
             'hosted_files': len(hosted), 'linked_files': len(candidates) - len(hosted),
             'terms': sorted({a['term'] for aliases in documents.values() for a in aliases if a['term']}),
             'site_bytes': directory_bytes(out)}
    (out / 'data' / 'stats.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    if stats['site_bytes'] > args.budget_mb * 1024 * 1024:
        raise SystemExit(f"Site is {stats['site_bytes'] / 2**20:.0f} MB, over the {args.budget_mb} MB budget")


if __name__ == '__main__':
    main()
