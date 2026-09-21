"""One-time read-only legacy import, invoked exclusively by an MCP migration job.

SQLite is used only to READ a schema-4 legacy snapshot. It is not a runtime
backend, compatibility interface, or alternative search path in the new server.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path
from .store import dump,sha


def migrate_legacy(store,expected_revision,key):
    configured=os.environ.get('RAG_LEGACY_ROOT')
    if not configured: raise ValueError('No read-only RAG_LEGACY_ROOT configured')
    root=Path(configured).resolve();database=root/'research.sqlite'
    if not database.is_file(): raise ValueError('Configured legacy database is missing')
    import sqlite3
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        db.execute('BEGIN')
        if db.execute('PRAGMA user_version').fetchone()[0]!=4: raise ValueError('Legacy migration requires schema 4')
        if db.execute('SELECT count(*) FROM cleanup_jobs').fetchone()[0]: raise ValueError('Legacy cleanup is incomplete')
        meta=dict(db.execute('SELECT * FROM meta WHERE id=1').fetchone())
        sources={r['id']:json.loads(r['data']) for r in db.execute('SELECT * FROM documents')}
        chunk_sets={r['id']:{**json.loads(r['data']),'active':bool(r['active'])} for r in db.execute('SELECT * FROM chunk_sets')}
        chunks={r['id']:dict(r) for r in db.execute('SELECT c.*,m.chunk_set_id,m.status,m.reason,m.updated_at FROM chunks c JOIN chunk_metadata m ON m.chunk_id=c.id')}
        artifacts={r['id']:json.loads(r['data']) for r in db.execute('SELECT * FROM artifacts')}
        versions={}
        for row in db.execute('SELECT * FROM versions'):
            versions.setdefault(row['artifact_id'],{})[str(row['version'])]=json.loads(row['data'])
        searches=[json.loads(r['data']) for r in db.execute('SELECT * FROM searches ORDER BY rowid')]
        events=[dict(r) for r in db.execute('SELECT * FROM events ORDER BY id')]
        requests={r['key']:{'fingerprint':r['fingerprint'],'response':json.loads(r['response']) if r['response'] else None} for r in db.execute('SELECT * FROM requests')}
    payload={'legacy_revision':meta['revision'],'source_ids':sorted(sources),'chunks':len(chunks)}
    def action(raw,state):
        if any(raw[field] for field in ('sources','chunks','artifacts','versions','searches')) or raw['project']:
            raise ValueError('Legacy import requires an empty new workspace')
        for sid,source in sources.items():
            original=(root/source['file']).resolve()
            if not original.is_relative_to(root/'sources') or not original.is_file() or sha(original.read_bytes())!=source['sha256']:
                raise ValueError('Legacy original path/hash mismatch: '+sid)
            if sha(dump(source['pages']).encode())!=source['text_sha256']: raise ValueError('Legacy page checksum mismatch')
            dest=store.root/source['file'];dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(original,dest)
            store.verify_source(source)
        for row in chunks.values():
            page=sources[row['source_id']]['pages'][row['page_index']]['text']
            if page[row['start']:row['end']]!=row['text']: raise ValueError('Legacy chunk span mismatch')
        store.index.index_rows(list(chunks.values()),sources,getattr(store,'_job_progress',None))
        for row in chunks.values(): row['embedding_fingerprint']=store.index.fingerprint
        raw.update(project=json.loads(meta['project']) if meta['project'] else None,sources=sources,chunks=chunks,
                   chunk_sets=chunk_sets,artifacts=artifacts,versions=versions,searches=searches,events=events,requests=requests,
                   index_generation=store.index.fingerprint,legacy_revision=meta['revision'])
        # Continue the original revision sequence, preserving historical receipts.
        state['revision']=meta['revision']
        return {'legacy_revision':meta['revision'],'sources':len(sources),'chunks':len(chunks),'artifacts':len(artifacts),
                'identity_and_spans_preserved':True,'originals_preserved':True,'inbox_copied':False,
                'vectors_reembedded_with':store.index.model_status(),'legacy_modified':False}
    return store.mutate('migrate_legacy_workspace',payload,expected_revision,key,action)


def restore_snapshot(store,snapshot,expected_revision,key):
    root=(store.root/'backups').resolve()
    original=(root/snapshot).resolve()
    if not original.is_relative_to(root) or not original.is_dir():
        raise ValueError('Snapshot must be an existing directory inside this workspace backups')
    records=json.loads((original/'manifest.json').read_text())
    if not {'workspace.json','qdrant-points.json'}<=set(records): raise ValueError('Incomplete JSON/Qdrant snapshot')
    for name,digest in records.items():
        path=(original/name).resolve()
        if Path(name).is_absolute() or '..' in Path(name).parts or not path.is_relative_to(original) or sha(path.read_bytes())!=digest:
            raise ValueError('Backup manifest/path/hash mismatch')
    from .persistence import encode
    envelope=json.loads((original/'workspace.json').read_text());restored=envelope['state']
    if sha(encode(restored).encode())!=envelope['sha256'] or restored['schema']!=5:
        raise ValueError('Invalid snapshot journal')
    def action(raw,state):
        if raw['sources'] or raw['artifacts'] or raw['project']: raise ValueError('Restore requires an empty workspace')
        points=json.loads((original/'qdrant-points.json').read_text())
        store.index.restore_points(points)
        for source in restored['sources'].values():
            src=original/source['file'];target=store.root/source['file'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,target)
        pending=raw['pending_job']
        raw.update(restored);raw['pending_job']=pending;raw['pending_cleanup']=None
        state['revision']=max(state['revision'],restored['revision'])
        for source in restored['sources'].values(): store.verify_source(source)
        return {'snapshot':snapshot,'restored_sources':len(restored['sources']),'restored_chunks':len(restored['chunks']),
                'restored_revision':restored['revision'],'identities_preserved':True}
    return store.mutate('restore_workspace',{'snapshot':snapshot},expected_revision,key,action)
