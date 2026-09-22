# Claude agent ingestion and independent workspaces

Version 0.5.0, branch `codex/claude-workspace-ingestion`. Implemented and tested through the real MCP protocol on 2026-09-22. No production data migration or import was performed. The old service remains a separate deployment.

## What was fixed

- `download_document`: the agent supplies a public HTTPS PDF URL or arXiv ID; **the MCP container downloads the bytes**. The caller needs no access to the server filesystem. Durable `job_status` reports completion/failure and a receipt with URL, redirects, SHA-256, bytes, page count and inbox filename. Downloading does not import or index.
- `list_workspaces` / `create_workspace`: separate project files, journal, idempotency records, jobs and Qdrant collection. Every scoped tool accepts `workspace_id`; omission always means `default`, never the most recently selected project. Creation does not overwrite, migrate or copy the old project. There is a limit of 100 additional workspaces.
- `document_ingestion_status`: verifies an inbox file against its actual SHA-256 and reports whether that file is imported, its source identity/format/role, active chunks and the workspace-wide index integrity. Source summaries, source pages and retrieval hits distinguish `pdf_source`, `text_source` and `project_note`. Downloaded imports retain acquisition provenance.
- MCP initialize instructions, `research_workflow`, and relevant tool descriptions now require explicit workspace routing, separate download/import/index status, no replacement of requested PDFs with generated notes, and honest limits for client-local attachments. The prompt remains client guidance, not a guarantee that a particular model obeys it.

## Container and inbox locations

New local MCP endpoint: `http://127.0.0.1:9076/mcp`, no token. Human review is separately published on loopback port 9077. After the user's explicit public-access approval, the `research-rag` ngrok endpoint was opened at **https://michiko-psychodiagnostic-melvina.ngrok-free.dev/mcp**; see [live endpoint configuration and verification](ngrok.md). A cloud-hosted Claude connector needs this public URL, not the Mac's loopback address. Client connections to the old 8976 endpoint still see version 0.4.0 and its 41 tools; reconnect to the new deployment to obtain 45 tools.

| Area | Container path | Host path relative to this repository |
|---|---|---|
| Default inbox | `/data/default/inbox` | `.agent-data/default/inbox` |
| Created workspace inbox | `/data/workspaces/<workspace_id>/inbox` | `.agent-data/workspaces/<workspace_id>/inbox` |
| Workspace registry | `/data/workspaces/registry.json` | `.agent-data/workspaces/registry.json` |
| Old deployment inbox | `/data/inbox` in the **old** MCP container | `.chunking-data/inbox` |

This installation's repository is `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-TTS-AI/codex-research-rag-qdrant`. `list_workspaces` reports the actual server paths; deployments may set another `AGENTS_DATA_DIR`. Configure the new stack with [compose.agents.yaml](../../compose.agents.yaml) and [agents.env.example](../../agents.env.example), using the [root installation instructions](../../README.md#ติดตั้งใหม่). Do not bind the old data directory or reuse its Qdrant/Ollama containers or volumes.

**There is no “Claude inbox” and no binary upload tool.** A file path or chat attachment on the client is not accessible to the container. Use a publicly reachable PDF URL/arXiv ID, or have an authorized operator place the actual file in the chosen server inbox. Do not ask the model to invent a URL, reconstruct a PDF or relabel a paraphrase as the original document.

## Agent sequence

1. `list_workspaces`; select the user-identified workspace. For an explicitly separate project, `create_workspace(name, expected_registry_revision, idempotency_key)` returns its new ID.
2. `workspace_status(workspace_id)`; `start_project` in an empty workspace using only researcher-supplied scope.
3. `download_document(url=..., expected_revision=..., idempotency_key=..., workspace_id=...)` **or** `arxiv_id=...`. Retain the returned `job_id` and poll `job_status` with the same workspace ID.
4. On completed download, read its receipt and `preview_inbox_document`. Verify bibliography against actual text. If the instruction was download only, stop here.
5. When authorized to import, read the latest workspace revision and call `import_document` with the receipt's filename and verified bibliography. Poll until completed. `document_ingestion_status` checks the resulting source, chunk count and workspace index readiness.
6. `retrieve_evidence` then `read_source_page` verify exact source/page/start/end/quote. A note hit remains a note; scores and exact spans do not establish semantic support or full-paper completeness.

Mutation retries reuse the exact key and arguments. Client disconnection does not cancel the server job. `interrupted` jobs require explicit `resume_job`. Do not submit another job with a new key to bypass failure or overwrite the original project. Human review remains a separate researcher action.

## Download limits

HTTPS port 443 only, no URL credentials or fragments, no forwarded client credentials or environment proxy, public DNS addresses only. Each redirect is revalidated and the TLS connection is pinned to validated IP addresses with hostname/certificate verification. Up to 5 redirects, 50 MiB, 1000 unencrypted pages; connection/read timeouts and a transfer deadline bound the network operation. HTTP errors, private destinations, HTML responses and invalid PDFs fail without adding sources or notes. Paywall circumvention, OCR, binary client upload and automatic reference crawling/import are not provided.

Journal receipts and imported-source provenance survive ordinary restarts and source backups. Workspace cleanup can remove receipts; inbox files remain according to the requested cleanup scope. Backup/restore excludes inbox itself, so restored source originals can exist without an inbox file. `list_documents` remains the source inventory in that case. A workspace's `ready=true` with zero chunks means an empty index, not proof of successful document import.

