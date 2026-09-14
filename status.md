# Course Archive RAG — Status

Last updated: 2026-09-14

## Current state

Stages 0–8 are complete for the defined local release. Extraction coverage is complete across all 635 course/program-wide source paths: OCR repaired image-only PDFs, LibreOffice conversion repaired legacy XLS/DOC files, C files use the source-code route, and three pages with no OCR-readable prose have explicit visual catalog records. Stage 8 includes refresh/retry operations, saved filters, automatic generation adoption, backups, archive-wide diagnostics, and one reproducible release gate. Stage 6 uses Qwen3 4B through Ollama on this Mac.

Archive root: `/Users/nigelli/Desktop/Canvas Files`. Original course files remain unchanged. Derived artifacts and private research live under Git-ignored `.rag/`. **Preserve/back up `.rag/library.sqlite`: conversations and saved items are not rebuildable from source files.** No source content has been uploaded for indexing or inference. The current Stage 7, Stage 8, and extraction-coverage changes are local and not yet committed/pushed.

## Release handoff

- [x] RAG implementation, viewer, supplied Columbia MAFN logo, stage-by-stage runbook, plan, status record, tests, and evaluations committed to `main`.
- [x] Upstream `main` filename rename merged before push; local `main` and `origin/main` are aligned at the release merge commit.
- [x] Post-merge inventory, extraction, normalization, and search rebuild completed locally; the active generation contains 28,056 searchable chunks and 186,176 semantic windows.
- [x] Local viewer restarted after the rebuild and browser-checked with the Columbia lockup visible and the Copilot route available.

## Stage tracker

| Stage | State | Evidence / remaining work |
| --- | --- | --- |
| 0 — Product contract | Local policy implemented | Exact-location citations, local inference, and default exclusion of review-marked material with per-question opt-in. |
| 1 — Inventory | Complete | 672 inventoried files, 666 unique contents, six duplicate groups, 179 review items; 635 course/program-wide paths enter search metadata. |
| 2 — Extraction | Complete | All 629 canonical documents produce text or an explicit visual catalog; extraction errors and empty outcomes are zero. |
| 3 — Normalization | Complete | 28,056 chunks with source-preserving provenance; internal application files are excluded before retrieval. |
| 4 — Retrieval | MVP complete | Lexical, semantic, hybrid, filters, citation lookup, CLI/API, regression tests. |
| 5 — Source viewer | MVP complete; browser acceptance passed | Columbia-blue UI, evidence drawer, deep links, verified source delivery, PDF page jumps with text-coordinate overlays, on-demand PPTX previews, and evidence-first fallbacks for other formats. |
| 6 — Grounded copilot | Complete | Local model synthesis, follow-ups/reset, pinned scope, exact quotations, model support checks, abstention, conflict presentation, and clickable citations. |
| 7 — Rich data | Complete for bounded scope | Structured queries, saved/replayable calculations, image OCR, nested archive provenance, conservative Copilot routing; limits below. |
| 8 — Operations | Complete | Refresh/retry jobs, saved filters, audit/backup/recovery, automatic generation adoption, archive-wide diagnostics and an 18-check release gate. |

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

- `viewer/index.html`, `viewer/styles.css`, and `viewer/app.js`: responsive local source library with masthead navigation for Library, Copilot, Coverage, and Review.
- Product Library-inspired results, filters, citation chips, evidence drawer, source aliases, related versions, review flags, and coverage counts, restyled in the Columbia-oriented blue palette.
- Supplied `viewer/maf-logo.png` displayed uncropped in the white masthead; deep navy headings and controls with light-blue accents carry the Columbia theme throughout.
- Reader layout refined after visual review: compact source list, wider document pane, wrapping page controls, source/evidence tabs with keyboard navigation, expanded reader mode, collapsed filters with visible active scope, and optional PDF text highlights. Long queries and repeated filenames no longer dominate the reading area.
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
- [x] Conversation UI: durable history, draft/pin/settings autosave, named conversations, New chat retaining prior history, and visible scope per turn. Up to 1,000 turns / 8 MB per conversation; six-question follow-up context. Scope/review changes stop reuse of earlier question context. Earlier answers are not source evidence.
- [x] Document pins: up to 12 exact indexed paths from search, retrieved evidence, or the drawer; pins and metadata filters are applied together before ranking and preserve duplicate aliases.
- [x] Every accepted answer claim has clickable citations and expandable supporting quotations. The full retrieved matches are shown separately with source terms and version labels.
- [x] Conflict cards require supported opposing claims from two distinct source documents. No automatic authority selection; course terms are not treated as publication dates.
- [x] Default review exclusion cannot be bypassed by empty/case-varied filters; review material requires explicit opt-in. Sources are checked for changed/missing bytes before synthesis and again before delivery.
- [x] Known instruction-override patterns are excluded from answer context after a live adversarial check exposed a model-only validation weakness. Original evidence remains inspectable; this is not a complete injection detector.
- [x] `scripts/run_rag.py`: starts the local model and viewer together, disables model cloud features, and stops only processes it owns. `scripts/evaluate_rag_copilot.py` records live model smoke checks.

