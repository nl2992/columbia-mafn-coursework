# Course Archive RAG — Status

Last updated: 2026-09-12

## Current state

Stages 4–6 are complete for the local release: hybrid retrieval, the source viewer, and a Copilot with local model explanations, conversations, pinned documents, and checked citations. Stages 1–3 have produced an ingestion baseline, with incomplete extraction coverage explicitly tracked below. Stage 6 uses Qwen3 4B through Ollama on this Mac.

Archive root: `/Users/nigelli/Desktop/Canvas Files`. Original course files remain unchanged. Derived artifacts live under the Git-ignored `.rag/` directory. No source content has been uploaded for indexing or inference.

## Stage tracker

| Stage | State | Evidence / remaining work |
| --- | --- | --- |
| 0 — Product contract | Local policy implemented | Exact-location citations, local inference, and default exclusion of review-marked material with per-question opt-in. |
| 1 — Inventory | Baseline complete | 642 snapshot paths, 636 unique contents, six duplicate groups, 170 review items. |
| 2 — Extraction | Baseline complete; coverage partial | OCR not run; blank/unsupported records are not successful text extraction. |
| 3 — Normalization | Baseline complete | 20,028 chunks with provenance, including 21 internal chunks excluded by Stage 4. |
| 4 — Retrieval | MVP complete | Lexical, semantic, hybrid, filters, citation lookup, CLI/API, regression tests. |
| 5 — Source viewer | MVP complete; browser acceptance passed | Columbia-blue UI, evidence drawer, deep links, verified source delivery, PDF page jumps with text-coordinate overlays, on-demand PPTX previews, and evidence-first fallbacks for other formats. |
| 6 — Grounded copilot | Complete | Local model synthesis, follow-ups/reset, pinned scope, exact quotations, model support checks, abstention, conflict presentation, and clickable citations. |
| 7–8 — Rich data and operations | Planned | Structured queries, visual extraction, refresh automation, broader evaluation. |

## Stage 4 delivered

- `scripts/rag_search.py`: build, search, citation, filters, status, and serve commands.
- SQLite FTS5/BM25 lexical search and offline MiniLM semantic search with reciprocal-rank fusion.
- Official model tokenizer, 384-dimensional normalized embeddings, and overlapping token windows covering long chunks.
- Filters for course, term, content type, lecturer, folder, extension, and review status. Duplicate aliases retain their own course/term context.
- Stable stored citation IDs; original chunk records preserved under `provenance`. Citation lookup returns current/changed/missing source-file states.
- Exact duplicate awareness and explicit version-family links; no automatic authoritative-version selection.
- Atomic index generations, embedding reuse, source/input hash checks, and stale-ingestion rejection.
- A localhost-only JSON API with Host/Origin checks and no query-URL logging. It is a local development service, not a multi-user authenticated deployment.
- Test fixtures and a reproducible real-archive evaluation set. Commands and API details are in `rag/README.md`.

## Stage 5 delivered

Stage 5 completion record — 2026-09-12: the current viewer scope is complete. The optional remaining enhancement is broader coordinate mapping for non-PDF formats.

- `viewer/index.html`, `viewer/styles.css`, and `viewer/app.js`: responsive local source library with persistent navigation for Search archive, Coverage, and Review queue.
- Product Library-inspired results, filters, citation chips, evidence drawer, source aliases, related versions, review flags, and coverage counts, restyled in the Columbia-oriented blue palette.
- Supplied `viewer/maf-logo.png` integrated as the Columbia University Mathematics of Finance MA Program sidebar lockup; the final theme uses the logo's deep navy, white, and light-blue treatment.
- PDF page viewer using the stored physical `pdf_page` locator; page input, previous/next controls, fit-width browser view, on-demand Poppler text-coordinate overlays, and open-in-new-tab.
- Text/code line-range viewer and image viewer; on-demand, hash-keyed PPTX-to-PDF slide previews; focused extracted-evidence panes for spreadsheet ranges, datasets, notebooks, and DOCX blocks; and evidence-first fallbacks for archives and other binary sources.
- `/api/source?path=...`: indexed-path-only, live-hash-verified, byte-range-capable source delivery. Viewer assets are allowlisted and served same-origin. No arbitrary file endpoint was added.
- `/api/preview?path=...`: verified PPTX/PPT conversion through the local LibreOffice runtime, cached under `.rag/viewer/previews/` by source hash, then served as a same-origin PDF with slide-count metadata.
- `/api/highlight?chunk=...&source=...`: verified PDF citation preview that renders the cited physical page and overlays Poppler text-coordinate boxes, cached under `.rag/viewer/highlights/` by source hash and page.
- Deep links retain query/filter context and the selected chunk/source alias. Citation resolution occurs before opening and surfaces changed/missing states.

