"""Real MCP integration only; no mocks, direct Store calls or semantic model judge."""
import argparse,asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from verify_qdrant_retrieval_mcp import connect,call
parser=argparse.ArgumentParser(description='Rechunk real MCP-imported originals and check exact spans, history and boundaries.')
parser.add_argument('--baseline',required=True,help='Full real MCP baseline JSON from capture_chunking_baseline_mcp.py')
parser.add_argument('--phase',choices=['sentence','sections'],default='sections')
parser.add_argument('--report',required=True)
args=parser.parse_args()
phase=args.phase; before=json.loads(Path(args.baseline).read_text());report={'phase':phase,'endpoint':before['endpoint'],'documents':[]};out=Path(args.report)
if out.exists():raise ValueError('Preserve previous evidence: select a new report path')
async def main():
 async with connect(before['endpoint']) as s:
  for doc in before['documents']:
   state=await call(s,'workspace_status',{});args={'source_id':doc['source_id'],'chunk_size_tokens':512,'chunk_overlap_tokens':64,'expected_revision':state['revision'],'idempotency_key':out.stem+':'+doc['filename']}
   job=await call(s,'rechunk_document',args)
   while job['status'] in ('queued','running'):
    await asyncio.sleep(1);job=await call(s,'job_status',{'job_id':job['job_id']})
   print(doc['filename'],job['status'],job.get('error'),flush=True)
   report['documents'].append({'filename':doc['filename'],'arguments':args,'job':job});out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
   assert job['status']=='completed',job
   cs=job['result']['result']['chunk_set_id'];rows=[];offset=0
   active=await call(s,'list_chunks',{'source_id':doc['source_id']});assert active['chunk_set_id']!=cs
   while True:
    part=await call(s,'list_chunks',{'source_id':doc['source_id'],'chunk_set_id':cs,'offset':offset,'limit':100})
    for row in part['chunks']:
     c=await call(s,'read_chunk',{'chunk_id':row['id']});page=doc['pages'][str(c['page_index'])]['text'];assert page[c['start']:c['end']]==c['text'];assert c['token_count']<=512
     rows.append(c)
    offset+=len(part['chunks'])
    if offset>=part['total']:break
   old=await call(s,'read_chunk',{'chunk_id':doc['chunks'][0]['id']});assert old['text']==doc['chunks'][0]['text']
   result=await call(s,'activate_chunk_set',{'chunk_set_id':cs,'expected_revision':(await call(s,'workspace_status',{}))['revision'],'idempotency_key':'activate-'+out.stem+':'+doc['filename']})
   inspection=await call(s,'inspect_document_chunks',{'source_id':doc['source_id']});assert not any(p['uncovered_nonblank_spans'] for p in inspection['pages'])
   findings={'inside_word_starts':[],'cross_headings':[]}
   for c in rows:
    page=doc['pages'][str(c['page_index'])]['text'];n=c['start']
    if doc['filename'].endswith('.pdf') and n and page[n-1].isascii() and page[n-1].isalnum() and page[n].isascii() and page[n].isalnum():findings['inside_word_starts'].append({'id':c['id'],'page':c['page_index'],'start':n})
    if '\n## ' in c['text'].strip():findings['cross_headings'].append(c['id'])
   assert not findings['inside_word_starts'],findings
   if phase=='sections':assert not findings['cross_headings'],findings
   report['documents'][-1].update(chunks=rows,inspection=inspection,findings=findings,old_chunk_preserved=True,candidate_inactive_before_activation=True)
   out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print('verified',len(rows),'chunks',findings,flush=True)
  report['index']=await call(s,'search_index_status',{});assert report['index']['ready']
  report['after']=await call(s,'workspace_status',{});out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
asyncio.run(main())
