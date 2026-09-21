"""Revisioned JSON state: real interprocess locks and atomic durable commits.

This is the canonical research journal, not a SQL compatibility layer. Vectors
are exclusively in Qdrant. Readers see either the old or the new complete state.
"""
import copy
import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import portalocker


def encode(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(',', ':'))


def empty_state():
    return dict(schema=5,revision=0,project=None,sources={},chunks={},chunk_sets={},
                artifacts={},versions={},searches=[],events=[],requests={},
                pending_cleanup=None,pending_job=None,index_generation=None)


def atomic_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            stream.write(encode(value)+'\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,path)
        if os.name!='nt':
            directory=os.open(path.parent,os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


class Journal:
    def __init__(self,root):
        self.root=Path(root)
        self.path=self.root/'workspace.json'
        self._mutex=threading.RLock()
        self._writer=threading.RLock()
        self._cache=None
        self._signature=None
        with self.lock():
            if not self.path.exists(): self.commit(empty_state())
            self.read()

    @contextmanager
    def lock(self):
        with self._writer:
            with portalocker.Lock(str(self.root/'.workspace.lock'),timeout=10):
                yield

    def read(self):
        # Atomic replace permits lock-free readers; never expose mutable cache.
        with self._mutex:
            st=self.path.stat(); signature=(st.st_ino,st.st_size,st.st_mtime_ns)
            if signature!=self._signature:
                envelope=json.loads(self.path.read_text(encoding='utf-8'))
                state=envelope['state']
                if hashlib.sha256(encode(state).encode()).hexdigest()!=envelope['sha256']:
                    raise ValueError('Workspace journal checksum mismatch')
                if state['schema']!=5: raise ValueError('Unsupported journal schema')
                self._cache=state; self._signature=signature
            return copy.deepcopy(self._cache)

    def commit(self,state):
        envelope={'sha256':hashlib.sha256(encode(state).encode()).hexdigest(),'state':state}
        atomic_json(self.path,envelope)
        self._signature=None
