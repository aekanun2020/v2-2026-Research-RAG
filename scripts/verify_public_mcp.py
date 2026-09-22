"""Read-only real MCP checks for an explicitly authorized public endpoint."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--local-url', default='http://127.0.0.1:9076/mcp')
    parser.add_argument('--report', required=True)
    args=parser.parse_args()
    out=Path(args.report)
    if out.exists(): raise ValueError('Preserve earlier evidence; use a new report filename')
    report={'checked_at':datetime.now(timezone.utc).isoformat(),'public_url':args.url,
        'authentication':'none; no Authorization header','calls':[],'checks':[],'status':'running'}
    def save(): out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def check(name,ok):
        report['checks'].append({'name':name,'passed':bool(ok)});save()
        if not ok: raise AssertionError(name)
    async def inspect(url, origin=None):
        async with httpx2.AsyncClient(timeout=30,headers={'Origin':origin} if origin else {}) as http:
            async with streamable_http_client(url,http_client=http) as streams:
                async with ClientSession(*streams,read_timeout_seconds=30) as s:
                    initialized=await s.initialize()
                    tools=await s.list_tools()
                    arguments={'workspace_id':'default'}
                    value=await s.call_tool('workspace_status',arguments)
                    check('workspace_status is successful: '+url,not value.is_error)
                    result={'url':url,'origin':origin,'initialize':initialized.model_dump(mode='json'),
                        'tools':[t.name for t in tools.tools],'tool_call':{'name':'workspace_status',
                        'arguments':arguments,'response':value.model_dump(mode='json')}}
                    report['calls'].append(result);save()
                    return result
    try:
        public=await inspect(args.url)
        check('public endpoint serves 45 tools including downloader',len(public['tools'])==45
            and {'download_document','list_workspaces','create_workspace','document_ingestion_status'}<=set(public['tools']))
        local=await inspect(args.local_url)
        check('public and local endpoints return the same workspace and tool catalog',public['tools']==local['tools']
            and public['tool_call']['response']==local['tool_call']['response'])
        u=urlsplit(args.url);origin=u.scheme+'://'+u.netloc
        allowed=await inspect(args.url,origin)
        check('explicit public Origin is accepted',allowed['tools']==public['tools'])
        init={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25',
            'capabilities':{},'clientInfo':{'name':'public-mcp-negative-check','version':'1'}}}
        async with httpx2.AsyncClient(timeout=30) as http:
            for headers,expected,label in [({'Host':'unapproved.invalid'},421,'unapproved Host'),
                                           ({'Origin':'https://unapproved.invalid'},403,'unapproved Origin')]:
                response=await http.post(args.local_url,json=init,headers={'Accept':'application/json, text/event-stream',**headers})
                report['calls'].append({'url':args.local_url,'method':'initialize','headers':headers,
                    'status_code':response.status_code,'body':response.text})
                check(label+' remains rejected',response.status_code==expected)
        report['status']='passed';save()
        print(json.dumps({'status':'passed','checks':len(report['checks']),'url':args.url,'tools':len(public['tools'])}))
    except BaseException as exc:
        def flatten(e):
            if isinstance(e,BaseExceptionGroup):return [x for sub in e.exceptions for x in flatten(sub)]
            return [{'type':type(e).__name__,'error':str(e)}]
        report.update(status='failed',errors=flatten(exc));save();raise


if __name__=='__main__': asyncio.run(main())
