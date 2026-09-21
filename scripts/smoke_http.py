"""Connect to the real token-free endpoint without printing credentials."""
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
    parser.add_argument('--url', default='http://127.0.0.1:8776/mcp')
    args = parser.parse_args()
    async with httpx2.AsyncClient() as http:
        async with streamable_http_client(args.url, http_client=http) as streams:
            async with ClientSession(*streams, read_timeout_seconds=30) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                called = await session.call_tool('workspace_status', {})
                if called.is_error:
                    raise RuntimeError(str(called))
                state = called.structured_content
                print(json.dumps({'endpoint': args.url, 'initialize': True,
                                  'protocol_version': initialized.protocol_version,
                                  'tool_count': len(listed.tools), 'tools': [t.name for t in listed.tools],
                                  'workspace_revision': state['revision'], 'external_model_calls': False}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
