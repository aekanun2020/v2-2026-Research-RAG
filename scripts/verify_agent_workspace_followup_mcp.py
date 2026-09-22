"""Related real-MCP workspace, manuscript and recovery checks on test data only."""
import argparse
import asyncio
import json
from pathlib import Path
import time

from verify_qdrant_retrieval_mcp import connect


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:9076/mcp')
    parser.add_argument('--seed-report', required=True)
    parser.add_argument('--report', required=True)
    args=parser.parse_args()
    seed=json.loads(Path(args.seed_report).read_text())
    if seed['status']!='passed' or seed['phase']!='prompt' or seed['endpoint']!=args.url:
        raise ValueError('Requires a passing prompt-phase report for this exact endpoint')
    wa,wb=(seed['workspaces'][k]['workspace_id'] for k in ('A','B'))
    if wa=='default' or wb=='default': raise ValueError('Never mutate default')
    out=Path(args.report)
    if out.exists(): raise ValueError('Preserve earlier evidence')
    report={'endpoint':args.url,'seed_report':args.seed_report,'workspaces':{'A':wa,'B':wb},
        'calls':[],'checks':[],'status':'running'}
    def save(): out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def check(name,ok):
        report['checks'].append({'name':name,'passed':bool(ok)});save()
        if not ok: raise AssertionError(name)
    async def call(name,arguments=None,w=wa,error=False):
        arguments=dict(arguments or {})
        if name!='list_workspaces': arguments['workspace_id']=w
        async with connect(args.url) as s:
            started=time.monotonic();response=await s.call_tool(name,arguments)
        report['calls'].append({'tool':name,'arguments':arguments,'seconds':time.monotonic()-started,
            'response':response.model_dump(mode='json')});save()
        if error:
            check('expected rejection: '+name,response.is_error);return response
        if response.is_error: raise RuntimeError(str(response))
        return response.structured_content
    async def state(w=wa): return await call('workspace_status',w=w)
    async def mutate(name,arguments,key):
        return await call(name,{**arguments,'expected_revision':(await state())['revision'],
            'idempotency_key':out.stem+'-'+key})
    async def poll(value):
        deadline=time.monotonic()+300
        while value['status'] in ('queued','running'):
            if time.monotonic()>deadline: raise TimeoutError('Job deadline')
            await asyncio.sleep(2);value=await call('job_status',{'job_id':value['job_id']})
        check('durable job completed',value['status']=='completed')
        return value['result']
    async def cleanup(scope,key):
        plan=await call('preview_workspace_cleanup',{'scope':scope})
        value=await call('cleanup_workspace',{'scope':scope,'plan_hash':plan['plan_hash'],
            'expected_revision':plan['revision'],'idempotency_key':out.stem+'-'+key})
        check('selected workspace cleanup completes',value['result']['status']=='completed')
        return value
    try:
        original=await state();other=await state(wb);default=await state('default')
        check('scope is the recorded disposable validation workspace',original['project']['topic']=='Independent project A'
            and other['project']['topic']=='Independent project B'
            and set(original['sources'])==set(c['response']['structured_content']['source_id']
                for c in seed['calls'] if c['tool']=='read_source_page') | set(sid for sid,s in original['sources'].items() if s['role']=='project_note'))
        check('validation workspace contains no existing manuscript',not original['artifacts'])
        source_id=seed['imported_source']['source_id']
        page=await call('read_source_page',{'source_id':source_id,'page_index':0})
        phrase='Working Paper (not peer reviewed)';start=page['text'].index(phrase)
        citation={'source_id':source_id,'page_index':0,'start':start,'end':start+len(phrase),'quote':phrase,'relation':'context'}
        for tool,stage in [('explore_topics','exploration'),('map_research_gaps','gaps'),('formulate_question','question'),
            ('design_study','design'),('track_execution','execution'),('interpret_results','analysis'),('draft_manuscript','manuscript')]:
            value=await call(tool,{'query':'ChatGPT writing productivity','limit':1})
            check(tool+' routes stage context to selected workspace',value['workspace_id']==wa and value['stage']==stage and value['project']==original['project'])
        blocks=[{'section':section,'text':'Not drafted: this artifact checks workspace routing and revision preservation.',
            'basis':'unresolved','citations':[]} for section in original['stages']['manuscript']['sections']]
        blocks.append({'section':'introduction','text':'The imported file identifies itself as a working paper that is not peer reviewed.',
            'basis':'evidence','citations':[citation]})
        body={'stage':'manuscript','title':'MCP regression draft — unresolved','blocks':blocks,
            'limitations':['Integration test artifact; not a scientific manuscript or accepted research.'],'dependency_ids':[]}
        first=(await mutate('save_artifact',body,'draft-v1'))['result']
        second=(await mutate('save_artifact',{**body,'artifact_id':first['id'],'title':'MCP regression draft — revision 2'},'draft-v2'))['result']
        check('manuscript retains ID and increments version',first['id']==second['id'] and first['version']==1 and second['version']==2)
        historical=await call('read_artifact',{'artifact_id':first['id'],'version':1})
        check('manuscript earlier version remains readable',historical['version']==1 and historical['title']==first['title'])
        await call('read_artifact',{'artifact_id':first['id']},w=wb,error=True)
        exported=await call('export_manuscript',{'manuscript_id':first['id'],'expected_revision':(await state())['revision'],'mode':'draft'})
        check('draft export belongs to selected workspace',wa in exported['directory'] and exported['manuscript_id']==first['id'])
        await call('export_manuscript',{'manuscript_id':first['id'],'expected_revision':(await state())['revision'],'mode':'reviewed'},error=True)
        backup=await call('backup_workspace')
        before_cleanup=await state()
        await cleanup('workspace','clear-for-restore')
        check('cleanup leaves other workspace intact',(await state(wb))==other)
        restored=await poll(await mutate('restore_workspace',{'snapshot':Path(backup['directory']).name},'restore'))
        recovered=await state()
        check('restore preserves source and manuscript identities',recovered['sources']==before_cleanup['sources']
            and recovered['artifacts']==before_cleanup['artifacts'] and recovered['project']==before_cleanup['project'])
        check('restored Qdrant collection has all vectors',recovered['search_index']['ready']
            and recovered['search_index']['indexed_chunks']==before_cleanup['search_index']['indexed_chunks'])
        found=await call('retrieve_evidence',{'query':'ChatGPT productivity','mode':'hybrid','source_ids':[source_id],'limit':1})
        check('real retrieval works after restore',bool(found['hits']))
        # Public arXiv download tests the ID route, without importing another paper.
        arxiv=await poll(await mutate('download_document',{'arxiv_id':'1802.05365v2'},'arxiv'))
        receipt=arxiv['result'];preview=await call('preview_inbox_document',{'filename':receipt['filename']})
        check('arXiv ID resolves to actual original PDF','Deep contextualized word representations' in preview['text']
            and receipt['requested_url']=='https://arxiv.org/pdf/1802.05365v2')
        check('arXiv download remains inbox-only',not (await call('document_ingestion_status',{'filename':receipt['filename']}))['imported'])
        check('default and second workspace remain unchanged',(await state('default'))==default and (await state(wb))==other)
        report.update(status='passed',manuscript_id=first['id'],source_id=source_id);save()
        print(json.dumps({'status':'passed','checks':len(report['checks']),'report':str(out)}))
    except Exception as exc:
        report.update(status='failed',error=str(exc));save();raise


if __name__=='__main__': asyncio.run(main())
