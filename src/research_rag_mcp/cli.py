import argparse
import json
from pathlib import Path

from .store import Store


def main():
    parser = argparse.ArgumentParser(description='Independent research RAG MCP workspace')
    parser.add_argument('--workspace', default=str(Path.cwd()/'.data'))
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    commands.add_parser('status')
    commands.add_parser('backup')
    serve = commands.add_parser('serve')
    serve.add_argument('--transport', choices=['streamable-http', 'stdio'], default='streamable-http')
    serve.add_argument('--port', type=int, default=8776)
    serve.add_argument('--host', choices=['127.0.0.1', '0.0.0.0'], default='127.0.0.1',
                       help='Listener address; use 0.0.0.0 inside a container with loopback-only published ports')
    review = commands.add_parser('review')
    review.add_argument('--port', type=int, default=0)
    review.add_argument('--host', choices=['127.0.0.1', '0.0.0.0'], default='127.0.0.1')
    restore = commands.add_parser('restore')
    restore.add_argument('snapshot')
    restore.add_argument('destination')
    args = parser.parse_args()
    try:
        if args.command == 'restore':
            print(json.dumps(Store.restore(args.snapshot, args.destination), indent=2))
            return
        store = Store(args.workspace)
        if args.command == 'serve':
            from .server import build_server, http_app
            if args.transport == 'stdio':
                build_server(store.root).run()
            else:
                if not 1 <= args.port <= 65535:
                    parser.error('--port must be 1..65535')
                import uvicorn
                uvicorn.run(http_app(store.root, args.port), host=args.host, port=args.port)
            return
        if args.command == 'review':
            from .review import serve_review
            from .workspaces import Workspaces
            serve_review(store, args.port, host=args.host, workspaces=Workspaces(args.workspace))
            return
        if args.command == 'backup':
            result = store.backup()
        elif args.command == 'status':
            from .workflow import status
            result = status(store)
        else:
            result = {'workspace': str(store.root), 'inbox': str(store.root/'inbox'),
                      'mcp_authentication': 'none', 'revision': store.read()['revision']}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc)+'\n')
