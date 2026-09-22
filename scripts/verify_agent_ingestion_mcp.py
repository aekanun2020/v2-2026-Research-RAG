"""Exercise real HTTP MCP, public PDFs and isolated Qdrant/Ollama; no substitutes."""
import argparse
import asyncio
import json
from pathlib import Path
import time

from verify_qdrant_retrieval_mcp import connect

PDF_URL = 'https://economics.mit.edu/sites/default/files/inline-files/Noy_Zhang_1_0.pdf'
TITLE = 'Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence'


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:9076/mcp')
    p.add_argument('--phase', choices=['workspace','download','prompt'], required=True)
    p.add_argument('--report', required=True)
    args = p.parse_args()
    path = Path(args.report)
    if path.exists(): raise ValueError('Preserve earlier evidence; use a new report filename')
    report = {'endpoint':args.url,'phase':args.phase,'calls':[],'checks':[],'status':'running'}
    def save(): path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def check(name, condition):
        report['checks'].append({'name':name,'passed':bool(condition)});save()
        if not condition: raise AssertionError(name)
    async def call(name, arguments=None, error=False):
        async with connect(args.url) as s:
            start=time.perf_counter();r=await s.call_tool(name,arguments or {})
        report['calls'].append({'tool':name,'arguments':arguments or {},'seconds':time.perf_counter()-start,
                               'response':r.model_dump(mode='json')});save()
        if error:
            check('expected rejection: '+name,r.is_error);return r
        if r.is_error: raise RuntimeError(str(r))
        return r.structured_content
    async def state(w='default'): return await call('workspace_status',{'workspace_id':w})
    async def create(name,key):
        rev=(await call('list_workspaces'))['registry_revision']
        return await call('create_workspace',{'name':name,'expected_registry_revision':rev,'idempotency_key':key})
    try:
        async with connect(args.url) as s:
            tools=(await s.list_tools()).tools
            report['tools']=[t.name for t in tools]
            if args.phase == 'prompt':
                prompt=await s.get_prompt('research_workflow')
                report['served_prompt']=prompt.model_dump(mode='json')
                instructions=prompt.messages[0].content.text
                check('served prompt distinguishes inbox staging from import','downloaded_to_inbox means bytes were staged, NOT imported' in instructions)
                check('served prompt requires explicit workspace and no note substitution',
                    'workspace_id explicitly on EVERY scoped call' in instructions and 'Download failure does not authorize a substitute' in instructions)
            check('create_workspace is available','create_workspace' in report['tools'])
            if args.phase != 'workspace':
                check('download_document is available','download_document' in report['tools'])
            check('all existing scoped tools expose workspace_id',all('workspace_id' in t.input_schema['properties'] for t in tools if t.name not in ['create_workspace','list_workspaces']))
        before=await state()
        a=await create('MCP regression A: original PDFs',path.stem+'-A')
        b=await create('MCP regression B: independent work',path.stem+'-B')
        wa,wb=a['workspace_id'],b['workspace_id'];report['workspaces']={'A':a,'B':b};save()
        retry=await call('create_workspace',{'name':a['name'],'expected_registry_revision':0,'idempotency_key':path.stem+'-A'})
        check('create exact retry retains workspace identity',retry['workspace_id']==wa)
        check('separate storage and vector collections',a['root']!=b['root'] and a['qdrant_collection']!=b['qdrant_collection'])
        await call('create_workspace',{'name':'changed name','expected_registry_revision':0,'idempotency_key':path.stem+'-A'},error=True)
        await call('workspace_status',{'workspace_id':'../default'},error=True)
        await call('workspace_status',{'workspace_id':'ws-'+'0'*32},error=True)
        async def start(w,topic):
            st=await state(w)
            return await call('start_project',{'workspace_id':w,'topic':topic,'goal':'Verify workspace separation through real MCP','unknowns':[], 'expected_revision':st['revision'],'idempotency_key':'same-key-across-workspaces'})
        results=await asyncio.gather(start(wa,'Independent project A'),start(wb,'Independent project B'))
        check('parallel calls route to their explicit workspace',[r['workspace_id'] for r in results]==[wa,wb])
        sa,sb=await asyncio.gather(state(wa),state(wb))
        check('projects remain independent',sa['project']['topic']=='Independent project A' and sb['project']['topic']=='Independent project B')
        await call('start_project',{'workspace_id':wa,'topic':'Overwrite','goal':'Should reject','unknowns':[],'expected_revision':sa['revision'],'idempotency_key':'overwrite'},error=True)
        if args.phase != 'workspace':
            await download_checks(call,check,state,wa,wb,path.stem,report,args.url)
        if args.phase == 'prompt':
            await provenance_checks(call,check,state,wa,wb,path.stem,report)
        after=await state()
        check('default project, sources and revision untouched',all(before[k]==after[k] for k in ['revision','project','sources','artifacts']))
        report['status']='passed';save()
        print(json.dumps({'status':report['status'],'checks':len(report['checks']),'workspaces':report['workspaces'],'report':str(path)},ensure_ascii=False))
    except Exception as e:
        report['status']='failed';report['error']=str(e);save();raise


