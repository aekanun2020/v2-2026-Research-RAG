"""Native MCP SDK verification from outside the GCP VM; no TLS bypass."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import ssl
import socket

from verify_qdrant_retrieval_mcp import connect, call

HOST = '34-142-163-231.sslip.io'
URL = 'https://' + HOST + '/mcp'
ROOT = Path(__file__).resolve().parents[2]

async def main():
    path = ROOT / 'docs/gcp/evidence/student2-external-https-20260924.json'
    if path.exists():
        raise ValueError('Preserve earlier evidence')
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'url': URL,
              'client_location': 'user Mac outside GCP VM', 'authentication': 'none',
              'tls_verification': 'system trust with hostname verification enabled', 'status': 'running'}
    try:
        with socket.create_connection((HOST, 443), timeout=20) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=HOST) as tls:
                report['certificate'] = tls.getpeercert()
                report['tls_version'] = tls.version()
        prior = json.loads((ROOT / 'docs/gcp/evidence/five-workspaces-20260923.json').read_text())
        row = prior['results'][0]
        async with connect(URL) as client:
            tools = (await client.list_tools()).tools
            report['tools'] = [t.name for t in tools]
            assert len(tools) == 45
            report['default_workspace'] = await call(client, 'workspace_status', {'workspace_id': 'default'})
            report['workspaces'] = await call(client, 'list_workspaces', {})
            arguments = {'workspace_id': row['workspace_id'], 'query': 'ChatGPT effects on writing productivity and quality',
                         'source_ids': [row['sha256']], 'mode': 'hybrid', 'limit': 2}
            hits = await call(client, 'retrieve_evidence', arguments)
            assert hits['hits']
            report['retrieval'] = {'arguments': arguments, 'result': hits, 'span_checks': []}
            for hit in hits['hits']:
                page = await call(client, 'read_source_page', {'workspace_id': row['workspace_id'],
                    'source_id': hit['source_id'], 'page_index': hit['page_index']})
                exact = page['text'][hit['start']:hit['end']] == hit['text'] == hit['citation']['quote']
                report['retrieval']['span_checks'].append({'chunk_id': hit['id'], 'exact': exact})
                assert exact
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'url': URL, 'tools': len(report['tools']),
                      'verified_quote_spans': len(report['retrieval']['span_checks']), 'tls': report['tls_version']}))

if __name__ == '__main__':
    asyncio.run(main())
