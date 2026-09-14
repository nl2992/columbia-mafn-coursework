"""Stage 7: bounded, read-only structured queries with reproducible provenance.

No eval, SQL supplied by the caller, formula evaluation, or model-generated code.
The same query engine powers the UI and the replay CLI.
"""
import csv
import hashlib
import json
import math
import re
import time
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from threading import Lock
from urllib.parse import quote

EXTENSIONS = {'.csv', '.tsv', '.xlsx', '.xlsm', '.xls'}
OPERATIONS = ('preview', 'count', 'sum', 'mean', 'min', 'max', 'stddev')
MAX_ROWS = 2_000_000
MAX_CELLS = 2_000_000


def check_workbook_container(path):
    # Bound XML expansion before openpyxl reads shared strings or workbook metadata.
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 10000 or sum(i.file_size for i in members) > 256 * 1024 * 1024:
            raise ValueError('Workbook exceeds the safe XML expansion limit')
        if any(i.file_size > 64*1024*1024 or i.file_size > max(1, i.compress_size)*500 for i in members):
            raise ValueError('Workbook XML exceeds the member size or compression limit')


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def serial(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value if value is None or isinstance(value, (bool, str, int, float)) else str(value)


def number(value):
    if value is None or isinstance(value, (bool, date, datetime)):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def iso_date(value, date_format='iso'):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    if isinstance(value, str) and date_format in ('mdy', 'dmy') and re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', value):
        try:
            return datetime.strptime(value, '%m/%d/%Y' if date_format == 'mdy' else '%d/%m/%Y').isoformat()
        except ValueError:
            pass
    if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}(?:$|[ T])', value):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).isoformat()
        except ValueError:
            pass
    return None


@contextmanager
def table(path, sheet=None):
    """Yield dimensions and an iterator of (row number, raw values, cached values)."""
    ext = path.suffix.lower()
    if ext in ('.csv', '.tsv'):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream, delimiter='\t' if ext == '.tsv' else ',')
            yield {'sheet': 'Data', 'rows': None, 'columns': None}, (
                (i, row, row) for i, row in enumerate(reader, 1))
    elif ext == '.xls':
        try:
            import xlrd
        except ImportError as exc:
            raise ValueError('Legacy XLS requires xlrd. See the Stage 7 runbook; XLSX and CSV work without it.') from exc
        book = xlrd.open_workbook(str(path), on_demand=True)
        try:
            ws = book.sheet_by_name(sheet) if sheet else book.sheet_by_index(0)
            def rows():
                for i in range(ws.nrows):
                    values = [xlrd.xldate_as_datetime(c.value, book.datemode) if c.ctype == xlrd.XL_CELL_DATE
                              else c.value for c in ws.row(i)]
                    yield i+1, values, values
            yield {'sheet': ws.name, 'rows': ws.nrows, 'columns': ws.ncols}, rows()
        finally:
            book.release_resources()
    else:
        check_workbook_container(path)
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=False, keep_links=False)
        cached = None
        try:
            cached = load_workbook(path, read_only=True, data_only=True, keep_links=False)
            ws = book[sheet] if sheet else book.worksheets[0]
            if not hasattr(ws, 'iter_rows'):
                raise ValueError('Choose a worksheet, not a chart sheet')
            if (ws.max_row or 0) * (ws.max_column or 0) > MAX_CELLS:
                raise ValueError('Worksheet exceeds the 2 million cell read limit')
            yield {'sheet': ws.title, 'rows': ws.max_row, 'columns': ws.max_column}, (
                (i, list(raw), list(values)) for i, (raw, values) in enumerate(zip(
                    ws.iter_rows(values_only=True), cached[ws.title].iter_rows(values_only=True)), 1))
        finally:
            book.close()
            if cached:
                cached.close()


