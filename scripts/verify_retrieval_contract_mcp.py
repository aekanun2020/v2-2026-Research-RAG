"""Read-only regression checks on the actual MCP server and imported corpus."""
import argparse
import asyncio
import json
from pathlib import Path

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--url', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Preserve existing reports; use a new output filename')
    cases = json.loads(Path('docs/quality-cases-2026-09-20.json').read_text())
    case = next(c for c in cases if c['id'] == 'T04')
    token = (Path(args.workspace)/'.http-token').read_text().strip()
    report = {'endpoint': args.url, 'checks': [], 'status': 'running',
              'protocol': 'real MCP Streamable HTTP; no direct retrieval calls'}

    def record(name):
        report['checks'].append(name)
        output.write_text(json.dumps(report, indent=2)+'\n')

    async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+token}, timeout=600) as http:
        async with streamable_http_client(args.url, http_client=http) as streams:
            async with ClientSession(*streams, read_timeout_seconds=600) as session:
                init = await session.initialize()
                report['version'] = init.server_info.version
                tools = (await session.list_tools()).tools
                assert len(tools) == 33
                record('initialize and tools/list: 33 actual tools')

                async def call(name, **arguments):
                    result = await session.call_tool(name, arguments)
                    assert not result.is_error, str(result)
                    return result.structured_content

                before = await call('workspace_status')
                base = dict(query=case['query'], mode='semantic', limit=3)
                old = await call('retrieve_evidence', **base, rerank=False)
                assert not old['reranking']['enabled']
                baseline = json.loads(Path('docs/quality-failing-before-2026-09-20.json').read_text())['cases'][0]['response']['hits']
                def spans(hits):
                    return [{k: h[k] for k in ('source_id', 'page_index', 'start', 'end', 'text')} for h in hits]
                assert spans(old['hits']) == spans(baseline)
                record('explicit rerank=false reproduces preserved E5 baseline exactly')
                narrowed = await call('retrieve_evidence', **base, source_ids=[case['expected_source_id']], candidate_limit=30)
                assert narrowed['hits'] and all(h['source_id'] == case['expected_source_id'] for h in narrowed['hits'])
                for hit in narrowed['hits']:
                    page = await call('read_source_page', source_id=hit['source_id'], page_index=hit['page_index'])
                    assert page['text'][hit['start']:hit['end']] == hit['text'] == hit['citation']['quote']
                record('source filter, minimum candidate budget, and exact original spans')
                hit = narrowed['hits'][0]
                chunk = await call('read_chunk', chunk_id=hit['id'])
                context = await call('get_chunk_context', chunk_id=hit['id'], before=0, after=0)
                assert chunk['text'] == hit['text'] == context['chunks'][0]['text']
                assert chunk['source_id'] == hit['source_id']
                record('retrieval chunk ID resolves through read_chunk and get_chunk_context')
                empty = await call('retrieve_evidence', **base, roles=['results'])
                assert not empty['hits'] and empty['corpus_sources'] == 0
                record('role boundary excludes literature from own results')
                lexical = await call('retrieve_evidence', query=case['query'], mode='lexical')
                assert not lexical['hits'] and not lexical['reranking']['enabled']
                record('explicit lexical mode retains lexical behavior')
                filtered = await call('retrieve_evidence', **base, min_rerank_score=1.0)
                assert not filtered['hits'] and filtered['status'] == 'insufficient_retrieved_evidence'
                record('explicit pairwise score threshold returns empty with no fallback')
                negative = next(c for c in cases if c['id'] == 'N02')
                unchecked = await call('retrieve_evidence', query=negative['query'], mode='semantic',
                                       limit=3, min_document_score=0)
                assert unchecked['hits'] and not unchecked['reranking']['document_gate']['enabled']
                record('explicit min_document_score=0 reveals rejected candidates for inspection')
                for override in ({'candidate_limit': 29}, {'candidate_limit': 201},
                                 {'min_rerank_score': -0.1}, {'min_rerank_score': 1.1},
                                 {'min_document_score': -0.1}, {'min_document_score': 1.1},
                                 {'min_rerank_score': 0.1, 'rerank': False},
                                 {'min_rerank_score': 0.1, 'mode': 'lexical'},
                                 {'source_ids': ['unknown-source']}, {'mode': 'unsupported'}):
                    response = await session.call_tool('retrieve_evidence', {**base, **override})
                    assert response.is_error, override
                record('10 invalid retrieval requests return MCP tool errors')
                assert await call('workspace_status') == before
                record('all checks preserve complete workspace status')
                report['status'] = 'passed; deterministic integration checks, not semantic grading'
                output.write_text(json.dumps(report, indent=2)+'\n')
                print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
