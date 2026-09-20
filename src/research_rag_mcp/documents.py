"""Versioned document identity and auditable, non-destructive chunk management."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

from . import semantic
from .retrieval import chunks


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


def migrate(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS chunk_sets(id TEXT PRIMARY KEY, source_id TEXT NOT NULL, data TEXT NOT NULL, active INTEGER NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_chunk_set ON chunk_sets(source_id) WHERE active=1;
        CREATE TABLE IF NOT EXISTS chunk_metadata(chunk_id TEXT PRIMARY KEY, chunk_set_id TEXT NOT NULL,
            status TEXT NOT NULL, reason TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS chunk_set_members ON chunk_metadata(chunk_set_id);
        CREATE TABLE IF NOT EXISTS cleanup_jobs(id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
    ''')
    for row in db.execute('SELECT * FROM documents').fetchall():
        source = json.loads(row['data'])
        if 'document_id' in source:
            continue
        sid = row['id']
        set_id = 'cs-'+uuid.uuid4().hex
        source.update(document_id='doc-'+uuid.uuid4().hex, source_version=1,
                      text_revision_id='text-'+digest([sid, source['text_sha256']]),
                      extraction={'engine': 'legacy; version not recorded'}, active_chunk_set_id=set_id)
        config = dict(chunk_set_id=set_id, source_id=sid, text_revision_id=source['text_revision_id'],
                      method='legacy page/character chunks', size=1200, overlap=200, created_at=stamp())
        db.execute('INSERT INTO chunk_sets VALUES(?,?,?,1)', (set_id, sid, dump(config)))
        db.execute("INSERT INTO chunk_metadata SELECT id,?,'active','Migrated; original chunk IDs preserved',? FROM chunks WHERE source_id=?",
                   (set_id, stamp(), sid))
        db.execute('UPDATE documents SET data=? WHERE id=?', (dump(source), sid))
    db.execute('PRAGMA user_version=4')


class DocumentManagement:
    def _create_chunk_set(self, db, source, size=1200, overlap=200, active=False):
        if type(size) != int or not 200 <= size <= 5000 or type(overlap) != int or not 0 <= overlap < size//2:
            raise ValueError('chunk size must be 200..5000; overlap must be 0..(size//2 - 1) characters')
        set_id = 'cs-'+uuid.uuid4().hex
        config = dict(chunk_set_id=set_id, source_id=source['source_id'], text_revision_id=source['text_revision_id'],
                      method='page-character-newline-v1', size=size, overlap=overlap, created_at=stamp())
        rows = []
        for page in source['pages']:
            for start, end, text in chunks(page['text'], size, overlap):
                cid = digest([set_id, source['source_id'], source['text_revision_id'], page['page_index'], start, end])
                rows.append(dict(id=cid, source_id=source['source_id'], page_index=page['page_index'], start=start, end=end, text=text))
        semantic.write_embeddings(db, rows)
        db.execute('INSERT INTO chunk_sets VALUES(?,?,?,?)', (set_id, source['source_id'], dump(config), int(active)))
        for row in rows:
            db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?)', tuple(row[k] for k in ('id','source_id','page_index','start','end','text')))
            db.execute('INSERT INTO chunk_metadata VALUES(?,?,?,?,?)', (row['id'], set_id, 'active', 'Imported from verified extracted text', stamp()))
        return {**config, 'active': active, 'chunk_count': len(rows)}

    def list_documents(self, offset=0, limit=50):
        self._pagination(offset, limit)
        with self.connect() as db:
            state = self.state(db)
            grouped = {}
            for source in state['sources'].values():
                summary = self.source_summary(source)
                summary['chunk_sets'] = [json.loads(row['data']) | {'active': bool(row['active'])}
                                         for row in db.execute('SELECT * FROM chunk_sets WHERE source_id=? ORDER BY rowid', (source['source_id'],))]
                grouped.setdefault(source['document_id'], []).append(summary)
            documents = [{'document_id': did, 'latest_source_version': max(s['source_version'] for s in versions),
                          'versions': sorted(versions, key=lambda s: s['source_version'])} for did, versions in sorted(grouped.items())]
        return {'total': len(documents), 'offset': offset, 'documents': documents[offset:offset+limit]}

    @staticmethod
    def _pagination(offset, limit):
        if type(offset) != int or offset < 0 or type(limit) != int or not 1 <= limit <= 100:
            raise ValueError('offset must be >=0 and limit 1..100')

    def list_chunks(self, source_id, chunk_set_id=None, status=None, offset=0, limit=50):
        self._pagination(offset, limit)
        if status is not None and status not in ('active', 'excluded', 'needs_review'):
            raise ValueError('Unknown chunk status')
        with self.connect() as db:
            state = self.state(db)
            source = state['sources'].get(source_id)
            if not source:
                raise ValueError('Unknown source_id')
            set_id = chunk_set_id or source['active_chunk_set_id']
            if not db.execute('SELECT 1 FROM chunk_sets WHERE id=? AND source_id=?', (set_id, source_id)).fetchone():
                raise ValueError('Unknown chunk_set_id for this source')
            rows = [dict(r) for r in db.execute('''SELECT c.*, m.chunk_set_id,m.status,m.reason,m.updated_at FROM chunks c
                     JOIN chunk_metadata m ON m.chunk_id=c.id WHERE m.chunk_set_id=? ORDER BY c.page_index,c.start''', (set_id,))]
            if status:
                rows = [r for r in rows if r['status'] == status]
            return {'source_id': source_id, 'document_id': source['document_id'], 'source_version': source['source_version'],
                    'chunk_set_id': set_id, 'total': len(rows), 'offset': offset,
                    'chunks': [{k:v for k,v in row.items() if k != 'text'} | {'characters': len(row['text'])} for row in rows[offset:offset+limit]]}

    def read_chunk(self, chunk_id):
        with self.connect() as db:
            state = self.state(db)
            row = db.execute('''SELECT c.*,m.chunk_set_id,m.status,m.reason,m.updated_at,s.active AS set_active
                   FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id JOIN chunk_sets s ON s.id=m.chunk_set_id WHERE c.id=?''', (chunk_id,)).fetchone()
            if not row:
                raise ValueError('Unknown chunk_id')
            row = dict(row)
            source = state['sources'][row['source_id']]
            citation = {k:row[k] for k in ('source_id','page_index','start','end')} | {'quote':row['text'], 'relation':'context'}
            self.citation(citation, state)
            vector = db.execute('SELECT model_fingerprint,dimensions,windows FROM embeddings WHERE chunk_id=?', (chunk_id,)).fetchone()
            return row | {k:source[k] for k in ('document_id','source_version','text_revision_id','origin','file')} | {
                'citation': citation, 'embedding': dict(vector) if vector else None,
                'text_sha256': hashlib.sha256(row['text'].encode()).hexdigest()}

    def get_chunk_context(self, chunk_id, before=1, after=1):
        if any(type(n) != int or not 0 <= n <= 5 for n in (before, after)):
            raise ValueError('before/after must be 0..5')
        target = self.read_chunk(chunk_id)
        with self.connect() as db:
            ids = [r['id'] for r in db.execute('''SELECT c.id FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id
                    WHERE m.chunk_set_id=? ORDER BY c.page_index,c.start''', (target['chunk_set_id'],))]
        index = ids.index(chunk_id)
        return {'target_chunk_id':chunk_id, 'chunks':[self.read_chunk(cid) for cid in ids[max(0,index-before):index+after+1]],
                'source_page':self.page(target['source_id'],target['page_index'])}

    def inspect_document_chunks(self, source_id):
        state = self.read()
        source = state['sources'].get(source_id)
        if not source:
            raise ValueError('Unknown source_id')
        self.verify_source(source)
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('''SELECT c.*,m.status FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id
                   WHERE m.chunk_set_id=? ORDER BY c.page_index,c.start''', (source['active_chunk_set_id'],))]
        pages, duplicate_groups = [], {}
        for row in rows:
            if source['pages'][row['page_index']]['text'][row['start']:row['end']] != row['text']:
                raise ValueError('Chunk integrity mismatch')
            duplicate_groups.setdefault(hashlib.sha256(row['text'].encode()).hexdigest(), []).append(row['id'])
        for page in source['pages']:
            spans = [(r['start'],r['end']) for r in rows if r['page_index']==page['page_index'] and r['status']=='active']
            cursor, gaps = 0, []
            for start,end in spans:
                if start>cursor and page['text'][cursor:start].strip():
                    gaps.append({'start':cursor,'end':start})
                cursor=max(cursor,end)
            if page['text'][cursor:].strip():
                gaps.append({'start':cursor,'end':len(page['text'])})
            pages.append({'page_index':page['page_index'], 'blank':not bool(page['text'].strip()), 'uncovered_nonblank_spans':gaps})
        return {'source_id':source_id,'document_id':source['document_id'],'chunk_set_id':source['active_chunk_set_id'],
                'chunk_count':len(rows),'status_counts':{s:sum(r['status']==s for r in rows) for s in ('active','excluded','needs_review')},
                'pages':pages,'exact_duplicate_groups':[ids for ids in duplicate_groups.values() if len(ids)>1],
                'limitation':'Integrity and coverage checks only. A researcher must inspect extraction and scientific meaning; no OCR or semantic quality certification.'}

    def rechunk_document(self, source_id, size, overlap, expected_revision, key):
        payload=dict(source_id=source_id,size=size,overlap=overlap)
        def action(db,state):
            source=state['sources'].get(source_id)
            if not source: raise ValueError('Unknown source_id')
            self.verify_source(source)
            return self._create_chunk_set(db,source,size,overlap,False)
        return self.mutate('rechunk_document',payload,expected_revision,key,action)

    def activate_chunk_set(self, chunk_set_id, expected_revision, key):
        def action(db,state):
            row=db.execute('SELECT * FROM chunk_sets WHERE id=?',(chunk_set_id,)).fetchone()
            if not row: raise ValueError('Unknown chunk_set_id')
            source=state['sources'][row['source_id']]
            self.verify_source(source)
            db.execute('UPDATE chunk_sets SET active=0 WHERE source_id=?',(row['source_id'],))
            db.execute('UPDATE chunk_sets SET active=1 WHERE id=?',(chunk_set_id,))
            source['active_chunk_set_id']=chunk_set_id
            db.execute('UPDATE documents SET data=? WHERE id=?',(dump(source),row['source_id']))
            return {'chunk_set_id':chunk_set_id,'source_id':row['source_id'],'active':True,'old_sets_retained':True}
        return self.mutate('activate_chunk_set',{'chunk_set_id':chunk_set_id},expected_revision,key,action)

    def set_chunk_status(self, chunk_id, status, reason, expected_revision, key):
        if status not in ('active','excluded','needs_review') or not reason.strip() or len(reason)>4000:
            raise ValueError('Use active/excluded/needs_review and a reason of 1..4000 characters')
        def action(db,state):
            if not db.execute('SELECT 1 FROM chunk_metadata WHERE chunk_id=?',(chunk_id,)).fetchone():
                raise ValueError('Unknown chunk_id')
            db.execute('UPDATE chunk_metadata SET status=?,reason=?,updated_at=? WHERE chunk_id=?',(status,reason,stamp(),chunk_id))
            return {'chunk_id':chunk_id,'status':status,'reason':reason,'evidence_preserved':True}
        return self.mutate('set_chunk_status',dict(chunk_id=chunk_id,status=status,reason=reason),expected_revision,key,action)

    def find_evidence_usage(self, chunk_id):
        chunk=self.read_chunk(chunk_id)
        with self.connect() as db:
            current=[json.loads(r['data']) for r in db.execute('SELECT data FROM artifacts')]
            versions=[json.loads(r['data']) for r in db.execute('SELECT data FROM versions')]
        usages=[]
        seen=set()
        for artifact in current+versions:
            identity=(artifact['id'],artifact['version'])
            if identity in seen: continue
            seen.add(identity)
            for index,block in enumerate(artifact['blocks']):
                for c in block['citations']:
                    if c['source_id']==chunk['source_id'] and c['page_index']==chunk['page_index'] and c['start']<chunk['end'] and c['end']>chunk['start']:
                        usages.append({'artifact_id':artifact['id'],'version':artifact['version'],'stage':artifact['stage'],
                                       'current':any(a['id']==artifact['id'] and a['version']==artifact['version'] for a in current),
                                       'block_index':index,'section':block['section'],'citation':c})
        return {'chunk_id':chunk_id,'usages':usages,'matching':'Overlapping exact source/page spans, including archived artifact versions'}

    def search_index_status(self):
        with self.connect() as db:
            rows=[dict(r) for r in db.execute('''SELECT c.id,c.source_id,c.text,e.model_fingerprint,e.text_sha256,e.vector,e.vector_sha256,e.dimensions
                         FROM chunks c LEFT JOIN embeddings e ON e.chunk_id=c.id''')]
        ready=0
        for r in rows:
            if (r['model_fingerprint']==semantic.FINGERPRINT and r['text_sha256']==hashlib.sha256(r['text'].encode()).hexdigest()
                    and r['vector'] is not None and r['dimensions']==semantic.DIMENSIONS and len(r['vector'])==semantic.DIMENSIONS*4
                    and hashlib.sha256(r['vector']).hexdigest()==r['vector_sha256']): ready+=1
        return {'model':semantic.model_status(),'total_chunks':len(rows),'indexed_chunks':ready,'pending_or_invalid_chunks':len(rows)-ready,
                'storage':'SQLite float32 vectors; exact CPU cosine scan','default_mode':'hybrid',
                'ready':ready==len(rows) and semantic.model_status()['assets_present']}

    def rebuild_search_index(self, source_ids, expected_revision, key):
        def action(db,state):
            selected=source_ids or list(state['sources'])
            if set(selected)-set(state['sources']): raise ValueError('Unknown source_id')
            for sid in selected: self.verify_source(state['sources'][sid])
            rows=[dict(r) for r in db.execute('SELECT * FROM chunks') if r['source_id'] in selected]
            for r in rows:
                page=state['sources'][r['source_id']]['pages'][r['page_index']]
                if page['text'][r['start']:r['end']]!=r['text']: raise ValueError('Chunk integrity mismatch; index not rebuilt')
            semantic.write_embeddings(db,rows)
            return {'source_ids':selected,'indexed_chunks':len(rows),'model':semantic.model_status()}
        return self.mutate('rebuild_search_index',{'source_ids':source_ids},expected_revision,key,action)
