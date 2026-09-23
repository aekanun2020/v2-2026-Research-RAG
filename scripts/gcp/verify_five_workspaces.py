"""Five real MCP clients, real PDF ingestion and exact source-span checks.

No external LLM, no relevance grading, no fake server or substituted dependency.
Test workspaces are explicitly named and retained as evidence.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time

from verify_qdrant_retrieval_mcp import connect

PDF = 'https://economics.mit.edu/sites/default/files/inline-files/Noy_Zhang_1_0.pdf'
TITLE = 'Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence'


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:9076/mcp')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    path = Path(args.report)
    if path.exists():
        raise ValueError('New report path required; preserve previous results')
    run_id = path.stem
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'endpoint': args.url,
              'clients': 5, 'pdf_url': PDF, 'workspaces': [], 'calls': [],
              'checks': [], 'status': 'running',
              'limits': 'One real PDF per workspace; deterministic source-span validation, no semantic quality assessment; not a four-hour soak test.'}

    def save():
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    def check(name, value):
        report['checks'].append({'name': name, 'passed': bool(value)})
        save()
        if not value:
            raise AssertionError(name)

    async def call(client, tool, arguments):
        start = time.perf_counter()
        result = await client.call_tool(tool, arguments)
        report['calls'].append({'tool': tool, 'arguments': arguments,
                                'seconds': time.perf_counter() - start,
                                'response': result.model_dump(mode='json')})
        save()
        if result.is_error:
            raise RuntimeError(str(result))
        return result.structured_content

    async def poll(client, workspace, job):
        deadline = time.monotonic() + 1800
        while job['status'] in ('queued', 'running'):
            if time.monotonic() > deadline:
                raise TimeoutError('Real import exceeded 30 minute test budget')
            await asyncio.sleep(3)
            job = await call(client, 'job_status', {'workspace_id': workspace, 'job_id': job['job_id']})
        check('job completed: ' + workspace + ':' + job['job_id'], job['status'] == 'completed')
        return job

    try:
        async with connect(args.url) as client:
            names = [t.name for t in (await client.list_tools()).tools]
            report['tools'] = names
            check('45 tools available', len(names) == 45)
            for index in range(5):
                registry = await call(client, 'list_workspaces', {})
                workspace = await call(client, 'create_workspace', {
                    'name': f'READINESS TEST {run_id} person {index + 1}',
                    'expected_registry_revision': registry['registry_revision'],
                    'idempotency_key': f'{run_id}-person-{index + 1}'})
                report['workspaces'].append(workspace)
            check('five distinct workspace IDs', len({w['workspace_id'] for w in report['workspaces']}) == 5)
            check('five distinct Qdrant collections', len({w['qdrant_collection'] for w in report['workspaces']}) == 5)
        barrier = asyncio.Barrier(5)

        async def exercise(workspace):
            wid = workspace['workspace_id']
            async with connect(args.url) as client:
                await barrier.wait()
                start = time.perf_counter()
                state = await call(client, 'workspace_status', {'workspace_id': wid})
                job = await call(client, 'download_document', {
                    'workspace_id': wid, 'url': PDF, 'expected_revision': state['revision'],
                    'idempotency_key': run_id + '-download'})
                done = await poll(client, wid, job)
                receipt = done['result']['result']
                preview = await call(client, 'preview_inbox_document', {'workspace_id': wid, 'filename': receipt['filename']})
                check('real PDF title inspected ' + wid, 'experimental evidence on the productivity effects' in ' '.join(preview['text'].lower().split()))
                state = await call(client, 'workspace_status', {'workspace_id': wid})
                await barrier.wait()
                import_start = time.perf_counter()
                job = await call(client, 'import_document', {
                    'workspace_id': wid, 'filename': receipt['filename'], 'origin': receipt['final_url'],
                    'role': 'literature', 'bibliography': {'title': TITLE},
                    'expected_revision': state['revision'], 'idempotency_key': run_id + '-import'})
                done = await poll(client, wid, job)
                source = done['result']['result']
                check('import matches downloaded SHA256 ' + wid, source['source_id'] == receipt['sha256'])
                row = {'workspace_id': wid, 'sha256': receipt['sha256'],
                       'bytes': receipt['bytes'], 'pages': receipt['page_count'],
                       'import_seconds': time.perf_counter() - import_start,
                       'download_and_import_seconds': time.perf_counter() - start,
                       'search_seconds': []}
                report.setdefault('results', []).append(row)
                await barrier.wait()
                for iteration in range(5):
                    t = time.perf_counter()
                    hits = await call(client, 'retrieve_evidence', {
                        'workspace_id': wid, 'query': 'ChatGPT effects on writing productivity and quality',
                        'mode': 'hybrid', 'source_ids': [source['source_id']], 'limit': 2})
                    row['search_seconds'].append(time.perf_counter() - t)
                    check(f'real hybrid hits {wid} round {iteration}', bool(hits['hits']))
                    for hit in hits['hits']:
                        page = await call(client, 'read_source_page', {
                            'workspace_id': wid, 'source_id': hit['source_id'], 'page_index': hit['page_index']})
                        check(f'exact source span {wid} {hit["id"]}',
                              page['text'][hit['start']:hit['end']] == hit['citation']['quote'] == hit['text'])
                    await barrier.wait()
                save()

        async with asyncio.TaskGroup() as group:
            for workspace in report['workspaces']:
                group.create_task(exercise(workspace))
        timings = sorted(t for row in report['results'] for t in row['search_seconds'])
        report['summary'] = {'workspaces_passed': len(report['results']), 'hybrid_requests': len(timings),
                             'search_median_seconds': statistics.median(timings),
                             'search_p95_seconds': timings[min(len(timings)-1, int(len(timings)*0.95))],
                             'search_max_seconds': max(timings),
                             'import_seconds': [r['import_seconds'] for r in report['results']]}
        report['status'] = 'passed'
        save()
        print(json.dumps(report['summary']))
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    asyncio.run(main())
