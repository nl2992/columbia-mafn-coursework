"""Offline MiniLM inference with the model's official tokenizer configuration."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# Optional project-local dependencies; nothing is installed or fetched at runtime.
_runtime = Path(__file__).resolve().parents[1] / '.rag/runtime'
if _runtime.is_dir():
    sys.path.insert(0, str(_runtime))

import numpy as np
import tokenizers
from tokenizers import Tokenizer

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_FILE = "onnx/model_qint8_arm64.onnx"
WINDOW = 224
STRIDE = 192
DIMENSION = 384


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def find_model(path=None):
    if path:
        p = Path(path).expanduser().resolve()
    else:
        cache = Path.home() / '.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2'
        ref = cache / 'refs/main'
        p = cache / 'snapshots' / ref.read_text().strip() if ref.exists() else Path('missing-model')
    if not all((p / name).is_file() for name in [MODEL_FILE, 'tokenizer.json']):
        raise RuntimeError('Local MiniLM ONNX files unavailable. Supply --model-dir with '
                           'tokenizer.json and onnx/model_qint8_arm64.onnx. No download is attempted.')
    return p


class WordPiece:
    def __init__(self, path):
        self.engine = Tokenizer.from_file(str(path))
        self.engine.no_truncation()
        self.engine.no_padding()
        self.cls, self.sep = (self.engine.token_to_id(t) for t in ('[CLS]', '[SEP]'))
        if self.cls is None or self.sep is None:
            raise ValueError('MiniLM tokenizer requires CLS and SEP tokens')

    def encode(self, text):
        return self.engine.encode(text, add_special_tokens=False).ids

    def windows(self, text):
        tokens = self.encode(text)
        for start in range(0, max(1, len(tokens)), STRIDE):
            end = min(start + WINDOW, len(tokens))
            yield start, end, [self.cls, *tokens[start:end], self.sep]
            if end == len(tokens):
                break


class MiniLM:
    def __init__(self, model_dir=None, threads=4):
        import onnxruntime as ort
        self.path = find_model(model_dir)
        self.tokenizer = WordPiece(self.path / 'tokenizer.json')
        self.identity = {'model_id': MODEL_ID, 'snapshot': self.path.name,
                         'onnx_sha256': digest_file(self.path / MODEL_FILE),
                         'tokenizer_sha256': digest_file(self.path / 'tokenizer.json'),
                         'dimension': DIMENSION, 'window_tokens': WINDOW, 'stride_tokens': STRIDE,
                         'pooling': 'attention-masked-mean+l2',
                         'tokenizer_impl': 'huggingface-tokenizers-' + tokenizers.__version__}
        self.fingerprint = hashlib.sha256(json.dumps(self.identity, sort_keys=True).encode()).hexdigest()
        # Once token IDs are identical, tokenizer implementation has no effect on
        # inference. Reuse the first build's cache only for exactly matching IDs,
        # weights, pooling, dimension, and model configuration.
        legacy_identity = {**self.identity, 'tokenizer_impl': 'bert-wordpiece-v1'}
        self.compatible_cache_fingerprints = [self.fingerprint, hashlib.sha256(
            json.dumps(legacy_identity, sort_keys=True).encode()).hexdigest()]
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(self.path / MODEL_FILE), sess_options=opts,
                                            providers=['CPUExecutionProvider'])

    def encode_ids(self, sequences):
        length = max(map(len, sequences))
        ids = np.zeros((len(sequences), length), dtype=np.int64)
        mask = np.zeros_like(ids)
        for i, sequence in enumerate(sequences):
            ids[i, :len(sequence)] = sequence
            mask[i, :len(sequence)] = 1
        hidden = self.session.run(None, {'input_ids': ids, 'attention_mask': mask,
                                         'token_type_ids': np.zeros_like(ids)})[0]
        weights = mask[..., None].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
        return (pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9)).astype('float32')

    def query(self, text):
        sequences = [ids for _, _, ids in self.tokenizer.windows(text)]
        vectors = self.encode_ids(sequences)
        mean = vectors.mean(axis=0)
        return mean / max(np.linalg.norm(mean), 1e-9)
