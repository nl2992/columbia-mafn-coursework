#!/usr/bin/env python3
"""Small local retrieval regression set, not a comprehensive relevance benchmark."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

from rag_search import ROOT, SearchIndex, load_jsonl, now, write_json


def matches(hit, expected):
    return (any(expected['source_contains'] in p for p in hit['source_paths'])
            and hit['locator']['type'] == expected['locator_type']
            and ('locator_value' not in expected or hit['locator']['value'] == expected['locator_value'])
            and expected.get('text_contains', '').casefold() in hit['text'].casefold())


def evaluate(index, cases):
    results=[]
    for case in cases:
        output=index.search(case['query'], mode=case.get('mode','hybrid'), top_k=5,
                            filters=case.get('filters'), phrase=case.get('phrase',False))
        hits=output['results']
        ranks=[i+1 for i,hit in enumerate(hits) if any(matches(hit,e) for e in case['expected_any'])]
        citation_errors=[]
        matched_sources=index.matching_sources(case.get('filters',{}))
        for hit in hits:
            resolved=index.resolve(hit['chunk_id'],hit['source_path'])
            coherent_paths={s['path'] for s in matched_sources.get(hit['document_id'],[])}
            if (resolved['provenance']!=hit['provenance'] or resolved['locator']!=hit['locator']
                    or resolved['artifact_version']!=hit['artifact_version']
                    or hit['source_path'] not in coherent_paths
                    or not all(s['state']=='current' for s in resolved['source_states'])):
                citation_errors.append(hit['chunk_id'])
        results.append({'id':case['id'],'group':case.get('group','core'),
                        'hit_at_5':bool(ranks),'first_relevant_rank':min(ranks) if ranks else None,
                        'citation_errors':citation_errors,'elapsed_ms':output['elapsed_ms'],
                        'eligible_chunks':output['eligible_chunks'],
                        'returned':[{'citation':h['citation'],'scores':h['scores']} for h in hits],
                        'note':case.get('note')})
        print(f"{'PASS' if ranks and not citation_errors else 'MISS'} {case['id']}: "
              f"rank {min(ranks) if ranks else '-'}, {output['elapsed_ms']} ms")
    groups={group:{'cases':len(rows),'hits':sum(r['hit_at_5'] for r in rows)}
            for group in sorted({r['group'] for r in results})
            if (rows:=[r for r in results if r['group']==group])}
    times=[r['elapsed_ms'] for r in results]
    report={'generated_at':now(),'generation':index.report['generation'],
            'case_count':len(results),'hit_at_5_count':sum(r['hit_at_5'] for r in results),
            'groups':groups,'citation_error_count':sum(len(r['citation_errors']) for r in results),
            'citations_checked':sum(len(r['returned']) for r in results),
            'first_query_ms':times[0], 'median_warm_ms':statistics.median(times[1:]),
            'limits':'Curated development smoke set, not held-out recall/precision or answer-quality evaluation. '
                     'Citation checks validate stored provenance and artifact hashes, not visual page rendering.',
            'results':results}
    report['mean_reciprocal_rank_at_5'] = sum(1/r['first_relevant_rank'] if r['first_relevant_rank'] else 0 for r in results)/len(results)
    report['provenance_check_rate'] = 1-report['citation_error_count']/max(1,report['citations_checked'])
    report['index_bytes'] = sum(p.stat().st_size for p in index.directory.iterdir() if p.is_file())
    report['source_paths_without_chunks'] = len(index.report['sources_without_chunks'])
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--cases',type=Path,default=ROOT/'rag/evaluation.jsonl')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--strict',action='store_true',help='Fail also on known challenge/coverage misses')
    parser.add_argument('--baseline',type=Path,help='Fail if a previously passing case regresses')
    args=parser.parse_args()
    index=SearchIndex(args.root)
    try:report=evaluate(index,list(load_jsonl(args.cases)))
    finally:index.close()
    report['regressions'] = []
    if args.baseline:
        previous = json.loads(args.baseline.read_text())
        current = {r['id']:r for r in report['results']}
        report['regressions'] = [r['id'] for r in previous['results'] if r['hit_at_5'] and
            (r['id'] not in current or not current[r['id']]['hit_at_5'] or current[r['id']]['citation_errors'])]
    output=args.output or args.root/'.rag/search-evaluation.json'
    write_json(output,report)
    print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
    print('Full report:',output)
    bad=[r for r in report['results'] if r['citation_errors'] or
         (not r['hit_at_5'] and (args.strict or r['group']=='core'))]
    raise SystemExit(1 if bad or report['regressions'] else 0)


if __name__=='__main__':main()