async def download_checks(call,check,state,wa,wb,key,report,url):
    async def poll(job,w=wa,fail=False):
        deadline=time.monotonic()+1200
        while job['status'] not in ('completed','failed','interrupted'):
            if time.monotonic()>deadline: raise TimeoutError('MCP job did not finish within test budget')
            await asyncio.sleep(3)
            job=await call('job_status',{'job_id':job['job_id'],'workspace_id':w})
        check('job reaches '+('failed' if fail else 'completed'),job['status']==('failed' if fail else 'completed'))
        return job
    initial=await state(wa)
    args={'url':PDF_URL,'workspace_id':wa,'expected_revision':initial['revision'],'idempotency_key':key+'-download'}
    started=time.perf_counter();job=await call('download_document',args)
    check('durable download acknowledges within 5 seconds',time.perf_counter()-started<5)
    completed=await poll(job);receipt=completed['result']['result'];report['download']=receipt
    check('download returns actual PDF metadata',receipt['status']=='downloaded_to_inbox' and receipt['page_count']>0 and receipt['bytes']>1000 and len(receipt['sha256'])==64)
    retry=await call('download_document',args)
    check('exact download retry reuses completed job',retry['job_id']==job['job_id'] and retry['result']==completed['result'])
    staged=await call('document_ingestion_status',{'filename':receipt['filename'],'workspace_id':wa})
    check('download alone has no source or chunks',not staged['imported'] and staged['active_chunks']==0 and not (await state(wa))['sources'])
    await call('preview_inbox_document',{'filename':receipt['filename'],'workspace_id':wb},error=True)
    await call('job_status',{'job_id':job['job_id'],'workspace_id':wb},error=True)
    preview=await call('preview_inbox_document',{'filename':receipt['filename'],'workspace_id':wa})
    check('original PDF title inspected before import','experimental evidence on the productivity effects' in ' '.join(preview['text'].lower().split()))
    imported=await poll(await call('import_document',{'filename':receipt['filename'],'origin':receipt['final_url'],
        'role':'literature','bibliography':{'title':TITLE},'expected_revision':(await state(wa))['revision'],
        'idempotency_key':key+'-import','workspace_id':wa}))
    source=imported['result']['result'];report['imported_source']=source
    check('import source ID matches original PDF hash',source['source_id']==receipt['sha256'])
    ingested=await call('document_ingestion_status',{'filename':receipt['filename'],'workspace_id':wa})
    check('explicit import produces source and active chunks',ingested['imported'] and ingested['active_chunks']>0)
    hits=await call('retrieve_evidence',{'query':'ChatGPT effects on writing productivity and quality',
        'mode':'hybrid','source_ids':[source['source_id']],'limit':2,'workspace_id':wa})
    check('real hybrid retrieval returns imported paper',bool(hits['hits']) and all(h['source_id']==source['source_id'] for h in hits['hits']))
    for hit in hits['hits']:
        page=await call('read_source_page',{'source_id':hit['source_id'],'page_index':hit['page_index'],'workspace_id':wa})
        check('retrieved quote resolves to original page span',page['text'][hit['start']:hit['end']]==hit['citation']['quote']==hit['text'])
    empty=await call('retrieve_evidence',{'query':'ChatGPT productivity','mode':'hybrid','workspace_id':wb})
    check('other workspace has no evidence leakage',not empty['hits'] and not (await state(wb))['sources'])
    rev=(await state(wa))['revision']
    for bad in [{'url':'http://example.org/paper.pdf'},{'url':PDF_URL,'arxiv_id':'2606.09863'}, {'arxiv_id':'../etc/passwd'}, {'url':'https://user:password@example.org/x.pdf'}]:
        await call('download_document',{**bad,'expected_revision':rev,'idempotency_key':key+'-invalid','workspace_id':wa},error=True)
    private=await poll(await call('download_document',{'url':'https://127.0.0.1/paper.pdf','workspace_id':wa,
        'expected_revision':rev,'idempotency_key':key+'-private'}),fail=True)
    check('private destination rejected before request','public IP' in private['error'])
    html=await poll(await call('download_document',{'url':'https://economics.mit.edu/','workspace_id':wa,
        'expected_revision':rev,'idempotency_key':key+'-html'}),fail=True)
    check('HTML is not silently treated as a PDF','not a PDF' in html['error'])
    end=await state(wa)
    check('failed downloads do not mutate project or invent notes',end['revision']==rev and len(end['sources'])==1 and all(s['role']=='literature' for s in end['sources'].values()))


async def provenance_checks(call,check,state,wa,wb,key,report):
    source=report['imported_source']
    check('PDF import reports actual format and download provenance',source['source_format']=='pdf'
        and source['evidence_kind']=='pdf_source' and source['download_provenance']['sha256']==source['source_id'])
    current=await state(wa)
    content=('MCP regression observation: downloaded PDF SHA-256 '+source['source_id']+
        ' was explicitly imported into workspace '+wa+'. This is a test execution note, not the original paper.')
    job=await call('add_context',{'content':content,'title':'MCP regression execution note',
        'source':'real MCP calls in '+key+'.json','expected_revision':current['revision'],
        'idempotency_key':key+'-note','workspace_id':wa})
    deadline=time.monotonic()+120
    while job['status'] in ('queued','running'):
        if time.monotonic()>deadline: raise TimeoutError('Note job timed out')
        await asyncio.sleep(2);job=await call('job_status',{'job_id':job['job_id'],'workspace_id':wa})
    check('explicitly requested execution note imports',job['status']=='completed')
    note=job['result']['result']
    check('note receipt distinguishes text note from PDF',note['role']=='project_note'
        and note['source_format']=='md' and note['evidence_kind']=='project_note' and 'download_provenance' not in note)
    hits=await call('retrieve_evidence',{'query':'MCP regression observation','source_ids':[note['source_id']],
        'mode':'hybrid','workspace_id':wa})
    check('retrieval preserves note classification',bool(hits['hits']) and all(h['evidence_kind']=='project_note'
        and h['source_format']=='md' for h in hits['hits']))
    status=await call('document_ingestion_status',{'filename':note['filename'],'workspace_id':wa})
    check('ingestion status does not relabel a note as PDF',status['format']=='md' and status['source']['evidence_kind']=='project_note')


if __name__ == '__main__': asyncio.run(main())
