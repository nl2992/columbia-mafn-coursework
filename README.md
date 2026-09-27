# Columbia MAFN Coursework Archive

Organized course and program materials for the Columbia MAFN coursework archive.

### **[Open the archive in your browser → nl2992.github.io/columbia-mafn-coursework](https://nl2992.github.io/columbia-mafn-coursework/)**

The hosted site needs no install or sign-in, and everything runs in your browser:

- **Library:** search every extracted page, slide, cell range and code block, then open the PDF at the cited page.
- **Copilot:** ask questions and get answers in seconds, with every quotation checked against its source. Nothing to download: Qwen3 30B answers on Cloudflare Workers AI ([`copilot-worker/`](copilot-worker/)). You can instead choose an in-browser model that runs on your own GPU after a one-time download.
- **Data:** calculate from the original workbook cells.

Search and Data never leave your browser. The hosted Copilot receives only your question and the retrieved passages, and stores nothing. The site's search is keyword-based. For semantic search, saved research, and adding documents, run the full app on a Mac. With no Mac, [open it in GitHub Codespaces](https://codespaces.new/nl2992/columbia-mafn-coursework?quickstart=1), which takes about 10–15 minutes to set up the first time ([details](docs/CODESPACES.md)).

**Full app on a Mac:** [step-by-step Mac setup with screenshots — clone, Download ZIP, pull updates, and launch →](docs/SETUP.md)

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

### See it in action

These screenshots come from a local run of the app against this archive, including the Fall 2026 courses. Everything runs on your Mac: search, the answer model, and calculations.

**1. Search the library and open the exact page.** Type a concept, narrow it with the filters (here **Term → Fall 2026**), and pick a result. The reader opens the cited PDF page, slide, or cell range. Searching *change of numeraire* goes straight to page 271 of the IEOR4735 lecture notes, with the Björk slides and F8 lecture listed next.

![Library search for "change of numeraire" filtered to Fall 2026, with the IEOR4735 lecture notes open at page 271](docs/images/demo-library-search.png)

**2. Check the evidence.** **Evidence & details** shows the verified source path, a stable citation (`IEOR4735_LectureNotes_F1-F14.pdf · p. 271`), and the passage that matched. **Pin document** adds the file to a Copilot question's scope, and **Save passage** keeps the passage in **Saved**.

![Evidence and details drawer showing the source path, citation chip, and matched passage](docs/images/demo-evidence.png)

**3. Ask the Copilot.** Open **Copilot**, optionally set a course filter, and ask in plain English. The local Qwen3 4B model answers only from retrieved passages. Each claim links to its source and carries a supporting quotation that was checked against that source. Asked how Homework I approximates *E[Y|X]*, it answers from cell 6 of the MATHGR5400 notebook. If the evidence is too weak, it declines to answer.

![Copilot answering a question about conditional expectation and regression with citations to HW1-2026-Columbia.ipynb cell 6](docs/images/demo-copilot.png)

**4. Calculate from the original cells.** In **Data**, choose a workbook or dataset, give it an explicit range, and run an operation. Here, the mean of NSW supermarket sales in `retail.xlsx` for STATGR5263 HW1. The result carries its source range, the matching rows, and a recipe you can replay, and you can save or export it.

![Data workspace computing the mean of column B in retail.xlsx with the source cells listed below](docs/images/demo-data.png)

**5. Confirm what is indexed.** **Coverage** shows the index size and any files without searchable text, along with each refresh job and its result. **Add docs** imports new files and publishes them to GitHub (see below).

![Coverage view: 30,116 chunks, 671 documents, 677 source paths, 0 paths without text, 4 terms](docs/images/demo-coverage.png)

### One-click setup and launch on macOS

On a new Mac with Homebrew installed, clone the repository and double-click **`Course Archive.app`** (or **`START HERE - Open Course Archive.command`**). When the local index is absent, the launcher opens **`SET UP THIS MAC.command`** in Terminal automatically. It installs the pinned local runtime and document tools, downloads and verifies both local models, builds the private index, installs the Desktop app, and opens it. See the **[illustrated setup guide](docs/SETUP.md)** for prerequisites, screenshots, GitHub access, document publishing, and troubleshooting.

After `git pull`, open the repository folder and double-click the navy-and-Columbia-blue **`Course Archive.app`** icon. It starts the local viewer and answer model, waits for the archive to be ready, and opens the UI in the default browser. If macOS blocks the unsigned local app the first time, Control-click it, choose **Open**, then confirm **Open**. **`START HERE - Open Course Archive.command`** is the clearly named double-clickable Terminal fallback.

```text
git pull → double-click Course Archive.app → the local UI opens
```

If startup fails, the app shows an alert and opens `.rag/logs/course-archive-app.log` with the exact error instead of failing invisibly. Simultaneous clicks share a launcher lock and wait for the same local service, avoiding port-conflict alerts.

To place a working app icon directly on the Desktop, double-click **`INSTALL ON DESKTOP.command`** once. It copies the universal native macOS applet to `~/Desktop/Course Archive.app`, records the location of this checkout, applies a local ad-hoc signature, registers the app with Finder, and launches it. Future code and document updates still come from `git pull` in the repository; the Desktop app delegates to the launch script in that checkout, so launcher updates also take effect after pulling. Desktop copies installed before this fix need **`INSTALL ON DESKTOP.command`** once.

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

With Fall 2026 added, the local generation covers all 677 course and program-wide source paths: 671 canonical documents, 30,116 searchable chunks, and 189,908 semantic windows, with zero empty extraction outcomes and zero extraction errors. The release gate requires those zero-gap counts. On this generation, one curated retrieval case, `levy-price-distribution`, returns the expected paper at the wrong page (page 3 now ranks sixth) and is flagged as a regression. See [status.md](status.md) before relying on the gate result.

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

## Fall 2026

| Course | Focus | Documentation |
| --- | --- | --- |
| IEOR4735 | Continuous Time Finance | [Course README](<Fall 2026/IEOR4735 - Continuous Time Finance/README.md>) |
| MATHGR5400 | Nonlinear Option Pricing | [Course README](<Fall 2026/MATHGR5400 - Nonlinear Option Pricing/README.md>) |
| MATHGR5521 | Topics in Mathematical Finance | [Course README](<Fall 2026/MATHGR5521 - Topics in Mathematical Finance/README.md>) |
| STATGR5263 | Statistical Inference & Time Series Modeling | [Course README](<Fall 2026/STATGR5263 - Statistical Inference & Time Series Modeling/README.md>) |
| STATGR5293 | Statistical Aspects of Finance | [Course README](<Fall 2026/STATGR5293 - Statistical Aspects of Finance/README.md>) |

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
