"""Durable MCP jobs: requests acknowledge promptly; clients poll explicit status.

No automatic quality degradation. Work survives a client timeout; interrupted
server work requires explicit resume_job and reuses its original idempotency key.
"""
import hashlib
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .persistence import atomic_json
from .store import dump,now


class Jobs:
    def __init__(self,store):
        self.store=store;self.root=store.root/'jobs';self.root.mkdir(exist_ok=True)
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='research-ingest')
        self.instance=uuid.uuid4().hex;self.futures={};self.lock=threading.Lock()

    def path(self,identifier):
        if len(identifier)!=64 or any(c not in '0123456789abcdef' for c in identifier): raise ValueError('Invalid job_id')
        return self.root/(identifier+'.json')

    def status(self,identifier):
        path=self.path(identifier)
        if not path.is_file(): raise ValueError('Unknown job_id')
        value=json.loads(path.read_text())
        if value['status'] in ('queued','running') and value['instance']!=self.instance:
            value['status']='interrupted';value['next_step']='resume_job with this job_id'
        return {k:v for k,v in value.items() if k not in ('arguments','instance','fingerprint')}

    def submit(self,operation,arguments):
        key=arguments['key']
        if not isinstance(key,str) or not key.strip() or len(key)>200: raise ValueError('Invalid idempotency_key')
        identifier=hashlib.sha256(key.encode()).hexdigest();path=self.path(identifier)
        fingerprint=hashlib.sha256(dump([operation,arguments]).encode()).hexdigest()
        with self.lock:
            if path.exists():
                job=json.loads(path.read_text())
                if job['fingerprint']!=fingerprint: raise ValueError('Idempotency key already used with different input')
                return self.status(identifier)
            # Existing jobs are immutable receipts for repeated requests. Reading
            # their status must not wait behind the worker's long writer lock.
            current=self.store.raw_state()
            self.store.require_no_pending_cleanup(current)
            if current['pending_job']: raise ValueError('Another ingestion job is active; poll job_status')
            with self.store.journal.lock():
                raw=self.store.raw_state();self.store.require_no_pending_cleanup(raw)
                if raw['pending_job']: raise ValueError('Another ingestion job is active; poll job_status')
                if raw['revision']!=arguments['expected_revision']: raise ValueError('Stale revision; read workspace_status')
                if key in raw['requests']: raise ValueError('Key already belongs to a prior operation; use its original tool or a new key')
                job={'job_id':identifier,'operation':operation,'arguments':arguments,'fingerprint':fingerprint,
                     'instance':self.instance,'status':'queued','created_at':now(),'updated_at':now(),
                     'progress':None,'result':None,'error':None}
                atomic_json(path,job)
                raw['pending_job']={'job_id':identifier,'operation':operation,'idempotency_key':key}
                self.store.journal.commit(raw)
                self.futures[identifier]=self.executor.submit(self._run,identifier)
        return self.status(identifier)

    def resume(self,identifier):
        path=self.path(identifier)
        with self.lock,self.store.journal.lock():
            job=json.loads(path.read_text())
            if job['status']=='completed': return self.status(identifier)
            if identifier in self.futures and not self.futures[identifier].done(): return self.status(identifier)
            raw=self.store.raw_state();self.store.require_no_pending_cleanup(raw)
            if raw['pending_job'] and raw['pending_job']['job_id']!=identifier: raise ValueError('Another job is active')
            if raw['revision']!=job['arguments']['expected_revision'] and job['arguments']['key'] not in raw['requests'] and job['operation']!='import_directory':
                raise ValueError('Workspace changed; cannot resume against a different revision')
            job.update(status='queued',instance=self.instance,updated_at=now(),error=None)
            atomic_json(path,job)
            raw['pending_job']={'job_id':identifier,'operation':job['operation'],'idempotency_key':job['arguments']['key']}
            self.store.journal.commit(raw)
            self.futures[identifier]=self.executor.submit(self._run,identifier)
        return self.status(identifier)

    def _run(self,identifier):
        # One worker per MCP process. The durable journal reservation excludes
        # unrelated writers; reads remain available while embeddings run.
        path=self.path(identifier);job=json.loads(path.read_text());job.update(status='running',updated_at=now())
        atomic_json(path,job)
        def progress(done,total):
            job.update(progress={'indexed_chunks':done,'total_chunks':total},updated_at=now())
            atomic_json(path,job)
        self.store._job_progress=progress
        self.store._job_owner.key=job['arguments']['key']
        try:
            receipt=self.store.raw_state()['requests'].get(job['arguments']['key'])
            if receipt and receipt.get('response'):
                result=receipt['response']
            elif job['operation']=='restore_workspace':
                from .migration import restore_snapshot
                result=restore_snapshot(self.store,**job['arguments'])
            elif job['operation']=='migrate_legacy_workspace':
                from .migration import migrate_legacy
                result=migrate_legacy(self.store,**job['arguments'])
            else:
                result=getattr(self.store,job['operation'])(**job['arguments'])
            job.update(status='completed',result=result,error=None,updated_at=now())
        except Exception as exc:
            job.update(status='failed',error=str(exc),updated_at=now())
        finally:
            self.store._job_progress=None
            self.store._job_owner.key=None
            atomic_json(path,job)
            with self.store.journal.lock():
                raw=self.store.raw_state()
                if raw['pending_job'] and raw['pending_job']['job_id']==identifier:
                    raw['pending_job']=None;self.store.journal.commit(raw)