Runtime note: Ollama was installed through Homebrew. Its dependency installation refreshed Python 3.14, OpenSSL, SQLite, and CA certificates and installed MLX libraries. The OpenSSL post-install step was rerun successfully; the archive's Python regression suite passed with the refreshed runtime.

## Persistence delivered — 2026-09-13

- [x] `.rag/library.sqlite` stores personal research independently of rebuildable search generations.
- [x] Questions save before inference; the server commits replies even after browser disconnect. Interrupted questions survive restart with an explicit retry state.
- [x] Autosaved drafts, history selection, titles, pins/settings, and conflict-safe multi-tab revisions.
- [x] Saved passages, answers and calculation results, with Open, Export and Delete; chat/library JSON export.
- [x] Browser acceptance: reload, fresh browser context, New chat/history reopen, source/answer saving and export. Temporary acceptance records were removed; deletion is recoverable as a database tombstone, not secure erasure.
- [x] Backup instructions and limits recorded in `rag/README.md`. No cloud sync or JSON-import UI. Chats cleared before persistence existed cannot be reconstructed.

## Stage 7 delivered — 2026-09-13

- [x] `scripts/rag_data.py`, `viewer/data.js`: Data catalog, sheets, explicit ranges, first-row headers, source-cell preview, formula/cache inspection, units and date coverage, numeric/date filters.
- [x] CSV/TSV/XLSX/XLSM/XLS. All 53 archive workbook/dataset paths pass sheet inspection (43 available without review opt-in). Legacy XLS uses local read-only `xlrd==2.0.1`, without Excel conversion or macro execution.
- [x] Explicitly approved local count, sum, mean, minimum, maximum and sample standard deviation. No arbitrary Python/SQL, formula execution, pivots, joins or named Excel table discovery.
- [x] Source hash checks before/after calculations; exact sheet/range, query recipe and implementation hash in saved/exported results; replay CLI refuses changed source/engine versions.
- [x] Independent full-CSV check: 663,074 rows, range `A1:G663075`, Close mean `1.506528232444607`, agreeing within floating-point tolerance with an independent `math.fsum` calculation (`1.5065282324446443`). Explicit MDY dates span 1984-01-03 through 2026-03-27; measured structured scan ~8.9 seconds on this Mac.
- [x] Conservative Copilot routing to text retrieval, structured lookup or computation; Data handoff preserves filters/pins/review policy and requires user confirmation of the file and operation.
- [x] First-frame OCR for 80 images; word boxes/confidence preserved in provenance, original image viewing and recognized-text search. OCR is unverified and does not interpret charts/equations semantically or caption animations.
- [x] Bounded ingestion of 34 ZIPs, including nested members; parent/member hashes and original page/line/range locators; 298 archive-member chunks published. `/api/member` serves only verified indexed members. Containers are conservatively review-marked for Copilot.
- [x] Review displays OCR confidence diagnostics and 112 skipped/limited member entries; `.rag/rich-extraction-report.json` has the source-by-source record. No top-level enrichment failure, but oversized market CSVs and unsupported binaries remain excluded.
- [x] Browser acceptance for calculations, original rows, save/reopen/export, scoped routing, origin/path protection and desktop/mobile layouts. The expanded suite also tests numeric correctness, explicit date formats, formula nonexecution, source changes, bounded nested ZIPs, OCR provenance and durable history.

Bounds: 128 MiB per structured input, 2 million rows, 256 selected columns, a 60-second scan limit, and 2 million cells per XLSX worksheet. ZIP limits: 25 MiB/member, 100 MiB total expanded bytes, 1,000 members, two nested ZIP levels, 5,000 records and 300 pages/member PDF. Previews show 30 matching rows; aggregates use all rows in the selected range. Calculation currently operates on standalone indexed datasets, not ZIP-contained datasets. These limits are deliberate, visible coverage boundaries—not claims that all content was ingested.