def inspect_table(path):
    if path.suffix.lower() in ('.csv', '.tsv'):
        return [{'name': 'Data', 'rows': None, 'columns': None}]
    if path.suffix.lower() == '.xls':
        try:
            import xlrd
        except ImportError as exc:
            raise ValueError('Install the optional xlrd reader from the Stage 7 runbook for legacy XLS') from exc
        book = xlrd.open_workbook(str(path), on_demand=True)
        try:
            return [{'name': s.name, 'rows': s.nrows, 'columns': s.ncols} for s in book.sheets()]
        finally:
            book.release_resources()
    from openpyxl import load_workbook
    check_workbook_container(path)
    book = load_workbook(path, read_only=True, keep_links=False)
    try:
        return [{'name': s.title, 'rows': s.max_row, 'columns': s.max_column} for s in book.worksheets]
    finally:
        book.close()


def execute(path, request):
    from openpyxl.utils import get_column_letter, column_index_from_string, range_boundaries
    allowed = {'path', 'sheet', 'range', 'header', 'operation', 'column', 'filter', 'include_review', 'date_format'}
    if not isinstance(request, dict) or set(request)-allowed:
        raise ValueError('Unknown structured query fields')
    op = request.get('operation', 'preview')
    if op not in OPERATIONS:
        raise ValueError('Unsupported operation')
    header = request.get('header', True)
    if type(header) is not bool:
        raise ValueError('header must be boolean')
    date_format = request.get('date_format', 'iso')
    if date_format not in ('iso', 'mdy', 'dmy'):
        raise ValueError('Choose ISO, month/day/year, or day/month/year dates')
    parse_date = lambda v: iso_date(v, date_format)
    if any(not isinstance(request.get(k, ''), str) for k in ('range','column','sheet')):
        raise ValueError('Sheet, range, and column must be strings')
    selected = request.get('range', '').upper().strip()
    if selected and not re.fullmatch(r'[A-Z]{1,3}[1-9]\d*:[A-Z]{1,3}[1-9]\d*', selected):
        raise ValueError('Use an explicit cell range such as A1:F500, or leave it blank for the full table')
    c1, r1, c2, r2 = range_boundaries(selected) if selected else (1, 1, 256, MAX_ROWS)
    if not (1 <= c1 <= c2 <= 256 and 1 <= r1 <= r2 <= MAX_ROWS):
        raise ValueError('Range exceeds bounds: 256 columns and 2 million rows')
    column = request.get('column', '').upper()
    col = column_index_from_string(column) if column else None
    if op not in ('preview', 'count') and (col is None or not c1 <= col <= c2):
        raise ValueError('Choose a numeric column inside the selected range')
    rule = request.get('filter') or {}
    if not isinstance(rule, dict) or set(rule)-{'column', 'type', 'min', 'max'}:
        raise ValueError('Invalid row filter')
    fi = column_index_from_string(rule['column'].upper()) if rule else None
    if fi and not c1 <= fi <= c2:
        raise ValueError('Filter column must be inside the selected range')
    parse = number if rule.get('type', 'number') == 'number' else parse_date
    if rule and rule.get('type', 'number') not in ('number', 'date'):
        raise ValueError('Filter type must be number or date (ISO YYYY-MM-DD)')
    lower, upper = (parse(rule.get(k)) if rule.get(k) not in (None, '') else None for k in ('min', 'max'))
    if any(rule.get(k) not in (None, '') and v is None for k, v in [('min', lower), ('max', upper)]):
        raise ValueError('Invalid filter bound; dates must use ISO format')
    if lower is not None and upper is not None and lower > upper:
        raise ValueError('Minimum must not exceed maximum')
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError('File exceeds the 128 MiB structured read limit')
    started = time.monotonic()
    schema, sample = {}, []
    matched = numeric = excluded = formulas = missing_formula_cache = scanned = 0
    total = compensation = mean = m2 = 0.0
    low = high = None
    last_row = 0
    with table(path, request.get('sheet')) as (meta, rows):
        for rn, raw, cached in rows:
            if rn > MAX_ROWS:
                raise ValueError('File exceeds the 2 million row read limit; no partial aggregate returned')
            if rn % 1000 == 0 and time.monotonic()-started > 60:
                raise ValueError('Structured read exceeded 60 seconds; choose a smaller range')
            if rn < r1:
                continue
            if rn > r2:
                break
            last_row = rn
            if not selected and len(raw) > 256:
                raise ValueError('Table exceeds 256 columns; select an explicit range')
            for ci in range(c1, min(c2, len(raw))+1):
                letter = get_column_letter(ci)
                if letter not in schema:
                    label = serial(raw[ci-1]) if header and rn == r1 else letter
                    unit = re.search(r'[\[(]([^\])]+)[\])]', str(label or ''))
                    schema[letter] = {'column': letter, 'label': label, 'unit': unit.group(1) if unit else 'unknown',
                                      'numeric': 0, 'nonempty': 0, 'date_min': None, 'date_max': None}
            cells = []
            for ci in range(c1, min(c2, len(raw))+1):
                value = cached[ci-1] if ci <= len(cached) else None
                formula = raw[ci-1] if path.suffix.lower() in ('.xlsx', '.xlsm') and isinstance(raw[ci-1], str) and raw[ci-1].startswith('=') else None
                cells.append({'cell': f'{get_column_letter(ci)}{rn}', 'value': serial(value), 'formula': formula})
                if formula:
                    formulas += 1
                    missing_formula_cache += value is None
                if header and rn == r1:
                    continue
                s = schema[get_column_letter(ci)]
                s['numeric'] += number(value) is not None
                s['nonempty'] += value not in (None, '')
                dt = parse_date(value)
                if dt:
                    s['date_min'] = min(s['date_min'] or dt, dt)
                    s['date_max'] = max(s['date_max'] or dt, dt)
            if header and rn == r1:
                continue
            scanned += 1
            if fi:
                value = parse(cached[fi-1]) if fi <= len(cached) else None
                if value is None or (lower is not None and value < lower) or (upper is not None and value > upper):
                    excluded += 1
                    continue
            matched += 1
            if len(sample) < 30:
                sample.append({'row': rn, 'cells': cells})
            value = number(cached[col-1]) if col and col <= len(cached) else None
            if value is not None:
                numeric += 1
                combined = total + value
                compensation += (total-combined)+value if abs(total)>=abs(value) else (value-combined)+total
                total = combined
                delta = value-mean
                mean += delta/numeric
                m2 += delta*(value-mean)
                low = min(low if low is not None else value, value)
                high = max(high if high is not None else value, value)
    if col and get_column_letter(col) not in schema:
        raise ValueError('Selected column does not exist in this table')
    values = {'preview': None, 'count': matched, 'sum': total+compensation if numeric else None,
              'mean': mean if numeric else None, 'min': low, 'max': high,
              'stddev': math.sqrt(max(m2, 0)/(numeric-1)) if numeric > 1 else None}
    value = values[op]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('Calculation overflow; no finite result')
    warnings = ['Units are copied only from header parentheses/brackets; otherwise unknown. No units or dates are inferred from filenames.',
                'Preview shows the first 30 matching rows. Schema/date coverage spans the selected range before row filters.',
                'Row numbers are CSV record numbers (header is record 1), or physical spreadsheet row numbers.']
    if formulas:
        warnings.append(f'{formulas} formulas found; {missing_formula_cache} have no cached value. Formulas are displayed, never executed. Cached values may be stale.')
    if path.suffix.lower() == '.xls':
        warnings.append('Legacy XLS exposes stored values, not formula text. Re-save as XLSX to inspect formulas.')
    if numeric < matched and col:
        warnings.append(f'{matched-numeric} blank, nonnumeric, non-finite, or uncached formula values excluded from the calculation.')
    if op == 'stddev':
        warnings.append('Standard deviation uses the sample definition (n−1); at least two numeric values are required.')
    return {'operation': op, 'value': value, 'sheet': meta['sheet'],
            'range': f'{get_column_letter(c1)}{r1}:{get_column_letter(max(c1, min(c2, max((column_index_from_string(k) for k in schema), default=c1))))}{last_row or r1}',
            'rows_scanned': scanned, 'rows_matched': matched, 'rows_filtered_out': excluded,
            'numeric_values': numeric, 'schema': list(schema.values()), 'preview': sample, 'warnings': warnings,
            'elapsed_ms': round((time.monotonic()-started)*1000, 1)}


