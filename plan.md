# Course Archive RAG — Build Plan

## Objective

Build a local, source-grounded research assistant for the Columbia MAFN coursework archive at `/Users/nigelli/Desktop/Canvas Files`.

The assistant must do more than return an answer. Every retrieved claim must remain traceable to the original material, and the user must be able to click a citation and see the exact source location in an integrated viewer:

- PDF: exact page
- PowerPoint: exact slide
- Word/Markdown/text/code: section or line range
- Spreadsheet: workbook, sheet, and cell/range
- Image: image asset plus OCR/caption region where available

The original archive remains authoritative and unchanged. The RAG index is a derived, rebuildable layer.

## Product direction

The Product Library at `/Users/nigelli/Desktop/Desk Work/Product Library/index.html` is being used as a reference for interaction patterns only. The useful patterns to carry into this product are:

- Persistent left-side navigation for major work areas
- Global search plus structured filters
- Saved views for repeatable research slices
- A detail drawer that combines metadata, evidence, and the source viewer
- Clickable citation chips that open the source at the cited location
- Evidence snippets shown next to the source reference
- Explicit flags and review queues for low-confidence extraction
- Scoped copilot questions, including current filters and selected sources
- Progress reporting for ingestion jobs

The domain model will remain course/archive-focused rather than product-library-focused.

## Visual direction — Columbia-oriented theme

The application should feel like a Columbia University academic research tool: calm, precise, editorial, and blue-led. The Product Library's HSBC red palette is reference-only and should not be carried into the RAG interface.

Use an initial Columbia-oriented token set, subject to a final brand review before public distribution:

```css
:root {
  --columbia-blue: #B9D9EB;
  --columbia-dark-blue: #071747;
  --ink: #0C173D;
  --muted: #5F6C83;
  --line: #D9E2EF;
  --surface: #FFFFFF;
  --canvas: #F5F8FC;
  --nav: #071747;
  --success: #087443;
  --warning: #9A6700;
  --danger: #B42318;
}
```

Theme rules:

- Use dark Columbia blue for navigation, headings, primary text, and active controls.
- Use Columbia blue for selected rows, filter context, soft banners, chart fills, and viewer framing.
- Use white surfaces with cool blue-gray borders instead of heavy shadows.
- Reserve red for errors, destructive actions, and high-priority alerts; it must not be the brand color.
- Keep charts within a blue-forward palette with accessible contrast and a secondary neutral scale.
- Use the supplied local `viewer/maf-logo.png` lockup for the Columbia University Mathematics of Finance MA Program identity; do not invent or download official marks as part of the RAG build.
- Preserve keyboard focus rings, readable contrast, and non-color indicators for flags and status.

The supplied lockup is the visual source of truth for the final theme: deep navy anchors navigation and editorial headings, white supports the logo and reading surfaces, and Columbia light blue is reserved for active controls, selection, evidence highlights, and citation chips. The asset is served locally with the viewer and is not fetched from the network.

The viewer should use the same system: a dark-blue drawer header, light-blue citation chips, a white document page, and a cool gray-blue viewer stage. Citation chips must remain visually distinct from warning and error states.

## Core user journeys

1. Ask a conceptual question across one or more courses.
2. Find an exact term, equation, person, ticker, or filename.
3. Filter research to a course, semester, folder type, lecturer, or file type.
4. Open a result and inspect the precise page, slide, sheet, or line cited.
5. Compare multiple sources or versions without losing provenance.
6. Review extraction failures and low-confidence OCR manually.
7. Re-ingest only new or changed files after the archive changes.

## Source and citation contract

Every chunk stored in the index must carry a stable provenance record:

```json
{
  "document_id": "sha256-or-stable-id",
  "source_path": "Fall 2025/MATHGR5010 - Intro to the Math of Finance/lectures/GR5010_Handout8Greeks2025.pdf",
  "artifact_version": "content-hash",
  "locator_type": "pdf_page",
  "locator_value": "14",
  "section_title": "Gamma",
  "char_start": 12040,
  "char_end": 13210,
  "text": "...",
  "extraction_method": "pdf-text"
}
```

The answer layer must cite these records directly. It must not generate page numbers after the answer is written or cite only a filename when a precise locator is available.

## Staged implementation

### Stage 0 — Product contract and guardrails

