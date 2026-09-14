#!/usr/bin/env python3
"""Run the Stage 8 release gate and write one auditable pass/fail report."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from rag_search import ROOT, now, write_json


def invoke(command, root):
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=900)
    if result.returncode:
        detail = (result.stderr+'\n'+result.stdout).strip()[-4000:]
        raise RuntimeError('Evaluation command failed: '+' '.join(command)+'\n'+detail)
    return result


def check(name, actual, expected, passed):
    return {'name':name, 'passed':bool(passed), 'actual':actual, 'expected':expected}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--skip-copilot',action='store_true',help='Offline diagnostic only; release will not pass')
    args=parser.parse_args()
    root=args.root.resolve()
    thresholds=json.loads((root/'rag/release-thresholds.json').read_text())
    baseline=root/'.rag/search-evaluation.json'
    invoke([sys.executable,'scripts/evaluate_rag_search.py','--baseline',str(baseline),
            '--output',str(root/'.rag/stage8-evaluation.json')],root)
    invoke([sys.executable,'scripts/evaluate_rag_coverage.py'],root)
    if not args.skip_copilot:
        invoke([sys.executable,'scripts/evaluate_rag_copilot.py'],root)
    retrieval=json.loads((root/'.rag/stage8-evaluation.json').read_text())
    coverage=json.loads((root/'.rag/coverage-evaluation.json').read_text())
    copilot_path=root/'.rag/copilot-evaluation.json'
    copilot=json.loads(copilot_path.read_text()) if copilot_path.is_file() else {}
    generation=json.loads((root/'.rag/search/CURRENT.json').read_text())['generation']
    jobs=sorted((root/'.rag/operations/jobs').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    latest=json.loads(jobs[0].read_text()) if jobs else {}
    checks=[
        check('retrieval generation',retrieval.get('generation'),generation,retrieval.get('generation')==generation),
        check('coverage generation',coverage.get('generation'),generation,coverage.get('generation')==generation),
        check('core retrieval hits at 5',retrieval.get('groups',{}).get('core',{}).get('hits'),
              thresholds['core_retrieval_hits_at_5'],retrieval.get('groups',{}).get('core',{}).get('hits')>=thresholds['core_retrieval_hits_at_5']),
        check('citation errors',retrieval.get('citation_error_count'),thresholds['maximum_citation_errors'],
              retrieval.get('citation_error_count')<=thresholds['maximum_citation_errors']),
        check('retrieval regressions',retrieval.get('regressions'),[],not retrieval.get('regressions')),
        check('archive diagnostic recall at 5',coverage.get('diagnostic_recall_at_5'),
              thresholds['minimum_archive_diagnostic_recall_at_5'],coverage.get('diagnostic_recall_at_5',0)>=thresholds['minimum_archive_diagnostic_recall_at_5']),
        check('archive citation/hash errors',len(coverage.get('errors',[])),0,not coverage.get('errors')),
        check('missing-text sources',retrieval.get('source_paths_without_chunks'),thresholds['maximum_missing_text_sources'],
              retrieval.get('source_paths_without_chunks')<=thresholds['maximum_missing_text_sources']),
        check('extraction error documents',latest.get('extraction_errors'),thresholds['maximum_extraction_error_documents'],
              latest.get('extraction_errors',10**9)<=thresholds['maximum_extraction_error_documents']),
        check('median warm search ms',retrieval.get('median_warm_ms'),thresholds['maximum_median_warm_search_ms'],
              retrieval.get('median_warm_ms',10**9)<=thresholds['maximum_median_warm_search_ms']),
        check('index bytes',retrieval.get('index_bytes'),thresholds['maximum_index_bytes'],
              retrieval.get('index_bytes',10**18)<=thresholds['maximum_index_bytes']),
        check('latest refresh job',latest.get('state'),'complete',latest.get('state')=='complete'),
        check('refresh backup',latest.get('backup'),'existing SQLite backup',bool(latest.get('backup')) and Path(latest['backup']).is_file()),
    ]
    if args.skip_copilot:
        checks.append(check('live Copilot evaluation','skipped','required',False))
    else:
        checks.extend([
            check('Copilot generation',copilot.get('generation'),generation,copilot.get('generation')==generation),
            check('Copilot cases',f"{copilot.get('passed')}/{copilot.get('total')}",
                  f"{thresholds['copilot_passed']}/{thresholds['copilot_total']}",
                  copilot.get('passed')>=thresholds['copilot_passed'] and copilot.get('total')==thresholds['copilot_total']),
            check('answer correctness',copilot.get('answer_correctness'),thresholds['minimum_answer_correctness'],
                  copilot.get('answer_correctness',0)>=thresholds['minimum_answer_correctness']),
            check('abstention accuracy',copilot.get('abstention_accuracy'),thresholds['minimum_abstention_accuracy'],
                  copilot.get('abstention_accuracy',0)>=thresholds['minimum_abstention_accuracy']),
            check('quotation validation',copilot.get('quotation_validation_rate'),thresholds['minimum_quotation_validation_rate'],
                  copilot.get('quotation_validation_rate',0)>=thresholds['minimum_quotation_validation_rate']),
        ])
    report={'schema_version':1,'generated_at':now(),'generation':generation,
            'status':'pass' if all(item['passed'] for item in checks) else 'fail',
            'checks':checks,
            'artifacts':{'retrieval':str(root/'.rag/stage8-evaluation.json'),
                         'coverage':str(root/'.rag/coverage-evaluation.json'),
                         'copilot':str(copilot_path), 'thresholds':str(root/'rag/release-thresholds.json')},
            'limits':'Release regression gate over curated questions, source-derived archive probes, and live local-model checks. '
                     'It does not estimate open-domain accuracy. Visual-only catalog records require source inspection, and OCR text may contain recognition errors.'}
    target=root/'.rag/release-evaluation.json'
    write_json(target,report)
    print(json.dumps({'status':report['status'],'generation':generation,'checks':checks,'report':str(target)},indent=2))
    raise SystemExit(report['status']!='pass')


if __name__=='__main__':main()
