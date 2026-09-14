#!/usr/bin/env python3
"""Archive-wide source/locator audit, separate from semantic relevance evaluation."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
from rag_search import ROOT, SearchIndex, STOPWORDS, digest_file, now, write_json


def probe_query(source, text):
    """Create a deterministic diagnostic query from title and source text."""
    title = Path(source['path']).stem
    words = re.findall(r'[^\W_]+', (title+' '+text).casefold())
    selected = []
    for word in words:
        if len(word) < 3 or word in STOPWORDS or word.isdigit() or word in selected:
            continue
        selected.append(word)
        if len(selected) == 8:
            break
    return ' '.join(selected)


def audit(index):
    groups = defaultdict(lambda: {'sources':0, 'searchable':0, 'retrieval_probes':0,
                                  'retrieval_hits_at_5':0, 'missing_text':[], 'errors':[]})
    checked = 0
    errors = []
    probes = []
    for source in index.db.execute('SELECT * FROM sources ORDER BY path'):
        key = source['course'] or source['term'] or 'Program-wide'
        row = index.db.execute('SELECT chunk_id,evidence FROM chunks WHERE document_id=? ORDER BY rowid LIMIT 1', (source['document_id'],)).fetchone()
        local_errors = []
        path = index.root/source['path']
        if not path.is_file() or not path.resolve().is_relative_to(index.root) or digest_file(path) != source['content_hash']:
            local_errors.append('Source missing, changed, or outside root')
        if row:
            hit = index.resolve(row['chunk_id'], source['path'])
            checked += 1
            if hit['source_path'] != source['path'] or not hit['locator']['value']:
                local_errors.append('Citation alias/locator mismatch')
            query = probe_query(source, json.loads(row['evidence'])['text'])
            filters = {field:[source[field]] for field in ('course','content_type') if source[field]}
            results = index.search(query, mode='lexical', top_k=5, filters=filters)['results'] if query else []
            found = any(result['document_id'] == source['document_id'] for result in results)
            probes.append({'source':source['path'], 'course':source['course'],
                           'content_type':source['content_type'], 'query':query, 'hit_at_5':found})
        group_names = ('course:'+key, 'content_type:'+(source['content_type'] or 'unknown'),
                       'format:'+path.suffix.lower())
        for group in group_names:
            groups[group]['sources'] += 1
            groups[group]['searchable'] += bool(row)
            groups[group]['retrieval_probes'] += bool(row)
            groups[group]['retrieval_hits_at_5'] += bool(row) and found
            if not row: groups[group]['missing_text'].append(source['path'])
            groups[group]['errors'].extend(local_errors)
        errors.extend({'source':source['path'], 'error':error} for error in local_errors)
    retrieval_hits = sum(probe['hit_at_5'] for probe in probes)
    return {'generated_at':now(), 'generation':index.report['generation'],
            'citations_checked':checked, 'errors':errors,
            'retrieval_probes':len(probes), 'retrieval_hits_at_5':retrieval_hits,
            'diagnostic_recall_at_5':retrieval_hits/max(1,len(probes)),
            'groups':dict(groups), 'probes':probes,
            'limits':'One locator and one deterministic lexical probe per searchable source alias, plus hashes for every indexed source. '
                     'Queries are derived from source titles/text to audit every course, content type, and format. '
                     'Missing text remains explicit. This is a regression diagnostic, not held-out semantic recall or answer correctness.'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args()
    index=SearchIndex(args.root)
    try: report=audit(index)
    finally: index.close()
    write_json(args.root/'.rag/coverage-evaluation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('groups','probes')},indent=2))
    raise SystemExit(bool(report['errors']))
