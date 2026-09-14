"""Bounded image OCR and nested ZIP extraction. Source members are never executed."""
import argparse
import csv
import hashlib
import io
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

MAX_MEMBER = 25 * 1024 * 1024
MAX_TOTAL = 100 * 1024 * 1024
MAX_MEMBERS = 1000
MAX_DEPTH = 2


def safe_member(info):
    name = info.filename
    path = PurePosixPath(name)
    if not name or '\\' in name or any(ord(c)<32 for c in name) or ':' in name or path.is_absolute() or '..' in path.parts:
        raise ValueError('Unsafe member path')
    if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
        raise ValueError('Links and encrypted members are not supported')
    if info.file_size > MAX_MEMBER or info.file_size > max(1, info.compress_size) * 200:
        raise ValueError('Member exceeds size or compression-ratio limit')


def member_bytes(path, chain):
    """Resolve only an indexed member chain, without extracting a pathname."""
    if not isinstance(chain, list) or not 1 <= len(chain) <= MAX_DEPTH + 1:
        raise ValueError('Invalid nested member chain')
    source = path
    for member in chain:
        with zipfile.ZipFile(source) as archive:
            infos = [i for i in archive.infolist() if i.filename == member]
            if len(infos) != 1:
                raise ValueError('Missing or ambiguous member')
            safe_member(infos[0])
            with archive.open(infos[0]) as stream:
                data = stream.read(MAX_MEMBER + 1)
            if len(data) > MAX_MEMBER:
                raise ValueError('Member exceeds size limit')
        source = io.BytesIO(data)
    return data


def image_records(path, record):
    import rag_pipeline as pipeline
    from PIL import Image
    # OCR first frame only: animation is explicitly reported, never implied covered.
    with Image.open(path) as img:
        width, height = img.size
        if width * height > 40_000_000:
            raise ValueError('Image exceeds 40 million pixel OCR limit')
        frames = getattr(img, 'n_frames', 1)
        with tempfile.TemporaryDirectory(prefix='rag-ocr-') as tmp:
            png = Path(tmp)/'frame.png'
            img.convert('RGB').save(png)
            result = pipeline.command_output(['tesseract', str(png), 'stdout', '-l', 'eng', '--psm', '11', 'tsv'], timeout=90)
    if result.returncode:
        raise ValueError('Local OCR could not read this image')
    words = []
    for word in csv.DictReader(io.StringIO(result.stdout), delimiter='\t'):
        text = (word.get('text') or '').strip()
        if text:
            words.append({'text': text, 'confidence': float(word['conf']),
                          'box': [int(word[k]) for k in ('left', 'top', 'width', 'height')]})
    text = ' '.join(w['text'] for w in words)
    confidence = round(sum(w['confidence'] for w in words)/len(words), 1) if words else None
    yield pipeline.base_record(record, record_type='image_ocr', locator_type='image_asset', locator_value='frame-1',
        text=f'Image: {path.name}\nOCR (first frame, unverified): {text or "No text detected"}',
        extraction_method='tesseract-tsv-psm11', width=width, height=height, frame_count=frames,
        ocr_words=words, ocr_confidence=confidence, extraction_warning='OCR may misread equations and diagrams; inspect the original. First frame only.',
        char_start=0, char_end=len(text))