Define the supported question types, answer style, citation format, privacy/rights rules, and assessment/solution handling. Establish the acceptance test: a user can ask a question, click a citation, and land on the exact source location.

Deliverables:

- This plan
- Living status file
- Initial acceptance-question set
- Source handling and access policy

Exit criteria: the team agrees that page/slide/range-level provenance is a first-class requirement.

### Stage 1 — Inventory and manifest

Perform a read-only scan of the archive. Classify files by term, course, folder role, extension, and likely content type. Record file size, timestamps, SHA-256, duplicate relationships, and extraction status. Exclude `.git` from ingestion while preserving source paths relative to the repo root.

Important classifications include `lecture`, `reading`, `reference`, `assignment`, `assessment`, `solution`, `code`, `data`, `workbook`, `session`, and `program-wide`.

Deliverables:

```text
.rag/manifest.jsonl
.rag/inventory-report.json
.rag/review-queue.jsonl
```

Exit criteria: every supported file has one manifest record and every unsupported or ambiguous file is explicitly accounted for.

### Stage 2 — Extraction with location preservation

Build format-specific extractors that emit text plus location metadata.

- PDF: page-aware extraction, with OCR fallback for scanned pages
- PPT/PPTX: slide text, notes, and slide number
- DOC/DOCX: headings, paragraphs, tables, and page estimate where reliable
- Markdown/TXT: headings and line ranges
- IPYNB: cell type, execution order, and cell number
- Python/MATLAB/TeX: code blocks and line ranges
- XLS/XLSX/CSV/TSV: workbook/sheet/table/range metadata and compact textual summaries
- Images/GIFs: OCR and visual description, linked to the original asset
- ZIP: inventory first, then selectively extract supported contents

PDFs and rendered slide previews must retain page/slide identifiers through every later transformation.

Deliverables:

```text
.rag/extracted/<document-id>.jsonl
.rag/extraction-report.json
.rag/ocr-cache/
```

Exit criteria: a sample from every supported format produces readable content and a valid source locator.

### Stage 3 — Canonical schema, deduplication, and chunking

Normalize all extracted records into documents, sections, locators, and chunks. Use parent-child relationships so a search hit can display a focused passage while the UI can expand to the surrounding section or page.

Rules:

- Keep source text lossless where possible; normalize only repeated headers, footers, and extraction noise.
- Preserve equations, symbols, tables, code, and list structure.
- Use moderate chunks, approximately 600–900 tokens, with controlled overlap.
- Keep version variants separate while linking them as related artifacts.
- Do not embed every row of large market datasets; create a dataset catalog and structured-query path instead.

Deliverable:

```text
.rag/chunks.jsonl
.rag/normalization-report.json
```

Exit criteria: each chunk can be mapped back to an exact source artifact and locator without ambiguity.

### Stage 4 — Search and retrieval MVP

Implemented and validated against the local archive. The service provides:

- Full-text search for exact phrases, equations, names, tickers, and filenames
- Dense vector search for conceptual similarity
- Hybrid score fusion
- Metadata filters for course, term, content type, lecturer, and folder
- Duplicate/version awareness
- A CLI and loopback JSON API returning chunks, scores, metadata, and citations

Implementation choices:

- SQLite FTS5/BM25 for words, names, filenames, and search-normalized mathematical symbols. `--phrase` adds a strict literal-substring constraint; equations with broken extraction still require source inspection.
- Local `all-MiniLM-L6-v2` embeddings using cached quantized ONNX weights and the official tokenizer. No API key, hosted inference, runtime download, or document upload.
- 384-dimensional vectors in NumPy files; exact cosine search is adequate at this archive size. Each chunk is covered by overlapping 224-token windows with 192-token stride, avoiding silent truncation of long evidence.
- Reciprocal-rank fusion of lexical and semantic candidates. Scores express ranking, not answer confidence; the default cosine cutoff of 0.25 is an uncalibrated noise floor, not an abstention guarantee.
- Course, term, content-type, lecturer, folder, file-type, and review filters are applied before candidate limits. Repeated values are ORed; different fields are ANDed on the same source alias. Lecturer metadata currently comes only from named seminar folders.
- Byte-identical files share chunks while retaining per-path course metadata. Explicit `[Ver N]` siblings are linked but not collapsed or presumed to be the newest authoritative version.
- Index only the course and program-wide roots; exclude application plans, status, scripts, and other internal files from retrieval. Assessment and solution files remain searchable but labeled for review; this is metadata, not an access-control system.
- Atomic generation publication, input/source hash checks, and a content-addressed embedding cache. Rebuild after ingestion changes; restart a running API to load the new generation. No automatic watcher yet.

