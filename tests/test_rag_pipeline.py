import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rag_pipeline as pipeline


def manifest(route, suffix=".pdf"):
    return {
        "document_id": "sha256:test",
        "content_hash": "test",
        "source_path": "Fall 2025/Test/source" + suffix,
        "source_paths": ["Fall 2025/Test/source" + suffix],
        "course": "Test",
        "term": "Fall 2025",
        "content_role": "lectures",
        "access_review": "not_reviewed",
        "route": route,
    }


class PipelineExtractionTests(unittest.TestCase):
    def test_image_only_pdf_ocr_is_parallel_but_records_stay_ordered(self):
        with tempfile.TemporaryDirectory() as name:
            old_rag = pipeline.RAG_DIR
            pipeline.RAG_DIR = Path(name)
            try:
                with patch.object(pipeline, "pdf_page_count", return_value=3), patch.object(
                    pipeline,
                    "command_output",
                    return_value=SimpleNamespace(returncode=0, stdout="\f\f\f", stderr=""),
                ), patch.object(
                    pipeline, "ocr_pdf_page", side_effect=lambda path, page, cache: f"OCR page {page}"
                ):
                    rows = list(pipeline.extract_pdf(Path("scan.pdf"), manifest("pdf"), True))
            finally:
                pipeline.RAG_DIR = old_rag
        self.assertEqual([row["page_number"] for row in rows], [1, 2, 3])
        self.assertEqual([row["text"] for row in rows], ["OCR page 1", "OCR page 2", "OCR page 3"])
        self.assertTrue(all(row["extraction_method"] == "tesseract" for row in rows))

    def test_legacy_doc_uses_converted_docx(self):
        expected = {"record_type": "text", "text": "legacy body"}
        with patch.object(pipeline, "converted_office_path", return_value=Path("converted.docx")), patch.object(
            pipeline, "extract_docx", return_value=iter([expected])
        ) as extractor:
            rows = list(pipeline.extract_legacy_document(Path("legacy.doc"), manifest("legacy_document", ".doc")))
        self.assertEqual(rows, [expected])
        extractor.assert_called_once()

    def test_visual_only_pdf_gets_an_explicit_catalog_record(self):
        with tempfile.TemporaryDirectory() as name:
            old_rag = pipeline.RAG_DIR
            pipeline.RAG_DIR = Path(name)
            try:
                with patch.object(pipeline, "pdf_page_count", return_value=1), patch.object(
                    pipeline,
                    "command_output",
                    return_value=SimpleNamespace(returncode=0, stdout="\f", stderr=""),
                ), patch.object(pipeline, "ocr_pdf_page", return_value=""):
                    row = list(pipeline.extract_pdf(Path("chart.pdf"), manifest("pdf"), True))[0]
            finally:
                pipeline.RAG_DIR = old_rag
        self.assertEqual(row["extraction_method"], "pdf-visual-catalog")
        self.assertIn("No OCR-readable text", row["text"])

    def test_c_files_are_source_code(self):
        self.assertEqual(pipeline.route_for(Path("model.c")), "source_code")


if __name__ == "__main__":
    unittest.main()
