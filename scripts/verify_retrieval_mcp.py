"""Exercise the real MCP endpoint; record evidence, never grade semantic relevance."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', required=True)
    p.add_argument('--url', default='http://127.0.0.1:8776/mcp')
    p.add_argument('--cases', default='docs/quality-cases-2026-09-20.json')
    p.add_argument('--case', action='append')
    p.add_argument('--split', choices=['regression', 'held_out'])
    p.add_argument('--mode', default='semantic', choices=['semantic', 'hybrid', 'lexical'])
    p.add_argument('--no-rerank', action='store_true')
    p.add_argument('--min-score', type=float)
    p.add_argument('--min-document-score', type=float)
    p.add_argument('--assert-top-source', action='store_true')
    p.add_argument('--assert-empty-controls', action='store_true')
    p.add_argument('--output', required=True)
    args = p.parse_args()
    cases = [c for c in json.loads(Path(args.cases).read_text())
             if (not args.case or c['id'] in args.case) and (not args.split or c['split'] == args.split)]
    if not cases:
        raise ValueError('No selected cases')
    target = Path(args.output)
    if target.exists():
        raise ValueError('Use a new output path; preserve preceding evidence')
    report = dict(started_at=datetime.now(timezone.utc).isoformat(), endpoint=args.url,
                  protocol='real MCP Streamable HTTP, official SDK', semantic_assessor='not assessed by this script',
                  cases=[], status='running')
    def save():
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    save()
    token = (Path(args.workspace)/'.http-token').read_text().strip()
    try:
        async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+token}, timeout=600) as http:
            async with streamable_http_client(args.url, http_client=http) as streams:
                async with ClientSession(*streams, read_timeout_seconds=600) as session:
                    init = await session.initialize()
                    report['server_version'] = init.server_info.version
                    report['tool_schemas'] = {t.name: t.input_schema for t in (await session.list_tools()).tools
                                              if t.name == 'retrieve_evidence'}
                    async def call(name, arguments):
                        result = await session.call_tool(name, arguments)
                        if result.is_error:
                            raise RuntimeError(str(result))
                        return result.structured_content
                    before = await call('workspace_status', {})
                    report['revision_before'] = before['revision']
                    pages = {}
                    for case in cases:
                        arguments = dict(query=case['query'], mode=args.mode, limit=3, roles=['literature'])
                        if args.no_rerank:
                            arguments['rerank'] = False
                        if args.min_score is not None:
                            arguments['min_rerank_score'] = args.min_score
                        if args.min_document_score is not None:
                            arguments['min_document_score'] = args.min_document_score
                        started = time.monotonic()
                        response = await call('retrieve_evidence', arguments)
                        elapsed = time.monotonic()-started
                        checks = []
                        for hit in response['hits']:
                            key = (hit['source_id'], hit['page_index'])
                            if key not in pages:
                                pages[key] = await call('read_source_page', dict(source_id=key[0], page_index=key[1]))
                            original = pages[key]['text'][hit['start']:hit['end']]
                            exact = original == hit['text'] == hit['citation']['quote']
                            checks.append(dict(chunk_id=hit['id'], exact_span=exact))
                            if not exact:
                                raise AssertionError('Original span mismatch: '+hit['id'])
                        top_source_matches = bool(response['hits'] and response['hits'][0]['source_id'] == case['expected_source_id'])
                        report['cases'].append(dict(case=case, arguments=arguments, response=response,
                                                   latency_seconds=elapsed, span_checks=checks,
                                                   top_source_matches=top_source_matches))
                        save()
                        print(json.dumps(dict(id=case['id'], seconds=round(elapsed, 2), hits=len(response['hits']),
                                              top_source_matches=top_source_matches,
                                              top_score=response['hits'][0]['score'] if response['hits'] else None)), flush=True)
                        if args.assert_top_source and case['expected_source_id'] and not top_source_matches:
                            raise AssertionError('Expected source is not first: '+case['id'])
                        if args.assert_empty_controls and case['expected_source_id'] is None and response['hits']:
                            raise AssertionError('Out-of-corpus control returned candidates: '+case['id'])
                    after = await call('workspace_status', {})
                    if before != after:
                        raise AssertionError('Retrieval changed workspace state')
                    report.update(status='passed deterministic checks; relevance requires Codex assessment',
                                  revision_after=after['revision'], workspace_unchanged=True)
                    save()
    except BaseException as exc:
        report.update(status='failed', error=repr(exc))
        save()
        raise


if __name__ == '__main__':
    asyncio.run(main())