def archive_records(path, record, enable_ocr=True):
    import rag_pipeline as pipeline
    budget = {'members': 0, 'bytes': 0, 'records': 0}
    issues = []

    def walk(source, chain):
        with zipfile.ZipFile(source) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_MEMBERS:
                issues.append('Archive member-count limit exceeded: ' + ' / '.join(chain))
                return
            names = [i.filename for i in infos]
            for info in infos:
                if info.is_dir() or '__MACOSX' in PurePosixPath(info.filename).parts or Path(info.filename).name.startswith('.'):
                    continue
                members = chain + [info.filename]
                label = ' → '.join(members)
                try:
                    budget['members'] += 1
                    if budget['members'] > MAX_MEMBERS or budget['records'] >= 5000:
                        issues.append('Archive traversal/record limit reached')
                        return
                    safe_member(info)
                    if names.count(info.filename) != 1:
                        raise ValueError('Duplicate member name')
                    if budget['bytes'] + info.file_size > MAX_TOTAL:
                        raise ValueError('Total uncompressed byte limit reached')
                    route = pipeline.route_for(Path(info.filename))
                    if route not in {'archive','pdf','text','markdown','source_code','image','spreadsheet','dataset','notebook','docx','pptx'}:
                        raise ValueError('Unsupported member format')
                    with archive.open(info) as stream:
                        data = stream.read(MAX_MEMBER+1)
                    budget['bytes'] += len(data)
                    if len(data) > MAX_MEMBER:
                        raise ValueError('Member exceeds byte limit')
                    if route == 'archive':
                        if len(chain) >= MAX_DEPTH:
                            raise ValueError('Nested ZIP depth limit reached')
                        yield from walk(io.BytesIO(data), members)
                        continue
                    member_hash = hashlib.sha256(data).hexdigest()
                    with tempfile.TemporaryDirectory(prefix='rag-member-') as tmp:
                        target = Path(tmp)/Path(info.filename).name
                        target.write_bytes(data)
                        if route == 'pdf' and (pipeline.pdf_page_count(target) or 0) > 300:
                            raise ValueError('Member PDF exceeds 300 pages')
                        if route == 'image':
                            rows = image_records(target, record) if enable_ocr else pipeline.extract_image(target, record, False)
                        elif route == 'spreadsheet':
                            from rag_data import inspect_table, MAX_CELLS
                            if any((s['rows'] or 0)*(s['columns'] or 0) > MAX_CELLS for s in inspect_table(target)):
                                raise ValueError('Member workbook exceeds cell limit')
                            rows = pipeline.extract_spreadsheet(target, record)
                        else:
                            rows = pipeline.extract_records(target, {**record, 'route': route}, False)
                        for row in rows:
                            if row.get('record_type') == 'error':
                                issues.append(label + ': ' + row.get('error', 'Extraction failed'))
                                continue
                            budget['records'] += 1
                            if budget['records'] > 5000:
                                raise ValueError('Archive record limit reached')
                            locator = {'type': row['locator_type'], 'value': row['locator_value']}
                            yield {**row, 'locator_type': 'archive_member',
                                   'locator_value': f"{label} · {locator['type']} {locator['value']}",
                                   'archive_members': members, 'member_hash': member_hash, 'member_locator': locator,
                                   'text': f"Archive member: {label}\n" + row.get('text', ''),
                                   'extraction_warning': 'Nested archive content is untrusted. Verify the member and its original locator.'}
                except Exception as exc:
                    issues.append(label + ': ' + str(exc))
    try:
        yield from walk(path, [])
    except Exception as exc:
        issues.append(str(exc))
    report = 'Archive extraction limits: 25 MiB/member, 100 MiB total, 1,000 members, two nested ZIP levels, 5,000 records.\n'
    report += f"Visited {budget['members']} members; extracted {budget['records']} records.\n"
    report += '\n'.join(issues) if issues else 'No skipped/failed supported members.'
    yield pipeline.base_record(record, record_type='archive_report', locator_type='archive_member_catalog',
                               locator_value='extraction-report', text=report, extraction_method='bounded-zip',
                               extraction_issues=issues, archive_budget=budget)


def enrich():
    import rag_pipeline as pipeline
    report = []
    for record in pipeline.jsonl_read(pipeline.RAG_DIR/'manifest.jsonl'):
        if record.get('duplicate_of') or record['route'] not in ('image', 'archive'):
            continue
        if Path(record['source_path']).parts[0] not in ('Fall 2025', 'Spring 2026', 'Program-wide'):
            continue
        path = pipeline.ROOT/record['source_path']
        if pipeline.sha256_file(path) != record['content_hash']:
            raise ValueError('Manifest is stale; run inventory first')
        try:
            if record['route'] == 'image':
                rows = list(image_records(path, record))
            else:
                rows = list(pipeline.extract_archive(path, record)) + list(archive_records(path, record))
            if pipeline.sha256_file(path) != record['content_hash']:
                raise ValueError('Source changed during extraction')
            output = pipeline.EXTRACTED_DIR/f"{record['content_hash']}.jsonl"
            pending = output.with_suffix('.pending')
            pipeline.jsonl_write(pending, rows)
            pending.replace(output)
            report.append({'source_path': record['source_path'], 'records': len(rows),
                           'issues': [issue for r in rows for issue in r.get('extraction_issues', [])],
                           'ocr_confidence': rows[0].get('ocr_confidence')})
        except Exception as exc:
            report.append({'source_path': record['source_path'], 'error': str(exc)})
        print(record['source_path'], flush=True)
    pipeline.json_dump(pipeline.RAG_DIR/'rich-extraction-report.json', {'generated_at': pipeline.utc_now(), 'documents': report})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    enrich()
