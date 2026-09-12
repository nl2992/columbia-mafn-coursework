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
- Loopback-only service, source-hash verification, no external inference upload, and a 22-test integration suite plus live Copilot checks.

### Run it stage by stage

Run these commands from the repository root. Stages 1–3 create the derived ingestion records, Stage 4 builds retrieval, Stage 5 opens the citation-first viewer, and Stage 6 adds local synthesis.

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
python3 scripts/run_rag.py
open 'http://127.0.0.1:8765/?view=copilot'
```

For a fresh machine, install the pinned search dependencies from [rag/README.md](rag/README.md), provision the local MiniLM embedding snapshot, and install/pull Ollama’s `qwen3:4b` model for Stage 6. The full API, runtime, rebuild, OCR, test, evaluation, coverage, and locator instructions are in [rag/README.md](rag/README.md); the implementation plan is in [plan.md](plan.md) and the living delivery record is in [status.md](status.md).

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