Deliverables:

```text
scripts/rag_embeddings.py
scripts/rag_search.py
scripts/evaluate_rag_search.py
tests/test_rag_search.py
rag/evaluation.jsonl
rag/requirements-search.txt
.rag/search/CURRENT.json
.rag/search/generations/<id>/index.sqlite
.rag/search/generations/<id>/vectors.npy
.rag/search/generations/<id>/owners.npy
.rag/search/generations/<id>/windows.npy
.rag/search/generations/<id>/build-report.json
.rag/search/embedding-cache.sqlite
.rag/search-evaluation.json
```

Example response shape:

```json
{
  "text": "...",
  "score": 0.031,
  "source_path": "...",
  "locator": { "type": "pdf_page", "value": 14 },
  "citation_id": "stored-chunk-id",
  "provenance": { "...": "original Stage 3 record, unchanged" }
}
```

Exit criteria: representative questions return relevant passages with correct locators before any answer generation is added.

Validation: 12 integration tests pass. The curated 16-query development set has 14 top-five hits and zero provenance/hash/filter errors across 68 returned citations. Two retained failures are a broad measure-change paraphrase and missing risk-course lecture text. This is an initial smoke set, not a held-out relevance benchmark. The current index contains 20,007 chunks from 507 documents; 123 source paths have no chunks (103 PDF, 16 XLS, two DOC, two C). Image/archive hits are catalogs, not visual understanding or nested-file extraction. See `status.md` for the living results and `rag/README.md` for commands.

### Stage 5 — Source viewer and citation-first interface — COMPLETE

Implemented as a local same-origin viewer on 2026-09-12. The key interaction is:

```text
Search or ask → result/citation chip → detail drawer → exact page/slide/range
```

Completion record — 2026-09-12:

- [x] Columbia-blue Product Library-inspired navigation, search, filters, coverage, and review views
- [x] Citation drawer with evidence, duplicate aliases, version context, review state, and live hash verification
- [x] Exact PDF physical-page viewer with page navigation and Poppler-derived text-coordinate overlays
- [x] On-demand PowerPoint preview with exact slide navigation and verified original-deck link
- [x] Focused evidence panes for spreadsheet ranges, datasets, notebooks, DOCX blocks, and code/text ranges
- [x] Stable deep links, safe localhost source delivery, fallbacks, and browser acceptance checks
- [x] Supplied Columbia University Mathematics of Finance MA Program logo integrated into the sidebar, with its navy/white/light-blue palette applied throughout
- [ ] Broader coordinate mapping for non-PDF formats remains optional follow-up work

Viewer requirements:

- Detail drawer with title, course, term, file type, folder role, and evidence snippets
- PDF.js-style inline PDF rendering with page input, page count, previous/next, zoom, fit-width, and open-in-new-tab
- Citation chips labeled with the source and locator, such as `Handout8 · p. 14`
- Clicking a citation opens the drawer directly at the cited page
- A visible “cited by” or “evidence” section beside the viewer
- Search-hit highlighting or at least a focused text excerpt for the cited passage
- Slide-aware preview for PPTX, preferably generated slide images; fallback must still show the exact slide number and open the original deck
- Sheet/range locator for spreadsheets and line-range locator for code
- Stable deep links so a source location can be copied and reopened
- Graceful fallback when inline preview is unavailable
- Resolve the returned citation URL, preserving the selected duplicate source alias; verify `source_states` before opening the original. Show changed/missing-file warnings instead of silently displaying a different version.
- Use the stored physical PDF page index, which can differ from the printed page number. Do not treat DOCX block numbers as pages or spreadsheet ranges as PDF pages.
- Show extraction coverage and separate total versus searchable document counts in filters. Keep assessments/solutions and explicit version variants visibly labeled.
- Start with focused evidence excerpts. For text-bearing PDFs, add a separately generated coordinate overlay from the rendered page and Poppler word/line boxes; do not treat upstream character offsets as coordinates. Scanned or malformed PDFs and non-PDF formats must retain a graceful evidence-first fallback.

