"""Versioned documents and chunk spans in the journal; vectors in Qdrant."""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from .retrieval import chunks


def dump(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


class DocumentManagement:
    def _create_chunk_set(self,raw,source,size=1200,overlap=200,active=False):
        if type(size)!=int or not 200<=size<=5000 or type(overlap)!=int or not 0<=overlap<size//2:
            raise ValueError('chunk size must be 200..5000; overlap must be below half the size')
        set_id='cs-'+uuid.uuid4().hex
        config=dict(chunk_set_id=set_id,source_id=source['source_id'],text_revision_id=source['text_revision_id'],
                    method='page-character-newline-v1',size=size,overlap=overlap,created_at=stamp(),active=active)
        rows=[]
        for page in source['pages']:
            for start,end,text in chunks(page['text'],size,overlap):
                cid=digest([set_id,source['source_id'],source['text_revision_id'],page['page_index'],start,end])
                rows.append(dict(id=cid,source_id=source['source_id'],page_index=page['page_index'],start=start,end=end,text=text,
                                 chunk_set_id=set_id,status='active',reason='Imported from verified extracted text',updated_at=stamp()))
        self.index.index_rows(rows,{source['source_id']:source},getattr(self,'_job_progress',None))
        raw['chunk_sets'][set_id]=config
        for r in rows: r['embedding_fingerprint']=self.index.fingerprint
        raw['chunks'].update({r['id']:r for r in rows})
        raw['index_generation']=self.index.fingerprint
        return {**config,'chunk_count':len(rows)}

    @staticmethod
    def _pagination(offset,limit):
        if type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=100:
            raise ValueError('offset must be >=0 and limit 1..100')

    def list_documents(self,offset=0,limit=50):
        self._pagination(offset,limit)
        raw=self.raw_state();grouped={}
        for source in raw['sources'].values():
            summary=self.source_summary(source)
            summary['chunk_sets']=[s for s in raw['chunk_sets'].values() if s['source_id']==source['source_id']]
            grouped.setdefault(source['document_id'],[]).append(summary)
        docs=[{'document_id':did,'latest_source_version':max(s['source_version'] for s in versions),
               'versions':sorted(versions,key=lambda s:s['source_version'])} for did,versions in sorted(grouped.items())]
        return {'total':len(docs),'offset':offset,'documents':docs[offset:offset+limit]}

    def _set_rows(self,raw,set_id):
        return sorted([r for r in raw['chunks'].values() if r['chunk_set_id']==set_id],key=lambda r:(r['page_index'],r['start'],r['id']))

    def list_chunks(self,source_id,chunk_set_id=None,status=None,offset=0,limit=50):
        self._pagination(offset,limit)
        if status is not None and status not in ('active','excluded','needs_review'): raise ValueError('Unknown chunk status')
        raw=self.raw_state();source=raw['sources'].get(source_id)
        if not source: raise ValueError('Unknown source_id')
        set_id=chunk_set_id or source['active_chunk_set_id']
        if raw['chunk_sets'].get(set_id,{}).get('source_id')!=source_id: raise ValueError('Unknown chunk_set_id for this source')
        rows=[r for r in self._set_rows(raw,set_id) if not status or r['status']==status]
        return {'source_id':source_id,'document_id':source['document_id'],'source_version':source['source_version'],
                'chunk_set_id':set_id,'total':len(rows),'offset':offset,
                'chunks':[{k:v for k,v in r.items() if k!='text'}|{'characters':len(r['text'])} for r in rows[offset:offset+limit]]}

    def read_chunk(self,chunk_id):
        raw=self.raw_state();row=raw['chunks'].get(chunk_id)
        if not row: raise ValueError('Unknown chunk_id')
        source=raw['sources'][row['source_id']]
        citation={k:row[k] for k in ('source_id','page_index','start','end')}|{'quote':row['text'],'relation':'context'}
        self.citation(citation,self.state(raw))
        return {**row,'set_active':raw['chunk_sets'][row['chunk_set_id']]['active'],
                **{k:source[k] for k in ('document_id','source_version','text_revision_id','origin','file')},
                'citation':citation,'embedding':self.index.model_status() if raw['index_generation'] else None,
                'text_sha256':hashlib.sha256(row['text'].encode()).hexdigest()}

    def get_chunk_context(self,chunk_id,before=1,after=1):
        if any(type(n)!=int or not 0<=n<=5 for n in (before,after)): raise ValueError('before/after must be 0..5')
        target=self.read_chunk(chunk_id)
        ids=[r['id'] for r in self._set_rows(self.raw_state(),target['chunk_set_id'])];pos=ids.index(chunk_id)
        return {'target_chunk_id':chunk_id,'chunks':[self.read_chunk(c) for c in ids[max(0,pos-before):pos+after+1]],
                'source_page':self.page(target['source_id'],target['page_index'])}

    def inspect_document_chunks(self,source_id):
        raw=self.raw_state();source=raw['sources'].get(source_id)
        if not source: raise ValueError('Unknown source_id')
        self.verify_source(source);rows=self._set_rows(raw,source['active_chunk_set_id'])
        pages=[];duplicates={}
        for row in rows:
            if source['pages'][row['page_index']]['text'][row['start']:row['end']]!=row['text']: raise ValueError('Chunk integrity mismatch')
            duplicates.setdefault(hashlib.sha256(row['text'].encode()).hexdigest(),[]).append(row['id'])
        for page in source['pages']:
            spans=[(r['start'],r['end']) for r in rows if r['page_index']==page['page_index'] and r['status']=='active']
            cursor=0;gaps=[]
            for start,end in spans:
                if start>cursor and page['text'][cursor:start].strip(): gaps.append({'start':cursor,'end':start})
                cursor=max(cursor,end)
            if page['text'][cursor:].strip(): gaps.append({'start':cursor,'end':len(page['text'])})
            pages.append({'page_index':page['page_index'],'blank':not bool(page['text'].strip()),'uncovered_nonblank_spans':gaps})
        return {'source_id':source_id,'document_id':source['document_id'],'chunk_set_id':source['active_chunk_set_id'],
                'chunk_count':len(rows),'status_counts':{s:sum(r['status']==s for r in rows) for s in ('active','excluded','needs_review')},
                'pages':pages,'exact_duplicate_groups':[ids for ids in duplicates.values() if len(ids)>1],
                'limitation':'Integrity and coverage checks only; no OCR or automatic semantic judgment.'}

    def rechunk_document(self,source_id,size,overlap,expected_revision,key):
        def action(raw,state):
            source=state['sources'].get(source_id)
            if not source: raise ValueError('Unknown source_id')
            self.verify_source(source)
            return self._create_chunk_set(raw,source,size,overlap,False)
        return self.mutate('rechunk_document',dict(source_id=source_id,size=size,overlap=overlap),expected_revision,key,action)

    def activate_chunk_set(self,chunk_set_id,expected_revision,key):
        def action(raw,state):
            row=raw['chunk_sets'].get(chunk_set_id)
            if not row: raise ValueError('Unknown chunk_set_id')
            source=state['sources'][row['source_id']];self.verify_source(source)
            for chunk_set in raw['chunk_sets'].values():
                if chunk_set['source_id']==row['source_id']: chunk_set['active']=chunk_set['chunk_set_id']==chunk_set_id
            source['active_chunk_set_id']=chunk_set_id
            return {'chunk_set_id':chunk_set_id,'source_id':row['source_id'],'active':True,'old_sets_retained':True}
        return self.mutate('activate_chunk_set',{'chunk_set_id':chunk_set_id},expected_revision,key,action)

    def set_chunk_status(self,chunk_id,status,reason,expected_revision,key):
        if status not in ('active','excluded','needs_review') or not reason.strip() or len(reason)>4000: raise ValueError('Invalid status/reason')
        def action(raw,state):
            row=raw['chunks'].get(chunk_id)
            if not row: raise ValueError('Unknown chunk_id')
            row.update(status=status,reason=reason,updated_at=stamp())
            return {'chunk_id':chunk_id,'status':status,'reason':reason,'evidence_preserved':True}
        return self.mutate('set_chunk_status',dict(chunk_id=chunk_id,status=status,reason=reason),expected_revision,key,action)

    def find_evidence_usage(self,chunk_id):
        chunk=self.read_chunk(chunk_id);raw=self.raw_state();current=list(raw['artifacts'].values())
        versions=[a for history in raw['versions'].values() for a in history.values()]
        usages=[];seen=set()
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
        return {'chunk_id':chunk_id,'usages':usages,'matching':'Overlapping exact source/page spans, including archived versions'}

    def search_index_status(self):
        raw=self.raw_state();rows=list(raw['chunks'].values())
        ready,invalid=self.index.inspect(rows)
        return {'model':self.index.model_status(),'total_chunks':len(rows),'indexed_chunks':ready,'pending_or_invalid_chunks':len(invalid),
                'storage':'Qdrant cosine vector index; journal contains evidence spans, no SQLite',
                'default_mode':'hybrid','ready':ready==len(rows) and (not rows or raw['index_generation']==self.index.fingerprint)}

    def rebuild_search_index(self,source_ids,expected_revision,key):
        def action(raw,state):
            selected=source_ids or list(state['sources'])
            if set(selected)-set(state['sources']): raise ValueError('Unknown source_id')
            for sid in selected: self.verify_source(state['sources'][sid])
            rows=[r for r in raw['chunks'].values() if r['source_id'] in selected]
            for r in rows:
                if state['sources'][r['source_id']]['pages'][r['page_index']]['text'][r['start']:r['end']]!=r['text']: raise ValueError('Chunk integrity mismatch')
            self.index.index_rows(rows,state['sources'],getattr(self,'_job_progress',None))
            for r in rows: r['embedding_fingerprint']=self.index.fingerprint
            raw['index_generation']=self.index.fingerprint
            return {'source_ids':selected,'indexed_chunks':len(rows),'model':self.index.model_status()}
        return self.mutate('rebuild_search_index',{'source_ids':source_ids},expected_revision,key,action)
