"""Verify the five real ingested PDFs survive a service restart."""
import asyncio
import json
from pathlib import Path
from verify_qdrant_retrieval_mcp import connect, call

async def main():
    previous = json.loads(Path('/evidence/five-workspaces-20260923.json').read_text())
    target = Path('/evidence/after-restart-20260923.json')
    if target.exists():
        raise ValueError('Preserve earlier evidence')
    report = {'status': 'running', 'source_report': 'five-workspaces-20260923.json', 'checks': []}
    try:
        async with connect('http://127.0.0.1:9076/mcp') as client:
            for row in previous['results']:
                wid = row['workspace_id']
                state = await call(client, 'workspace_status', {'workspace_id': wid})
                assert len(state['sources']) == 1 and row['sha256'] in state['sources']
                hits = await call(client, 'retrieve_evidence', {'workspace_id': wid,
                    'query': 'ChatGPT effects on writing productivity and quality',
                    'mode': 'hybrid', 'source_ids': [row['sha256']], 'limit': 2})
                assert hits['hits']
                for hit in hits['hits']:
                    page = await call(client, 'read_source_page', {'workspace_id': wid,
                        'source_id': hit['source_id'], 'page_index': hit['page_index']})
                    assert page['text'][hit['start']:hit['end']] == hit['text'] == hit['citation']['quote']
                report['checks'].append({'workspace_id': wid, 'sha256': row['sha256'],
                    'passed': True, 'source_count': len(state['sources']), 'hits': hits})
                target.write_text(json.dumps(report, indent=2) + '\n')
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'workspaces': len(report['checks'])}))

if __name__ == '__main__':
    asyncio.run(main())
