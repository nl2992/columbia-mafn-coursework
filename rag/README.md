# Local RAG ingestion and search

## Document intake and GitHub publishing

Start the complete local app with `python3 scripts/run_rag.py --open`, or double-click `Course Archive.app` in Finder. Open **Add docs**, select an existing archive folder and one or more documents, then click **Import, verify & publish**. The browser hashes every selection; the server decodes it only on loopback, verifies its size and SHA-256, rejects path traversal, unsupported types, symlinks, collisions and oversized batches, and writes each file atomically.

One intake job runs at a time. It executes, in order:

```text
local save → incremental refresh with OCR/retry → Stage 8 release gate
           → Git LFS staging → scoped commit → push origin HEAD
```

The commit includes only the uploaded paths, even if unrelated working-tree changes exist. Automatic publishing requires a checked-out branch, an `origin` remote, Git LFS, and working GitHub credentials. It never pushes a batch whose refresh or release gate failed. The app accepts at most 20 files, 64 MB each and 128 MB total; browser JSON transport is intended for ordinary course-document batches rather than very large datasets.

Job records live under `.rag/imports/jobs/`. A failed file remains in its chosen source folder so it can be inspected; no automatic deletion or overwrite occurs. After fixing a failure, manually verify and publish an already-saved batch with:

```bash
python3 scripts/rag_operations.py refresh --retry-errors --ocr
python3 scripts/evaluate_rag_release.py
git add -- 'Fall 2025/COURSE/folder/file.pdf'
git commit --only -m 'Add course documents' -- 'Fall 2025/COURSE/folder/file.pdf'
git push origin HEAD
```

Replace the sample path with every file in that batch. If a local commit was already created and only the push failed, use `git push origin HEAD` after restoring GitHub access. The viewer adopts a successful new index generation between requests.

## Stage 8 operations

Run these from the archive root:

```sh
python3 scripts/rag_operations.py scan
python3 scripts/rag_operations.py refresh
python3 scripts/rag_operations.py status
python3 scripts/evaluate_rag_search.py --baseline .rag/search-evaluation.json --output .rag/stage8-evaluation.json
python3 scripts/evaluate_rag_coverage.py
python3 scripts/evaluate_rag_release.py
```

Refresh hashes sources, inventories changes, reuses extraction by content hash, normalizes active documents and rebuilds search with cached embeddings. Deleted sources cannot reappear from old extraction files. One refresh runs at a time. Progress and audit records live in `.rag/operations/jobs/`; Coverage shows the latest jobs. Direct legacy pipeline commands must not run concurrently with refresh.

Failures restore the previous manifest/chunks/reports; completed extraction files remain reusable for retry. Run `refresh` again after fixing an interrupted or failed job. `refresh --retry-errors` retries error, unsupported and empty outcomes; add `--ocr` to OCR empty PDF pages during those retries. It does not force OCR of already-readable pages. Per-document extraction failures remain visible in `.rag/operations-review.jsonl`; a completed rebuild does not imply complete text coverage.

A running viewer adopts a successfully published generation between requests. Filesystem scheduling is not enabled. The completed acceptance instance is at `http://127.0.0.1:8767/`.

More course documentation is expected over time. Add new files under the existing course/program roots, then use the incremental refresh workflow and release gate in this runbook. A batch is accepted only when every new source has searchable text or an explicit visual catalog record, extraction errors are zero, and the remaining release checks pass. Preserve `.rag/library.sqlite` so saved research and conversations survive index rebuilds.

Each refresh creates a consistent backup of personal research under `.rag/operations/backups/`, including committed WAL writes. To create an additional backup, choose a new destination:

```sh
python3 scripts/rag_operations.py backup /private/tmp/mafn-library-backup.sqlite
```

Copy backups to your normal external backup storage. For restore, stop the service, preserve the existing database and WAL/SHM sidecars, then restore the consistent backup as `.rag/library.sqlite` without stale sidecars. Never delete `.rag/` to rebuild. Job recovery copies and generations are retained; cleanup is manual.

