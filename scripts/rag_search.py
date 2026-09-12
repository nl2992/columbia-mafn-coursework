#!/usr/bin/env python3
"""Local Stage 4: FTS5/BM25 + MiniLM cosine retrieval and a loopback JSON API."""
from __future__ import annotations

import argparse
import base64
import html
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
from xml.etree import ElementTree

from rag_embeddings import DIMENSION, MiniLM, digest_file
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
ALLOWED_ROOTS = {'Fall 2025', 'Spring 2026', 'Program-wide'}
STOPWORDS = set('a an the and or of in on at to for from with as is are was were be been '
                'this that these those how what which when where why does do did can could '
                'would should i me my you your please explain describe show find give about'.split())
ROLES = {'lectures':'lecture', 'lecture_slides':'lecture', 'readings':'reading',
         'reference':'reference', 'references':'reference', 'resources':'reference',
         'assignments':'assignment', 'questions':'assignment', 'assessments':'assessment',
         'solutions':'solution', 'workbooks':'workbook', 'data':'data', 'code':'code',
         'computational':'code', 'source':'code', 'experiments':'experiment', 'sessions':'seminar',
         'assets':'image', 'visuals':'image', 'topics':'topic', 'applications':'application',
         'syllabi':'syllabus'}
GREEK = dict(zip('αβγδθελμρστφω', 'alpha beta gamma delta theta epsilon lambda mu rho sigma tau phi omega'.split()))
FILTER_KEYS = {'course', 'term', 'content_type', 'lecturer', 'folder', 'file_type', 'review'}


def now():
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize_search(text):
    """Search-only representation; original evidence is stored verbatim."""
    text = ''.join(f' {GREEK[ch.lower()]} ' if ch.lower() in GREEK else ch for ch in text)
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(ch))
    return re.sub(r'[_/\\\-–—]+', ' ', text)


def source_metadata(row):
    """Each duplicate path gets its own context, so filters can match any alias."""
    path = Path(row['source_path'])
    parts = path.parts
    course_label = parts[1] if parts[0] != 'Program-wide' and len(parts) > 1 else ''
    course = course_label.split(' - ')[0]
    folders = [x.lower() for x in parts[2:-1]]
    roles = [ROLES[x] for x in folders if x in ROLES]
    content_type = roles[-1] if roles else 'other'
    name = path.stem.lower()
    if 'solution' in name or 'answer key' in name or 'solutions' in folders:
        content_type = 'solution'
    elif 'assessments' in folders or re.search(r'\b(exam|midterm|quiz)\b', name):
        content_type = 'assessment'
    elif 'syllabus' in name or 'syllabi' in folders:
        content_type = 'syllabus'
    elif path.name == 'README.md':
        content_type = 'course_map'
    lecturer = ''
    if 'sessions' in parts:
        pos = parts.index('sessions') + 1
        if pos < len(parts)-1:
            lecturer = re.sub(r'^\d{4}\s+', '', parts[pos])
    version_match = re.search(r'\[Ver\s+(\d+)\]', path.stem, re.I)
    family_stem = re.sub(r'\s*\[Ver\s+\d+\]', '', path.stem, flags=re.I)
    family = hashlib.sha256(str(path.parent / family_stem).casefold().encode()).hexdigest()[:24]
    return {'path': row['source_path'], 'document_id': row['document_id'],
            'course': course, 'course_label': course_label,
            'term': row.get('term') or ('Program-wide' if parts[0]=='Program-wide' else ''),
            'content_type': content_type, 'folder': path.parent.as_posix(),
            'file_type': path.suffix.lstrip('.').lower(), 'lecturer': lecturer,
            'review': 'review_required' if content_type in ('solution','assessment') else row.get('access_review','not_reviewed'),
            'version_family': family, 'version_label': version_match.group(1) if version_match else None,
            'content_hash': row['content_hash']}


