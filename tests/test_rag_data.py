"""Structured retrieval correctness, bounded archive ingestion, and provenance."""
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import threading
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from rag_data import execute, inspect_table, route_question, iso_date, DataService
from rag_rich import archive_records, member_bytes, safe_member, image_records
from rag_search import source_metadata


class StructuredTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rag-data-test-')
        self.root = Path(self.tmp.name).resolve()
        self.csv = self.root/'data.csv'
        self.csv.write_text('Date,Price (USD),Volume\n2026-01-01,10,2\n2026-01-02,20,4\n2026-01-03,,6\n2026-01-04,invalid,8\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_numeric_operations_and_exact_source_rows(self):
        for op, expected in [('count',4),('sum',30),('mean',15),('min',10),('max',20)]:
            result = execute(self.csv, {'operation':op,'column':'B'})
            self.assertEqual(result['value'], expected)
            self.assertEqual(result['range'], 'A1:C5')
            self.assertEqual(result['numeric_values'], 2)
        std = execute(self.csv, {'operation':'stddev','column':'B'})
        self.assertAlmostEqual(std['value'], 50**0.5)
        self.assertEqual(std['preview'][0]['cells'][1]['cell'], 'B2')
        self.assertEqual(std['schema'][1]['unit'], 'USD')
        self.assertEqual(std['schema'][0]['date_max'], '2026-01-04T00:00:00')

    def test_filters_ranges_and_header_choice(self):
        result = execute(self.csv, {'operation':'sum','column':'C','filter':{'column':'A','type':'date','min':'2026-01-02','max':'2026-01-03'}})
        self.assertEqual(result['value'], 10)
        self.assertEqual(result['rows_matched'], 2)
        result = execute(self.csv, {'operation':'mean','column':'C','range':'B3:C4','header':False})
        self.assertEqual(result['value'], 5)
        self.assertEqual(result['range'], 'B3:C4')

    def test_date_format_must_be_explicit(self):
        self.assertIsNone(iso_date('01/03/1984'))
        self.assertEqual(iso_date('01/03/1984','mdy'), '1984-01-03T00:00:00')
        self.assertEqual(iso_date('01/03/1984','dmy'), '1984-03-01T00:00:00')

    def test_sum_retains_small_values_between_large_offsets(self):
        self.csv.write_text('value\n10000000000000000\n1\n-10000000000000000\n')
        self.assertEqual(execute(self.csv, {'operation':'sum','column':'A'})['value'],1)

    def test_formula_text_not_evaluated_and_cached_values_not_invented(self):
        from openpyxl import Workbook
        path = self.root/'book.xlsx'
        book=Workbook();sheet=book.active;sheet.title='Prices'
        sheet.append(['Value','Formula']);sheet.append([3,'=A2*2']);book.save(path);book.close()
        self.assertEqual(inspect_table(path)[0]['name'], 'Prices')
        result = execute(path, {'operation':'sum','column':'B','sheet':'Prices'})
        self.assertIsNone(result['value'])
        self.assertEqual(result['preview'][0]['cells'][1]['formula'], '=A2*2')
        self.assertTrue(any('no cached value' in w for w in result['warnings']))

    def test_rejects_code_invalid_ranges_and_unknown_fields(self):
        for req in [{'operation':'eval'}, {'code':'open("secret")'}, {'range':'A1:C999999999'},
                    {'range':'C3:A1'}, {'column':'Z','operation':'sum'}, {'header':'false'},
                    {'filter':{'column':'A','type':'date','min':'bad'}}, {'filter':{'column':'B','min':10,'max':2}}]:
            with self.subTest(req=req), self.assertRaises(ValueError):
                execute(self.csv, req)

    def test_router_is_explicit_and_does_not_guess_columns(self):
        self.assertEqual(route_question('Calculate average Volume in the CSV'), 'computation')
        self.assertEqual(route_question('Show the formulas in this workbook'), 'structured_lookup')
        self.assertEqual(route_question('Explain the mean reversion model'), 'text')
        self.assertEqual(route_question('What is option gamma?'), 'text')

    def service(self, review='not_reviewed'):
        row={'path':self.csv.name,'content_hash':hashlib.sha256(self.csv.read_bytes()).hexdigest(),'review':review}
        index=SimpleNamespace(root=self.root,request_lock=threading.RLock(),ensure_current=lambda:None,
                              matching_sources=lambda filters:{'document':[row]})
        return DataService(index)

    def test_service_blocks_unindexed_changed_sources_and_review_bypass(self):
        service=self.service()
        with self.assertRaises(ValueError): service.query({'path':'../secret.csv'})
        self.csv.write_text('Changed source')
        with self.assertRaises(ValueError): service.query({'path':self.csv.name})
        with self.assertRaises(ValueError): self.service('review_required').describe(self.csv.name)
        with self.assertRaises(ValueError): self.service().verified(self.csv.name,'true')

    def test_source_changed_mid_calculation_is_not_returned(self):
        service=self.service()
        def mutate(path, request):
            path.write_text('Changed during read');return {}
        with patch('rag_data.execute',side_effect=mutate), self.assertRaises(ValueError):
            service.query({'path':self.csv.name})

    def test_result_preserves_source_recipe_and_engine_version(self):
        result=self.service().query({'path':self.csv.name,'operation':'sum','column':'B'})
        self.assertEqual(result['recipe']['range'],'A1:C5')
        self.assertEqual(result['value'],30)
        self.assertEqual(result['source_hash'],hashlib.sha256(self.csv.read_bytes()).hexdigest())
        self.assertEqual(len(result['engine']['sha256']),64)

    def test_concurrent_read_rejected_without_starting_second_scan(self):
        service=self.service();service.busy.acquire()
        try:
            with self.assertRaises(ValueError):service.query({'path':self.csv.name})
        finally:service.busy.release()


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='rag-rich-test-');self.root=Path(self.tmp.name)
        self.path=self.root/'sample.zip'

    def tearDown(self):
        self.tmp.cleanup()

    def record(self):
        fingerprint=hashlib.sha256(self.path.read_bytes()).hexdigest()
        return {'document_id':fingerprint,'content_hash':fingerprint,'source_path':'Spring 2026/Course/data/sample.zip','route':'archive'}

    def test_nested_text_has_member_hash_and_original_line_locator(self):
        nested=io.BytesIO()
        with zipfile.ZipFile(nested,'w') as archive:
            archive.writestr('notes.txt','Gamma is curvature.\nSecond source line.')
        with zipfile.ZipFile(self.path,'w') as archive:
            archive.writestr('folder/inner.zip',nested.getvalue())
        rows=list(archive_records(self.path,self.record(),False))
        hit=next(r for r in rows if r['locator_type']=='archive_member')
        self.assertEqual(hit['archive_members'], ['folder/inner.zip','notes.txt'])
        self.assertEqual(hit['member_locator']['type'],'line_range')
        payload=member_bytes(self.path,hit['archive_members'])
        self.assertEqual(hashlib.sha256(payload).hexdigest(),hit['member_hash'])
        self.assertEqual(source_metadata(self.record())['review'],'review_required')

    def test_archive_never_writes_traversal_symlinks_or_duplicate_paths(self):
        link=zipfile.ZipInfo('link.txt');link.external_attr=(stat.S_IFLNK|0o777)<<16
        with zipfile.ZipFile(self.path,'w') as archive:
            archive.writestr('../escape.txt','do not write')
            archive.writestr(link,'/etc/passwd')
            archive.writestr('safe.txt','inspectable source text')
        rows=list(archive_records(self.path,self.record(),False))
        self.assertFalse((self.root.parent/'escape.txt').exists())
        members=[r for r in rows if r['locator_type']=='archive_member']
        self.assertEqual(len(members),1)
        self.assertEqual(len(rows[-1]['extraction_issues']),2)
        with self.assertRaises(ValueError):member_bytes(self.path,['../escape.txt'])

    def test_size_and_compression_bomb_limits(self):
        huge=zipfile.ZipInfo('huge.txt');huge.file_size=30*1024*1024;huge.compress_size=100
        with self.assertRaises(ValueError):safe_member(huge)
        bomb=zipfile.ZipInfo('bomb.txt');bomb.file_size=100000; bomb.compress_size=1
        with self.assertRaises(ValueError):safe_member(bomb)

    def test_ocr_preserves_word_boxes_confidence_and_first_frame_warning(self):
        from PIL import Image
        from types import SimpleNamespace
        image=self.root/'label.png';Image.new('RGB',(200,100),'white').save(image)
        record={'document_id':'image','content_hash':'hash','source_path':'label.png'}
        output='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t10\t20\t50\t12\t92\tGamma\n'
        with patch('rag_pipeline.command_output',return_value=SimpleNamespace(returncode=0,stdout=output)):
            row=list(image_records(image,record))[0]
        self.assertIn('Gamma',row['text'])
        self.assertEqual(row['ocr_words'][0]['box'],[10,20,50,12])
        self.assertEqual(row['ocr_confidence'],92)
        self.assertIn('First frame',row['extraction_warning'])


if __name__ == '__main__':
    unittest.main()