class DataService:
    def __init__(self, index):
        self.index = index
        self.busy = Lock()

    def catalog(self, filters=None, source_paths=None, include_review=False):
        with self.index.request_lock:
            self.index.ensure_current()
            rows = [r for group in self.index.matching_sources(filters or {}).values() for r in group]
        return [{**r, 'operations': list(OPERATIONS)} for r in rows if Path(r['path']).suffix.lower() in EXTENSIONS
                and (include_review or r['review'] != 'review_required')
                and (source_paths is None or r['path'] in source_paths)]

    def verified(self, source, include_review=False):
        if type(include_review) is not bool:
            raise ValueError('include_review must be boolean')
        rows = self.catalog(include_review=include_review)
        row = next((r for r in rows if r['path'] == source), None)
        if row is None:
            raise ValueError('Dataset is not indexed or requires review opt-in')
        path = (self.index.root/source).resolve()
        if not path.is_relative_to(self.index.root) or not path.is_file() or digest(path) != row['content_hash']:
            raise ValueError('Source missing or changed; refresh ingestion before calculating')
        return path, row

    def describe(self, source, include_review=False):
        path, row = self.verified(source, include_review)
        sheets = inspect_table(path)
        self.verified(source, include_review)
        return {'source': row, 'sheets': sheets, 'operations': list(OPERATIONS)}

    def query(self, request):
        if not self.busy.acquire(blocking=False):
            raise ValueError('Another structured query is running; try again shortly')
        try:
            return self._query(request)
        finally:
            self.busy.release()

    def _query(self, request):
        if not isinstance(request, dict):
            raise ValueError('Query must be an object')
        path, row = self.verified(request.get('path'), request.get('include_review', False))
        result = execute(path, request)
        self.verified(row['path'], request.get('include_review', False))
        recipe = {**request, 'sheet': result['sheet'], 'range': result['range']}
        code_hash = digest(Path(__file__))
        return {**result, 'source_path': row['path'], 'source_hash': row['content_hash'],
                'created_at': datetime.now(timezone.utc).isoformat(), 'recipe': recipe,
                'engine': {'path': 'scripts/rag_data.py', 'sha256': code_hash, 'version': 1},
                'citation': {'label': f"{path.name} · {result['sheet']}!{result['range']}",
                             'source_url': '/api/source?path=' + quote(row['path'], safe='')},
                'replay': 'python3 scripts/rag_data.py --replay result.json'}


