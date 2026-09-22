"""User-selected Qdrant/Ollama/PyThaiNLP/BM25/RRF retrieval implementation.

Qdrant is the actual vector engine. The research journal retains immutable chunk
spans and filters; no embedding BLOBs or linear NumPy vector scan remains.
"""
import asyncio
import hashlib
import json
import os
import threading
import time
import uuid
from collections import OrderedDict

from qdrant_client import models
from pyragdoc.core.storage import QdrantService
from pyragdoc.core.embedding import OllamaProvider, EmbeddingService
from pyragdoc.core.bm25 import BM25Retriever
from pyragdoc.core.rrf import RRFCombiner
from pyragdoc.models.documents import DocumentChunk, DocumentMetadata, SearchResult
from pyragdoc.utils.thai_tokenizer import ThaiTokenizer


def run(coro):
    return asyncio.run(coro)


def point_id(chunk_id):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'research-rag:chunk:'+chunk_id))


class RetrievalIndex:
    def __init__(self, *, collection=None):
        self.model=os.environ.get('EMBEDDING_MODEL','nomic-embed-text:latest')
        self.digest=os.environ.get('EMBEDDING_MODEL_DIGEST','')
        if not self.digest:
            raise ValueError('EMBEDDING_MODEL_DIGEST must pin the installed Ollama model')
        self.dimensions=int(os.environ.get('EMBEDDING_DIMENSIONS','768'))
        self.fingerprint=hashlib.sha256(json.dumps([self.model,self.digest,self.dimensions,'cosine','upstream-no-prefix'],sort_keys=True).encode()).hexdigest()
        self.provider=OllamaProvider(self.model,os.environ.get('OLLAMA_URL','http://127.0.0.1:11434'))
        self.embedding=EmbeddingService(self.provider)
        self.storage=QdrantService(os.environ.get('QDRANT_URL','http://127.0.0.1:6333'),
                                   collection or os.environ.get('QDRANT_COLLECTION','research_chunks'),self.dimensions)
        self.tokenizer=ThaiTokenizer()
        self.rrf=RRFCombiner(k=60)
        self._cache=OrderedDict(); self._cache_lock=threading.Lock()
        self._initialized=False; self._init_lock=threading.Lock()
        self._verified_at=0

    def ensure_ready(self):
        with self._init_lock:
            if not self._initialized:
                run(self.storage.initialize())
                for field in ('chunk_set_id','source_id','model_fingerprint'):
                    self.storage.client.create_payload_index(self.storage.collection_name,
                        'metadata.custom.'+field,models.PayloadSchemaType.KEYWORD,wait=True)
                self._initialized=True
            if time.monotonic()-self._verified_at>10:
                found=[m for m in self.provider.client.list().models if m.model==self.model]
                if not found or found[0].digest!=self.digest:
                    raise ValueError('Ollama model digest differs from the pinned model; no automatic substitution')
                self._verified_at=time.monotonic()

    def model_status(self):
        return {'provider':'ollama','model':self.model,'digest':self.digest,'dimensions':self.dimensions,
                'fingerprint':self.fingerprint,'device':'cpu','external_api':False}

    def chunk(self,row,source):
        custom={k:row[k] for k in ('source_id','page_index','start','end','chunk_set_id')}
        custom.update(chunk_id=row['id'],model_fingerprint=self.fingerprint,
                      text_sha256=hashlib.sha256(row['text'].encode()).hexdigest(),
                      document_id=source['document_id'],source_version=source['source_version'],
                      text_revision_id=source['text_revision_id'],role=source['role'])
        return DocumentChunk(id=point_id(row['id']),text=row['text'],metadata=DocumentMetadata(
            source=source['origin'],title=source['bibliography']['title'],page_number=row['page_index']+1,custom=custom))

    def index_rows(self,rows,sources,progress=None):
        self.ensure_ready()
        for begin in range(0,len(rows),16):
            batch=rows[begin:begin+16]
            chunks=[self.chunk(row,sources[row['source_id']]) for row in batch]
            # The selected upstream embedding path; all calls are local CPU.
            vectors=[run(self.embedding.generate_embedding(row['text'])) for row in batch]
            if any(len(v)!=self.dimensions for v in vectors):
                raise ValueError('Embedding dimension mismatch')
            run(self.storage.add_documents(vectors,chunks))
            if progress: progress(min(begin+len(batch),len(rows)),len(rows))

    def _lexical(self,rows,sources):
        key=hashlib.sha256('\n'.join(r['id']+':'+hashlib.sha256(r['text'].encode()).hexdigest() for r in rows).encode()).hexdigest()
        with self._cache_lock:
            if key in self._cache:
                self._cache.move_to_end(key); return self._cache[key]
        retriever=BM25Retriever(self.tokenizer)
        run(retriever.index_documents([self.chunk(r,sources[r['source_id']]) for r in rows]))
        with self._cache_lock:
            self._cache[key]=retriever
            while len(self._cache)>32: self._cache.popitem(last=False)
        return retriever

    def search(self,query,rows,sources,mode,limit):
        started=time.perf_counter(); timings={}
        method={'lexical':'PyThaiNLP newmm + BM25','semantic':'Ollama embeddings + Qdrant cosine',
                'hybrid':'PyThaiNLP BM25 + Ollama/Qdrant cosine; RRF k=60'}[mode]
        if not rows: return {'hits':[],'method':method,'timings':{'total_seconds':0}}
        by_point={point_id(row['id']):row for row in rows}
        candidate_limit=max(limit*2,limit)
        lexical=[]; semantic=[]
        if mode!='semantic':
            t=time.perf_counter()
            lexical=run(self._lexical(rows,sources).search(query,candidate_limit))
            timings['lexical_seconds']=time.perf_counter()-t
        if mode!='lexical':
            t=time.perf_counter();self.ensure_ready()
            vector=run(self.embedding.generate_embedding(query))
            timings['query_embedding_seconds']=time.perf_counter()-t
            t=time.perf_counter()
            # Explicit active IDs enforce version/status filters inside Qdrant.
            # No unfiltered retrieval followed by a too-late source filter.
            filters=models.Filter(must=[models.HasIdCondition(has_id=list(by_point)),
                models.FieldCondition(key='metadata.custom.model_fingerprint',match=models.MatchValue(value=self.fingerprint))])
            semantic=run(self.storage.search(vector,candidate_limit,filters=filters))
            timings['vector_search_seconds']=time.perf_counter()-t
        combined=lexical if mode=='lexical' else semantic if mode=='semantic' else self.rrf.combine([lexical,semantic],candidate_limit)
        lexical_scores={x.chunk.id:x.score for x in lexical};semantic_scores={x.chunk.id:x.score for x in semantic}
        hits=[]
        from .retrieval import deduplicate
        for item in combined:
            expected=by_point.get(item.chunk.id)
            if expected is None or item.chunk.text!=expected['text']:
                raise ValueError('Qdrant chunk identity/text mismatch; inspect index integrity')
            if mode!='lexical' and item.chunk.metadata.custom.get('chunk_id')!=expected['id']:
                raise ValueError('Qdrant payload identity mismatch')
            hits.append({**expected,'score':item.score,'lexical_score':lexical_scores.get(item.chunk.id),
                         'semantic_score':semantic_scores.get(item.chunk.id),
                         'matched_terms':list(set(self.tokenizer.tokenize(query))&set(self.tokenizer.tokenize(expected['text'])))})
        timings['total_seconds']=time.perf_counter()-started
        return {'hits':deduplicate(hits,limit),'method':method,'timings':timings}

    def inspect(self,rows):
        self.ensure_ready()
        ready=0;invalid=[]
        for begin in range(0,len(rows),128):
            batch=rows[begin:begin+128]
            records={str(p.id):p for p in self.storage.client.retrieve(self.storage.collection_name,
                        [point_id(r['id']) for r in batch],with_payload=True,with_vectors=False)}
            for row in batch:
                point=records.get(point_id(row['id']))
                meta=(point.payload or {}).get('metadata',{}).get('custom',{}) if point else {}
                if point and point.payload.get('text')==row['text'] and meta.get('model_fingerprint')==self.fingerprint and meta.get('chunk_id')==row['id']:
                    ready+=1
                else: invalid.append(row['id'])
        return ready,invalid

    def clear(self):
        self.ensure_ready()
        self.storage.client.delete(self.storage.collection_name,models.FilterSelector(filter=models.Filter()),wait=True)
        with self._cache_lock: self._cache.clear()

    def export_points(self,chunk_ids):
        self.ensure_ready();points=[]
        for begin in range(0,len(chunk_ids),128):
            batch=chunk_ids[begin:begin+128]
            records=self.storage.client.retrieve(self.storage.collection_name,[point_id(c) for c in batch],with_payload=True,with_vectors=True)
            points.extend({'id':str(p.id),'vector':p.vector,'payload':p.payload} for p in records)
        return points

    def restore_points(self,points):
        self.ensure_ready()
        if self.storage.client.count(self.storage.collection_name,exact=True).count:
            raise ValueError('Restore requires an empty dedicated Qdrant collection')
        for begin in range(0,len(points),64):
            self.storage.client.upsert(self.storage.collection_name,[models.PointStruct(**p) for p in points[begin:begin+64]],wait=True)
