"""Read-only deployment check over actual MCP HTTP; never executes cleanup."""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8776/mcp')
    args = parser.parse_args()
    token = (Path(args.workspace)/'.http-token').read_text().strip()
    async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+token}, timeout=60) as http:
        async with streamable_http_client(args.url, http_client=http) as streams:
            async with ClientSession(*streams, read_timeout_seconds=60) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                names = [tool.name for tool in listed.tools]
                assert {'preview_workspace_cleanup', 'cleanup_workspace'} <= set(names)

                async def read(name, arguments):
                    result = await session.call_tool(name, arguments)
                    if result.is_error:
                        raise RuntimeError(str(result))
                    return result.structured_content

                before = await read('workspace_status', {})
                plans = [await read('preview_workspace_cleanup', {'scope': scope})
                         for scope in ('search_index', 'documents', 'workspace', 'all_except_inbox')]
                after = await read('workspace_status', {})
                assert before == after, 'Read-only preview changed workspace state'
                print(json.dumps({
                    'verified_at': datetime.now(timezone.utc).isoformat(),
                    'endpoint': args.url, 'protocol_version': initialized.protocol_version,
                    'server_version': initialized.server_info.version,
                    'tool_count': len(names), 'tools': names,
                    'workspace_unchanged': True, 'cleanup_executed': False,
                    'workspace_revision': after['revision'],
                    'source_count': len(after['sources']), 'inbox_count': len(after['inbox']),
                    'search_index': after['search_index'], 'plans': plans,
                }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