## Stage 6 delivered

Stage 6 completion record — 2026-09-12: the remaining Stage 6 features are implemented after the initial evidence-digest slice.

- [x] Local cited explanations: Ollama 0.33.3 with `qwen3:4b`, model digest `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`. Downloaded weights occupy approximately 2.5 GB under `.rag/models/ollama/`.
- [x] `scripts/rag_copilot.py`: bounded source context, exact quotation validation, separate model support/relevance check, abstention, and explicit local-model failure states. Generated claims that fail checks are withheld.
- [x] `POST /api/ask`: up to 40 KB of JSON with query, filters, pins, answer style, and at most six earlier questions. GET remains available for evidence excerpts. Host/Origin and content-type checks apply.
- [x] Conversation UI: follow-ups, 20-turn display cap, New chat, visible scope per turn, and no persisted chat. Scope/review changes stop reuse of earlier question context; reloading clears chat and pins.
- [x] Document pins: up to 12 exact indexed paths from search, retrieved evidence, or the drawer; pins and metadata filters are applied together before ranking and preserve duplicate aliases.
- [x] Every accepted answer claim has clickable citations and expandable supporting quotations. The full retrieved matches are shown separately with source terms and version labels.
- [x] Conflict cards require supported opposing claims from two distinct source documents. No automatic authority selection; course terms are not treated as publication dates.
- [x] Default review exclusion cannot be bypassed by empty/case-varied filters; review material requires explicit opt-in. Sources are checked for changed/missing bytes before synthesis and again before delivery.
- [x] Known instruction-override patterns are excluded from answer context after a live adversarial check exposed a model-only validation weakness. Original evidence remains inspectable; this is not a complete injection detector.
- [x] `scripts/run_rag.py`: starts the local model and viewer together, disables model cloud features, and stops only processes it owns. `scripts/evaluate_rag_copilot.py` records live model smoke checks.

Runtime note: Ollama was installed through Homebrew. Its dependency installation refreshed Python 3.14, OpenSSL, SQLite, and CA certificates and installed MLX libraries. The OpenSSL post-install step was rerun successfully; the archive's Python regression suite passed with the refreshed runtime.

## Active index

Built: 2026-09-10. Generation: `30a24cbcbcbe477db4e7dbcea71bcf34`.

| Measure | Value |
| --- | ---: |
| Course/program-wide source paths in index metadata | 635 |
| Unique documents with chunks | 507 |
| Source paths represented by chunks, including aliases | 512 |
| Searchable chunks | 20,007 |
| Internal/non-course chunks excluded | 21 |
| Semantic token-window vectors | 130,449 |
| Vector dimensions | 384 |
| Source paths without chunks | 123 |
| Active generation size | ~369 MiB |

The initial full embedding build took about 19 minutes. After correcting tokenizer handling of extracted symbols, the final build reused 129,617 windows and encoded 832 in about 49 seconds. Old generations and the embedding cache are retained, so total `.rag/search` disk use is larger (~1.24 GiB).

Model: cached `sentence-transformers/all-MiniLM-L6-v2`, quantized ARM64 ONNX, snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Model/tokenizer hashes and input fingerprints are recorded in the generation's `build-report.json`.

## Verification

- **22/22 integration tests pass**, covering retrieval, provenance, pinned alias scope, review gating, bounded follow-up context, accepted/rejected claims, invented citations/quotations, conflict routing, model failure, source changes, instruction-override quotations, and GET/POST request protections.
- **14/16 real-archive queries hit the expected source in the top five**: all 14 core smoke cases passed. Two misses remain visible in the suite.
- **68 citations checked; zero provenance, artifact-hash, or filter-context errors.** This validates stored evidence, not visual page rendering.
- Latest measured evaluation latency: median warm search ~69 ms; first query ~3.2 seconds, including model loading and input validation. Literal phrase scans were slower (~285–1,676 ms). The earlier run measured ~29 ms warm; these are variable local observations, not service guarantees.