In Library, expand Filters, enter a name and click **Save view**. Open the named view from Saved to restore the query, mode and exact filters. If a saved scope no longer exists, it is rejected rather than broadened. Views support export and deletion alongside other saved research.

`evaluate_rag_release.py` runs the retrieval comparison, archive-wide coverage audit, and live Copilot evaluation, then applies the versioned thresholds in `rag/release-thresholds.json`. It writes `.rag/release-evaluation.json` and exits nonzero on any failure. The current generation passes 18/18 checks. The coverage audit checks one source-derived retrieval probe, one locator, and the live hash for each of 512 searchable aliases, grouped across every course, content type, and format. Source-derived probes are stability diagnostics rather than held-out natural-query relevance. Browser acceptance: `tests/verify_stage8.cjs` uses Playwright/Chrome and defaults to port 8765 (`RAG_TEST_URL` overrides it).

Stages 1–3 use `scripts/rag_pipeline.py`; Stage 4 uses `scripts/rag_search.py`; Stages 5–6 provide the local source viewer and conversational Copilot. See [plan.md](../plan.md) and the living [status.md](../status.md).

## Search the existing index

From `/Users/nigelli/Desktop/Canvas Files`:

```bash
python3 scripts/rag_search.py search "Newton secant tangent convergence" --course MATHGR5030
python3 scripts/rag_search.py search "fractional Brownian motion covariance Hurst" --lecturer Gatheral
python3 scripts/rag_search.py search "investor views equilibrium returns portfolio" --mode semantic --course MATHGR5380
python3 scripts/rag_search.py search "basket.py" --mode lexical --phrase
python3 scripts/rag_search.py search "Girsanov" --course STAT5264-2 --json
python3 scripts/rag_search.py filters
python3 scripts/rag_search.py status
```

Use `citation CHUNK_ID` with an ID returned by search; add `--source RELATIVE_SOURCE_PATH` to retain a selected duplicate alias. Global `--root` and `--model-dir` options go **before** the command.

Repeated `--course`, `--term`, `--content-type`, `--file-type`, and `--review` values are exact case-insensitive alternatives. `--folder` and `--lecturer` are substring filters. Different filter fields must match the same source alias. `filters` reports both total and searchable document counts; empty lecturer fields mean unknown, not no lecturer.

Default mode is hybrid. `--top-k` accepts 1–50. `--phrase` requires a literal substring in evidence or a matched source path (lexical or hybrid only); it is useful for filenames/equations but is not a LaTeX equivalence engine. Ordinary lexical queries are safely quoted token OR searches, not raw FTS syntax. Source evidence is unchanged; only the search representation normalizes accents, Greek names, and filename punctuation.

`--min-cosine` defaults to 0.25 and controls semantic candidates only. Neither cosine nor the fused `score` is answer confidence. Broad conceptual queries can still return irrelevant results; inspect the source.

## Local API

```bash
python3 scripts/rag_search.py serve --port 8765
curl 'http://127.0.0.1:8765/api/health'
curl 'http://127.0.0.1:8765/api/search?q=Girsanov&course=STAT5264-2&top_k=5'
curl 'http://127.0.0.1:8765/api/filters'
```

Search responses include text, a preview excerpt, component scores, source aliases, metadata, related versions, and `citation.resolve_url`. Fetch that URL to resolve the stable chunk ID and check each source's `current`, `changed`, or `missing` state. It preserves the selected path through a `source` query parameter. Original Stage 3 fields are available unchanged under `provenance`.

