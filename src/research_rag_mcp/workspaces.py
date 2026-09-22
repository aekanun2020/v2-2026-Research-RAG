"""Explicit workspace routing; no global current workspace or environment mutation."""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid

import portalocker

from .jobs import Jobs
from .persistence import atomic_json
from .store import Store, dump, now, require_text


class Workspaces:
    def __init__(self, default_root):
        self.default_root = Path(default_root).expanduser().resolve()
        self.root = Path(os.environ.get('RAG_WORKSPACES_ROOT',
                         str(self.default_root.with_name(self.default_root.name+'-workspaces')))).expanduser().resolve()
        if self.root.is_relative_to(self.default_root) or self.default_root.is_relative_to(self.root):
            raise ValueError('Workspace registry and default workspace must have disjoint directories')
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root/'registry.json'
        self.collection = os.environ.get('QDRANT_COLLECTION', 'research_chunks')
        self.mutex = threading.RLock()
        self.contexts = {}
        with self.lock():
            if not self.path.exists():
                atomic_json(self.path, {'schema':1, 'revision':0, 'default_root':str(self.default_root),
                    'collection_prefix':self.collection, 'workspaces':{}, 'requests':{}})
            self.read()

    def lock(self):
        return portalocker.Lock(str(self.root/'.registry.lock'), timeout=10)

    def read(self):
        raw = json.loads(self.path.read_text())
        if (raw['schema'] != 1 or raw['default_root'] != str(self.default_root)
                or raw['collection_prefix'] != self.collection):
            raise ValueError('Workspace registry configuration changed; do not reassign existing storage')
        return raw

    def describe(self, workspace_id):
        if workspace_id == 'default':
            return {'workspace_id':'default','name':'Default workspace',
                    'root':str(self.default_root),'qdrant_collection':self.collection}
        if not re.fullmatch(r'ws-[a-f0-9]{32}', workspace_id):
            raise ValueError('Unknown workspace_id; use list_workspaces or create_workspace')
        entry = self.read()['workspaces'].get(workspace_id)
        if not entry:
            raise ValueError('Unknown workspace_id; use list_workspaces or create_workspace')
        path = self.root/workspace_id
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError('Unsafe workspace directory')
        return {**entry, 'root':str(path),'qdrant_collection':self.collection+'_'+workspace_id}

    def context(self, workspace_id='default'):
        description = self.describe(workspace_id)
        with self.mutex:
            if workspace_id not in self.contexts:
                store = Store(description['root'], collection=description['qdrant_collection'])
                self.contexts[workspace_id] = (store, Jobs(store))
            return self.contexts[workspace_id]

    def list(self):
        raw = self.read()
        entries = [self.describe('default')]+[self.describe(w) for w in raw['workspaces']]
        return {'registry_revision':raw['revision'],'workspaces':entries,
                'default_workspace_id':'default', 'selection':'Pass workspace_id on every call; no global switch',
                'access_control':'None: workspace IDs separate data, not user permissions'}

    def create(self, name, expected_registry_revision, idempotency_key):
        require_text(name, 'name', 300)
        require_text(idempotency_key, 'idempotency_key', 200)
        fingerprint = hashlib.sha256(dump({'name':name}).encode()).hexdigest()
        with self.lock():
            raw = self.read()
            previous = raw['requests'].get(idempotency_key)
            if previous:
                if previous['fingerprint'] != fingerprint:
                    raise ValueError('Idempotency key already used with different workspace name')
                workspace_id = previous['workspace_id']
            else:
                if raw['revision'] != expected_registry_revision:
                    raise ValueError('Stale registry revision; read list_workspaces')
                if len(raw['workspaces']) >= 100:
                    raise ValueError('Workspace limit (100) reached')
                workspace_id = 'ws-'+uuid.uuid4().hex
                raw['workspaces'][workspace_id] = {'workspace_id':workspace_id,'name':name,'created_at':now()}
                raw['requests'][idempotency_key] = {'fingerprint':fingerprint,'workspace_id':workspace_id}
                raw['revision'] += 1
                atomic_json(self.path, raw)
        # A reconnect after a crash creates any missing empty directories for the
        # already recorded ID, rather than generating a second workspace.
        self.context(workspace_id)
        return {**self.describe(workspace_id),'registry_revision':self.read()['revision'],
                'next_step':'workspace_status(workspace_id), then start_project with researcher-supplied scope',
                'existing_workspaces_modified':False}