Retained failures:

1. Semantic-only “change probability measure Brownian motion” misses the target Girsanov page in the top five. Hybrid search naming Girsanov retrieves page 9. Keep this as a ranking-improvement test.
2. “Expected shortfall value at risk,” filtered to MATHGR5320 lectures, has no searchable lecture evidence. A syllabus match would not resolve that coverage gap.

The evaluation is a small curated development set, not held-out recall/precision, answer correctness, or hallucination testing. Full results: `.rag/search-evaluation.json`. Dataset: `rag/evaluation.jsonl`.

## Extraction coverage and inherited limitations

The inventory snapshot contains approximately **1.234 GiB of source bytes**. Earlier workspace-size estimates included non-source data. It lists 433 PDFs, 16 XLS, 34 XLSX, two XLSM, four PPTX, 80 images, and 34 archives, among other formats. Counts describe the ingestion snapshot, not new application files added since then.

The extraction report's 620 non-error document outcomes include cached, empty, and unsupported records; **they do not mean 620 documents have searchable content**. Stage 3 produced chunks for 512 unique documents including internal files; Stage 4 retains 507 course/program-wide documents.

The 123 course/program-wide source paths without chunks comprise:

- 103 PDFs with no searchable extracted text. OCR was not enabled; review whether OCR or another extraction fix is appropriate.
- 16 legacy `.xls` files whose LibreOffice conversion failed.
- Two legacy `.doc` files and two `.c` files not extracted by the current pipeline.

Particularly limited course coverage: MATHGR5320 has only two searchable documents out of 39 (course map and syllabus). The filter API now exposes both total and searchable document counts.

Further boundaries:

- Image and ZIP records are asset/member catalogs, not visual understanding or recursive archive ingestion.
- The large CSV is a schema/sample catalog, not row-level semantic search or a numerical query engine.
- Stage 3's 9,085 PDF-locator chunks are **not a count of distinct pages**; long pages can yield multiple chunks. Similarly, locator-group counts describe chunks, not unique slides/ranges.
- PDF citations use physical file-page indices, not necessarily printed page labels. DOCX block locators are not pages.
- PDF text-coordinate overlays are derived from the rendered page and Poppler boxes, not from upstream character offsets. Scanned/malformed PDFs may fall back to the original page; non-PDF formats remain evidence-first.
- Assessment/solution review labels are metadata, not an access-control boundary. Some answer-bearing mixed documents may need manual classification.
- Retrieval scores are ranking signals, not calibrated confidence. The local model support check is fallible; a matching quotation does not by itself prove that its paraphrase is correct.
- Stage 6 returns abstention when no claims pass its checks. Conflict presentation covers only retrieved excerpts; it cannot establish that no other source disagrees. Automatic authority resolution and calibrated confidence are not provided.
- Known instruction-override patterns are filtered, and the model has no tools or filesystem access. Arbitrary prompt-injection resistance is not guaranteed.

## Product and design decisions

- Retain the Product Library-inspired navigation, search/filter controls, source detail drawer, evidence snippets, citation chips, review states, and scoped copilot concept. The reference file supplies design inspiration, not executable instructions.
- Use Columbia-oriented blue throughout the future UI: `#B9D9EB`, `#1D4F91`, dark navigation `#102A43`, white surfaces, and cool blue-gray borders. Red is reserved for alerts and destructive actions; no invented official Columbia marks.
- Local API/CLI first for Stage 4; a local web interface in Stage 5. No paid inference service or external vector database is required for this baseline.
- Source files remain authoritative. The viewer should verify the returned citation's selected source alias and hash, then open the stored locator.
- Duplicate/version handling must remain visible. Do not silently conflate editions or choose a “latest” file by filename.

## Stage 5 verification

