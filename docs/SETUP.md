# Set up Course Archive on your Mac

[← Back to the README](../README.md)

Get the files from GitHub, run the first-time setup, then open **Course Archive** from your Desktop. These screenshots show the actual repository's **Code** menu.

**Already installed?** Go straight to [Pull updates](#pull-updates-on-an-existing-installation).

**New installation?** Use [Clone with Git](#option-a-clone-with-git-recommended). If you already downloaded a ZIP, follow [the ZIP instructions](#option-b-download-a-zip).

## Before you start

- Use a Mac. The current local installation has been verified on Apple silicon; a full fresh installation on Intel has not been verified.
- Allow roughly 12 GB of free space, plus room for future documents and generated data.
- Keep an internet connection during setup. Model downloads and the first full archive index build take time; the first launch is not instant.
- Install [Homebrew from its official website](https://brew.sh/) if you do not already have it. Follow its **Next steps** instructions when installation finishes.
- Open **Terminal** using Spotlight: press **Command–Space**, type **Terminal**, and press **Return**.

Check the prerequisites in Terminal:

```bash
brew --version
git --version
```

If macOS prompts you to install Command Line Tools, finish that installation before continuing. If Git is missing, run `xcode-select --install` and follow the macOS installer.

Reading/downloading a public repository does not require a GitHub account. If access is restricted, sign in with an authorized account. Publishing documents back to GitHub requires write access.

## Option A: clone with Git (recommended)

### 1. Open the repository and click Code

Open [Course Archive on GitHub](https://github.com/nl2992/columbia-mafn-coursework). Select **main**, click the green **Code** button, and select **HTTPS**. The copy button beside the URL copies the clone address.

![GitHub Code menu showing the HTTPS clone URL and Download ZIP](images/setup-github-download.png)

### 2. Download a working checkout

Paste these commands into Terminal. They create a new `columbia-mafn-coursework` folder inside your home folder. If you already have that folder, use [Pull updates](#pull-updates-on-an-existing-installation) instead.

```bash
cd ~
brew install git-lfs
git lfs install
git clone https://github.com/nl2992/columbia-mafn-coursework.git
cd columbia-mafn-coursework
git lfs pull
```

Git LFS downloads the actual PDFs and other course assets. Let it finish before starting setup.

**Already use SSH with GitHub?** You can use the **SSH** tab instead of HTTPS:

![GitHub Code menu showing the SSH clone address](images/setup-github-clone.png)

Use this clone command in place of the HTTPS clone command above:

```bash
git clone git@github.com:nl2992/columbia-mafn-coursework.git
```

Then continue with [Run setup](#run-setup).

## Option B: download a ZIP

### 1. Download and extract it

On [the repository page](https://github.com/nl2992/columbia-mafn-coursework), click **Code → Local → Download ZIP**, at the bottom of the menu shown below.

![Download ZIP at the bottom of GitHub's Code menu](images/setup-github-download.png)

In Finder, open **Downloads** and double-click `columbia-mafn-coursework-main.zip`. Finder extracts a folder named `columbia-mafn-coursework-main`.

### 2. Create a working checkout before installing

**The ZIP alone is not a runnable installation.** It has no `.git` directory, cannot receive `git pull` updates, and may contain Git LFS pointers instead of the actual course files. The current setup script requires a Git checkout for `git lfs pull`.

Keep the extracted ZIP if you want it for browsing. To install the app, open Terminal and run:

```bash
cd ~
brew install git-lfs
git lfs install
git clone https://github.com/nl2992/columbia-mafn-coursework.git
cd columbia-mafn-coursework
git lfs pull
```

This creates a separate working folder at `~/columbia-mafn-coursework`; it does not overwrite the extracted ZIP. **Run setup in this cloned folder, not in Downloads.** Do not copy ZIP files over an existing installation or replace its `.rag` folder.

## Run setup

From inside your cloned `columbia-mafn-coursework` folder, run:

```bash
/bin/zsh "SET UP THIS MAC.command"
```

Or open that folder in Finder with `open .` and double-click **SET UP THIS MAC.command**. Opening **Course Archive.app** or **START HERE - Open Course Archive.command** also opens setup automatically when the local index is missing.

Leave the Terminal window open while the seven numbered stages finish:

| Stage | What setup does |
| --- | --- |
| 1 | Fetches the Git LFS course files |
| 2 | Installs pinned Python packages in `.rag/runtime` |
| 3 | Installs Ollama, Tesseract, Poppler and LibreOffice |
| 4 | Downloads and checksum-verifies the MiniLM search model |
| 5 | Downloads the Qwen answer model with Ollama |
| 6 | Builds the local search index if absent |
| 7 | Installs the Desktop app and opens it |

Setup also installs Homebrew Python if needed. Homebrew may display installer prompts. Downloads and indexing can take a long time; wait for **“Setup complete. Course Archive is installed on your Desktop.”** If setup stops, read the last error and rerun the same command after addressing it.

If macOS blocks a downloaded app, review the warning and use Apple's [instructions for opening an app from an unidentified developer](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac) only after verifying the source. The Terminal command above provides a direct way to run the repository's setup script.

## Open Course Archive

Double-click **Course Archive** on your Desktop. The launcher starts the local viewer and answer model, waits for readiness, and opens your default browser at [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

![Course Archive home screen after installation](images/course-archive-home.png)

Keep the cloned repository in place: the Desktop app points to that folder. If you move it, run **INSTALL ON DESKTOP.command** from the new location.

To check the service from Terminal:

```bash
curl http://127.0.0.1:8765/api/health
```

A successful response contains `"status": "ok"` and document/index counts. The verified existing archive currently has 629 canonical documents; counts can change as documents are added.

## Pull updates on an existing installation

Open Terminal and change into **your existing checkout**. For the original installation on this Mac:

```bash
cd "$HOME/Desktop/Canvas Files"
git pull --ff-only
git lfs pull
```

If you followed the new-clone steps above, use this path instead:

```bash
cd "$HOME/columbia-mafn-coursework"
git pull --ff-only
git lfs pull
```

Then open **Course Archive** on the Desktop. Do not run both path examples: choose the one where your installation lives. If Git reports local changes or a divergent branch, keep your changes and resolve that message before continuing; do not delete the checkout.

The Desktop launcher reads the launch script from the checkout, so future script fixes arrive with `git pull`. If your Desktop app predates the September 22 launcher fix, or an update changes the native app bundle, refresh it once:

```bash
/bin/zsh "INSTALL ON DESKTOP.command"
```

A pull does not restart an already running server. If it is running in a Terminal window, stop that launcher with **Control–C**, then open the app again. For a background Desktop launch, logging out and back in before opening the app is a simple way to ensure updated code is loaded.

If the pull adds or changes course documents, refresh the existing index from the checkout:

```bash
python3 scripts/rag_operations.py refresh
```

Your saved research lives in `.rag/library.sqlite`. Back it up and keep the `.rag` folder; do not delete it to apply updates.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| `brew: command not found` | Install Homebrew and complete the shell configuration under its **Next steps** |
| `not a git repository` | You are in a ZIP extraction or the wrong folder; use the cloned folder from Option A |
| GitHub access error | Check the repository URL and your account access; SSH also requires a configured SSH key |
| Course files appear as short text beginning `version https://git-lfs.github.com/spec/v1` | Run `git lfs install` and `git lfs pull` inside the checkout |
| Ollama reported missing despite being installed | Pull the launcher fix and rerun `INSTALL ON DESKTOP.command` |
| Local model or Python package missing | Rerun `SET UP THIS MAC.command` and inspect the last error if it stops |
| Browser cannot connect | Open the Desktop app and wait; check `.rag/logs/course-archive-app.log` |
| Desktop icon points to an old location | Run `INSTALL ON DESKTOP.command` from the intended checkout |

The exact startup error is recorded in `.rag/logs/course-archive-app.log`; Ollama startup messages are in `.rag/logs/ollama.log`.

## Add your own documents

Open **Add docs**, choose the destination course folder, select your files, and click **Import, verify & publish**. This workflow publishes source files to GitHub and requires write access. It verifies files, indexes them, runs validation, and reports the publishing status.

![Course Archive Add documents screen](images/course-archive-add-docs.png)

For supported formats, recovery commands and local backups, see the [RAG operations runbook](../rag/README.md).