The Stage 5 viewer is available at [http://127.0.0.1:8765/](http://127.0.0.1:8765/) when the service is running. It binds only to `127.0.0.1`, rejects foreign Host/Origin values, emits no CORS permission, serves only allowlisted viewer assets and indexed hash-verified source files, and avoids logging query URLs. No multi-user authentication, TLS, or public deployment is provided. Stop with Ctrl-C. Stage 8 makes a running service adopt an atomically published index between requests.

## Stage 5 viewer

The viewer implements the citation-first path:

```text
Search → result card → citation chip → evidence drawer → verified source location
```

The white masthead displays the supplied local Columbia University Mathematics of Finance MA Program lockup at `viewer/maf-logo.png`, uncropped at every screen size. Navy headings and controls, light-blue accents, and white reading surfaces carry the theme throughout; no external logo or brand asset is downloaded.

The source list sits beside a wider reader. Choose **Source page** or **Evidence & details** to switch between the original and its excerpt/provenance; arrow keys switch these tabs too. **Expand reader** temporarily hides the source list. Filters collapse with the active scope still visible. Page controls wrap independently of long document titles. On mobile the source list sits above the reader. PDF previews open cleanly; enable **Text highlights** to see Poppler coordinates for extracted text across the page. These boxes cover page text and are not exact chunk-span alignment. Preview HTML uses a versioned cache key so older generated layouts refresh while reusing existing page images.

PDF results open in a same-origin browser PDF frame at the stored physical page, with page input, previous/next controls, fit-width browser display, and open-in-new-tab. Code/text line ranges use a focused text pane; images open inline. PPTX slides render on demand to a local PDF preview at the cited slide. Spreadsheet ranges, datasets, notebooks, and DOCX blocks open in a focused extracted-evidence pane labeled with the exact locator, while archives and other binary files show the evidence and verified-original link. The drawer shows source states, duplicate aliases, related versions, artifact hash, review flags, and the unmodified Stage 3 provenance.

Deep links retain search/filter context and the selected `chunk` plus `source` in the URL. The server checks the source path against the active index and re-hashes the live file before delivery; it supports byte ranges for browser PDF loading, creates hash-keyed PPTX preview PDFs under `.rag/viewer/previews/`, and creates hash-keyed PDF page overlays under `.rag/viewer/highlights/` from Poppler text coordinates. It never serves arbitrary paths. Scanned or malformed PDFs may fall back to the original page; other formats remain evidence-first.

Open the viewer with:

```bash
python3 scripts/rag_search.py serve --port 8765
open http://127.0.0.1:8765/
```

## Stage 6 Copilot

Start the viewer and local model together from the repository root:

```bash
python3 scripts/run_rag.py
```

Open [Copilot](http://127.0.0.1:8765/?view=copilot). Use Cited explanation for local model synthesis, or Evidence excerpts for retrieval without generation. Pin documents from search results or the source drawer, then choose Pinned documents to restrict questions to those files plus the current filters. Each accepted claim has source citations and expandable supporting quotations; retrieved matches appear separately.

Follow-up questions use up to six earlier questions within the same scope and review policy. Earlier answers are not used as source evidence. Questions, replies, drafts, pins and settings now persist in `.rag/library.sqlite`. New chat retains previous conversations in Saved; reloading restores the selected chat. Questions submitted through the form use a POST body rather than the URL. Browser local storage contains only the active-chat pointer; the research itself stays in the local database. Old chats already cleared before this feature cannot be recovered.

The installed model is `qwen3:4b` (Q4_K_M, ~2.5 GB), served by Ollama 0.33.3. Weights are in `.rag/models/ollama/`. The adapter sends requests only to `127.0.0.1:11434`, disables proxies/redirects, checks for an installed local model, and does not expose filesystem or tool access to the model. The launcher sets `OLLAMA_NO_CLOUD=1` and binds both services to loopback. It reuses an existing model service and stops only processes it starts.

For another Mac, install Ollama explicitly (`brew install ollama`; Homebrew may refresh dependencies), then start its local service and pull the model once:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS="$PWD/.rag/models/ollama" OLLAMA_NO_CLOUD=1 ollama serve
# In a second terminal, while that model service is running:
ollama pull qwen3:4b
```

After provisioning, `python3 scripts/run_rag.py` starts everything. `python3 scripts/rag_search.py serve --port 8765` starts only the viewer/search API. If an existing viewer is already running, the launcher reports its address. Published index generations switch automatically; Python or front-end code changes still require a service or page reload. An offline model leaves Evidence excerpts available, while synthesis reports its unavailability explicitly.

```bash
curl -H 'Content-Type: application/json' \
  --data '{"query":"What is option gamma?","filters":{"course":["MATHGR5010"]},"answer_style":"synthesis"}' \
  'http://127.0.0.1:8765/api/ask'
curl 'http://127.0.0.1:8765/api/copilot/status'
# Legacy GET returns excerpts, with no model synthesis:
curl 'http://127.0.0.1:8765/api/ask?q=Girsanov&mode=hybrid&top_k=5'
```

POST accepts `query`, `mode`, `top_k` (1–8), `filters`, `source_paths` (1–12 exact indexed paths, or null for archive scope), `history` (up to six `{ "query": "..." }` objects), `answer_style` (`synthesis`/`evidence`), `include_review` (boolean), and `min_cosine`. Bodies are limited to 40 KB; questions to 2,000 characters. Pins and filters intersect before ranking on the same alias. Source paths that are not indexed are rejected. The source hashes are checked before generation and again before delivering an answer.

Review-marked material is excluded by default. Explicit solution/assessment filters without `include_review:true` return a policy error; empty review lists cannot bypass the default. Opt-in produces a visible warning. Source labels remain metadata rather than an authentication boundary.

The synthesis model receives at most eight bounded evidence excerpts with citation metadata and emits structured claims. The application requires known citation IDs and matching quotations, then runs a separate local support/relevance check. Claims marked uncertain or unsupported are withheld; if no claims remain, the answer abstains. Conflict cards require support from distinct documents, without automatically deciding which version is correct. The model can still misjudge support; matching text, version labels, and course terms are not calibrated confidence or publication-date authority.

Known instruction-override patterns are excluded from model evidence; source instructions are treated as data and cannot invoke tools. This reduces a specific observed failure, not all possible prompt injections. Inspect source pages for equations and extraction errors. Reference implementations: [Ollama chat API](https://docs.ollama.com/api/chat), [structured output schemas](https://docs.ollama.com/capabilities/structured-outputs), and [Qwen3 4B model](https://ollama.com/library/qwen3:4b).

## Runtime and reproducible builds

Tested on this Mac with Python 3.14, NumPy 2.4.4, ONNX Runtime 1.25.1, tokenizers 0.22.2, and SQLite with FTS5. Pinned packages are in `rag/requirements-search.txt`. If dependencies are missing, install them explicitly into the project-local ignored runtime:

```bash
python3 -m pip install --target .rag/runtime -r rag/requirements-search.txt
python3 scripts/rag_search.py build
```

The model is already cached locally on this machine. A different machine must separately provision `tokenizer.json` and `onnx/model_qint8_arm64.onnx` from the same MiniLM snapshot; the search/build commands never download them. Supply their parent directory explicitly when needed:

```bash
python3 scripts/rag_search.py --model-dir /absolute/path/to/model-snapshot build
```

The inference path uses the official tokenizer without truncation, overlapping 224-token windows with 192-token stride, attention-masked mean pooling, and L2 normalization. Long evidence retains its original locator while every window participates in retrieval. The best window represents each chunk; results are deduplicated by document plus locator. See the [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) for the model and [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html#the_bm25_function) for lexical ranking.

Builds validate source hashes against the manifest, preserve the previous active generation on failure, and publish `CURRENT.json` atomically after integrity checks. `.rag/search/embedding-cache.sqlite` reuses exact token-sequence embeddings for compatible model configurations. The cache includes compatibility with this project's initial tokenizer build only when token IDs and model configuration match exactly.

Active generation files are `index.sqlite`, `vectors.npy`, `owners.npy`, `windows.npy`, and `build-report.json`. The report records model/input fingerprints, exclusions, and every source path without chunks. Old generations are retained; automatic retention/cleanup is not implemented.

## Tests and evaluation

```bash
python3 -m unittest discover -s tests -v
python3 scripts/evaluate_rag_search.py
python3 scripts/evaluate_rag_search.py --strict
python3 scripts/evaluate_rag_copilot.py
python3 scripts/evaluate_rag_coverage.py
python3 scripts/evaluate_rag_release.py
```

The 54-test regression suite covers temporary retrieval corpora, deterministic synthesis fixtures, durable storage, structured calculations, source changes, formulas, explicit dates, parallel PDF OCR, legacy DOC conversion, visual-only catalogs, bounded archive processing, refresh rollback, backups, large-document result diversification, malformed support-check recovery, and live generation switching. Browser checks are `tests/verify_stage7.cjs`, `tests/verify_stage8.cjs`, and `tests/verify_persistence.cjs` (require Playwright and Chrome, plus the running local service). They create and remove only their own temporary saved items. The separate retrieval evaluation uses `rag/evaluation.jsonl` and writes `.rag/search-evaluation.json`; its retained result is 15/16 archive cases at five, including all 14 core cases and the repaired coverage case, with 73 citations free of provenance/hash/filter errors. Default exits nonzero for core/citation failures; `--strict` also fails for the retained semantic challenge.

The live Copilot evaluation uses the installed Qwen model and writes `.rag/copilot-evaluation.json`: 8/8 development checks passed (gamma, Newton/secant comparison, follow-up, expected shortfall from the repaired risk lectures, unsupported personal-portfolio abstention, negation, an instruction-override test, and a synthetic conflict). The validator retries one malformed response and falls back to independent per-claim checks when the small local model repeats claim IDs; it never guesses positional verdicts. The initial 7/8 report is preserved in `.rag/copilot-evaluation-initial.json`; its instruction-override failure led to an application filter and regression test. These small smoke sets are not held-out accuracy, exhaustive conflict detection, or general injection-resistance benchmarks.

## Run the pipeline

From the repository root:

```bash
python3 scripts/rag_pipeline.py inventory
python3 scripts/rag_pipeline.py extract
python3 scripts/rag_pipeline.py normalize
```

For a later OCR pass:

```bash
python3 scripts/rag_pipeline.py extract --ocr --force
python3 scripts/rag_pipeline.py normalize
python3 scripts/rag_search.py build
```

The pipeline writes only derived artifacts to `.rag/`:

- `manifest.jsonl`: one record per source file
- `inventory-report.json`: counts by type, course, term, and route
- `review-queue.jsonl`: legacy, unsupported, visual, restricted, and large-data items
- `extracted/`: format-specific records with source locators
- `extraction-report.json`: extraction results and failures
- `chunks.jsonl`: normalized, provenance-preserving chunks
- `normalization-report.json`: chunk and locator counts

## Locator model

The pipeline uses a generalized locator so the future viewer can route citations correctly:

| Source | Locator |
| --- | --- |
| PDF | `pdf_page` |
| PPTX | `pptx_slide` |
| DOCX | `docx_block` |
| Markdown, text, code | `line_range` |
| XLS/XLSX/XLSM | `spreadsheet_range` |
| CSV/TSV | `dataset_schema` |
| Notebook | `notebook_cell` |
| Image | `image_asset` |
| ZIP | `archive_member_catalog`, plus `archive_member` carrying member chain/hash and the member's own locator |

Large CSV/TSV files produce a schema and sample catalog rather than one embedding per row. Stage 7 queries the original rows separately, with explicit structured operations and source hashes.

## Design choices

- The source archive is read-only from the pipeline's perspective.
- `.git` and `.rag` are excluded from inventory.
- Duplicate content is hashed once and linked to all source paths.
- Assessment and solution materials are indexed but marked `review_required`.
- PDF page numbers are captured during extraction, not inferred later.
- Chunks carry their original document, artifact version, locator, section, line, sheet, and character offsets.
- Optional OCR is explicit because it is slower and should be reviewed for low-confidence pages.

## Coverage and source integrity

Stage 4 indexes only `Fall 2025`, `Spring 2026`, and `Program-wide` roots, excluding internal application documents. After changing course files, use the Stage 8 refresh command below. Search rejects changed ingestion artifacts; citation resolution separately checks live source bytes. A running service adopts an atomically published generation between requests. Source edits without refreshing ingestion can leave stale search hits, which citation lookup flags.

The accepted index contains 28,056 chunks and 186,176 semantic windows from 629 canonical documents, representing all 635 source paths after duplicate aliases are restored. Missing-source and extraction-error counts are both zero. The repaired set includes page-preserving OCR for 103 image-only PDFs, isolated LibreOffice conversion for 16 XLS and two DOC files, and source-code extraction for two C files. Two unlabeled equity charts and one handwritten flow sketch contain no OCR-readable prose; their physical pages have explicit `pdf-visual-catalog` records directing users to inspect the visual source. OCR may misread equations, so citations still open the original page. CSV search hits remain schema/samples; Data operations read the actual selected rows.

## Stage 7: data, images, and archives

### Start and use Data

The existing ingestion environment supplies `openpyxl` and Pillow. The additional read-only legacy XLS dependency is pinned locally:

```bash
python3 -m pip install --target .rag/runtime -r rag/requirements-data.txt
python3 scripts/run_rag.py
```

Open [Data](http://127.0.0.1:8765/?view=data). Select a file and sheet. Start with the default `A1:Z31` preview; headers are the first row of the selected range. Clear the range to scan the entire table, or enter an exact range. Choose a numeric column letter for sum/mean/min/max/sample standard deviation, or Count rows. Optional numeric/date filters use inclusive bounds. ISO, month/day/year and day/month/year are explicit source-format choices; ambiguous dates are not guessed. Datetime bounds are exact timestamps (a date-only upper bound means midnight).

Preview exposes at most 30 matching rows with original cell addresses. Schema/date coverage spans the whole selected range before row filters. Units come only from parentheses/brackets in headers; otherwise they are unknown, not inferred financial units. Count includes all records/worksheet rows in the range, excluding the header when selected. Numeric operations skip blanks, nonnumeric/non-finite values and formulas without stored caches, with warnings. XLSX/XLSM shows formula text and stored values, never recalculates formulas or runs macros. XLS exposes stored values, not formula text.

The API is `GET /api/data`, `GET /api/data/schema?path=...`, and `POST /api/data/query`. Review-marked files require explicit `include_review:true`. Only active indexed paths are accepted, with live source hashes checked before and after the operation. Computation is a fixed Python operation list, not arbitrary SQL or model-generated Python. Copilot recognizes explicit dataset/column/calculation requests and offers a scoped Data handoff; users confirm the exact file and parameters before execution. The conservative router does not understand every mathematical phrasing.

Limits: 128 MiB/file, 2 million rows, 256 selected columns, 60 seconds per scan, one structured query at a time. XLSX worksheets over 2 million cells and excessive ZIP/XML expansion are refused. No partial aggregate is silently returned after hitting a limit. Current Data catalog: 53 files with review opt-in (43 without); all 53 passed sheet-listing verification. File types are CSV, TSV, XLSX, XLSM, and XLS. Named Excel table discovery, pivots, joins, arbitrary formulas, and chart generation are not implemented.

### Save, export, and reproduce a calculation

Save result stores the snapshot under Saved calculations. Reopening displays historical values and checks the current source; it does not rerun. Export result downloads JSON containing the result, preview, warnings, exact sheet/range, source SHA-256, request recipe, and `scripts/rag_data.py` implementation hash. Replay an exported result from the repo root:

```bash
python3 scripts/rag_data.py --replay /absolute/path/to/mafn-data-result.json
```

Replay refuses changed sources or a different implementation hash. Keep the matching code revision and dependencies for long-term reproducibility. Numeric operations use binary floating point, not arbitrary precision. Generated outputs are local; exporting alone does not save to the application database—use Save result for that.

### Enrich images and archive contents

With the baseline manifest/extraction present and local Tesseract available:

```bash
python3 scripts/rag_rich.py
python3 scripts/rag_pipeline.py normalize
python3 scripts/rag_search.py build
# Restart the running viewer to load this generation.
```

This targets images and ZIPs without redoing all PDF extraction. It records first-frame OCR words, pixel boxes and confidence, and replaces only derived extraction records after checking source hashes. OCR is unverified and can misread mathematical notation; it is not semantic chart interpretation or generated visual captioning. Review shows lower-confidence entries. Run this command again after a forced baseline extraction, which otherwise replaces rich records with baseline catalogs.

ZIP ingestion reads supported members into bounded temporary files and never executes them. Limits: 25 MiB/member, 100 MiB expanded total, 1,000 visited members, two nested ZIP levels, 5,000 records, and 300 pages/member PDF. Unsafe paths, links, duplicates, encrypted entries, excessive expansion and unsupported binaries are skipped with explicit reasons. Original member paths, hashes and page/line/range locators survive normalization. `/api/member?chunk=...&source=...` resolves only indexed member citations and verifies both parent and member hashes. PDF/image members open inline; other members expose focused evidence and a verified download. Archive content requires Copilot review opt-in because containers may mix assessment and ordinary material.

The enrichment pass processed 80 images and 34 ZIPs, with no top-level source failure and 112 reported member skips/limits. There are 298 archive-member chunks in the published index. Oversized market CSV members remain catalog-only, and structured calculation currently targets standalone indexed files, not datasets still inside ZIPs. `.rag/rich-extraction-report.json` and Review show the actual coverage; a successful container pass does not mean every member was read.

## Persistent personal research and backups

`scripts/rag_library.py` owns `.rag/library.sqlite` independently of search generations. It stores conversations (up to 1,000 turns / 8 MB each), drafts, pins, saved passages, answers and calculation snapshots. Questions are committed before inference and replies before delivery, so closing the browser cannot discard a completed server response. Restart recovery preserves interrupted questions with a retry message. Concurrent tab revisions are checked; a stale edit becomes a separate copy instead of overwriting newer work. Saved citations are historical and are re-resolved when opened.

Use Saved → Export library for portable JSON, or Export chat for one conversation. JSON import is not implemented yet; preserve the SQLite database for a full application restore. Delete removes an item from the UI using a tombstone, not secure physical erasure. No cloud sync, encryption-at-rest layer, or multi-user isolation is provided.

**Do not delete `.rag/` to rebuild search.** The search generations/cache are derived; `library.sqlite` is personal data. While the server is running, use SQLite's backup command to include committed WAL content, choosing a new backup filename:

```bash
sqlite3 .rag/library.sqlite ".backup '.rag/library-backup-2026-09-13.sqlite'"
```

Keep a copy outside the working directory on your normal backup storage. For restore, stop the launcher, preserve the existing database and its WAL/SHM sidecars, then restore a consistent SQLite backup as `.rag/library.sqlite` with no stale sidecars. Do not copy only the live main database file while writes are active. Retrieval rebuilds and the Stage 7 enrichment commands do not modify this personal database.

PDF locators refer to physical file pages; printed page labels can differ. DOCX blocks are not pages. PDF overlays use independently extracted Poppler text coordinates; upstream character offsets remain metadata only, and scanned/malformed PDFs or non-PDF formats retain evidence-first fallbacks.
