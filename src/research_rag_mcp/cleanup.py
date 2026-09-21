"""Preview-bound, resumable cleanup of the journal and real Qdrant index."""
import hashlib
import json
import secrets
from .purge import inventory, DATA_DIRECTORIES

SCOPES=('search_index','documents','workspace','all_except_inbox')


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False)


class WorkspaceCleanup:
    def _cleanup_plan(self,raw,scope):
        if scope not in SCOPES: raise ValueError('Unknown cleanup scope')
        if raw['pending_job']: raise ValueError('Wait for the ingestion job before cleanup')
        blockers=[]
        if scope=='documents' and (raw['artifacts'] or raw['versions']):
            blockers.append('Document cleanup is blocked by artifact/history citations')
        counts={'embeddings':len(raw['chunks']),'chunks':len(raw['chunks']) if scope!='search_index' else 0,
                'chunk_metadata':len(raw['chunks']) if scope!='search_index' else 0,
                'chunk_sets':len(raw['chunk_sets']) if scope!='search_index' else 0,
                'documents':len(raw['sources']) if scope!='search_index' else 0}
        for name in ('artifacts','versions','searches','events'):
            counts[name]=len(raw[name]) if scope in ('workspace','all_except_inbox') else 0
        plan={'scope':scope,'revision':raw['revision'],'workspace':str(self.root),'delete_counts':counts,
              'source_ids':sorted(raw['sources']),'artifact_ids':sorted(raw['artifacts']),
              'clears_project':scope in ('workspace','all_except_inbox'),'backup_required':scope!='all_except_inbox',
              'can_execute':not blockers,'blockers':blockers,'source_files_retained':len(raw['sources']),
              'preserves':['inbox','source files','existing exports/backups'],
              'limitation':'Cleanup does not improve relevance or provide secure erasure'}
        if scope=='all_except_inbox':
            files,inbox=inventory(self.root)
            plan.update(filesystem=files,inbox=inbox,source_files_retained=0,
                        preserves=['inbox','journal schema and cleanup receipt'])
        plan['plan_hash']=hashlib.sha256(encoded(plan).encode()).hexdigest()
        return plan

    def preview_workspace_cleanup(self,scope):
        with self.journal.lock():
            raw=self.raw_state();self.require_no_pending_cleanup(raw)
            return self._cleanup_plan(raw,scope)

    def cleanup_workspace(self,scope,plan_hash,expected_revision,key):
        if scope not in SCOPES or not isinstance(key,str) or not key.strip() or len(key)>200:
            raise ValueError('Supply supported scope and idempotency_key')
        fingerprint=hashlib.sha256(encoded(['cleanup_workspace',{'scope':scope,'plan_hash':plan_hash},'mcp-client']).encode()).hexdigest()
        with self.journal.lock():
            raw=self.raw_state();previous=raw['requests'].get(key)
            if previous:
                if previous['fingerprint']!=fingerprint or previous['response'] is None: raise ValueError('Idempotency key conflict/retired')
                return previous['response']
            pending=raw['pending_cleanup']
            if pending:
                if (pending['idempotency_key'],pending['plan_hash'],pending['expected_revision'],pending['scope'])!=(key,plan_hash,expected_revision,scope):
                    raise ValueError('Resume cleanup with its exact original arguments')
            else:
                if raw['revision']!=expected_revision: raise ValueError('Stale revision')
                plan=self._cleanup_plan(raw,scope)
                if not secrets.compare_digest(plan_hash,plan['plan_hash']): raise ValueError('Cleanup plan changed; preview again')
                if plan['blockers']: raise ValueError('; '.join(plan['blockers']))
                backup=self._backup_state(raw) if plan['backup_required'] else None
                raw['pending_cleanup']={'scope':scope,'plan_hash':plan_hash,'expected_revision':expected_revision,
                    'idempotency_key':key,'fingerprint':fingerprint,'plan':plan,'backup':backup}
                self.journal.commit(raw)
        return self._finish_cleanup(key)

    def _finish_cleanup(self,key):
        with self.journal.lock():
            raw=self.raw_state();job=raw['pending_cleanup']
            if not job or job['idempotency_key']!=key: raise ValueError('Unknown pending cleanup')
            plan=job['plan'];scope=job['scope'];vector_cleared=False
            try:
                self.index.clear();vector_cleared=True
                if scope=='all_except_inbox':
                    current,inbox=inventory(self.root)
                    if inbox!=plan['inbox']: raise ValueError('Inbox changed since preview')
                    expected={e['path']:e for e in plan['filesystem']['entries']}
                    for entry in current['entries']:
                        if expected.get(entry['path'])!=entry: raise ValueError('Unplanned or changed file: '+entry['path'])
                    for entry in sorted(current['entries'],key=lambda e:(e['path'].count('/'),e['path']),reverse=True):
                        path=self.root/entry['path']
                        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p.is_relative_to(self.root)):
                            raise ValueError('Refuse symlink during cleanup')
                        if entry['kind']=='file': path.unlink()
                        elif entry['path'] not in DATA_DIRECTORIES: path.rmdir()
                    remaining,inbox=inventory(self.root)
                    if inbox!=plan['inbox'] or any(e['path'] not in DATA_DIRECTORIES for e in remaining['entries']):
                        raise ValueError('Filesystem cleanup incomplete')
            except Exception as exc:
                return {'revision':raw['revision'],'result':{'operation':'cleanup_workspace','scope':scope,'status':'incomplete',
                    'reason':str(exc),'vector_index_cleared':vector_cleared,'journal_cleared':False,'backup':job['backup'],
                    'resume_with':{k:job[k] for k in ('scope','plan_hash','expected_revision','idempotency_key')}}}
            raw['index_generation']=None
            if scope!='search_index':
                for field in ('chunks','chunk_sets','sources'): raw[field]={}
            if scope in ('workspace','all_except_inbox'):
                raw.update(project=None,artifacts={},versions={},searches=[],events=[])
            for receipt in raw['requests'].values():
                if (receipt.get('response') or {}).get('result',{}).get('operation')!='cleanup_workspace': receipt['response']=None
            if scope=='all_except_inbox': raw['requests']={}
            raw['pending_cleanup']=None;raw['revision']+=1
            result={'operation':'cleanup_workspace','scope':scope,'status':'completed','deleted':plan['delete_counts'],
                'backup':job['backup'],'vector_index_cleared':True,'journal_cleared':scope!='search_index',
                'source_files_retained':plan['source_files_retained'],'preserves':plan['preserves'],
                'quality_improvement_claimed':False,'next_step':'rebuild_search_index' if scope=='search_index' else 'import_document'}
            if scope=='all_except_inbox': result.update(inbox_unchanged=True,deleted_files=plan['filesystem']['files'],filesystem_complete=True)
            response={'revision':raw['revision'],'result':result}
            raw['requests'][key]={'fingerprint':job['fingerprint'],'response':response}
            self.journal.commit(raw)
            return response