Implementation choices:

- Plain HTML/CSS/JavaScript served by the existing loopback service, with no frontend build step or external asset dependency.
- Product Library-inspired persistent navigation, search/filter bar, results list, evidence drawer, coverage view, and review view, restyled in the Columbia-oriented blue system.
- Search result selection first resolves `/api/chunks/<id>?source=<path>` and checks the live artifact hash. Changed or missing files pause opening and display a warning.
- PDF citations open the exact physical page in a same-origin browser PDF frame, with previous/next/page controls and open-in-new-tab. A PDF's physical page index is labeled explicitly because it can differ from printed numbering.
- Text/code line ranges load the verified source into a readable text pane. Images open inline. PPTX citations render on demand through a local, hash-keyed PDF preview while preserving the verified original deck link. PDF citations additionally open a hash-keyed page image with Poppler text-coordinate overlays when the page exposes text. Spreadsheet ranges, notebooks, DOCX blocks, and datasets use a focused extracted-evidence pane labeled with the exact locator; archives and other binary types retain a verified-original fallback.
- Duplicate aliases and related versions remain selectable in the evidence drawer. Citation deep links persist the query, filters, chunk ID, and selected source path in the URL.
- The server exposes only known viewer assets and indexed, hash-verified source paths. It supports byte ranges for browser PDF loading, rejects traversal/unindexed paths, and binds to localhost.

Stage 5 verification: viewer delivery and protection checks remain covered by the current integration suite (22 tests). The browser acceptance run passed across PDF page, PPTX slide, line-range, and dataset citations; PDF page overlays are rendered from Poppler coordinates, and a real PowerPoint citation opened at slide 2 in a 22-slide preview with the source state current. PPTX previews and PDF page overlays are rendered on demand and cached by source hash. Full visual rendering remains browser-dependent.

Exit criteria: a test user can verify five citations visually without manually searching the original file. The current build meets the navigation, evidence, deep-link, hash-check, PDF page-jump, PDF text-coordinate overlay, and PPTX slide-preview portions; broader per-format pixel mapping remains explicitly open.

### Stage 6 — Grounded copilot — COMPLETE

Completed on 2026-09-12. The initial extractive digest has been extended to local model synthesis, conversations, document pins, claim checks, and conflict presentation. The selected implementation is Qwen3 4B through Ollama on this Mac; model weights are stored in `.rag/models/ollama/` and cloud inference is disabled in the supplied launcher.

Completion record — 2026-09-12:

- [x] Copilot view with Columbia-blue styling, privacy copy, scope display, and prompt chips
- [x] Questions run against the active local index using the current course, term, material, lecturer, file-type, and review filters
- [x] `POST /api/ask` for bounded question/context requests; legacy GET remains an evidence-excerpt endpoint
- [x] Local model explanations with inline citations for each accepted claim, plus a separate retrieved-evidence section
- [x] Review gate: `review_required` material is excluded by default, with an explicit opt-in for solutions and assessments
- [x] Abstention when retrieval is empty or no generated claims pass validation; model unavailability is shown separately
- [x] Citation chips that return to the Stage 5 evidence drawer and exact source locator
- [x] Regression coverage for grounding, review exclusion/opt-in, abstention, HTTP delivery, and viewer wiring
- [x] Follow-up questions using bounded earlier-question context; New chat clears conversation state
- [x] Pin up to 12 documents from results, retrieved evidence, or the source drawer; intersect pins with filters before ranking
- [x] Exact quotation checks followed by a separate local model support/relevance check; unsupported or uncertain claims are omitted
- [x] Common instruction-override patterns excluded from answer evidence; retrieved text is treated as data
- [x] Conflicting statements require support from two distinct documents and a model support check; both citations stay visible
- [x] Version labels and course terms remain visible; dates must be supported in source quotations, and no version is automatically authoritative
- [x] Changed/missing source checks before synthesis and again before returning an answer
- [x] Local runtime launcher, model availability status, request limits, concurrent source access, and development evaluation

Implementation choices:

