#!/usr/bin/env bash
# Start the archive viewer and local answer model in the background, then wait until it is ready.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
mkdir -p .rag/logs

if curl --silent --fail --max-time 2 http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
  echo "Course Archive is already running on port 8765."
  exit 0
fi
nohup python3 scripts/run_rag.py --port 8765 >> .rag/logs/codespace-app.log 2>&1 &
for _ in $(seq 1 240); do
  if curl --silent --fail --max-time 2 http://127.0.0.1:8765/api/health >/dev/null 2>&1; then
    echo "Course Archive is ready. Open the Ports tab and click the globe icon on port 8765 if the browser did not open."
    exit 0
  fi
  sleep 1
done
echo "Course Archive did not start; see .rag/logs/codespace-app.log" >&2
exit 1
