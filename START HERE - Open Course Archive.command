#!/bin/zsh
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"

script_dir="${0:A:h}"
cd "${script_dir}" || exit 1
if [[ ! -f .rag/search/CURRENT.json ]]; then
  print "First launch: opening setup to download dependencies and build the local archive index."
  exec /usr/bin/open -a Terminal "${script_dir}/SET UP THIS MAC.command"
fi
exec /usr/bin/env python3 scripts/run_rag.py --port 8765 --open