- The default answer style uses provider `local-ollama`, model `qwen3:4b` (Q4_K_M, ~2.5 GB). Evidence excerpts remain selectable and work without the answer model.
- Synthesis receives at most eight retrieved excerpts of up to 2,300 characters, their citation metadata, and the question. It has no tools or filesystem access.
- Each generated claim supplies a known evidence ID and exact supporting quotation. Only claims that pass quotation matching and a separate model support/relevance check are displayed. Support is categorical, not a calibrated confidence score; the model can still make mistakes.
- Conversation state remains in the browser tab (up to 20 visible turns); at most six prior questions can contribute to a follow-up. Prior answers and evidence are never trusted as new source material. A changed scope or review policy stops reuse of earlier context. Reloading clears chat and pins.
- Conflict handling presents supported disagreements rather than resolving authority automatically. Publication dates are not inferred from course terms. Missing or garbled extraction can still limit comparisons.
- The default safety posture excludes solution and assessment material marked `review_required`. Opt-in is visible and produces a warning; the metadata label is not an access-control boundary.
- Citation records preserve the selected source alias, locator, artifact version, and live source verification already implemented in Stage 5.
- The service and model bind to loopback. The adapter disables proxies and redirects and uses an installed local model; the launcher disables Ollama cloud features. No inference content is uploaded.

Deliverables: `scripts/rag_copilot.py`, `scripts/run_rag.py`, `scripts/evaluate_rag_copilot.py`, the expanded viewer and integration suite, and `.rag/copilot-evaluation.json`.

Verification: 22 integration tests and 8/8 live-model development checks, plus browser checks for follow-ups, pinning, New chat, and citation navigation. The initial failed instruction-override case is retained in the evaluation history; see `status.md` for results and limits.

Exit criteria: a user can ask and follow up across the archive or pinned documents, inspect each answer's supporting quotations, click citations into the original source viewer, and see explicit abstention or conflict states. These behaviors are implemented and covered by regression and browser checks. Small-model reliability, broader injection resistance, and held-out evaluation remain continuing quality work in Stage 8, not guarantees of this release.

### Stage 7 — Structured, visual, and computational retrieval

Extend beyond text:

- Spreadsheet-aware queries over sheets, tables, formulas, and ranges
- Dataset catalog with schema, date coverage, units, and available structured operations
- Optional Python execution for approved numerical questions, with generated outputs linked to the input dataset and code
- OCR/caption search for images and diagrams
- Archive contents and nested files

Exit criteria: the assistant can identify when a question requires text retrieval, structured lookup, or computation and routes it appropriately.

### Stage 8 — Evaluation, refresh, and operations

Create a regression suite across all courses and content types. Track retrieval recall, citation precision, answer correctness, abstention quality, latency, extraction failures, and index size.

Add:

- Hash-based incremental ingestion
- New/changed/deleted-file detection
- Retryable ingestion jobs and progress states
- Review queue for low-confidence OCR/extraction
- Saved views and reusable filters
- Audit log for index rebuilds and source changes
- Backup/rebuild instructions

Exit criteria: a changed source file can be re-indexed without duplicating unchanged content, and evaluation results remain stable across releases.

## Proposed application areas

The first UI can mirror the Product Library’s information architecture while adapting labels to the archive:

- Archive: searchable source table
- Ingest: file inventory, extraction jobs, and failures
- Review: low-confidence and unsupported files
- Map: course/content/date breakdowns and coverage visuals
- Copilot: scoped, citation-grounded questions

The detail drawer is the main unit of interaction: metadata and evidence on one side, the exact source viewer on the other.

## Definition of done for the first release

The first release is complete when it can:

1. Ingest the text-rich archive formats.
2. Answer representative cross-course questions.
3. Return exact page/slide/line citations.
4. Open each citation in the viewer at the correct location.
5. Show the evidence snippet beside the source.
6. Filter by course, term, and material type.
7. Re-index changed files incrementally.
8. Clearly report when evidence is missing or extraction failed.

## Immediate next step

Stage 6 is complete with local model synthesis, conversations, pinned documents, support checks, and source citations. Continue to Stage 7 for spreadsheet/data questions and visual extraction. Keep numerical calculations tied to a structured query or computation path; the text copilot must not imply access to unindexed dataset rows.

Track a parallel ingestion-quality follow-up: prioritize the 103 PDFs without chunks, especially MATHGR5320 (only two of 39 documents currently searchable), repair legacy XLS/DOC and C-file handling, then rebuild the index and rerun the retained coverage test. Stronger semantic retrieval/reranking remains an evaluation-led follow-up; do not hide the existing paraphrase failure.
