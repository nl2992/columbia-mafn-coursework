#!/bin/zsh
set -euo pipefail

repo_root="${0:A:h}"
cd "${repo_root}"
mkdir -p .rag/runtime .rag/models/minilm .rag/logs

setup_failed() {
  local exit_code=$?
  trap - ZERR
  print -u2 "\nSetup stopped with an error. The last command above identifies what needs attention."
  /usr/bin/osascript -e 'display alert "Course Archive setup stopped" message "Review the last error in the Terminal window, fix it, and run SET UP THIS MAC.command again." as critical' >/dev/null 2>&1 || true
  exit "${exit_code}"
}
trap setup_failed ZERR

print "\nCourse Archive · one-time setup\n"
if ! command -v brew >/dev/null 2>&1; then
  print -u2 "Homebrew is required. Install it from https://brew.sh, then double-click this setup file again."
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  print -u2 "Git is required. Run: xcode-select --install"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  print -u2 "Python 3 is required. Install it with: brew install python"
  exit 1
fi

print "[1/7] Fetching Git LFS course assets"
if ! command -v git-lfs >/dev/null 2>&1; then brew install git-lfs; fi
git lfs install
git lfs pull

print "[2/7] Installing local extraction and search dependencies"
python3 -m pip install --break-system-packages --upgrade --target .rag/runtime -r rag/requirements-all.txt
export PYTHONPATH="${repo_root}/.rag/runtime${PYTHONPATH:+:${PYTHONPATH}}"

print "[3/7] Installing local document tools"
for package in ollama tesseract poppler; do
  if ! brew list "${package}" >/dev/null 2>&1; then brew install "${package}"; fi
done
if ! command -v soffice >/dev/null 2>&1; then brew install --cask libreoffice; fi

print "[4/7] Downloading and verifying the local MiniLM embedding model"
snapshot="1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
base="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/${snapshot}"
mkdir -p .rag/models/minilm/onnx
curl --fail --location --retry 3 --output .rag/models/minilm/tokenizer.json "${base}/tokenizer.json"
curl --fail --location --retry 3 --output .rag/models/minilm/onnx/model_qint8_arm64.onnx "${base}/onnx/model_qint8_arm64.onnx"
echo "be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037  .rag/models/minilm/tokenizer.json" | shasum -a 256 -c
echo "4278337fd0ff3c68bfb6291042cad8ab363e1d9fbc43dcb499fe91c871902474  .rag/models/minilm/onnx/model_qint8_arm64.onnx" | shasum -a 256 -c

print "[5/7] Provisioning the local Qwen answer model"
if ! curl --noproxy '*' --silent --fail --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 OLLAMA_MODELS="${repo_root}/.rag/models/ollama" \
    nohup ollama serve >> .rag/logs/ollama.log 2>&1 &
  for _ in {1..60}; do
    curl --noproxy '*' --silent --fail --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep .5
  done
fi
if ! curl --noproxy '*' --silent --fail --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  print -u2 "Ollama did not become ready. See .rag/logs/ollama.log."
  exit 1
fi
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS="${repo_root}/.rag/models/ollama" OLLAMA_NO_CLOUD=1 ollama pull qwen3:4b

print "[6/7] Building the private local archive index when needed"
if [[ ! -f .rag/search/CURRENT.json ]]; then
  python3 scripts/rag_pipeline.py inventory
  python3 scripts/rag_pipeline.py extract --ocr
  python3 scripts/rag_pipeline.py normalize
  python3 scripts/rag_search.py build
else
  print "Existing local index found; keeping it."
fi

print "[7/7] Installing and launching the Desktop app"
./'INSTALL ON DESKTOP.command'
print "\nSetup complete. Course Archive is installed on your Desktop."