## Active index

Built: 2026-09-14. Generation: `2ff51575a5a746adac87499395b20990`.

| Measure | Value |
| --- | ---: |
| Course/program-wide source paths in index metadata | 635 |
| Unique documents with chunks | 629 |
| Source paths represented by chunks, including aliases | 635 |
| Searchable chunks | 28,056 |
| Internal/non-course chunks excluded | 0 (now excluded before extraction) |
| Semantic token-window vectors | 186,176 |
| Vector dimensions | 384 |
| Source paths without chunks | 0 |
| Active generation size | 550,112,928 bytes (~525 MiB) |

The extraction-coverage build reused 134,996 windows and encoded 51,177 new windows in about 12 minutes. The final three visual catalog records then reused 186,173 windows and encoded three. Old generations and the embedding cache are retained; retention/cleanup is not yet automated.

Model: cached `sentence-transformers/all-MiniLM-L6-v2`, quantized ARM64 ONNX, snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Model/tokenizer hashes and input fingerprints are recorded in the generation's `build-report.json`.

## Verification

- **54 regression tests** cover retrieval, provenance, pinned alias scope, review gating, bounded follow-up context, claim validation/retry, model failure, source changes, GET/POST protections, persistent history, structured calculations, OCR/legacy extraction, source-version checks, bounded archive processing, refresh recovery, backups, and generation switching.
- **15/16 real-archive queries hit the expected source in the top five**: all 14 core cases and the repaired risk-coverage case pass. The one retained semantic challenge remains visible.
- **73 citations checked; zero provenance, artifact-hash, or filter-context errors.** This validates stored evidence, not visual page interpretation.
- Latest retrieval evaluation: median warm search 45.9 ms. All core cases pass with no regressions. These are local observations, not service guarantees.

Retained challenge: semantic-only “change probability measure Brownian motion” misses the target Girsanov page in the top five. Hybrid search naming Girsanov retrieves page 9. Keep this as a ranking-improvement test.

The evaluation is a small curated development set, not held-out recall/precision, answer correctness, or hallucination testing. Full results: `.rag/search-evaluation.json`. Dataset: `rag/evaluation.jsonl`.

## Extraction coverage and remaining limitations

The inventory snapshot contains approximately **1.234 GiB of source bytes**. Earlier workspace-size estimates included non-source data. It lists 433 PDFs, 16 XLS, 34 XLSX, two XLSM, four PPTX, 80 images, and 34 archives, among other formats. Counts describe the ingestion snapshot, not new application files added since then.

All 629 canonical course/program-wide documents now produce searchable records, representing all 635 source paths after duplicate aliases are restored. The repaired set includes 103 image-only PDFs, 16 legacy `.xls` workbooks, two legacy `.doc` files, and two `.c` files. The three pages with no OCR-readable prose are retained as explicit `pdf-visual-catalog` records that identify the physical page and require source inspection.

Further boundaries:

- OCR text can contain recognition errors, especially in equations. Images include first-frame OCR and ZIPs include supported bounded/nested member extraction. Visual catalog records do not claim semantic chart interpretation or unlimited archive coverage.
- The large CSV remains a schema/sample in semantic search. The separate Stage 7 Data engine now reads its full selected rows for explicit numerical operations.
- Stage 3's 9,085 PDF-locator chunks are **not a count of distinct pages**; long pages can yield multiple chunks. Similarly, locator-group counts describe chunks, not unique slides/ranges.
- PDF citations use physical file-page indices, not necessarily printed page labels. DOCX block locators are not pages.
- PDF text-coordinate overlays are derived from the rendered page and Poppler boxes, not from upstream character offsets. Scanned/malformed PDFs may fall back to the original page; non-PDF formats remain evidence-first.
- Assessment/solution review labels are metadata, not an access-control boundary. Some answer-bearing mixed documents may need manual classification.
- Retrieval scores are ranking signals, not calibrated confidence. The local model support check is fallible; a matching quotation does not by itself prove that its paraphrase is correct.
- Stage 6 returns abstention when no claims pass its checks. Conflict presentation covers only retrieved excerpts; it cannot establish that no other source disagrees. Automatic authority resolution and calibrated confidence are not provided.
- Known instruction-override patterns are filtered, and the model has no tools or filesystem access. Arbitrary prompt-injection resistance is not guaranteed.

