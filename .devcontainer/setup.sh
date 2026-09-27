#!/usr/bin/env bash
# One-time Codespaces provisioning: Linux counterpart of "SET UP THIS MAC.command".
# Downloads the prebuilt index from this repository's `codespace-index` release instead of
# rebuilding it, because OCR and embedding the whole archive takes hours on a CPU-only VM.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
mkdir -p .rag/runtime .rag/models/minilm/onnx .rag/logs

ollama_version="v0.33.3"
ollama_sha256="c13cea8f3389db4145f8a6cb88d1747242a48639d7c13e3bda7c1ebdc6eebb2f"
minilm_snapshot="1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
repository="${GITHUB_REPOSITORY:-$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')}"
index_url="${RAG_INDEX_URL:-https://github.com/${repository}/releases/download/codespace-index}"

echo "[1/6] Installing document tools"
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends poppler-utils tesseract-ocr zstd >/dev/null

echo "[2/6] Fetching Git LFS course files"
git lfs install --skip-repo >/dev/null
git lfs pull

echo "[3/6] Installing pinned Python packages into .rag/runtime"
python3 -m pip install --quiet --upgrade --target .rag/runtime -r rag/requirements-all.txt

echo "[4/6] Downloading and verifying the MiniLM embedding model"
base="https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/${minilm_snapshot}"
curl --fail --silent --show-error --location --retry 3 --output .rag/models/minilm/tokenizer.json "${base}/tokenizer.json"
curl --fail --silent --show-error --location --retry 3 --output .rag/models/minilm/onnx/model_qint8_arm64.onnx "${base}/onnx/model_qint8_arm64.onnx"
sha256sum --check --quiet <<EOF
be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037  .rag/models/minilm/tokenizer.json
4278337fd0ff3c68bfb6291042cad8ab363e1d9fbc43dcb499fe91c871902474  .rag/models/minilm/onnx/model_qint8_arm64.onnx
EOF

echo "[5/6] Installing Ollama ${ollama_version} and the Qwen3 4B answer model"
if ! command -v ollama >/dev/null 2>&1; then
  archive="$(mktemp)"
  curl --fail --silent --show-error --location --retry 3 --output "${archive}" \
    "https://github.com/ollama/ollama/releases/download/${ollama_version}/ollama-linux-amd64.tar.zst"
  echo "${ollama_sha256}  ${archive}" | sha256sum --check --quiet
  # GPU runtimes are unused on Codespaces' CPU-only machines; skip them to save several GB.
  sudo tar --zstd -xf "${archive}" -C /usr/local --exclude='*cuda*' --exclude='*rocm*' --exclude='*vulkan*'
  rm -f "${archive}"
fi
export OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 OLLAMA_MODELS="${repo_root}/.rag/models/ollama"
if ! curl --silent --fail --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup ollama serve >> .rag/logs/ollama.log 2>&1 &
  for _ in $(seq 1 60); do
    curl --silent --fail --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
    sleep 0.5
  done
fi
ollama pull qwen3:4b

echo "[6/6] Downloading the prebuilt archive index"
if [[ -f .rag/search/CURRENT.json ]]; then
  echo "Existing index found; keeping it."
else
  bundle="$(mktemp)"
  curl --fail --silent --show-error --location --retry 3 --output "${bundle}" "${index_url}/course-archive-index.tar.gz"
  expected="$(curl --fail --silent --show-error --location --retry 3 "${index_url}/course-archive-index.tar.gz.sha256" | cut -d' ' -f1)"
  echo "${expected}  ${bundle}" | sha256sum --check --quiet
  tar -xzf "${bundle}" -C "${repo_root}"
  rm -f "${bundle}"
fi
built_from="$(python3 -c 'import json; print(json.load(open(".rag/codespace-index.json"))["commit"])' 2>/dev/null || echo unknown)"
if [[ "${built_from}" != "unknown" ]] && ! git diff --quiet "${built_from}" HEAD -- 'Fall *' 'Spring *' 'Summer *' 'Winter *' 'Program-wide' 2>/dev/null; then
  echo "Note: course files changed after the index was built (${built_from:0:7}); new or edited files are not searchable until the index release is republished."
fi

echo "Setup complete. The archive starts automatically when you open the Codespace."
