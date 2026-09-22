# Public research-rag endpoint — 2026-09-22

MCP URL: **https://michiko-psychodiagnostic-melvina.ngrok-free.dev/mcp**

- ngrok endpoint name: `research-rag`. This is the endpoint label; the hostname above was assigned by ngrok.
- Host: `Aekanun’s MacBook Pro`, local Docker Desktop. Direct upstream: `http://127.0.0.1:9076`, MCP path `/mcp`, container `codex-rag-agents-mcp-1`.
- Authentication: none. The user explicitly approved public access to all 45 tools, including read/write/cleanup for every workspace of this new service. The earlier automatic approval rejections occurred before this explicit scope approval; no tunnel was started by those rejected attempts.
- This tunnel does not expose port 8976, human review port 9077, Qdrant or Ollama directly. Other containers were not changed. ngrok HTTP traffic inspection is disabled.
- The default workspace was empty during verification. Other workspaces contain the clearly named regression data documented in the [implementation record](README.md).

## Verification and host configuration

The initial real MCP initialize request failed: the service accepted only loopback Host headers. A direct protocol request returned **421 `Invalid Host header`**; the MCP container logged the exact ngrok hostname. Preserved evidence: [SDK failure](ngrok-before-host-config.json) and [HTTP rejection](ngrok-host-rejection.json).

The actual MCP server now accepts an optional `RAG_PUBLIC_ORIGIN`, validated as one exact HTTPS origin on port 443. The local operator configuration sets it to `https://michiko-psychodiagnostic-melvina.ngrok-free.dev`. [Compose](../../compose.agents.yaml) passes it only to the new MCP service. The MCP SDK's Host/Origin validation remains enabled; no wildcard, header-rewriting proxy, transport replacement or authentication mechanism was added. Only the new MCP container was rebuilt/recreated for this change.

[The original-case rerun and nearby checks](ngrok-after-host-config.json) passed 8 checks through the actual HTTP MCP service:

- Public `initialize` reports version 0.5.0; `tools/list` lists 45 tools including the four additions.
- Public `tools/call` → `workspace_status` with `{"workspace_id":"default"}` succeeds without an Authorization header and returns revision 0 with no sources/artifacts.
- The public and local endpoints return the same tool catalog and workspace state.
- The exact public Origin succeeds; unapproved Host and Origin remain rejected with 421 and 403.

[Runtime observation](ngrok-runtime.json) verifies process PID 57211 remained running, the tunnel forwards to the correct local service, and the other seven containers retained their IDs/images/start times. Tests are implemented in [verify_public_mcp.py](../../scripts/verify_public_mcp.py). Actual use inside Claude has not been tested by Codex; enter the public URL above in the custom connector and verify `download_document` is visible.

## Running process and restart

The ngrok process was started detached on this Mac, not installed as a login service. PID and local logs are under `.agent-data/runtime/ngrok-research-rag.pid` and `.agent-data/runtime/ngrok-research-rag-20260922.log`, excluded from Git. The endpoint requires the Mac, Docker service and ngrok process to remain running.

After verifying the existing process has stopped and the URL is not serving another endpoint, restart with the verified URL explicitly:

```sh
ngrok http http://127.0.0.1:9076 \
  --name research-rag \
  --url https://michiko-psychodiagnostic-melvina.ngrok-free.dev \
  --inspect=false
```

Do not enable pooling to combine this service with another endpoint. If the public hostname changes, update the exact `RAG_PUBLIC_ORIGIN` in `.env.agents`, recreate only this deployment's MCP service, and repeat the protocol check. `.env.agents` and the existing ngrok account token remain local and are not committed.
