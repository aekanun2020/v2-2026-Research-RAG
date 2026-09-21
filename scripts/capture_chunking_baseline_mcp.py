"""All ingestion and data inspection through the actual MCP endpoint."""
import argparse,asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from verify_qdrant_retrieval_mcp import connect,call
parser=argparse.ArgumentParser(description='Capture real baseline chunking from ELMo PDF and attributed Markdown originals in an empty dedicated MCP workspace.')
parser.add_argument('--url',required=True)
parser.add_argument('--report',required=True)
args=parser.parse_args()
out=Path(args.report)
if out.exists():raise ValueError('Preserve previous evidence: select a new report path')
async def main():
 report={'endpoint':args.url,'documents':[]}
 async with connect(report['endpoint']) as s:
  report['before']=await call(s,'workspace_status',{})
  assert not report['before']['sources']
  for filename,title,origin in [('elmo.pdf','Deep contextualized word representations','https://arxiv.org/abs/1802.05365'),('customerservice-policy.md','Upstream customer service policy','https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp/blob/5e5373a7a0919201b44f5aa78edad069a09974db/customerservice-policy.md'),('research-rag-readme.md','Research RAG README at 4901196','https://github.com/aekanun2020/2026-Research-RAG/blob/4901196/README.md')]:
   rev=(await call(s,'workspace_status',{}))['revision']
   args=dict(filename=filename,origin=origin,role='literature' if filename.endswith('.pdf') else 'project_note',bibliography={'title':title},expected_revision=rev,idempotency_key='chunking-baseline:'+filename)
   job=await call(s,'import_document',args)
   while job['status'] in ('queued','running'):
    await asyncio.sleep(1); job=await call(s,'job_status',{'job_id':job['job_id']})
   assert job['status']=='completed',job
   sid=job['result']['result']['source_id']; rows=[]; pages={};offset=0
   while True:
    part=await call(s,'list_chunks',{'source_id':sid,'offset':offset,'limit':100})
    for c in part['chunks']:
     rows.append(await call(s,'read_chunk',{'chunk_id':c['id']}))
     if str(c['page_index']) not in pages:pages[str(c['page_index'])]=await call(s,'read_source_page',{'source_id':sid,'page_index':c['page_index']})
    offset+=len(part['chunks'])
    if offset>=part['total']:break
   report['documents'].append({'filename':filename,'arguments':args,'job':job,'source_id':sid,'chunk_set_id':part['chunk_set_id'],'chunks':rows,'pages':pages})
   out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
   print(filename,len(rows),'chunks',flush=True)
  report['after']=await call(s,'workspace_status',{});out.write_text(json.dumps(report,ensure_ascii=False,indent=2))
asyncio.run(main())