## Reproduced baseline

[Read-only MCP observation](before-2026-09-22.json), 2026-09-22: the real 0.4.0 endpoint at port 8976 reports 41 tools, revision 290, and an `External lit summary` source with role `project_note`. The schema for `import_document` accepts only an inbox filename. There is no download tool, workspace-creation tool, or workspace selector. `build_server` closes over one Store/Jobs instance; `start_project` refuses to overwrite the existing project. These explain the screenshot without assuming the referenced PDFs were imported.

## Implementation order and acceptance

1. Explicit workspace IDs and separate journal, files, Qdrant collection, jobs and human review. Re-run creation and concurrent independent project calls through MCP before adding the downloader.
2. Durable server-side HTTPS PDF download, then a separate explicit import. Check real public PDFs, exact retries, PDF/URL validation, no-import behavior, full import and retrieval provenance through MCP.
3. Update MCP initialize instructions, tool descriptions and `research_workflow` prompt together. State exact workspace and download/import/index status; client summaries cannot stand in for original paper imports. Verify served prompt and exercise the instructed sequence using MCP.

Every component uses a new `codex-rag-agents` container, network, data root and volumes. The old 8976 service and its data remain untouched. No authentication token is added to MCP. Workspaces provide data organization and request routing, not per-user authorization on an unauthenticated endpoint.

## Recorded regression results

All imports, downloads, retrievals, revisions, backups and restore/cleanup checks below use the actual MCP HTTP service, actual public PDFs, Qdrant and CPU Ollama. No simulated server, direct Store mutation, external LLM judge or human acceptance was used. Counts overlap across phases and must not be summed as distinct cases.

| Phase | Before | After |
|---|---|---|
| Workspace routing | [Original 0.4.0 failure: missing tool](baseline-workspace-test.json) | [11 checks passed](workspace-after.json): concurrent A/B creation/start, same key in different workspaces, exact retry, unknown/path IDs and overwrite rejection |
| Server-side acquisition | [Missing downloader before implementation](baseline-download-test.json) | [36 checks passed](download-after.json): real MIT PDF, durable receipt/retry, staging-only state, separate import, actual hybrid retrieval, exact page spans, no cross-workspace access, private URL/HTML rejection |
| Prompt and provenance | [Served original instructions](prompt-before.json), [original missing instruction](baseline-prompt-test.json) | [43 checks passed](prompt-after-ready.json): repeat original functional sequence, metadata/provenance and explicitly requested execution-note classification |
| Related workflow | Separate regression after focused cases passed | [24 checks passed](workflow-followup.json): 7 stage contexts, manuscript identity/history, draft export, reviewed-export rejection, backup/cleanup/restore with real vectors, retrieval after restore, actual arXiv ID download left inbox-only |

One prompt test was started while the new container was being recreated and received `httpx2.RemoteProtocolError: Server disconnected without sending a response` before any checks or mutations. [That failed attempt is retained](prompt-after.json); [the rerun after deployment completed](prompt-after-ready.json) passed. The initial app build also failed because the local lockfile still declared 0.4.0; `uv lock --offline` updated only this package's version to 0.5.0, and subsequent builds succeeded. No dependency was substituted.

The original PDF used in the main case was the authors' [MIT working paper](https://economics.mit.edu/sites/default/files/inline-files/Noy_Zhang_1_0.pdf): 15 pages, 532,994 bytes, SHA-256 `3a85c26cf0560425d0d1d60c0cd574c0c38c17ac0dee1f1d2010123f3a1a9736`, 21 indexed chunks. The related ID case downloaded [ELMo v2](https://arxiv.org/abs/1802.05365v2), inspected its real title and did not import it.

Codex directly inspected the two main-case hits for the English query `ChatGPT effects on writing productivity and quality`: page 1 directly describes the experiment/productivity outcome and page 6 discusses quality, inequality and human-machine complementarity. Both are relevant to this broad query and their stored quotes matched original page spans. This narrow inspection is not a new Thai semantic-search benchmark, proof that every chunk is readable, or evaluation by another model.

[Final read-only runtime evidence](final-runtime.json) confirms initialize instructions equal the served prompt, 45 tools, a default workspace at revision 0 with no sources/artifacts, and disjoint containers/networks/mounts across the two deployments. The old endpoint was observed at revision 290 initially and 292 finally; this task made only read calls to it, so these snapshots do not establish who wrote those intervening revisions. Its containers were not recreated by this change. Test records are confined to explicitly named regression workspaces; the user's separate downloaded paper collection was not imported.

Reproduce with [workspace/download/prompt verifier](../../scripts/verify_agent_ingestion_mcp.py) and [related workflow verifier](../../scripts/verify_agent_workspace_followup_mcp.py). Use a fresh report filename and the isolated 9076 test deployment. The latter intentionally clears/restores only the exact disposable workspace recorded in its passing seed report; never supply a production report or endpoint.

**Not established:** actual Claude Desktop/Claude cloud agent behavior, human review interactions, Windows client behavior, large-file/redirect-limit boundaries, interrupted-process download recovery and broad concurrent workload performance. The separate review UI's workspace selector and source/form routing were updated but not operated on behalf of the researcher. Protocol success is not a claim that a model will follow the prompt or that the papers are scientifically validated.