## Product and design decisions

- Retain the Product Library-inspired navigation, search/filter controls, source detail drawer, evidence snippets, citation chips, review states, and scoped copilot concept. The reference file supplies design inspiration, not executable instructions.
- Use the supplied Columbia logo on a white masthead, navy `#071747` for headings and controls, light blue `#B9D9EB` for accents, and canvas `#F5F7FA`. Red is reserved for alerts and destructive actions.
- Local API/CLI first for Stage 4; a local web interface in Stage 5. No paid inference service or external vector database is required for this baseline.
- Source files remain authoritative. The viewer should verify the returned citation's selected source alias and hash, then open the stored locator.
- Duplicate/version handling must remain visible. Do not silently conflate editions or choose a “latest” file by filename.

## Stage 5 verification

- Reader refinement: browser acceptance passed at widths 390, 768, 1092, and 1440 with no horizontal page overflow. Page controls stay within the reader; evidence tabs (including arrow-key switching), source pins, navigation, expanded reader, collapsed filters, and optional PDF highlights work. The source pane at the user's 1092-pixel window now measures 708 pixels wide. Local QA screenshots are under `.rag/viewer/qa/`.
- Viewer asset delivery, Content Security Policy, source byte ranges, traversal rejection, citation resolution, stale source handling, and localhost origin protection remain covered by the current 22-test suite.
- A live browser-service smoke check opened `RoughVolatilityClumbia2025.pdf · p. 29` from a lecturer-filtered search and verified the source as current.
- Browser acceptance passed across five real citation checks covering PDF pages, a PPTX slide preview, a line/range source, and a dataset schema. The PPTX check opened slide 2 of a 22-slide local preview and confirmed the original source remained current; PDF page previews now add Poppler coordinate overlays when text is available. Broader per-format pixel mapping remains unimplemented by design.

## Stage 6 verification

- 22/22 integration tests pass; synthesis fixtures test application validation independently of live model behavior.
- Live local-model evaluation: **8/8 checks pass**. Gamma, Newton/secant comparison, a gamma follow-up, and expected shortfall produce supported citations; a personal-portfolio question abstains; negation and the known instruction-override test are rejected; a synthetic fee conflict preserves both sides.
- Warm answer/check times in the final live run were approximately 6–18 seconds; no-evidence retrieval completed in under a second. These are observations on this Mac, not service guarantees.
- The initial 7/8 report remains in `.rag/copilot-evaluation-initial.json`. The model-only verifier accepted an instruction-override quotation; an application exclusion check and regression test were added before the final 8/8 run. Broader injection resistance remains unmeasured.
- Browser interactions verified a generated gamma answer, the follow-up “When is it greatest?”, citation click-through to `GR5010_Handout8Greeks2025.pdf · p. 9` with a current source hash, pinning that handout, an evidence request restricted to it, and New chat clearing turns while retaining the pin.
- `/api/health` remained responsive during model inference. JavaScript and Python syntax checks pass. The launcher reuses a running model and starts the viewer successfully.

## Next action

Use **Add docs** for source updates; it now runs the Stage 8 refresh and release gate before committing and pushing the uploaded paths. Stage 7 numerical questions use the explicit Data path; the text Copilot does not calculate from catalog samples. The next quality backlog is richer semantic interpretation of visual-only pages, oversized archive members, automatic retention cleanup, and the retained semantic paraphrase challenge.

Additional course documentation is expected to be added over time. Treat each upload batch as an incremental ingestion cycle: scan for added/changed/deleted files, run refresh with OCR/retry when needed, inspect the review queue, and accept the new generation only after the zero-missing-source, zero-extraction-error release gate passes. Existing conversations and saved research remain in `.rag/library.sqlite` across rebuilds.

No further design choice is needed to use Stages 4–7. The current choices are local inference, default review exclusion, explicit structured execution, and bounded extraction. Arbitrary-code execution, hosted deployment or content upload would require a separate product decision.

## Change log

### Document intake and one-click launch — 2026-09-14

