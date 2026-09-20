"""Pinned local CPU cross-encoder ranking; scores are not correctness judgments."""
from collections import OrderedDict
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import sys
import threading

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MANIFEST = json.loads(Path(__file__).with_name('reranker_manifest.json').read_text())
RECIPE = 'query-passage-pair:512-only-second-stride64:max-window-logit:sigmoid:int8:first-page-document-score:v1'
FINGERPRINT = hashlib.sha256(json.dumps([MANIFEST, RECIPE], sort_keys=True).encode()).hexdigest()
_LOCK = threading.Lock()


def directory():
    return Path(os.environ.get('RESEARCH_RAG_RERANKER_DIR', Path.cwd()/'.models/bge-reranker-v2-m3-ONNX')).resolve()


def status():
    root = directory()
    return dict(model_id=MANIFEST['model_id'], original_model_id=MANIFEST['original_model_id'],
                model_revision=MANIFEST['revision'], fingerprint=FINGERPRINT, recipe=RECIPE,
                provider='CPUExecutionProvider', external_inference=False,
                assets_present=all((root/name).is_file() for name in MANIFEST['files']))


class Reranker:
    def __init__(self, root):
        for name, expected in MANIFEST['files'].items():
            path = root/name
            if not path.is_file():
                raise ValueError('Reranker asset missing; run scripts/download_reranker.py or rebuild the container: '+name)
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected:
                raise ValueError('Reranker asset hash mismatch: '+name)
        print(f'Reranker validated: {MANIFEST["model_id"]}@{MANIFEST["revision"]}; CPUExecutionProvider', file=sys.stderr)
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(root/'onnx/model_int8.onnx'), sess_options=options,
                                            providers=['CPUExecutionProvider'])
        self.session.disable_fallback()
        if self.session.get_providers() != ['CPUExecutionProvider']:
            raise ValueError('Only CPU reranking is permitted')
        self.inputs = {i.name for i in self.session.get_inputs()}
        if not self.inputs <= {'input_ids', 'attention_mask', 'token_type_ids'}:
            raise ValueError('Unexpected reranker input schema')
        self.tokenizer = Tokenizer.from_file(str(root/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=512, stride=64, strategy='only_second')
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def score(self, query, texts):
        with self.lock:
            keys = [(query, hashlib.sha256(t.encode()).hexdigest()) for t in texts]
            pending = dict(zip(keys, texts))
            windows, owners = [], []
            for key, text in pending.items():
                if key in self.cache:
                    continue
                try:
                    encoded = self.tokenizer.encode(query, text)
                except Exception as exc:
                    raise ValueError('Query does not fit the reranker token budget; shorten the query') from exc
                for window in [encoded, *encoded.overflowing]:
                    windows.append(window)
                    owners.append(key)
            scores = {key: [] for key in owners}
            for start in range(0, len(windows), 4):
                batch = windows[start:start+4]
                width = max(len(e.ids) for e in batch)
                ids = np.full((len(batch), width), self.tokenizer.token_to_id('<pad>'), dtype=np.int64)
                mask = np.zeros_like(ids)
                types = np.zeros_like(ids)
                for i, item in enumerate(batch):
                    ids[i, :len(item.ids)] = item.ids
                    mask[i, :len(item.ids)] = item.attention_mask
                    types[i, :len(item.ids)] = item.type_ids
                inputs = dict(input_ids=ids, attention_mask=mask, token_type_ids=types)
                output = self.session.run(None, {k: inputs[k] for k in self.inputs})[0]
                if output.shape not in ((len(batch), 1), (len(batch),)) or not np.isfinite(output).all():
                    raise ValueError('Invalid reranker output')
                for key, value in zip(owners[start:start+4], output.reshape(-1)):
                    scores[key].append(float(value))
            for key, values in scores.items():
                logit = max(values)
                self.cache[key] = dict(rerank_logit=logit, rerank_score=float(1/(1+np.exp(-np.clip(logit, -80, 80)))),
                                       rerank_windows=len(values))
            result = [dict(self.cache[key]) for key in keys]
            while len(self.cache) > 4096:
                self.cache.popitem(last=False)
            return result


@lru_cache(maxsize=1)
def _reranker(root):
    return Reranker(Path(root))


def rerank(rows, query, overviews):
    if not rows:
        return []
    with _LOCK:
        model = _reranker(str(directory()))
    source_ids = list(dict.fromkeys(row['source_id'] for row in rows))
    document_scores = dict(zip(source_ids, model.score(query, [overviews[sid] for sid in source_ids])))
    scores = model.score(query, [row['text'] for row in rows])
    result = [{**row, **score, 'retrieval_score': row['score'], 'first_stage_rank': i+1,
               'document_score': document_scores[row['source_id']]['rerank_score'],
               'score': score['rerank_score']} for i, (row, score) in enumerate(zip(rows, scores))]
    return sorted(result, key=lambda r: (-r['score'], r['first_stage_rank']))
