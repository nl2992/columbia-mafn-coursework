# Run the Course Archive in GitHub Codespaces

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/nl2992/columbia-mafn-coursework?quickstart=1)

Codespaces runs the full app in a cloud Linux machine that belongs to you. That includes library search with the exact-page reader, the Copilot and the Data workspace. You need a GitHub account, but not a Mac, Homebrew, or anything installed locally.

## Start it

1. Click **Open in GitHub Codespaces** above, or on the repository page choose **Code → Codespaces → Create codespace on main**.
2. Wait for setup to finish. The first start takes about 10–15 minutes while it:
   - installs the pinned Python packages, Poppler and Tesseract
   - fetches the course PDFs through Git LFS
   - downloads and verifies the MiniLM embedding model, Ollama and Qwen3 4B
   - downloads the prebuilt search index from the [`codespace-index` release](https://github.com/nl2992/columbia-mafn-coursework/releases/tag/codespace-index)
3. The archive opens in a new browser tab when port **8765** is ready. If it doesn't, open the **Ports** tab and click the globe icon next to **Course Archive (8765)**.

Later starts of the same codespace skip setup and are ready in about a minute. Codespaces stop after 30 minutes idle. Open the codespace again from [github.com/codespaces](https://github.com/codespaces), and the app restarts on its own.

## What to expect

| Feature | In Codespaces |
| --- | --- |
| Library search, filters, exact-page PDF reader, evidence drawer | Same as on a Mac |
| Copilot (Qwen3 4B) | Works, but CPU-only. An answer takes about 1–5 minutes instead of under a minute. |
| Data workspace | Same as on a Mac |
| PowerPoint slide previews | Not available. LibreOffice isn't installed, so use **Open original**. |
| Saved conversations and passages | Stored only in that codespace. Export them before deleting the codespace. |
| Add docs | Imports into that codespace's copy only. Publish from a Mac checkout instead. |

Port 8765 is **private** by default, so only you can open it while signed in to GitHub. The server accepts requests only from `localhost` and from this codespace's own forwarded address.

## Cost

Codespaces usage is billed to the person who creates the codespace, not to the repository. A 4-core machine uses 4 core-hours per hour from GitHub's monthly free allowance. Delete codespaces you no longer need at [github.com/codespaces](https://github.com/codespaces).

## Troubleshooting

- **The page never opens.** Run `bash .devcontainer/start.sh` in the terminal and read `.rag/logs/codespace-app.log`.
- **The Copilot reports the model is unavailable.** Check `.rag/logs/ollama.log`. On a busy 4-core machine, retry once the first answer has loaded the model.
- **Setup failed partway.** Run `bash .devcontainer/setup.sh` again. Each step is safe to repeat.
- **Recently added files are not searchable.** The codespace uses the index published in the release. After adding documents on a Mac and refreshing the index there, republish it (see below).

## Maintainers: republish the index

After course files change and the Mac index has been refreshed, commit and push the files, then run this from the repository root:

```bash
./scripts/package_codespace_index.sh --publish
```

The script refuses to run if course files differ from `HEAD`. It records the generation and commit it was built from, and uploads `course-archive-index.tar.gz` and its SHA-256 to the `codespace-index` release. The bundle contains only the search index and extracted text. Personal research (`.rag/library.sqlite`), models, OCR caches and backups are never included. New codespaces pick up the updated index. Existing ones keep theirs until you delete `.rag/search/CURRENT.json` and rerun `bash .devcontainer/setup.sh`.
