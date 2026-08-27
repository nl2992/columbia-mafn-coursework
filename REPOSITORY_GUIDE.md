# Private GitHub export guide

This workspace is prepared for a private GitHub export, but it has not been published and no remote has been configured.

## Before the first commit

1. Install Git and Git LFS, then run `git lfs install`.
2. Review [CONTENT-NOTICE.md](CONTENT-NOTICE.md) and confirm that every intended source file may be stored in your private repository.
3. Check the archive size and the largest files. The three largest ZIP archives are close to GitHub’s single-file limit; Git LFS is required for this archive.
4. Review `git status --short` and confirm that no credentials, personal data, or unrelated files are present.

For this workspace specifically, the local Git repository is already initialized on `main`, but it has no commits and no remote. Git LFS was not installed when this guide was prepared. Install it before staging any binary or data files.

## Recommended single-repository export

From the repository root:

```bash
git init
git lfs install
git add .
git lfs status
git status --short
git commit -m "Organize MAFN course archive"
git branch -M main
git remote add origin git@github.com:OWNER/PRIVATE-REPO.git
git push -u origin main
```

Create the GitHub repository as **private** and empty when possible; the local README and history already exist. Replace `OWNER/PRIVATE-REPO` with the intended private repository.

## Recommended staged upload for this archive

Because the archive is large, committing by top-level area makes progress easier to inspect and retry:

```bash
cd "/Users/nigelli/Desktop/Canvas Files"
brew install git-lfs
git lfs install

git add .gitignore .gitattributes CONTENT-NOTICE.md INDEX.md README.md REPOSITORY_GUIDE.md TEXTBOOK_CATALOG.md
git commit -m "Add archive documentation and export policy"

git add "Fall 2025"
git commit -m "Add Fall 2025 course archive"

git add "Spring 2026" "Program-wide"
git commit -m "Add Spring 2026 and program materials"

git lfs ls-files
git remote add origin git@github.com:OWNER/PRIVATE-REPO.git
git push -u origin main
```

If you prefer one initial commit, replace the three `git add`/`git commit` blocks with `git add .` and one commit after Git LFS is installed. Do not run `git add .` before installing Git LFS.

## Optional one-repository-per-module export

Each course-level directory is self-contained enough to serve as a separate repository root. If you choose separate private repositories, copy or export one course directory at a time into a clean working directory, retain its course README, and include `.gitattributes` plus [CONTENT-NOTICE.md](CONTENT-NOTICE.md) in each repository. Do not create nested `.git` directories inside this archive unless you intentionally want independent repositories.

Suggested private repository slugs:

| Source module | Suggested slug |
| --- | --- |
| MATHGR5010 | `mathgr5010-intro-math-finance-fall-2025` |
| STAT5264-2 | `stat5264-stochastic-processes-fall-2025` |
| STATGR5264 | `statgr5264-stochastic-processes-applications-fall-2025` |
| MATHGR5030 | `mathgr5030-numerical-methods-finance-spring-2026` |
| MATHGR5360 | `mathgr5360-financial-price-analysis-spring-2026` |
| MATHGR5380 | `mathgr5380-multi-asset-portfolio-management-spring-2026` |
| MATHGR5450 | `mathgr5450-credit-analytics-spring-2026` |
| STATGR5265 | `statgr5265-stochastic-methods-finance-spring-2026` |

The naming suggestions are optional; choose names that match your existing private GitHub organization.

## What this preparation does not do

- It does not create a GitHub repository.
- It does not add credentials or configure a remote.
- It does not push any files.
- It does not convert existing files into Git LFS pointer files until the first Git add/commit is performed with Git LFS installed.
