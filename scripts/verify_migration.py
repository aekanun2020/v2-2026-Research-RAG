"""Verify an actual 0.1.0 workspace snapshot; never synthesize a legacy schema.

The directory must be an isolated disposable copy with before.json produced by
real 0.1.0 import/search. This check migrates and rebuilds its index.
"""
import argparse
import json
import sqlite3
from pathlib import Path
from research_rag_mcp.store import Store

parser=argparse.ArgumentParser()
parser.add_argument('workspace',type=Path)
parser.add_argument('--report',required=True,type=Path)
args=parser.parse_args()
root=args.workspace
before=json.loads((root/'before.json').read_text())
with sqlite3.connect(root/'research.sqlite') as db:
    schema=db.execute('PRAGMA user_version').fetchone()[0]
    assert schema==1, 'Supply a fresh real 0.1.0 workspace, not an already migrated copy'
    old_ids=[r[0] for r in db.execute('SELECT id FROM chunks ORDER BY id')]
store=Store(root)
with store.connect() as db:
    assert db.execute('PRAGMA user_version').fetchone()[0]==4
    assert old_ids==[r[0] for r in db.execute('SELECT id FROM chunks ORDER BY id')]
for hit in before['hits']:
    assert store.read_chunk(hit['id'])['citation']==hit['citation']
source=before['source']; revision=store.read()['revision']
retry=store.import_document(source['filename'],source['origin'],source['role'],source['bibliography'],
                            revision-1,'legacy-import')
assert retry['result']==source
assert store.read()['revision']==revision
try:
    store.search('Bayesian',mode='semantic')
except ValueError as exc:
    assert 'missing or stale' in str(exc)
else:
    raise AssertionError('Legacy vectors must be explicitly rebuilt')
store.rebuild_search_index(None,revision,'migration-index')
assert store.search_index_status()['ready']
query='การประมาณค่าแบบเบย์สำหรับข้อมูลที่มีโครงสร้างหลายระดับ'
assert any(h['page_index']==0 and h['start']==0 for h in store.search(query,mode='semantic',limit=3)['hits'])
report={'before_schema':schema,'after_schema':4,'original_chunk_ids_preserved':len(old_ids),
        'citations_preserved':len(before['hits']),'legacy_retry_response_preserved':True,
        'index':store.search_index_status(),'original_thai_query_recovers_abstract_top3':True}
args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