def create_database(path):
    db = sqlite3.connect(path)
    db.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE info(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE chunks(rowid INTEGER PRIMARY KEY, chunk_id TEXT UNIQUE NOT NULL,
          document_id TEXT NOT NULL, parent_id TEXT NOT NULL, locator_type TEXT NOT NULL,
          locator_value TEXT NOT NULL, evidence TEXT NOT NULL);
        CREATE INDEX chunk_document ON chunks(document_id);
        CREATE TABLE sources(path TEXT PRIMARY KEY, document_id TEXT NOT NULL,
          course TEXT, course_label TEXT, term TEXT, content_type TEXT, folder TEXT,
          file_type TEXT, lecturer TEXT, review TEXT, version_family TEXT,
          version_label TEXT, content_hash TEXT);
        CREATE INDEX source_document ON sources(document_id);
        CREATE INDEX source_course ON sources(course);
        CREATE VIRTUAL TABLE fts USING fts5(title, context, text, tokenize='unicode61 remove_diacritics 2');
    ''')
    return db


def build(root=ROOT, model_dir=None, batch_size=32, threads=4):
    started = time.perf_counter()
    root = Path(root).resolve()
    rag = root / '.rag'
    search = rag / 'search'
    search.mkdir(parents=True, exist_ok=True)
    # Exclusive local lock prevents two builds publishing conflicting generations.
    import fcntl
    with (search / 'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        manifest_path, chunks_path = rag/'manifest.jsonl', rag/'chunks.jsonl'
        source_fingerprints = {p.name: digest_file(p) for p in (manifest_path, chunks_path)}
        model = MiniLM(model_dir, threads)
        manifest = list(load_jsonl(manifest_path))
        sources = [source_metadata(m) for m in manifest if Path(m['source_path']).parts[0] in ALLOWED_ROOTS]
        groups = defaultdict(list)
        for source in sources:
            groups[source['document_id']].append(source)
        for source in sources:
            path = (root/source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f"Missing or out-of-root source: {source['path']}")
            if digest_file(path) != source['content_hash']:
                raise ValueError(f"Source changed since inventory: {source['path']}. Refresh stages 1-3.")
        chunks, excluded = [], 0
        for row in load_jsonl(chunks_path):
            if row['document_id'] not in groups:
                excluded += 1
                continue
            if not row.get('text','').strip() or not row.get('locator_value'):
                raise ValueError('Chunk lacks text or source locator: ' + str(row.get('chunk_id')))
            if row['artifact_version'] != groups[row['document_id']][0]['content_hash']:
                raise ValueError('Chunk/manifest hash mismatch: ' + row['chunk_id'])
            chunks.append(row)
        chunks.sort(key=lambda x:x['chunk_id'])
        if not chunks:
            raise ValueError('No course chunks available')
        generation = uuid.uuid4().hex
        directory = search/'generations'/generation
        directory.mkdir(parents=True)
        db = create_database(directory/'index.sqlite')
        for source in sources:
            db.execute('INSERT INTO sources VALUES ('+','.join('?' for _ in source)+')', tuple(source.values()))
        cache = sqlite3.connect(search/'embedding-cache.sqlite')
        cache.execute('CREATE TABLE IF NOT EXISTS vectors(key TEXT PRIMARY KEY, vector BLOB NOT NULL)')
        vector_list, owners, windows = [], [], []
        pending, pending_keys, pending_indices = [], [], []
        cache_hits = encoded = 0

        def flush():
            nonlocal encoded
            if not pending:
                return
            vectors = model.encode_ids(pending)
            for index, key, vector in zip(pending_indices, pending_keys, vectors):
                vector_list[index] = vector
                cache.execute('INSERT OR REPLACE INTO vectors VALUES (?,?)', (key,vector.tobytes()))
            encoded += len(pending)
            pending.clear(); pending_keys.clear(); pending_indices.clear()
            cache.commit()

        for idx, row in enumerate(chunks):
            aliases = groups[row['document_id']]
            title = ' '.join(Path(s['path']).name for s in aliases)
            context = ' '.join(' '.join(str(s.get(k) or '') for k in
                                       ['course','course_label','term','content_type','lecturer','folder']) for s in aliases)
            db.execute('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',
                       (idx,row['chunk_id'],row['document_id'],row['parent_id'],
                        row['locator_type'],row['locator_value'],json.dumps(row,ensure_ascii=False)))
            db.execute('INSERT INTO fts(rowid,title,context,text) VALUES (?,?,?,?)',
                       (idx,normalize_search(title),normalize_search(context),normalize_search(row['text'])))
            for start, end, ids in model.tokenizer.windows(row['text']):
                token_bytes = np.asarray(ids,dtype='<i4').tobytes()
                key = hashlib.sha256(model.fingerprint.encode()+token_bytes).hexdigest()
                cached = None
                for fingerprint in model.compatible_cache_fingerprints:
                    cache_key = hashlib.sha256(fingerprint.encode()+token_bytes).hexdigest()
                    cached = cache.execute('SELECT vector FROM vectors WHERE key=?',(cache_key,)).fetchone()
                    if cached:
                        break
                owners.append(idx); windows.append((start,end))
                if cached:
                    vector_list.append(np.frombuffer(cached[0],dtype='float32').copy())
                    if cache_key != key:
                        cache.execute('INSERT OR IGNORE INTO vectors VALUES (?,?)',(key,cached[0]))
                    cache_hits += 1
                else:
                    pending_indices.append(len(vector_list)); vector_list.append(None)
                    pending.append(ids); pending_keys.append(key)
                if len(pending) >= batch_size:
                    flush()
            if (idx+1)%250==0 or idx+1==len(chunks):
                print(f'build: {idx+1}/{len(chunks)} chunks, {encoded} windows encoded, '
                      f'{cache_hits} reused, {time.perf_counter()-started:.0f}s', file=sys.stderr,flush=True)
                db.commit()
        flush()
        vectors = np.stack(vector_list).astype('float32')
        np.save(directory/'vectors.npy',vectors,allow_pickle=False)
        np.save(directory/'owners.npy',np.asarray(owners,dtype='int32'),allow_pickle=False)
        np.save(directory/'windows.npy',np.asarray(windows,dtype='int32'),allow_pickle=False)
        if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-4):
            raise ValueError('Embedding normalization check failed')
        represented = {c['document_id'] for c in chunks}
        report = {'schema_version':SCHEMA_VERSION,'generation':generation,'built_at':now(),
                  'chunk_count':len(chunks),'vector_count':len(vectors),'dimension':DIMENSION,
                  'documents_with_chunks':len(represented),'source_path_count':len(sources),
                  'excluded_noncourse_chunks':excluded,
                  'sources_without_chunks':[s['path'] for s in sources if s['document_id'] not in represented],
                  'model':model.identity,'model_fingerprint':model.fingerprint,'model_dir':str(model.path),
                  'input_sha256':source_fingerprints,'encoded_windows':encoded,'reused_windows':cache_hits,
                  'elapsed_seconds':round(time.perf_counter()-started,2),
                  'ranking':'BM25 + cosine, reciprocal rank fusion k=60; one result per source locator',
                  'citation_limits':'Page/slide locators retained; PDF text-coordinate overlays are best-effort and other formats remain evidence-first.'}
        db.execute('INSERT INTO info VALUES (?,?)',('report',json.dumps(report)))
        db.execute("INSERT INTO fts(fts) VALUES('optimize')")
        db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('SQLite integrity check failed')
        db.close();cache.commit();cache.close()
        for path in (manifest_path,chunks_path):
            if digest_file(path) != source_fingerprints[path.name]:
                raise ValueError('Inputs changed during build; old index remains active')
        for source in sources:
            path = (root/source['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file() or digest_file(path) != source['content_hash']:
                raise ValueError('Source changed during build; old index remains active: ' + source['path'])
        write_json(directory/'build-report.json',report)
        pointer=search/'CURRENT.tmp'
        write_json(pointer,{'generation':generation})
        os.replace(pointer,search/'CURRENT.json')
        print(json.dumps({k:v for k,v in report.items() if k not in ['sources_without_chunks','model_dir']},indent=2))
        return report


def fts_query(query):
    words = re.findall(r'[^\W_]+',normalize_search(query))
    words = list(dict.fromkeys(x for x in words if x not in STOPWORDS))[:32]
    return ' OR '.join('"'+x.replace('"','""')+'"' for x in words)


class SearchIndex:
    def __init__(self, root=ROOT, model_dir=None):
        self.root=Path(root).resolve()
        search=self.root/'.rag/search'
        try:
            generation=json.loads((search/'CURRENT.json').read_text())['generation']
        except FileNotFoundError as exc:
            raise RuntimeError('Search index missing. Run: python3 scripts/rag_search.py build') from exc
        if not re.fullmatch('[0-9a-f]{32}',generation):
            raise ValueError('Invalid generation pointer')
        self.directory=search/'generations'/generation
        self.db=sqlite3.connect((self.directory/'index.sqlite').as_uri()+'?mode=ro',uri=True,check_same_thread=False)
        self.request_lock=threading.RLock()
        self.db.row_factory=sqlite3.Row
        self.report=json.loads(self.db.execute("SELECT value FROM info WHERE key='report'").fetchone()[0])
        self.vectors=np.load(self.directory/'vectors.npy',mmap_mode='r',allow_pickle=False)
        self.owners=np.load(self.directory/'owners.npy',mmap_mode='r',allow_pickle=False)
        self.windows=np.load(self.directory/'windows.npy',mmap_mode='r',allow_pickle=False)
        if len(self.owners)!=len(self.vectors) or self.vectors.shape[1]!=self.report['dimension']:
            raise ValueError('Vector index shape mismatch; rebuild')
        self.model_dir=model_dir or self.report['model_dir']
        self.model=None
        self.aliases=defaultdict(list)
        for row in self.db.execute('SELECT * FROM sources ORDER BY path'):
            self.aliases[row['document_id']].append(dict(row))
        self._input_stats=None

    def close(self):
        self.db.close()

    def ensure_current(self):
        paths=[self.root/'.rag'/name for name in self.report['input_sha256']]
        stats=tuple((p.stat().st_mtime_ns,p.stat().st_size) for p in paths)
        if stats!=self._input_stats:
            if any(digest_file(p)!=self.report['input_sha256'][p.name] for p in paths):
                raise RuntimeError('Stage 1-3 outputs changed; run rag_search.py build to refresh the index')
            self._input_stats=stats

    def filters(self):
        self.ensure_current()
        return {field:[dict(r) for r in self.db.execute(
                f'SELECT {field} AS value, COUNT(DISTINCT document_id) AS documents, '
                'COUNT(DISTINCT CASE WHEN document_id IN (SELECT document_id FROM chunks) '
                'THEN document_id END) AS searchable_documents '
                f'FROM sources WHERE {field} IS NOT NULL AND {field} != \'\' GROUP BY {field} ORDER BY {field}')]
                for field in sorted(FILTER_KEYS)}

    def matching_sources(self,filters):
        unknown=set(filters)-FILTER_KEYS
        if unknown:
            raise ValueError('Unknown filters: '+', '.join(sorted(unknown)))
        clauses,params=[],[]
        for key, values in filters.items():
            values=[values] if isinstance(values,str) else values
            if not isinstance(values,list) or not all(isinstance(v,str) for v in values):
                raise ValueError('Filters must contain strings or lists of strings')
            if not values:
                continue
            alternatives=[]
            for value in values:
                if key in ('folder','lecturer'):
                    alternatives.append(f'instr(lower({key}), lower(?)) > 0')
                else:
                    alternatives.append(f'{key} = ? COLLATE NOCASE')
                params.append(value)
            clauses.append('('+' OR '.join(alternatives)+')')
        query='SELECT * FROM sources'+(' WHERE '+' AND '.join(clauses) if clauses else '')
        matched=defaultdict(list)
        for row in self.db.execute(query,params):
            matched[row['document_id']].append(dict(row))
        return matched

    def _result(self,row,matched=None):
        evidence=json.loads(row['evidence'])
        sources=self.aliases[row['document_id']]
        chosen=(matched or sources)[0]
        kind,value=evidence['locator_type'],evidence['locator_value']
        unit={'pdf_page':'p.','pptx_slide':'slide','line_range':'lines','notebook_cell':'cell'}.get(kind,kind)
        route='/api/chunks/'+quote(evidence['chunk_id'],safe='')+'?source='+quote(chosen['path'],safe='')
        family=chosen['version_family']
        related=[{'path':r['path'],'version_label':r['version_label'],'document_id':r['document_id']}
                 for r in self.db.execute('SELECT path,version_label,document_id FROM sources '
                     'WHERE version_family=? AND document_id != ? ORDER BY path',(family,row['document_id']))]
        locator_warning=('PDF page previews include Poppler text-coordinate overlays when available; scanned or malformed PDFs may fall back to the original.'
                         if kind=='pdf_page' else
                         'Character offsets refer to upstream extraction; this source type is shown as focused evidence rather than a pixel highlight.')
        return {'chunk_id':evidence['chunk_id'],'text':evidence['text'],
                'source_path':chosen['path'],'source_paths':[s['path'] for s in sources],
                'matched_source_paths':[s['path'] for s in (matched or sources)],
                'document_id':evidence['document_id'],'artifact_version':evidence['artifact_version'],
                'locator':{'type':kind,'value':value},'citation_id':evidence['chunk_id'],
                'citation':{'label':f"{Path(chosen['path']).name} · {unit} {value}",
                            'resolve_url':route,'document_id':evidence['document_id'],
                            'artifact_version':evidence['artifact_version'],'source_path':chosen['path'],
                            'locator_type':kind,'locator_value':value},
                'metadata':chosen,'sources':sources,'related_versions':related,
                'provenance':evidence,
                'locator_warning':locator_warning}

    def resolve(self,chunk_id,source_path=None):
        self.ensure_current()
        row=self.db.execute('SELECT * FROM chunks WHERE chunk_id=?',(chunk_id,)).fetchone()
        if row is None:
            raise KeyError(chunk_id)
        matched=None
        if source_path is not None:
            matched=[s for s in self.aliases[row['document_id']] if s['path']==source_path]
            if not matched:
                raise KeyError(source_path)
        result=self._result(row,matched)
        states=[]
        for source in result['sources']:
            path=(self.root/source['path']).resolve()
            state='missing'
            if path.is_relative_to(self.root) and path.is_file():
                state='current' if digest_file(path)==source['content_hash'] else 'changed'
            states.append({'path':source['path'],'state':state})
        result['source_states']=states
        return result

    def search(self,query,mode='hybrid',top_k=5,filters=None,phrase=False,min_cosine=0.25,source_paths=None):
        started=time.perf_counter()
        if not isinstance(query,str) or not query.strip() or len(query)>2000:
            raise ValueError('Query must contain 1-2000 characters')
        if mode not in ('lexical','semantic','hybrid') or not 1<=top_k<=50:
            raise ValueError('mode must be lexical/semantic/hybrid; top_k must be 1-50')
        if phrase and mode=='semantic':
            raise ValueError('Literal phrase search requires lexical or hybrid mode')
        if not 0 <= min_cosine <= 1:
            raise ValueError('min_cosine must be between 0 and 1')
        self.ensure_current()
        filters=filters or {}
        matched=self.matching_sources(filters)
        if source_paths is not None:
            if not isinstance(source_paths,list) or not 1<=len(source_paths)<=12 or not all(isinstance(p,str) for p in source_paths):
                raise ValueError('Pinned sources must contain 1-12 indexed source paths')
            known={s['path'] for aliases in self.aliases.values() for s in aliases}
            if any(p not in known for p in source_paths):
                raise ValueError('A pinned source is not in the active index; remove or repin it')
            selected=set(source_paths)
            matched={doc:[s for s in aliases if s['path'] in selected] for doc,aliases in matched.items()}
            matched={doc:aliases for doc,aliases in matched.items() if aliases}
        rows=list(self.db.execute('SELECT rowid,document_id,locator_type,locator_value FROM chunks'))
        eligible=[r['rowid'] for r in rows if r['document_id'] in matched]
        if phrase:
            eligible_set=set(eligible)
            literal={r[0] for r in self.db.execute('SELECT rowid FROM chunks WHERE '
                      "instr(lower(json_extract(evidence,'$.text')),lower(?))>0 OR "
                      "instr(lower(json_extract(evidence,'$.source_path')),lower(?))>0",(query,query))}
            # Also match duplicate filenames.
            path_docs={d for d,ss in matched.items() if any(query.casefold() in s['path'].casefold() for s in ss)}
            eligible=[r['rowid'] for r in rows if r['rowid'] in eligible_set and
                      (r['rowid'] in literal or r['document_id'] in path_docs)]
        eligible_set=set(eligible)
        lexical,semantic={},{}
        cap=max(100,top_k*20)
        expression=fts_query(query)
        if eligible and mode!='semantic' and expression:
            # Filter before taking top candidates; no post-top-k filtering losses.
            for row in self.db.execute('SELECT rowid,bm25(fts,4.0,0.3,1.0) AS score '
                         'FROM fts WHERE fts MATCH ? ORDER BY score,rowid',(expression,)):
                if row['rowid'] in eligible_set:
                    lexical[row['rowid']]={'rank':len(lexical)+1,'bm25':row['score']}
                    if len(lexical)>=cap:
                        break
        if phrase and not lexical:
            lexical={rid:{'rank':i+1,'bm25':None} for i,rid in enumerate(eligible[:cap])}
        if eligible and mode!='lexical' and expression:
            if self.model is None:
                self.model=MiniLM(self.model_dir)
                if self.model.fingerprint!=self.report['model_fingerprint']:
                    self.model=None
                    raise RuntimeError('Embedding model differs from index; rebuild with this model')
            qvector=self.model.query(query)
            scores=np.asarray(self.vectors @ qvector)
            mask=np.isin(self.owners,np.asarray(eligible))
            scores[~mask]=-np.inf
            # All windows participate; take best window for each chunk.
            best=np.full(self.report['chunk_count'],-np.inf,dtype='float32')
            np.maximum.at(best,self.owners,scores)
            order=np.argsort(-best,kind='stable')
            for rid in order[:cap]:
                if best[rid]<min_cosine:
                    break
                window_ids=np.flatnonzero(self.owners==rid)
                best_window=window_ids[np.argmax(scores[window_ids])]
                semantic[int(rid)]={'rank':len(semantic)+1,'cosine':float(best[rid]),
                                  'window_tokens':self.windows[best_window].tolist()}
        fused={rid:(1/(60+lexical[rid]['rank']) if rid in lexical else 0)+
                   (1/(60+semantic[rid]['rank']) if rid in semantic else 0)
               for rid in set(lexical)|set(semantic)}
        order=sorted(fused,key=lambda rid:(-fused[rid],rid))
        results,seen=[],set()
        for rid in order:
            row=self.db.execute('SELECT * FROM chunks WHERE rowid=?',(rid,)).fetchone()
            group=(row['document_id'],row['locator_type'],row['locator_value'])
            if group in seen:
                continue
            seen.add(group)
            result=self._result(row,matched[row['document_id']])
            result['score']=fused[rid]
            result['scores']={'lexical':lexical.get(rid),'semantic':semantic.get(rid)}
            result['excerpt']=result['text'][:500]
            results.append(result)
            if len(results)>=top_k:
                break
        return {'query':query,'mode':mode,'filters':filters,'literal_phrase':phrase,
                'generation':self.report['generation'],'eligible_chunks':len(eligible),
                'score_kind':'reciprocal_rank_fusion; ranking score, not confidence',
                'elapsed_ms':round((time.perf_counter()-started)*1000,1),'results':results,
                'coverage':{'source_paths_without_chunks':len(self.report['sources_without_chunks']),
                            'scope':'Extracted text and catalog records only; missing text is not searchable.'},
                'note':None if results else 'No matches under these filters and similarity threshold.'}

    def ask(self,query,mode='hybrid',top_k=5,filters=None,include_review=False,min_cosine=0.25,
            source_paths=None,history=None,answer_style='evidence',generator=None):
        from rag_copilot import answer_question
        return answer_question(self,query,mode,top_k,filters,include_review,min_cosine,
                               source_paths,history,answer_style,generator)

def pdf_highlight_markup(path, page_number, cache_dir, source_hash, citation_label):
    """Build a self-contained highlighted page using Poppler coordinates."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key=f'{source_hash}-p{page_number}'
    html_path=cache_dir/(key+'.html')
    if html_path.is_file():
        return html_path
    png_path=cache_dir/(key+'.png')
    if not png_path.is_file():
        temporary_prefix=cache_dir/(key+'.'+uuid.uuid4().hex)
        rendered=subprocess.run(['pdftoppm','-f',str(page_number),'-l',str(page_number),
                                 '-singlefile','-png','-r','144',str(path),str(temporary_prefix)],
                                capture_output=True,text=True,timeout=180,check=False)
        generated=Path(str(temporary_prefix)+'.png')
        if rendered.returncode!=0 or not generated.is_file():
            detail=(rendered.stderr or rendered.stdout or 'PDF page rendering failed').strip()[-500:]
            raise RuntimeError(detail)
        temporary=png_path.with_suffix('.png.tmp')
        shutil.copyfile(generated,temporary);os.replace(temporary,png_path)
        generated.unlink(missing_ok=True)
    xml=subprocess.run(['pdftohtml','-xml','-f',str(page_number),'-l',str(page_number),
                        '-i','-stdout',str(path)],capture_output=True,text=True,timeout=180,check=False)
    if xml.returncode!=0 or not xml.stdout.strip():
        detail=(xml.stderr or 'PDF text-coordinate extraction failed').strip()[-500:]
        raise RuntimeError(detail)
    try:
        root=ElementTree.fromstring(xml.stdout)
        page=root.find('.//page')
        if page is None:
            raise ValueError('Rendered PDF page has no coordinate metadata')
        page_width=float(page.attrib['width']);page_height=float(page.attrib['height'])
        boxes=[]
        for node in page.findall('text'):
            text=''.join(node.itertext()).strip()
            if not text:
                continue
            try:
                left=float(node.attrib['left']);top=float(node.attrib['top'])
                width=float(node.attrib['width']);height=float(node.attrib['height'])
            except (KeyError,ValueError):
                continue
            boxes.append((left/page_width*100,top/page_height*100,
                          width/page_width*100,height/page_height*100))
    except (ElementTree.ParseError,KeyError,ValueError,ZeroDivisionError) as exc:
        raise RuntimeError(f'PDF coordinate extraction failed: {exc}') from exc
    image_data=base64.b64encode(png_path.read_bytes()).decode('ascii')
    safe_label=html.escape(citation_label,quote=True)
    safe_title=html.escape(path.name,quote=True)
    overlays=''.join(f'<span class="evidence-box" style="left:{left:.4f}%;top:{top:.4f}%;width:{width:.4f}%;height:{height:.4f}%" aria-hidden="true"></span>'
                     for left,top,width,height in boxes)
    document=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_label}</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
html,body {{ margin:0; min-height:100%; background:#e8eef3; color:#102a43; font:14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
.shell {{ padding:20px; }}
.caption {{ max-width:900px; margin:0 auto 14px; color:#536579; font-size:12px; }}
.caption strong {{ color:#102a43; }}
.page {{ position:relative; width:min(100%, {page_width:.2f}px); margin:0 auto; aspect-ratio:{page_width:.4f}/{page_height:.4f}; background:#fff; box-shadow:0 8px 24px rgba(16,42,67,.18); overflow:hidden; }}
.page img {{ display:block; width:100%; height:100%; object-fit:fill; }}
.evidence-box {{ position:absolute; background:rgba(185,217,235,.52); border:1px solid rgba(29,79,145,.45); border-radius:2px; mix-blend-mode:multiply; }}
.legend {{ max-width:900px; margin:14px auto 0; color:#536579; font-size:11px; }}
.swatch {{ display:inline-block; width:12px; height:12px; margin-right:5px; vertical-align:-2px; background:rgba(185,217,235,.75); border:1px solid rgba(29,79,145,.45); }}
</style></head><body><main class="shell"><div class="caption"><strong>{safe_title}</strong> · {safe_label}</div><div class="page"><img src="data:image/png;base64,{image_data}" alt="{safe_label}">{overlays}</div><div class="legend"><span class="swatch"></span>Extracted text coordinates for this cited physical page. The original PDF remains the authoritative source.</div></main></body></html>'''
    temporary=html_path.with_suffix('.html.tmp')
    temporary.write_text(document,encoding='utf-8');os.replace(temporary,html_path)
    return html_path


def handler_for(index):
    class Handler(BaseHTTPRequestHandler):
        STATIC_FILES = {
            '/': 'index.html',
            '/viewer': 'index.html',
            '/viewer/': 'index.html',
            '/viewer/index.html': 'index.html',
            '/viewer/app.js': 'app.js',
            '/viewer/styles.css': 'styles.css',
            '/viewer/maf-logo.png': 'maf-logo.png',
        }

        def log_message(self, fmt, *args):
            # Queries can contain private course content; do not log request URLs.
            print('search-api:',fmt.split('"')[0],file=sys.stderr)

        def do_GET(self):
            with index.request_lock:
                self.dispatch(head=False)

        def do_HEAD(self):
            with index.request_lock:
                self.dispatch(head=True)

        def do_POST(self):
            self.connection.settimeout(15)
            try:
                host=self.headers.get('Host','').split(':')[0]
                if host not in ('localhost','127.0.0.1') or self.headers.get('Origin') not in (None,f'http://{self.headers.get("Host")}'):
                    self.reply(403,{'error':'Local same-origin requests only'});return
                if urlparse(self.path).path!='/api/ask':
                    self.reply(404,{'error':'Unknown endpoint'});return
                if self.headers.get_content_type()!='application/json' or self.headers.get('Transfer-Encoding'):
                    self.reply(415,{'error':'Use a JSON request body'});return
                length=int(self.headers.get('Content-Length','0'))
                if not 1<=length<=40000:
                    self.reply(413,{'error':'Question context exceeds the 40 KB limit'});return
                payload=json.loads(self.rfile.read(length))
                allowed={'query','mode','top_k','filters','include_review','min_cosine','source_paths','history','answer_style'}
                if not isinstance(payload,dict) or set(payload)-allowed:
                    raise ValueError('Unknown question fields')
                payload.setdefault('answer_style','synthesis')
                self.reply(200,index.ask(**payload))
            except (ValueError,TypeError) as exc:
                self.reply(400,{'error':str(exc)})
            except (RuntimeError,OSError) as exc:
                self.reply(409,{'error':str(exc)})
            except Exception:
                self.reply(500,{'error':'Could not complete the local answer'})

        def dispatch(self, head=False):
            try:
                host=self.headers.get('Host','').split(':')[0]
                if host not in ('localhost','127.0.0.1'):
                    self.reply(403,{'error':'Local requests only'});return
                if self.headers.get('Origin') not in (None,f'http://{self.headers.get("Host")}'):
                    self.reply(403,{'error':'Cross-origin access disabled'});return
                parsed=urlparse(self.path);params=parse_qs(parsed.query)
                one=lambda k,d=None:params.get(k,[d])[0]
                if parsed.path in self.STATIC_FILES:
                    self.serve_static(self.STATIC_FILES[parsed.path],head);return
                if parsed.path=='/api/health':
                    index.ensure_current()
                    data={'status':'ok','generation':index.report['generation'],
                          'chunks':index.report['chunk_count'],'vectors':len(index.vectors),
                          'documents':index.report['documents_with_chunks'],
                          'source_paths':index.report['source_path_count'],
                          'source_paths_without_chunks':len(index.report['sources_without_chunks'])}
                elif parsed.path=='/api/filters':
                    data=index.filters()
                elif parsed.path=='/api/copilot/status':
                    from rag_copilot import LocalGenerator
                    data=LocalGenerator().status()
                elif parsed.path=='/api/search':
                    data=index.search(one('q',''),one('mode','hybrid'),int(one('top_k','5')),
                         {k:params[k] for k in FILTER_KEYS if k in params},
                         phrase=one('phrase','false')=='true',min_cosine=float(one('min_cosine','0.25')))
                elif parsed.path=='/api/ask':
                    data=index.ask(one('q',''),one('mode','hybrid'),int(one('top_k','5')),
                         {k:params[k] for k in FILTER_KEYS if k in params},
                         include_review=one('include_review','false')=='true',min_cosine=float(one('min_cosine','0.25')))
                elif parsed.path.startswith('/api/chunks/'):
                    data=index.resolve(unquote(parsed.path[len('/api/chunks/'):]),one('source'))
                elif parsed.path=='/api/source':
                    self.serve_source(one('path',''),head);return
                elif parsed.path=='/api/preview':
                    self.serve_preview(one('path',''),head);return
                elif parsed.path=='/api/highlight':
                    self.serve_highlight(one('chunk',''),one('source',''),head);return
                else:
                    self.reply(404,{'error':'Unknown endpoint'});return
                self.reply(200,data)
            except (ValueError,TypeError) as exc:
                self.reply(400,{'error':str(exc)})
            except KeyError:
                self.reply(404,{'error':'Citation not found in active index'})
            except (RuntimeError,FileNotFoundError) as exc:
                self.reply(409,{'error':str(exc)})
            except Exception:
                self.reply(500,{'error':'Search failed; inspect local index and runtime'})

        def serve_static(self,name,head=False):
            path=self.root_viewer()/name
            if not path.is_file():
                self.reply(404,{'error':'Viewer asset unavailable'});return
            payload=path.read_bytes()
            content_type={'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8',
                          'styles.css':'text/css; charset=utf-8','maf-logo.png':'image/png'}[name]
            self.send_response(200);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store')
            self.send_header('Content-Security-Policy',"default-src 'self'; frame-src 'self'; object-src 'self'; script-src 'self'; style-src 'self'; base-uri 'none'; form-action 'self'")
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if not head:self.wfile.write(payload)

        def root_viewer(self):
            return index.root/'viewer'

        def verify_indexed_source(self,source_path):
            if not source_path or len(source_path)>2000:
                self.reply(400,{'error':'A relative indexed source path is required'});return None
            index.ensure_current()
            row=index.db.execute('SELECT * FROM sources WHERE path=?',(source_path,)).fetchone()
            if row is None:
                self.reply(404,{'error':'Source is not in the active index'});return None
            path=(index.root/source_path).resolve()
            if not path.is_relative_to(index.root) or not path.is_file():
                self.reply(404,{'error':'Source file is missing'});return None
            if digest_file(path)!=row['content_hash']:
                self.reply(409,{'error':'Source changed; refresh Stage 1-3 outputs before viewing'});return None
            return row,path

        def serve_pdf_path(self,pdf_path,filename,head=False,preview_pages=None):
            size=pdf_path.stat().st_size
            start,end=0,size-1;status=200
            range_header=self.headers.get('Range','')
            if range_header:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header.strip())
                if not match:
                    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
                left,right=match.groups()
                if left:
                    start=int(left);end=int(right) if right else size-1
                else:
                    suffix=int(right) if right else 0;start=max(size-suffix,0);end=size-1
                if start<0 or start>=size or end<start:
                    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
                end=min(end,size-1);status=206
            length=end-start+1
            self.send_response(status);self.send_header('Content-Type','application/pdf')
            self.send_header('Content-Length',str(length));self.send_header('Accept-Ranges','bytes')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.send_header('Content-Disposition',"inline; filename*=UTF-8''"+quote(filename,safe=''))
            if preview_pages:self.send_header('X-Preview-Pages',str(preview_pages))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            if head:return
            with pdf_path.open('rb') as stream:
                stream.seek(start);remaining=length
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:break
                    self.wfile.write(block);remaining-=len(block)

        def serve_source(self,source_path,head=False):
            verified=self.verify_indexed_source(source_path)
            if verified is None:return
            row,path=verified
            size=path.stat().st_size
            start,end=0,size-1
            status=200
            range_header=self.headers.get('Range','')
            if range_header:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',range_header.strip())
                if not match:
                    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
                left,right=match.groups()
                if left:
                    start=int(left)
                    end=int(right) if right else size-1
                else:
                    suffix=int(right) if right else 0
                    start=max(size-suffix,0);end=size-1
                if start<0 or start>=size or end<start:
                    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
                end=min(end,size-1);status=206
            length=end-start+1
            content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            self.send_response(status);self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(length));self.send_header('Accept-Ranges','bytes')
            if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.send_header('Content-Disposition',"inline; filename*=UTF-8''"+quote(path.name,safe=''))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            if head:return
            with path.open('rb') as stream:
                stream.seek(start);remaining=length
                while remaining:
                    block=stream.read(min(1024*1024,remaining))
                    if not block:break
                    self.wfile.write(block);remaining-=len(block)

        def serve_preview(self,source_path,head=False):
            verified=self.verify_indexed_source(source_path)
            if verified is None:return
            row,path=verified
            if path.suffix.lower() not in ('.pptx','.ppt'):
                self.reply(400,{'error':'Preview is currently available for PowerPoint files only'});return
            preview_dir=index.root/'.rag/viewer/previews'
            preview_dir.mkdir(parents=True,exist_ok=True)
            preview_path=preview_dir/(row['content_hash']+'.pdf')
            if not preview_path.is_file():
                try:
                    with tempfile.TemporaryDirectory(prefix='rag-pptx-preview-') as workspace:
                        output_dir=Path(workspace)/'output';output_dir.mkdir()
                        profile=Path(workspace)/'profile';profile.mkdir()
                        command=['soffice','--headless',f'-env:UserInstallation={profile.as_uri()}',
                                '--convert-to','pdf','--outdir',str(output_dir),str(path)]
                        converted=subprocess.run(command,capture_output=True,text=True,timeout=180,check=False)
                        generated=output_dir/(path.stem+'.pdf')
                        if converted.returncode!=0 or not generated.is_file():
                            detail=(converted.stderr or converted.stdout or 'LibreOffice conversion failed').strip()[-500:]
                            self.reply(409,{'error':'PowerPoint preview could not be rendered','detail':detail});return
                        temporary=preview_path.with_suffix('.pdf.tmp')
                        shutil.copyfile(generated,temporary);os.replace(temporary,preview_path)
                except (FileNotFoundError,subprocess.TimeoutExpired) as exc:
                    self.reply(409,{'error':'PowerPoint preview requires the local LibreOffice runtime','detail':str(exc)});return
            pages=None
            try:
                info=subprocess.run(['pdfinfo',str(preview_path)],capture_output=True,text=True,timeout=30,check=False)
                match=re.search(r'^Pages:\s+(\d+)\s*$',info.stdout,re.MULTILINE)
                pages=int(match.group(1)) if match else None
            except (FileNotFoundError,subprocess.TimeoutExpired):
                pass
            self.serve_pdf_path(preview_path,path.name+'.pdf',head,pages)

        def serve_highlight(self,chunk_id,source_path,head=False):
            if not chunk_id:
                self.reply(400,{'error':'A citation chunk ID is required'});return
            resolved=index.resolve(chunk_id,source_path or None)
            verified=self.verify_indexed_source(resolved['source_path'])
            if verified is None:return
            row,path=verified
            if resolved['locator']['type']!='pdf_page' or path.suffix.lower()!='.pdf':
                self.reply(400,{'error':'Text highlighting is currently available for PDF page citations only'});return
            page=int(resolved['locator']['value'])
            page_count=resolved.get('provenance',{}).get('page_count')
            if page<1 or (page_count and page>int(page_count)):
                self.reply(400,{'error':'Citation page is outside the verified PDF'});return
            label=resolved.get('citation',{}).get('label') or f'{path.name} · p. {page}'
            try:
                asset=pdf_highlight_markup(path,page,index.root/'.rag/viewer/highlights',row['content_hash'],label)
            except (OSError,RuntimeError,ValueError) as exc:
                self.reply(409,{'error':'PDF highlight preview could not be rendered','detail':str(exc)[-500:]});return
            payload=asset.read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)));self.send_header('Content-Disposition','inline; filename*=UTF-8\'\''+quote(path.stem+'-page-'+str(page)+'.html',safe=''))
            self.send_header('Content-Security-Policy',"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'self'")
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
            if not head:self.wfile.write(payload)

        def reply(self,status,data):
            payload=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers();self.wfile.write(payload)
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--model-dir',type=Path)
    sub=parser.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('--batch-size',type=int,default=32);b.add_argument('--threads',type=int,default=4)
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--mode',choices=['lexical','semantic','hybrid'],default='hybrid')
    s.add_argument('--top-k',type=int,default=5);s.add_argument('--phrase',action='store_true');s.add_argument('--json',action='store_true')
    s.add_argument('--min-cosine',type=float,default=0.25)
    for field in sorted(FILTER_KEYS):
        s.add_argument('--'+field.replace('_','-'),action='append')
    c=sub.add_parser('citation');c.add_argument('chunk_id');c.add_argument('--source')
    sub.add_parser('filters');sub.add_parser('status')
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    try:
        if args.command=='build':
            if not 1<=args.batch_size<=128 or not 1<=args.threads<=32:
                raise ValueError('batch-size must be 1-128; threads must be 1-32')
            build(args.root,args.model_dir,args.batch_size,args.threads);return
        index=SearchIndex(args.root,args.model_dir)
        try:
            if args.command=='search':
                filters={k:getattr(args,k) for k in FILTER_KEYS if getattr(args,k)}
                data=index.search(args.query,args.mode,args.top_k,filters,args.phrase,args.min_cosine)
                if args.json:
                    print(json.dumps(data,ensure_ascii=False,indent=2))
                else:
                    for i,r in enumerate(data['results'],1):
                        print(f"{i}. {r['citation']['label']}\n   {r['source_path']}\n"
                              f"   {r['excerpt'].replace(chr(10),' ')}\n   {r['citation_id']}\n")
                    print(f"{len(data['results'])} results; {data['elapsed_ms']} ms; {data['eligible_chunks']} eligible chunks")
            elif args.command=='citation':
                print(json.dumps(index.resolve(args.chunk_id,args.source),ensure_ascii=False,indent=2))
            elif args.command=='filters':
                print(json.dumps(index.filters(),ensure_ascii=False,indent=2))
            elif args.command=='status':
                index.ensure_current();print(json.dumps(index.report,ensure_ascii=False,indent=2))
            elif args.command=='serve':
                server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(index))
                print(f'Search API ready at http://127.0.0.1:{server.server_port}/api/health',flush=True)
                try: server.serve_forever()
                finally: server.server_close()
        finally:
            index.close()
    except (ValueError,RuntimeError,OSError,sqlite3.Error) as exc:
        print(f'Error: {exc}',file=sys.stderr);sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__=='__main__':
    main()
