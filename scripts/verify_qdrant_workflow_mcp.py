"""Real MCP integration on a separate workspace/collection; no simulated dependencies.

Uses a supplied original ELMo PDF, the selected upstream's real Thai policy,
the archived short publisher-policy excerpt, and measured MCP latencies.
Unresolved manuscript blocks exercise persistence; they are not research findings.
Never accepts work on behalf of a human researcher.
"""
import argparse
import asyncio
import csv
import io
import json
import time
from pathlib import Path
from verify_qdrant_retrieval_mcp import connect


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--url', default='http://127.0.0.1:8879/mcp')
    p.add_argument('--report', required=True)
    args = p.parse_args()
    out = Path(args.report)
    if out.exists(): raise ValueError('Preserve prior evidence; use a new report')
    report = {'endpoint':args.url, 'authentication':'none', 'calls':[], 'checks':[], 'status':'running',
              'scope':'Dedicated validation workspace; real originals and measured data; no human acceptance'}
    def save(): out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def check(name, condition):
        report['checks'].append({'name':name,'passed':bool(condition)}); save()
        assert condition, name
    async def call(name,arguments=None,error=False):
        # A new real MCP session on every call tests reconnect/poll semantics.
        arguments=dict(arguments or {})
        if 'idempotency_key' in arguments: arguments['idempotency_key']=out.stem+':'+arguments['idempotency_key']
        async with connect(args.url) as session:
            start=time.perf_counter();response=await session.call_tool(name,arguments or {})
            row={'tool':name,'arguments':arguments or {},'seconds':time.perf_counter()-start,
                 'response':response.model_dump(mode='json')}
            report['calls'].append(row);save()
            if error:
                check('expected rejection: '+name,response.is_error)
                return response
            if response.is_error: raise RuntimeError(str(response))
            return response.structured_content
    async def revision(): return (await call('workspace_status'))['revision']
    async def mutate(name,arguments,key):
        return await call(name,{**arguments,'expected_revision':await revision(),'idempotency_key':key})
    async def job(name,arguments,key):
        initial=await mutate(name,arguments,key)
        check(name+' returns durable job_id',bool(initial.get('job_id')))
        check(name+' acknowledged within 5 seconds',report['calls'][-1]['seconds']<5)
        value=initial
        while value['status'] in ('queued','running'):
            await asyncio.sleep(0.5)
            value=await call('job_status',{'job_id':value['job_id']})
        check(name+' job completed',value['status']=='completed')
        return value
    def citation(page, length=200):
        return dict(source_id=page['source_id'],page_index=page['page_index'],start=0,
                    end=min(length,len(page['text'])),quote=page['text'][:length],relation='context')
    async def cleanup(scope,key):
        plan=await call('preview_workspace_cleanup',{'scope':scope})
        result=await call('cleanup_workspace',{'scope':scope,'plan_hash':plan['plan_hash'],
                            'expected_revision':plan['revision'],'idempotency_key':key})
        check(scope+' completed',result['result']['status']=='completed')
        return result
    try:
        state=await call('workspace_status')
        check('dedicated workspace initially empty',not state['sources'] and not state['project'])
        preview=await call('preview_inbox_document',{'filename':'elmo.pdf'})
        check('real ELMo title from preview','Deep contextualized word representations' in preview['text'])
        await call('preview_inbox_document',{'filename':'batch/customerservice-policy.md'})
        await call('preview_inbox_document',{'filename':'batch/elsevier-policy-excerpt.txt'})
        await mutate('start_project',{'topic':'Verify the authorized Qdrant research-rag migration',
                      'goal':'Check real import, retrieval, original spans and manuscript persistence through MCP',
                      'unknowns':['Semantic relevance requires Codex assessment; human scientific acceptance remains pending']},'validation-start')
        import_args=dict(filename='elmo.pdf',origin='https://arxiv.org/abs/1802.05365',role='literature',
                         bibliography={'title':'Deep contextualized word representations'},
                         expected_revision=await revision(),idempotency_key='validation-elmo')
        first=await call('import_document',import_args)
        check('PDF import acknowledged within 5 seconds',report['calls'][-1]['seconds']<5)
        repeated=await call('import_document',import_args)
        check('exact import retry acknowledged within 5 seconds',report['calls'][-1]['seconds']<5)
        check('reconnect repeats same durable job',first['job_id']==repeated['job_id'])
        await call('import_document',{**import_args,'origin':'changed-origin'},error=True)
        during=await call('workspace_status')
        check('workspace status remains responsive during import',report['calls'][-1]['seconds']<5)
        value=first
        while value['status'] in ('queued','running'):
            await asyncio.sleep(1);value=await call('job_status',{'job_id':first['job_id']})
        check('PDF import completed after client disconnected',value['status']=='completed')
        pdf=value['result']['result']['source_id']
        resumed=await call('resume_job',{'job_id':first['job_id']})
        check('completed resume returns same receipt',resumed['result']==value['result'])
        await job('add_directory',{'path':'batch','role':'project_note','bibliography_by_filename':{
            'batch/customerservice-policy.md':{'title':'Upstream customer service policy'},
            'batch/elsevier-policy-excerpt.txt':{'title':'Elsevier generative AI policy excerpt'}}},'validation-batch')
        sources=await call('list_sources')
        # The separate guidelines-role source uses the actual publisher excerpt,
        # with its source URL prefix so it is a distinct attributed document.
        guideline=await job('add_context',{'content':'Source: https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals\n\n'+Path('tests/evidence/elsevier-policy-excerpt.txt').read_text(),
            'title':'Elsevier AI policy — short attributed excerpt','source':'https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals',
            'role':'journal_guidelines'},'validation-guideline')
        guideline_id=guideline['result']['result']['source_id']
        measured=json.loads(Path('docs/qdrant-concurrent-2026-09-21.json').read_text())
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['source_id','latency_seconds'])
        writer.writerows((r['case']['id'],r['seconds']) for r in measured['calls'])
        data=await job('add_context',{'content':stream.getvalue(),'format':'csv','role':'results',
            'title':'Measured 12-client hybrid MCP latencies, 2026-09-21','source':'docs/qdrant-concurrent-2026-09-21.json'},'validation-measurements')
        data_id=data['result']['result']['source_id']
        summary=await call('summarize_dataset',{'source_id':data_id})
        check('CSV summary uses 12 actual measurements',summary['rows']==12)
        lat=next(c for c in summary['columns'] if c['column']=='latency_seconds')
        check('CSV mean matches measured timings',abs(lat['mean']-sum(r['seconds'] for r in measured['calls'])/12)<1e-10)
        current=await call('workspace_status')
        thai_id=next(sid for sid,src in current['sources'].items() if src['filename']=='customerservice-policy.md')
        for left,right in [('PDPA','pdpa'),('2562','๒๕๖๒')]:
            a=await call('retrieve_evidence',dict(query=left,mode='lexical',source_ids=[thai_id],limit=3))
            b=await call('retrieve_evidence',dict(query=right,mode='lexical',source_ids=[thai_id],limit=3))
            check('normalized lexical matches: '+right,bool(a['hits']) and [h['id'] for h in a['hits']]==[h['id'] for h in b['hits']])
        thai=await call('search_documentation',{'query':'การคุ้มครองข้อมูลส่วนบุคคล','search_mode':'bm25','limit':3})
        chunks=await call('list_chunks',{'source_id':pdf,'limit':100})
        chunk=await call('read_chunk',{'chunk_id':chunks['chunks'][0]['id']})
        context=await call('get_chunk_context',{'chunk_id':chunk['id']})
        check('chunk exact original span',context['source_page']['text'][chunk['start']:chunk['end']]==chunk['text'])
        await call('inspect_document_chunks',{'source_id':pdf})
        old_set=chunks['chunk_set_id']
        candidate=await job('rechunk_document',{'source_id':pdf,'chunk_size_tokens':384,'chunk_overlap_tokens':48},'validation-rechunk')
        new_set=candidate['result']['result']['chunk_set_id']
        check('candidate does not activate itself',(await call('list_chunks',{'source_id':pdf}))['chunk_set_id']==old_set)
        await mutate('activate_chunk_set',{'chunk_set_id':new_set},'validation-activate')
        check('old chunk remains readable',(await call('read_chunk',{'chunk_id':chunk['id']}))['text']==chunk['text'])
        active=await call('list_chunks',{'source_id':pdf,'limit':1})
        excluded=active['chunks'][0]['id']
        await mutate('set_chunk_status',{'chunk_id':excluded,'status':'excluded','reason':'Exercise explicit withholding in dedicated validation workspace'},'validation-exclude')
        retrieved=await call('retrieve_evidence',{'query':'Deep contextualized word representations','source_ids':[pdf],'limit':30})
        check('excluded chunk absent from hybrid',all(h['id']!=excluded for h in retrieved['hits']))
        await mutate('set_chunk_status',{'chunk_id':excluded,'status':'active','reason':'Restore chunk after measured exclusion check'},'validation-reactivate')
        current=await call('workspace_status')
        for stage,definition in current['stages'].items():
            if definition['number'] and stage!='submission':
                context=await call(definition['tool'],{'query':'contextual word representations','limit':2})
                check('stage context '+stage,context['stage']==stage)
        page=await call('read_source_page',{'source_id':pdf,'page_index':0})
        cite=citation(page)
        def blocks(stage):
            return [dict(section=section,text='Unresolved scientific content in the explicitly identified MCP integration record.',
                         basis='unresolved',citations=[cite]) for section in current['stages'][stage]['sections']]
        base={'stage':'manuscript','title':'Integration record — no scientific findings or submission',
              'blocks':blocks('manuscript'),'limitations':['Software persistence exercise only; no human review or scientific conclusion.'],'dependency_ids':[]}
        artifact=(await mutate('save_artifact',base,'validation-manuscript'))['result']
        check('manuscript receives ID and version',bool(artifact['id']) and artifact['version']==1)
        altered={**base,'blocks':[dict(b) for b in base['blocks']]}
        altered['blocks'][0]={**altered['blocks'][0],'citations':[{**cite,'quote':cite['quote']+'X'}]}
        await call('save_artifact',{**altered,'expected_revision':await revision(),'idempotency_key':'validation-bad-citation'},error=True)
        revised=(await mutate('save_artifact',{**base,'artifact_id':artifact['id'],'title':base['title']+' revision 2'},'validation-manuscript-v2'))['result']
        check('manuscript keeps ID and increments revision',revised['id']==artifact['id'] and revised['version']==2 and revised['status']=='draft')
        historical=await call('read_artifact',{'artifact_id':artifact['id'],'version':1})
        check('old manuscript preserved',historical['title']==artifact['title'] and historical['historical'])
        usage=await call('find_evidence_usage',{'chunk_id':chunk['id']})
        check('citations linked across manuscript revisions',{u['version'] for u in usage['usages']}=={1,2})
        submission=await call('prepare_submission',{'manuscript_id':artifact['id'],'guideline_source_id':guideline_id})
        check('submission blocks unresolved/unreviewed manuscript',bool(submission['blockers']) and not submission['automatic_submission'])
        exported=await call('export_manuscript',{'manuscript_id':artifact['id'],'expected_revision':await revision(),'mode':'draft'})
        check('real draft export contains evidence and manuscript','manuscript.md' in exported['files'] and 'evidence.json' in exported['files'])
        await call('export_manuscript',{'manuscript_id':artifact['id'],'expected_revision':await revision(),'mode':'reviewed'},error=True)
        index_before=await call('search_index_status')
        await cleanup('search_index','validation-clear-index')
        await call('retrieve_evidence',{'query':'contextual embeddings','source_ids':[pdf]},error=True)
        await job('rebuild_search_index',{'source_ids':None},'validation-rebuild')
        check('rebuilt actual vectors ready',(await call('search_index_status'))['ready'])
        backup=await call('backup_workspace')
        report['backup']=backup;save()
        before_restore=await call('workspace_status')
        cleared=await cleanup('workspace','validation-clear-workspace')
        check('workspace cleanup removes journal sources',not (await call('workspace_status'))['sources'])
        restored=await job('restore_workspace',{'snapshot':Path(backup['directory']).name},'validation-restore')
        after_restore=await call('workspace_status')
        check('restore advances current revision',after_restore['revision']>cleared['revision'])
        check('restore preserves source IDs',after_restore['sources']==before_restore['sources'])
        check('restore preserves manuscript history',(await call('read_artifact',{'artifact_id':artifact['id'],'version':1}))==historical)
        check('restore preserves actual Qdrant vectors ready',after_restore['search_index']['ready'])
        await call('retrieve_evidence',{'query':'contextual embeddings','source_ids':[pdf],'mode':'hybrid'})
        await cleanup('all_except_inbox','validation-final-cleanup')
        final=await call('workspace_status')
        check('cleanup preserves inbox and removes research state',not final['sources'] and not final['artifacts'] and final['inbox']==before_restore['inbox'])
        report['status']='passed real MCP integration; no scientific acceptance or semantic grading';save()
    except BaseException as exc:
        report.update(status='failed',error=repr(exc));save();raise


if __name__=='__main__': asyncio.run(main())