- Added a CU-themed **Add docs** workspace with existing-folder selection, multi-file preview, supported-format and size validation, durable progress cards, and clear GitHub destination details.
- Added loopback-only upload handling with safe-name/path enforcement, checksum and byte-count verification, collision rejection, atomic writes, one active job, and 20-file / 64-MB-per-file / 128-MB-per-batch bounds.
- Automated incremental OCR/index refresh, the complete Stage 8 release gate, upload-path-only Git commits through Git LFS, and `origin` push. Failed validation never publishes; failed processing keeps the source files and durable diagnostics locally.
- Added `Course Archive.app` and `START HERE - Open Course Archive.command` for Finder launch, plus the equivalent `python3 scripts/run_rag.py --open` path and complete new-Mac, upload, publishing, and recovery instructions. The app now has a dedicated navy/Columbia-blue archive icon and opens its diagnostic log with a visible alert when startup fails.
- Refined the icon with a Columbia-style crown at upper right and a true alpha-transparent exterior while preserving opaque white document/chart details. Added `INSTALL ON DESKTOP.command`; installed copies retain an explicit checkout path and continue launching the pulled repository.
- Serialized app startup per port so simultaneous Finder launches wait for one healthy service rather than racing to bind port 8765.

### Extraction coverage completion — 2026-09-14

- Recovered all 103 image-only PDFs with parallel, page-preserving Tesseract OCR; repaired 16 XLS and two DOC sources through isolated LibreOffice conversions; refreshed two C sources through the code path.
- Added honest visual-page catalog records for two unlabeled equity charts and one handwritten flow sketch whose pages contain no OCR-readable prose.
- Published generation `2ff51575a5a746adac87499395b20990`: 28,056 chunks, 186,176 vectors, 629 searchable canonical documents, 635/635 represented source paths, zero empty outcomes, and zero extraction errors.
- Added large-document result diversification so newly indexed textbooks do not crowd lecture evidence, while deferred hits still fill tightly scoped searches. Added bounded support-check retry and per-claim validation fallback for malformed local-model IDs.
- The strengthened thresholds require zero missing-text sources and zero extraction errors. The final release gate passes 18/18; archive diagnostics hit 605/635 probes (95.3%) with zero locator/hash errors, and all 54 Python tests pass.

### Stage 8 completion — 2026-09-14

- Added serialized refresh/retry jobs, durable progress, source-change records, extraction reuse, failed-build input recovery and consistent SQLite backups. The completed coverage refresh ends with zero extraction errors and zero empty outcomes.
- Added persistent named filter views with exact scope restoration and Coverage job history. The running server now adopts newly published generations between requests; the HTTP regression test builds and loads a new generation without a restart.
- Added `scripts/evaluate_rag_release.py` and versioned thresholds. The accepted generation passes **18/18 release checks**: 14/14 core retrieval, zero regressions, 73 clean returned citations, 605/635 archive diagnostic hits at five, 635/635 valid source-alias citations/hashes, and 8/8 live Copilot checks with 100% bounded answer, abstention, and quotation scores.
- All **54 regression tests pass**. Median warm search was 45.9 ms; index size was 550,112,928 bytes. Reports: `.rag/release-evaluation.json`, `.rag/stage8-evaluation.json`, `.rag/coverage-evaluation.json`, and `.rag/copilot-evaluation.json`.
- Refined the CU front end across all areas: stronger navy navigation and editorial hierarchy, Columbia-blue dividers/selection, coherent controls and cards, a two-step Data workflow, and a complete two-row mobile navigation. Browser QA passed at 390 and 1440 pixels; a real citation opened `GR5010_Handout8Greeks2025.pdf` at physical page 9.
- Personal backup: `.rag/operations/backups/776276aa56824d7aae61f173ca4e7146.sqlite`. Updated local app: `http://127.0.0.1:8767/`.
- Stage 8 is complete for the defined local release. No automatic filesystem schedule or retention deletion is enabled. The known semantic miss, visual interpretation, and oversized archive members remain explicit post-release backlog. These changes are local and uncommitted.

### 2026-09-13

- Implemented durable conversations, drafts/pins/settings and Saved research, with conflict handling, server-side reply persistence, exports and backup guidance.
- Implemented Stage 7 structured Data queries, explicit date formats, approved numerical operations, saved/replayable results and scoped Copilot handoff.
- Processed 80 image assets and 34 ZIPs, retained OCR/member provenance and visible skipped-content limits, rebuilt the local index and reran retrieval evaluation.
- Added regression/browser acceptance coverage and updated the plan, runbook and remaining Stage 8 work. No source course files were changed or uploaded.

### 2026-09-12

- Refined the viewer after user visual feedback: full logo on a white masthead, wider reading area, compact results, visible page controls, source/evidence tabs, expandable reader, collapsible filters, and clean PDF pages with optional text highlights. Updated the current visual direction and browser acceptance record.
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
