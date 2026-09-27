#!/usr/bin/env bash
# Package the published search generation for Codespaces and optionally upload it to the
# `codespace-index` GitHub release that .devcontainer/setup.sh downloads.
# Only what the server reads is included: never personal research (.rag/library.sqlite), models,
# runtimes, OCR caches, backups, or job logs (which record local paths).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
generation="$(python3 -c 'import json; print(json.load(open(".rag/search/CURRENT.json"))["generation"])')"
commit="$(git rev-parse HEAD)"
if ! git diff --quiet HEAD -- 'Fall *' 'Spring *' 'Summer *' 'Winter *' 'Program-wide' || \
   [[ -n "$(git ls-files --others --exclude-standard -- 'Fall *' 'Spring *' 'Summer *' 'Winter *' 'Program-wide')" ]]; then
  echo "Course files differ from HEAD; commit them and refresh the index before packaging." >&2
  exit 1
fi

python3 - "${generation}" "${commit}" <<'EOF'
import datetime, json, sys
json.dump({'generation': sys.argv[1], 'commit': sys.argv[2],
           'packaged_at': datetime.datetime.now(datetime.timezone.utc).isoformat()},
          open('.rag/codespace-index.json', 'w'), indent=2)
EOF

mkdir -p dist
out="dist/course-archive-index.tar.gz"
members=(.rag/codespace-index.json .rag/manifest.jsonl .rag/chunks.jsonl .rag/extracted
         .rag/search/CURRENT.json ".rag/search/generations/${generation}")
for name in extraction-report.json rich-extraction-report.json review-queue.jsonl operations-review.jsonl; do
  [[ -f ".rag/${name}" ]] && members+=(".rag/${name}")
done
COPYFILE_DISABLE=1 tar -czf "${out}" "${members[@]}"
(cd dist && shasum -a 256 course-archive-index.tar.gz > course-archive-index.tar.gz.sha256)
echo "Packaged generation ${generation} (commit ${commit:0:7}): $(du -h "${out}" | cut -f1)"

if [[ "${1:-}" == "--publish" ]]; then
  notes="Prebuilt search index for GitHub Codespaces. Generation ${generation}, built from ${commit}."
  if gh release view codespace-index >/dev/null 2>&1; then
    gh release upload codespace-index "${out}" "${out}.sha256" --clobber
    gh release edit codespace-index --notes "${notes}"
  else
    gh release create codespace-index "${out}" "${out}.sha256" --title "Codespaces search index" --notes "${notes}" --latest=false
  fi
fi