def route_question(query):
    """Conservative deterministic handoff; never guess a file, column, or unit."""
    structured = re.search(r'\b(csv|tsv|xlsx?|spreadsheet|workbook|dataset|data set|column|rows?|cells?|sheet)\b', query, re.I)
    numerical = re.search(r'\b(calculate|compute|sum|average|mean|median|standard deviation|stddev|minimum|maximum|total|how many|count)\b', query, re.I)
    lookup = re.search(r'\b(show|list|inspect|lookup|look up|filter|range|formula|schema)\b', query, re.I)
    if structured and (numerical or lookup):
        return 'computation' if numerical else 'structured_lookup'
    return 'text'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay', type=Path, required=True, help='Exported Data result JSON')
    args = parser.parse_args()
    snapshot = json.loads(args.replay.read_text())
    # Replay still enforces the active allowlist, review policy and source version.
    from rag_search import SearchIndex
    index = SearchIndex()
    try:
        service = DataService(index)
        path, row = service.verified(snapshot['source_path'], snapshot['recipe'].get('include_review', False))
        if row['content_hash'] != snapshot['source_hash'] or digest(Path(__file__)) != snapshot['engine']['sha256']:
            raise SystemExit('Source or engine version changed; cannot reproduce this snapshot exactly')
        print(json.dumps(service.query(snapshot['recipe']), indent=2, ensure_ascii=False, allow_nan=False))
    finally:
        index.close()
