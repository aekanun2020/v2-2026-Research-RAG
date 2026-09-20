"""Pinned multilingual embeddings, local CPU inference and exact cosine search."""
import hashlib
import json
import os
import sys
import threading
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ort.disable_telemetry_events()

MANIFEST = json.loads(Path(__file__).with_name('model_manifest.json').read_text())
MODEL_ID = MANIFEST['model_id']
DIMENSIONS = MANIFEST['dimensions']
RECIPE = 'e5-query-passage:masked-mean:l2:512-stride64:mean-overflow-windows:v1'
FINGERPRINT = hashlib.sha256(json.dumps([MANIFEST, RECIPE], sort_keys=True).encode()).hexdigest()
_LOCK = threading.Lock()


def model_directory():
    return Path(os.environ.get('RESEARCH_RAG_MODEL_DIR', Path.cwd()/'.models/multilingual-e5-base')).resolve()


def model_status():
    root = model_directory()
    return {'model_id': MODEL_ID, 'model_revision': MANIFEST['revision'], 'fingerprint': FINGERPRINT,
            'dimensions': DIMENSIONS, 'provider': 'CPUExecutionProvider', 'recipe': RECIPE,
            'assets_present': all((root/name).is_file() for name in MANIFEST['files']),
            'external_inference': False}


class Encoder:
    def __init__(self, root):
        if MODEL_ID != 'intfloat/multilingual-e5-base':
            raise ValueError('Unexpected embedding model identifier')
        for name, expected in MANIFEST['files'].items():
            path = root/name
            if not path.is_file():
                raise ValueError('Embedding model asset missing; run scripts/download_model.py or rebuild the container: '+name)
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('Embedding model hash mismatch: '+name)
        print(f'Embedding model validated: {MODEL_ID}@{MANIFEST["revision"]}; provider=CPUExecutionProvider', file=sys.stderr)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(root/'onnx/model.onnx'), sess_options=options,
                                            providers=['CPUExecutionProvider'])
        self.session.disable_fallback()
        if self.session.get_providers() != ['CPUExecutionProvider']:
            raise ValueError('Only CPU inference is permitted')
        self.inputs = {entry.name for entry in self.session.get_inputs()}
        if not self.inputs <= {'input_ids', 'attention_mask', 'token_type_ids'}:
            raise ValueError('Unexpected embedding model input schema')
        self.tokenizer = Tokenizer.from_file(str(root/'onnx/tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=512, stride=64)
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def encode(self, texts, kind):
        if kind not in ('query', 'passage'):
            raise ValueError('Embedding kind must be query or passage')
        with self.lock:
            keys = [kind+': '+text for text in texts]
            missing = list(dict.fromkeys(key for key in keys if key not in self.cache))
            windows, owners = [], []
            for key in missing:
                encoded = self.tokenizer.encode(key)
                for window in [encoded, *encoded.overflowing]:
                    windows.append(window)
                    owners.append(key)
            vectors = {key: [] for key in missing}
            for start in range(0, len(windows), 8):
                batch = windows[start:start+8]
                width = max(len(e.ids) for e in batch)
                ids = np.full((len(batch), width), self.tokenizer.token_to_id('<pad>'), dtype=np.int64)
                mask = np.zeros_like(ids)
                for i, entry in enumerate(batch):
                    ids[i, :len(entry.ids)] = entry.ids
                    mask[i, :len(entry.ids)] = entry.attention_mask
                inputs = {'input_ids': ids, 'attention_mask': mask, 'token_type_ids': np.zeros_like(ids)}
                hidden = self.session.run(None, {k: inputs[k] for k in self.inputs})[0]
                if hidden.shape != (len(batch), width, DIMENSIONS):
                    raise ValueError('Unexpected embedding output dimensions')
                pooled = (hidden * mask[..., None]).sum(axis=1) / mask.sum(axis=1, keepdims=True)
                for owner, vector in zip(owners[start:start+8], pooled):
                    vectors[owner].append(vector/np.linalg.norm(vector))
            for key, parts in vectors.items():
                vector = np.mean(parts, axis=0)
                vector = (vector/np.linalg.norm(vector)).astype('<f4')
                if not np.isfinite(vector).all():
                    raise ValueError('Non-finite embedding')
                self.cache[key] = (vector.tobytes(), len(parts))
            results = [self.cache[key] for key in keys]
            while len(self.cache) > 4096:
                self.cache.popitem(last=False)
            return results


@lru_cache(maxsize=1)
def _encoder(root):
    return Encoder(Path(root))


def encode(texts, kind='passage'):
    if not texts:
        return []
    with _LOCK:
        encoder = _encoder(str(model_directory()))
    return encoder.encode(texts, kind)


def write_embeddings(db, rows):
    encoded = encode([row['text'] for row in rows])
    for row, (vector, windows) in zip(rows, encoded):
        db.execute('INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?,?,?,?)',
                   (row['id'], FINGERPRINT, hashlib.sha256(row['text'].encode()).hexdigest(),
                    vector, hashlib.sha256(vector).hexdigest(), DIMENSIONS, windows))


def cosine_scores(db, rows, query):
    if not rows:
        return []
    records = {r['chunk_id']: r for r in db.execute('SELECT * FROM embeddings')}
    vectors = []
    for row in rows:
        record = records.get(row['id'])
        if (not record or record['model_fingerprint'] != FINGERPRINT
                or record['text_sha256'] != hashlib.sha256(row['text'].encode()).hexdigest()):
            raise ValueError('Semantic index missing or stale; call rebuild_search_index for the affected source')
        raw = record['vector']
        if len(raw) != DIMENSIONS*4 or record['dimensions'] != DIMENSIONS or hashlib.sha256(raw).hexdigest() != record['vector_sha256']:
            raise ValueError('Semantic vector integrity mismatch; call rebuild_search_index')
        vector = np.frombuffer(raw, dtype='<f4')
        if not np.isfinite(vector).all() or not np.isclose(np.linalg.norm(vector), 1, atol=0.001):
            raise ValueError('Invalid semantic vector; call rebuild_search_index')
        vectors.append(vector)
    query_vector = np.frombuffer(encode([query], 'query')[0][0], dtype='<f4')
    return (np.stack(vectors) @ query_vector).clip(-1, 1).tolist()
