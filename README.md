# Columbia MAFN Coursework Archive

Organized course and program materials for the Columbia MAFN coursework archive.

Each course folder contains its own `README.md` with the course map, module sequence, and links to the organized materials. Source filenames and explicit version variants are preserved unless a directory name was normalized for navigation.

## Local RAG research assistant

This repository includes a source-grounded RAG for searching the coursework archive, inspecting the exact cited page or locator, and asking questions with a local evidence-checked Copilot. The original course files remain authoritative; the rebuildable index is intentionally ignored from Git under `.rag/`.

Key features:

- Hybrid lexical and offline semantic retrieval with course, term, material, lecturer, file-type, folder, and review filters.
- Stable citations that preserve source aliases, versions, hashes, and exact PDF pages, slides, ranges, cells, or blocks.
- Local viewer with evidence drawer, PDF page jumps and text overlays, PowerPoint slide previews, format-aware fallbacks, deep links, and coverage/review views.
- Local Qwen3 4B Copilot with follow-up questions, pinned-document scope, review-policy warnings, exact supporting quotations, abstention, conflict presentation, and citation click-through.
- Persistent conversations, drafts and pins, with a Saved area for passages, answers, and calculation snapshots; JSON exports keep research portable.
- Stage 7 Data workspace: workbook sheets, original cells/formulas, dataset schemas, explicit date interpretation, and reproducible numerical operations with source/engine fingerprints.
- Image OCR and bounded nested ZIP search with member-level provenance, verified member opening, and visible extraction limits.
- Stage 8 incremental refresh with change detection, retryable jobs, saved filter views, consistent research backups, automatic generation adoption, and an auditable release gate.
- CU-themed responsive interface built around the supplied Columbia Mathematics of Finance lockup, with deep navy navigation, Columbia-blue evidence states, and a structured two-step Data workflow.
- Loopback-only service, source-hash verification, no external inference upload, and regression/browser acceptance checks.

Personal research lives in Git-ignored `.rag/library.sqlite`. Unlike the index, it cannot be rebuilt from the course files. Back it up; do not delete the whole `.rag/` directory to refresh search.

### One-click setup and launch on macOS

On a new Mac, clone the repository and double-click **`SET UP THIS MAC.command`**. It installs the pinned local runtime and document tools, downloads and verifies both local models, builds the private index, installs the Desktop app, and opens it. See the **[illustrated setup guide](docs/SETUP.md)** for prerequisites, screenshots, GitHub access, document publishing, and troubleshooting.

After `git pull`, open the repository folder and double-click the navy-and-Columbia-blue **`Course Archive.app`** icon. It starts the local viewer and answer model, waits for the archive to be ready, and opens the UI in the default browser. If macOS blocks the unsigned local app the first time, Control-click it, choose **Open**, then confirm **Open**. **`START HERE - Open Course Archive.command`** is the clearly named double-clickable Terminal fallback.

```text
git pull → double-click Course Archive.app → the local UI opens
```

If startup fails, the app shows an alert and opens `.rag/logs/course-archive-app.log` with the exact error instead of failing invisibly. Simultaneous clicks share a launcher lock and wait for the same local service, avoiding port-conflict alerts.

To place a working app icon directly on the Desktop, double-click **`INSTALL ON DESKTOP.command`** once. It copies the universal native macOS applet to `~/Desktop/Course Archive.app`, records the location of this checkout, applies a local ad-hoc signature, registers the app with Finder, and launches it. Future code and document updates still come from `git pull` in the repository; the Desktop app continues to launch that checkout.

The equivalent command is:

```bash
python3 scripts/run_rag.py --port 8765 --open
```

One-time setup on a new Mac:

```bash
./SET\ UP\ THIS\ MAC.command
```

The setup command handles Git LFS, pinned Python packages in the project-local `.rag/runtime`, local document tools, verified model downloads, the first index build, and Desktop installation. Routine pulls on an already provisioned Mac need only the app click. The `.app` stays inside the repository because its launcher resolves the scripts and local index relative to that folder.

### Add documents and publish them

Open **Add docs** in the app, choose an existing course or program folder, select up to 20 supported documents, then click **Import, verify & publish**. Each file is checksum-verified and saved locally without overwriting an existing filename. In the background the app runs incremental extraction and OCR, rebuilds the index, runs the full Stage 8 release gate, commits only the uploaded source files through Git LFS, and pushes the current branch to `origin`. The status card shows every stage and the resulting commit.

