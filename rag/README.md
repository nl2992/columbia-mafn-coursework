# Local RAG ingestion and search

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

The Stage 5 viewer is available at [http://127.0.0.1:8765/](http://127.0.0.1:8765/) when the service is running. It binds only to `127.0.0.1`, rejects foreign Host/Origin values, emits no CORS permission, serves only allowlisted viewer assets and indexed hash-verified source files, and avoids logging query URLs. No multi-user authentication, TLS, or public deployment is provided. Stop with Ctrl-C; restart after publishing a rebuilt index.

## Stage 5 viewer

The viewer implements the citation-first path:

```text
Search → result card → citation chip → evidence drawer → verified source location
```

The sidebar uses the supplied local Columbia University Mathematics of Finance MA Program lockup at `viewer/maf-logo.png`. Its deep-navy, white, and light-blue treatment is shared by navigation, headings, active states, evidence highlights, and citation chips; no external logo or brand asset is downloaded.

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

Follow-up questions use up to six earlier questions within the same scope and review policy. Earlier answers are not used as source evidence. The tab keeps up to 20 turns in memory; New chat clears questions and replies while preserving pins/filters. Reloading clears chat and pins. No chat database or browser persistence is created. Questions submitted through the form use a POST body rather than the URL.

The installed model is `qwen3:4b` (Q4_K_M, ~2.5 GB), served by Ollama 0.33.3. Weights are in `.rag/models/ollama/`. The adapter sends requests only to `127.0.0.1:11434`, disables proxies/redirects, checks for an installed local model, and does not expose filesystem or tool access to the model. The launcher sets `OLLAMA_NO_CLOUD=1` and binds both services to loopback. It reuses an existing model service and stops only processes it starts.

For another Mac, install Ollama explicitly (`brew install ollama`; Homebrew may refresh dependencies), then start its local service and pull the model once:

```bash
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS="$PWD/.rag/models/ollama" OLLAMA_NO_CLOUD=1 ollama serve
# In a second terminal, while that model service is running:
ollama pull qwen3:4b
```

After provisioning, `python3 scripts/run_rag.py` starts everything. `python3 scripts/rag_search.py serve --port 8765` starts only the viewer/search API. If an existing viewer is already running, the launcher reports its address; restart it to load backend changes. An offline model leaves Evidence excerpts available, while synthesis reports its unavailability explicitly.

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
```

The 22 integration tests build a temporary small corpus with the local embedding model and deterministic synthesis fixtures. The separate retrieval evaluation uses `rag/evaluation.jsonl` and writes `.rag/search-evaluation.json`; its retained result is 14/16 archive cases at five with 68 citations free of provenance/hash/filter errors. Default exits nonzero for core/citation failures; `--strict` also fails for retained challenge/coverage misses.

The live Copilot evaluation uses the installed Qwen model and writes `.rag/copilot-evaluation.json`: 8/8 development checks passed (gamma, Newton/secant comparison, follow-up, unsupported personal-portfolio question, missing course coverage, negation, an instruction-override test, and a synthetic conflict). Answer cases ran in approximately 6–18 seconds warm on this Mac. The initial 7/8 report is preserved in `.rag/copilot-evaluation-initial.json`; its instruction-override failure led to an application filter and regression test. These small smoke sets are not held-out accuracy, exhaustive conflict detection, or general injection-resistance benchmarks.

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
| ZIP | `archive_member_catalog` |

Large CSV/TSV files produce a schema and sample catalog rather than one chunk per row. This keeps the text index useful while leaving room for a future structured-data query layer.

## Design choices

- The source archive is read-only from the pipeline's perspective.
- `.git` and `.rag` are excluded from inventory.
- Duplicate content is hashed once and linked to all source paths.
- Assessment and solution materials are indexed but marked `review_required`.
- PDF page numbers are captured during extraction, not inferred later.
- Chunks carry their original document, artifact version, locator, section, line, sheet, and character offsets.
- Optional OCR is explicit because it is slower and should be reviewed for low-confidence pages.

## Coverage and source integrity

Stage 4 indexes only `Fall 2025`, `Spring 2026`, and `Program-wide` roots, excluding internal application documents. After changing course files, rerun inventory/extract/normalize and then rebuild search. Search rejects changed ingestion artifacts; citation resolution separately checks live source bytes. A running service does not automatically switch to a new generation. Source edits without refreshing ingestion can leave stale search hits, which citation lookup flags.

The current index contains 20,007 chunks from 507 documents, plus metadata for 635 source paths. Of those paths, 123 have no chunks: 103 PDFs, 16 XLS, two DOC, and two C. OCR is not enabled in this baseline. Blank/unsupported extraction records must not be counted as successful text coverage. Images and ZIPs are catalogs; CSV hits describe the dataset schema/sample, not row-level answers.

PDF locators refer to physical file pages; printed page labels can differ. DOCX blocks are not pages. PDF overlays use independently extracted Poppler text coordinates; upstream character offsets remain metadata only, and scanned/malformed PDFs or non-PDF formats retain evidence-first fallbacks.
