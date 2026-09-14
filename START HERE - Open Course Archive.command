#!/bin/zsh
set -u

script_dir="${0:A:h}"
cd "${script_dir}" || exit 1
exec /usr/bin/env python3 scripts/run_rag.py --port 8765 --open
