"""Real MCP migration and evidence regression; no store calls or LLM judge."""
import argparse
import asyncio
import json
import time
from pathlib import Path
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);parser.add_argument('--url',default='http://127.0.0.1:8876/mcp');parser.add_argument('--report',required=True)
    args=parser.parse_args();path=Path(args.report)
    if path.exists(): raise RuntimeError('Use a new report path to preserve prior evidence')
    report={'endpoint':args.url,'calls':[],'assessor':'No automated semantic judge; deterministic protocol/span checks only'}
    def save(): path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    async with httpx2.AsyncClient(timeout=30) as http:
        async with streamable_http_client(args.url,http_client=http) as streams:
            async with ClientSession(*streams,read_timeout_seconds=30) as session:
                report['initialize']=(await session.initialize()).model_dump(mode='json')
                report['tools']=(await session.list_tools()).model_dump(mode='json')
                async def call(name,arguments):
                    start=time.perf_counter();response=await session.call_tool(name,arguments)
                    row={'tool':name,'arguments':arguments,'seconds':time.perf_counter()-start,'response':response.model_dump(mode='json')}
                    report['calls'].append(row);save()
                    if response.is_error: raise RuntimeError(str(response))
                    return response.structured_content
                before=await call('workspace_status',{})
                job=await call('migrate_legacy_workspace',{'expected_revision':before['revision'],'idempotency_key':'qdrant-migrate-v024-20260921'})
                print(json.dumps({'job':job},ensure_ascii=False),flush=True)
                while job['status'] in ('queued','running'):
                    await asyncio.sleep(5)
                    job=await call('job_status',{'job_id':job['job_id']})
                    print(json.dumps({'status':job['status'],'progress':job.get('progress'),'error':job.get('error')},ensure_ascii=False),flush=True)
                assert job['status']=='completed',job
                after=await call('workspace_status',{})
                assert len(after['sources'])==22
                assert after['search_index']['total_chunks']==2106
                assert after['search_index']['ready']
                assert after['inbox']==[]
                report['summary']={'sources':len(after['sources']),'chunks':after['search_index']['total_chunks'],'revision':after['revision'],'status':'migrated'}
                save();print(json.dumps(report['summary']),flush=True)
asyncio.run(main())
