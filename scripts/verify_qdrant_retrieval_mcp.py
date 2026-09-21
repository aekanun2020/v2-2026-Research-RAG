"""Exercise real token-free MCP; deterministic checks, never semantic grading."""
import argparse
import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def connect(url):
    async with httpx2.AsyncClient(timeout=30) as http:
        async with streamable_http_client(url, http_client=http) as streams:
            async with ClientSession(*streams, read_timeout_seconds=30) as session:
                await session.initialize()
                yield session


async def call(session, name, arguments):
    response = await session.call_tool(name, arguments)
    if response.is_error:
        raise RuntimeError(str(response))
    return response.structured_content


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8876/mcp')
    parser.add_argument('--report', required=True)
    parser.add_argument('--suite', choices=['concurrent', 'thai'], required=True)
    args = parser.parse_args()
    path = Path(args.report)
    if path.exists():
        raise ValueError('Use a new report path to preserve prior evidence')
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), endpoint=args.url,
                  authentication='none; no Authorization header', assessor='Codex must inspect results; this script checks spans only',
                  suite=args.suite, calls=[], status='running')
    def save():
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    async with connect(args.url) as session:
        before = await call(session, 'workspace_status', {})
        report['revision_before'] = before['revision']
        report['tool_names'] = [tool.name for tool in (await session.list_tools()).tools]
        cases = json.loads(Path('docs/quality-cases-2026-09-20.json').read_text())
        original_ids = sorted({c['expected_source_id'] for c in cases if c['expected_source_id']})
        if args.suite == 'concurrent':
            newer = [src for sid, src in before['sources'].items() if sid not in original_ids]
            assert len(newer) == 12
            cases = [dict(id=src['source_id'], query=src['bibliography']['title']+' architecture method evaluation limitations',
                          source_ids=[src['source_id']], mode='hybrid', limit=2) for src in newer]
        else:
            cases = [dict(id=c['id'], query=c['query'], expected_source_id=c['expected_source_id'],
                          source_ids=original_ids, mode=mode, limit=3) for mode in ('semantic','hybrid') for c in cases]
        ready = 0
        barrier = asyncio.Event()
        async def exercise(case, concurrent=False):
            nonlocal ready
            row = {'case': case, 'arguments': {k:case[k] for k in ('query','source_ids','mode','limit')}}
            try:
                async with connect(args.url) as client:
                    if concurrent:
                        ready += 1
                        if ready == len(cases): barrier.set()
                        await barrier.wait()
                    start = time.perf_counter()
                    response = await call(client, 'retrieve_evidence', row['arguments'])
                    row.update(seconds=time.perf_counter()-start, response=response, span_checks=[])
                    assert response['mode'] == case['mode']
                    assert response['corpus_sources'] == len(case['source_ids'])
                    for hit in response['hits']:
                        page = await call(client, 'read_source_page', {'source_id':hit['source_id'],'page_index':hit['page_index']})
                        exact = page['text'][hit['start']:hit['end']] == hit['text'] == hit['citation']['quote']
                        row['span_checks'].append(dict(chunk_id=hit['id'], exact=exact))
                        assert exact and hit['source_id'] in case['source_ids']
                    row['status'] = 'passed protocol/filter/span checks; relevance not graded'
            except Exception as exc:
                row.update(status='failed', error=repr(exc))
            report['calls'].append(row); save()
            print(json.dumps({'id':case['id'], 'mode':case['mode'], 'seconds':row.get('seconds'), 'status':row['status']}),flush=True)
        if args.suite == 'concurrent':
            await asyncio.gather(*(exercise(case, True) for case in cases))
        else:
            for case in cases: await exercise(case)
        after = await call(session, 'workspace_status', {})
        assert before == after, 'Read-only retrieval changed workspace state'
        report.update(revision_after=after['revision'], workspace_unchanged=True,
                      successful=sum(row['status'].startswith('passed') for row in report['calls']),
                      total=len(cases), status='complete')
        save()


if __name__ == '__main__':
    asyncio.run(main())