Files may be PDF, PowerPoint, Word, Excel, CSV/TSV, notebook, code/text/Markdown/TeX, image, or ZIP. The limit is 64 MB per file and 128 MB per batch. Choose an existing folder so course metadata remains predictable; create and document a new course folder in Git before using it as a destination. If indexing, release validation, authentication, or pushing fails, the documents remain in the selected local folder and the job card keeps the error. Fix the reported problem and submit the uncommitted files again after moving or renaming the originals, or use the manual recovery commands in [rag/README.md](rag/README.md#document-intake-and-github-publishing).

### Run it stage by stage

Run these commands from the repository root. Stages 1–3 create the derived ingestion records, Stage 4 builds retrieval, Stage 5 opens the citation-first viewer, Stage 6 adds local synthesis, Stage 7 adds rich data, and Stage 8 operates and evaluates the release.

```bash
# Stage 1 — inventory the archive
python3 scripts/rag_pipeline.py inventory

# Stage 2 — extract text and format-aware locators
python3 scripts/rag_pipeline.py extract

# Stage 3 — normalize, preserve provenance, and chunk
python3 scripts/rag_pipeline.py normalize

# Stage 4 — build the lexical + semantic search index
python3 scripts/rag_search.py build

# Stage 5 — start the source viewer and search API
python3 scripts/rag_search.py serve --port 8765
```

Open [the local viewer](http://127.0.0.1:8765/) after Stage 5. To run Stages 5–6 together with the local Qwen model, stop the Stage 5 process and use:

```bash
python3 scripts/run_rag.py --open
```

For a fresh machine, run [`SET UP THIS MAC.command`](SET%20UP%20THIS%20MAC.command), which provisions the pinned dependencies and both local models before building the index. The full API, runtime, rebuild, OCR, test, evaluation, coverage, and locator instructions are in [rag/README.md](rag/README.md); the implementation plan is in [plan.md](plan.md) and the living delivery record is in [status.md](status.md).

The accepted local generation represents all 635 course/program-wide source paths: 629 canonical documents, 28,056 searchable chunks, 186,176 semantic windows, zero empty extraction outcomes, and zero extraction errors. The release gate requires those zero-gap counts and passes all 18 checks.

Stage 7 (after the baseline ingestion; Tesseract and the ingestion libraries must be installed):

```bash
python3 -m pip install --break-system-packages --target .rag/runtime -r rag/requirements-data.txt
python3 scripts/rag_rich.py
python3 scripts/rag_pipeline.py normalize
python3 scripts/rag_search.py build
# Start the local viewer and Copilot:
python3 scripts/run_rag.py
```

Open [Data](http://127.0.0.1:8765/?view=data). Choose a source and sheet, preview its cells, then confirm the range, column and operation. Save or export the result with its recipe. The [Stage 7 runbook](rag/README.md#stage-7-data-images-and-archives) explains limitations, replay, and personal-library backup.

Stage 8 refresh and release gate:

```bash
python3 scripts/rag_operations.py scan
python3 scripts/rag_operations.py refresh
python3 scripts/evaluate_rag_release.py
```

The refresh reuses unchanged extraction and embeddings, records added/changed/deleted sources, backs up personal research, and publishes atomically. A running viewer adopts the new generation between requests. The release command combines retrieval, archive-wide citation/coverage, performance, size, extraction, and live Copilot checks; thresholds are versioned in [rag/release-thresholds.json](rag/release-thresholds.json).

## Fall 2025

| Course | Focus | Documentation |
| --- | --- | --- |
| MATH5050 | Practitioners Seminar | [Course README](<Fall 2025/MATH5050 - Practitioners Seminar/README.md>) |
| MATHGR5010 | Intro to the Math of Finance | [Course README](<Fall 2025/MATHGR5010 - Intro to the Math of Finance/README.md>) |
| STAT5264-2 | Stochastic Processes | [Course README](<Fall 2025/STAT5264-2 - Stochastic Processes/README.md>) |
| STATGR5264 | Stochastic Processes: Applications I | [Course README](<Fall 2025/STATGR5264 - Stochastic Processes-Applications I/README.md>) |

## Spring 2026

| Course | Focus | Documentation |
| --- | --- | --- |
| MATHGR5030 | Numerical Methods in Finance | [Course README](<Spring 2026/MATHGR5030 - Numerical Methods in Finance/README.md>) |
| MATHGR5320 | Financial Risk Management and Regulation | [Course README](<Spring 2026/MATHGR5320 - Financial Risk Mgmt & Regulation/README.md>) |
| MATHGR5360 | Mathematical Methods: Financial Price Analysis | [Course README](<Spring 2026/MATHGR5360 - Math Methods - Financial Price Analysis/README.md>) |
| MATHGR5380 | Multi-Asset Portfolio Management | [Course README](<Spring 2026/MATHGR5380 - Multi-Asset Portfolio Mgmt/README.md>) |
| MATHGR5450 | Credit Analytics | [Course README](<Spring 2026/MATHGR5450 - Credit Analytics/README.md>) |
| STATGR5265 | Stochastic Methods in Finance | [Course README](<Spring 2026/STATGR5265 - Stochastic Methods in Finance/README.md>) |

## Program-wide materials

| Collection | Contents | Documentation |
| --- | --- | --- |
| GSAS Fall 2025 Orientation | Orientation assets | [Collection README](<Program-wide/GSAS Fall 2025 Orientation/README.md>) |
| MAFN Infinity | Cross-course syllabi and program assets | [Collection README](<Program-wide/MAFN Infinity/README.md>) |

## Organization conventions

- `lectures/` contains lecture notes, slides, handouts, and module sequences.
- `assignments/` contains homework, problem sets, projects, and quizzes; `solutions/` contains retained answer materials.
- `assessments/` contains exams, practice exams, and diagnostic material.
- `readings/` and `reference/` contain research papers, course references, syllabi, and supporting material.
- `computational/`, `code/`, `data/`, `workbooks/`, `experiments/`, and `source/` preserve the computational relationships of the relevant courses.
- `sessions/` groups practitioner-seminar material by date and speaker.

## Privacy and rights

This archive contains course, assessment, solution, institutional, and third-party materials. Keep it private and follow the restrictions attached to the source documents.