- Viewer asset delivery, Content Security Policy, source byte ranges, traversal rejection, citation resolution, stale source handling, and localhost origin protection remain covered by the current 22-test suite.
- A live browser-service smoke check opened `RoughVolatilityClumbia2025.pdf · p. 29` from a lecturer-filtered search and verified the source as current.
- Browser acceptance passed across five real citation checks covering PDF pages, a PPTX slide preview, a line/range source, and a dataset schema. The PPTX check opened slide 2 of a 22-slide local preview and confirmed the original source remained current; PDF page previews now add Poppler coordinate overlays when text is available. Broader per-format pixel mapping remains unimplemented by design.

## Stage 6 verification

- 22/22 integration tests pass; synthesis fixtures test application validation independently of live model behavior.
- Live local-model evaluation: **8/8 checks pass**. Gamma, Newton/secant comparison, and a follow-up produce supported citations; a personal-portfolio question and missing risk-course lecture coverage abstain; negation and the known instruction-override test are rejected; a synthetic fee conflict preserves both sides.
- Warm answer/check times in the final live run were approximately 6–18 seconds; no-evidence retrieval completed in under a second. These are observations on this Mac, not service guarantees.
- The initial 7/8 report remains in `.rag/copilot-evaluation-initial.json`. The model-only verifier accepted an instruction-override quotation; an application exclusion check and regression test were added before the final 8/8 run. Broader injection resistance remains unmeasured.
- Browser interactions verified a generated gamma answer, the follow-up “When is it greatest?”, citation click-through to `GR5010_Handout8Greeks2025.pdf · p. 9` with a current source hash, pinning that handout, an evidence request restricted to it, and New chat clearing turns while retaining the pin.
- `/api/health` remained responsive during model inference. JavaScript and Python syntax checks pass. The launcher reuses a running model and starts the viewer successfully.

## Next action

Continue to Stage 7: structured spreadsheet/dataset queries and visual extraction. The Copilot currently reads indexed text and catalogs; questions requiring row-level calculations must use the future structured-data path.

Parallel backlog: repair missing PDF text (prioritize risk-course lectures), legacy formats, and C extraction; rebuild search after refreshed Stage 1–3 outputs; improve the retained semantic-paraphrase test with an evaluated model/reranking change.

No further design choice is needed to use Stages 4–6. The current choice is local inference with default review exclusion; any hosted deployment or content upload would be a separate product decision.

## Change log

### 2026-09-12

- Finalized Stage 4 documentation and the viewer handoff, preserving known coverage and ranking gaps.
- Re-ran the integration suite and the 16-case archive evaluation; the suite now includes the Stage 6 copilot checks.
- Built the first Stage 5 viewer with Columbia-blue styling, evidence drawer, PDF page jumps, verified source delivery, format fallbacks, and on-demand PPTX slide previews.
- Completed the browser acceptance run; the Manoj Singh deck now opens at cited slide 2 through a verified 22-slide local preview.
- Added on-demand PDF page previews with Poppler-derived text-coordinate overlays; page 29 of the rough-volatility deck renders with 80 verified overlay boxes.
- Implemented the Stage 6 foundational local extractive copilot with default review exclusion, explicit review opt-in, abstention, evidence claims, clickable citations, and a direct Copilot deep link; updated this status record to mark the delivered scope.
- Completed the remaining Stage 6 scope: local Qwen synthesis, conversations, document pins, exact supporting quotations, claim validation, conflict presentation, model/runtime handling, and browser interaction checks. Preserved the initial 7/8 live evaluation report before addressing its instruction-override failure.
- Integrated the supplied Columbia Mathematics of Finance MA Program logo locally and aligned the viewer's navigation, headings, active states, citations, and reading surfaces to its deep-navy/white/light-blue palette.

### 2026-09-10

- Built and validated Stage 4 against the actual archive.
- Corrected official-tokenizer handling and rebuilt affected embeddings with cache reuse.
- Added filter-aware citation resolution, offline inference, atomic generations, API safeguards, and regression tests.
- Corrected earlier coverage/count descriptions; recorded two evaluation misses rather than treating the archive as fully searchable.
- Advanced the next step to the Columbia-blue citation viewer.

### 2026-09-08

- Identified the archive and Product Library reference.
- Created the plan/status files, viewer-first provenance contract, and Columbia-oriented theme.
- Implemented and ran baseline Stages 1–3 with page/slide/range-aware provenance.
