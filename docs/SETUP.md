# Course Archive setup guide

This guide takes a Mac from a fresh GitHub clone to the CU-themed Course Archive app on the Desktop. The archive runs locally: its derived index, saved research, and model files stay under the checkout's Git-ignored `.rag/` folder.

## What you need

- macOS on Apple silicon or Intel
- about 12 GB of free disk space for the repository, local models, dependencies, and search index
- a reliable internet connection for the first setup
- access to the private GitHub repository
- permission to push to the repository if you will use **Add docs** to publish files
- [Homebrew](https://brew.sh/) installed

The first index build processes the full course archive and can take a long time. Later launches and incremental document uploads reuse the local index.

## 1. Clone the repository

Open Terminal and use either SSH:

```bash
git clone git@github.com:nl2992/columbia-mafn-coursework.git
cd columbia-mafn-coursework
```

or HTTPS:

```bash
git clone https://github.com/nl2992/columbia-mafn-coursework.git
cd columbia-mafn-coursework
```

GitHub must authorize your account to read this private repository. To publish new documents, configure a GitHub account with write access. For HTTPS, [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login) is the simplest route:

```bash
brew install gh
gh auth login
```

## 2. Run the one-time setup

In Finder, open the cloned folder and double-click **SET UP THIS MAC.command**. You can run the same setup from Terminal:

```bash
./SET\ UP\ THIS\ MAC.command
```

If macOS blocks the file, Control-click it, choose **Open**, then confirm **Open**. The setup is safe to run again after an interrupted download or build.

The command:

1. retrieves Git LFS course files;
2. installs pinned Python packages into `.rag/runtime`;
3. installs Ollama, Tesseract, Poppler, and LibreOffice through Homebrew;
4. downloads and verifies the pinned MiniLM search model;
5. downloads the local `qwen3:4b` answer model;
6. builds the private local index when it is absent; and
7. installs and opens `Course Archive.app` on the Desktop.

## 3. Launch the app

After setup, double-click **Course Archive.app** on the Desktop. It starts the local services, waits until the archive is ready, and opens the UI in the default browser.

![Course Archive library screen](images/course-archive-home.png)

For routine updates, pull the latest repository changes and open the Desktop app:

```bash
cd ~/path/to/columbia-mafn-coursework
git pull --ff-only
```

The Desktop app remembers the checkout path. If a pull changes `Course Archive.app` or its launcher, double-click **INSTALL ON DESKTOP.command** again to refresh the Desktop copy.

## 4. Add and publish documents

Open **Add docs**, choose an existing archive folder, and select up to 20 documents. The app accepts PDF, PowerPoint, Word, Excel, CSV/TSV, notebooks, code/text/Markdown/TeX, images, and ZIP archives. Each file can be up to 64 MB; a batch can be up to 128 MB.

![Course Archive Add documents screen](images/course-archive-add-docs.png)

Click **Import, verify & publish**. The app then:

1. verifies and saves the selected files without overwriting existing names;
2. runs incremental extraction and OCR;
3. rebuilds and validates the search index;
4. commits only the uploaded source files through Git LFS; and
5. pushes the current branch to `origin`.

Keep the browser tab open while the job runs. The status card shows the active stage, commit, push result, and any error. If validation or GitHub publishing fails, the local files stay in the selected folder so the issue can be corrected without uploading them again.

## Troubleshooting

The launcher writes its exact error to:

```text
.rag/logs/course-archive-app.log
```

Useful checks from the repository root are:

```bash
# Repeat or repair setup
./SET\ UP\ THIS\ MAC.command

# Refresh the Desktop app copy
./INSTALL\ ON\ DESKTOP.command

# Confirm that the local UI is healthy
curl http://127.0.0.1:8765/api/health

# Confirm GitHub access before publishing documents
git fetch origin
git push --dry-run origin HEAD
```

If the app says the local answer model is missing, rerun **SET UP THIS MAC.command**. If Finder still shows an older app after a pull, rerun **INSTALL ON DESKTOP.command** and then open the new Desktop copy.

For extraction recovery, manual stage commands, backups, API details, and release checks, see the [RAG operations runbook](../rag/README.md).
