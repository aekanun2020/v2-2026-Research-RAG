> Historical 0.2.4 documentation. For the current Qdrant/Ollama migration and changed job contract, see [migration record](qdrant-migration.md) and [current README](../README.md).

# Local container deployment

User requested containers with Streamable HTTP on 2026-09-20. This deployment belongs to the standalone `codex-research-rag-mcp` project on the local MacBook.

## Current deployment — 0.2.4

Both local RAG containers are healthy on `codex-research-rag-mcp:0.2.4`, image ID `sha256:46994bcdb92d186c3a5f0fa41d67b252fb1da57c419a3e6bb704e1849fddc085`. The endpoint is still `http://127.0.0.1:8776/mcp` with bearer authentication and loopback-only publication. [Deployment log](quality-deploy-2026-09-20.txt), [current inventory](quality-containers-after-2026-09-20.json), [18 final packaged source hashes](quality-final-image-source-hashes-2026-09-20.json). All 17 unrelated containers retain their IDs, images, states and start times. Temporary test containers were removed.

[MCP runtime inspection](quality-runtime-after-2026-09-20.json) confirms version 0.2.4, 33 tools, revision 24, 10 sources and 221 inbox files. [Preservation comparison](quality-state-preservation-2026-09-20.json) verifies the same complete inbox hash inventory and 618 indexed chunks (547 active; 71 retained inactive experimental chunks). No cleanup/reimport/reindex was performed during deployment. Prior 0.2.3 cleanup remains history below.

The runtime bundles both pinned E5 and BGE models; inference uses CPU only and does not call an external model. Default semantic/hybrid retrieval uses BGE reranking with **no automatic score cutoff**, because a tested first-page cutoff rejected a relevant held-out query. [Quality results and failures](retrieval-quality-2026-09-20.md), [production retrieval](quality-production-retrieval-2026-09-20.json), [native MCP verification](quality-native-runtime-2026-09-20.json), [final-image MCP contract checks](quality-final-contract-2026-09-20.json). Scores and passage order can differ between macOS and Linux CPU kernels; final claims use Linux results.

The separate review service restarted; previously issued review capability URLs are historical. No native UI was opened or operated.

## Observed baseline

- No Dockerfile or Compose configuration existed. MCP ran as host Python PID 59586 on `127.0.0.1:8776`; review was a second host process on port 52456.
- Docker context `desktop-linux` initially had no daemon socket. Starting the installed Docker application hidden in the background made Docker Engine 29.8.0 reachable. The existing 17 local containers were all stopped; their IDs and states were captured before deployment. No Mac Studio connection was made.
- Both services hardcoded their listener to `127.0.0.1`. A Docker published port must reach a listener on the container network interface.
- Before the change, the real CLI command `.venv/bin/python -m research_rag_mcp --workspace .data serve --host 0.0.0.0 --port 18776` exited **2**: `unrecognized arguments: --host 0.0.0.0`.

## Historical deployment — 0.2.3

Verified **2026-09-20 21:19 ICT (14:19 UTC)**. Both local RAG containers run healthy on `codex-research-rag-mcp:0.2.3`, with Linux manifest `sha256:8e2733253134813ad2b203102e5b978a0784607217f5068c3d6cb16f39b6fdb8`. The [container state](purge-containers-runtime-2026-09-20.json), [deployment log](purge-deploy-2026-09-20.txt), and [source hashes](purge-image-source-hashes-2026-09-20.json) record the running implementation. [Before](purge-containers-before-2026-09-20.txt) and [after](purge-containers-after-2026-09-20.txt) inventories confirm all 17 unrelated containers retain identical IDs, names, images and states. No Mac Studio resources were accessed.

The endpoint `http://127.0.0.1:8776/mcp` initializes as 0.2.3 and lists 33 tools. [Read-only previews](purge-runtime-before-2026-09-20.json) verified all four cleanup scopes without changing revision 10, the 10 imported sources or 547 indexed chunks. The new scope `all_except_inbox` binds the complete filesystem inventory and all 221 inbox hashes.

The user-authorized production cleanup then executed through the actual `cleanup_workspace` MCP tool over Streamable HTTP using the official Python SDK. This was a direct MCP `tools/call`, not a native task-catalog invocation or direct database/filesystem deletion by the client. The cached native catalog still had 31 tools. [Exact arguments, receipt and verification](purge-execution-2026-09-20.json) record successful removal of 10 sources, 547 chunks/embeddings, old request/event history, and all 27 data files outside inbox (24,079,596 bytes), including existing backups and import logs. No new backup was created. Every one of the 221 inbox files (806,172,536 bytes) retained its original hash.

[Native MCP status after cleanup](purge-native-after-2026-09-20.json) independently verifies revision 11, zero sources/artifacts/chunks/embeddings, 221 inbox files and no pending cleanup. A second read-only preview verified zero remaining target files; only empty managed directories remain outside inbox alongside runtime database and credentials. One minimal receipt remains for idempotency, and an exact retry returned the same result without deleting anything further.

[Validation](validation.md) records 38 passing source tests plus one opt-in skip, seven passing installed-container cleanup tests, and a real schema-3 backup migration to schema 4 with every pre-existing row preserved. The old backups named in historical sections below were removed by the explicitly authorized permanent cleanup. Do not downgrade an existing schema-4 data workspace to an older runtime. The model, endpoint, token and mounts remain unchanged; review capability URLs from before the service restart are historical. Thai search quality has not yet been improved by this cleanup.

## Historical deployment — 0.2.2

Updated **2026-09-20 20:52 ICT (13:52 UTC)**. Both local Research RAG services are healthy on `codex-research-rag-mcp:0.2.2`. Image manifest-list identity: `sha256:1f28bcc8d72d1fcd4a7ccf246c56fcb8f54a4dbcfab962289977e440817fdbfa`; Linux platform manifest: `sha256:1366451c5b4bb8ddc2f742c9ec2aa83e98b035e982da5aaeee76c486c9d77c11`.

The actual Streamable HTTP endpoint `http://127.0.0.1:8776/mcp` initializes as server version 0.2.2, lists **33 tools**, and successfully previews all three cleanup scopes without changing state. See [runtime calls and plans](cleanup-runtime-2026-09-20.json), [deployment/state comparison](cleanup-deployment-checks-2026-09-20.json), [deployment log](cleanup-deploy-2026-09-20.txt), and [read-only verification client](https://github.com/aekanun2020/2026-Research-RAG/blob/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/scripts/verify_cleanup_http.py).

Native MCP status after deployment verifies revision **10**, **10 sources**, **547/547 indexed chunks** and **221 inbox files**. Source metadata is unchanged. No production cleanup had executed at this historical checkpoint. Native `backup_workspace` created `/data/backups/ca9b398d18464783bbac95d69cc9c207` before deployment. All **17 unrelated local containers** retain their IDs, images and states. No Mac Studio resource was accessed.

The source suite passed 35 tests with one opt-in Crossref skip; all four cleanup cases passed in the installed Linux image with no external networking. These are implementation checks, not proof of improved Thai retrieval. See [cleanup contract](workspace-cleanup.md) and [validation](validation.md).

The current Codex task's cached native catalog still lists the previous 31 tools, although the real endpoint has 33. Refresh/reconnect the research-rag MCP client before native calls to the two new tools. No direct production database cleanup was used to bypass that limitation. Endpoint binding, credentials, mounts and model stay the same. The separate review process restarted, so any previously issued review capability URL is historical.

## Historical deployment — 0.2.1

Updated at **2026-09-20 19:47 ICT (12:47 UTC)** to add the read-only
`preview_inbox_document` MCP tool. Both existing local RAG services are healthy
on `codex-research-rag-mcp:0.2.1`, image
`sha256:cfe4dcbb73f228392fa2f9900a482c59383d1239e6041320fd60d9437b20faee`.
The MCP healthcheck initializes the real service and lists **31 tools**. See
[runtime evidence](inbox-preview-runtime-2026-09-20.json),
[preview contract and tests](inbox-preview.md), and
[installed-image regression output](inbox-preview-container-tests-2026-09-20.txt).

The existing workspace, inbox and bearer token are reused. Before deployment,
`backup_workspace` created `/data/backups/45c9ba081c9e48e78b2bfcfcb31110c2`.
Direct native MCP status after deployment remains revision 0 with 221 inbox
PDFs and zero imported documents/chunks. The currently active Codex task must
refresh its catalog before it can call the new tool; its cached list still has
30 tools. The user requires native MCP tools for ingestion, so no CLI/Python
production import was used. All 17 other local containers are unchanged.

Endpoint, data paths and authentication remain as documented below. The review
process restarted during this update, so any previous review capability URL is
historical; obtain its current URL from the review service when needed.

## Historical deployment — 0.2.0

Updated for semantic retrieval and document/chunk management at **2026-09-20 13:00 ICT (06:00 UTC)**. The initial 10:03 deployment and 10:25 manuscript-identity update remain recorded below as history. Both services run in the local Docker Desktop context `desktop-linux`, Compose project `codex-research-rag`:

| Container | Host endpoint | State |
|---|---|---|
| `codex-research-rag-mcp-1` | `http://127.0.0.1:8776/mcp` | Running, healthy |
| `codex-research-rag-review-1` | `http://127.0.0.1:8777/?token=<review-token>` | Running, healthy |

Project location: `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-TTS-AI/codex-research-rag-mcp`. Persistent data are in this directory's `.data`, bind-mounted at `/data` in both containers. The existing bearer credential is preserved at `.data/.http-token`; do not commit or paste it into documentation. MCP clients must send it as `Authorization: Bearer <token>`.

The current image is `codex-research-rag-mcp:0.2.0`, identity `sha256:56bcca357c5df8f85408e9912731888c09be35e5997959a9bd191610462900aa`. See [current runtime verification](semantic-runtime-2026-09-20.json), [application source hashes](semantic-image-source-hashes-2026-09-20.json), [model provenance](../third-party/embedding-model/README.md), and [base-image provenance](../third-party/container/README.md). The runtime is Linux arm64 with Python 3.12.14 and MCP SDK 2.2.0. All 13 packaged Python/JSON files matched local source hashes. Original deployment records retain their historical image identities.

The image includes pinned multilingual-e5-base ONNX weights/tokenizer; inference uses CPU only. First build downloads approximately 1.13 GB of model assets and verifies SHA-256. Runtime needs no inference network or API key. Evidence, chunk metadata and 768-dimensional float32 vectors are persisted in SQLite under `.data`; no dedicated vector DB is deployed.

[Thirty integration cases](semantic-final-suite-2026-09-20.txt) passed in 227.681 seconds before update. The actual public-on-loopback endpoint initialized protocol 2025-11-25, listed **30 tools**, and accepted workspace/document/index/semantic-search calls. Production remains revision **0** with no imported documents; nonempty retrieval was tested against the real PDF in isolated containers. Both services are healthy; review GET is 200. Missing bearer, foreign Origin and foreign Host return 401, 403 and 421. The existing bearer and all pre-existing logical records were preserved, and all **17 unrelated local containers** retained their IDs, names, images and states. No Mac Studio resource was accessed.

Before migration from schema 1 to 3, an actual old-runtime backup was written to `.data/backups/badf25526ec444d194e80634d256a3cb`. Migration adds identities/index tables; prior research records remain unchanged. Rollback must use this schema-1 backup with the old 0.1.0 runtime in a separate restored directory; do not point the old runtime at a schema-3 workspace. Backups exclude bearer tokens; retain the separately protected original token file.

The [Compose configuration](../compose.yaml) uses numeric non-root user `501:20` on this Mac via ignored `.env`, read-only image files, writable `/tmp`, and persistent `/data`. Copy [the example settings](../.env.example) only for a fresh installation and set UID/GID to the local directory owner's IDs. Container listeners bind `0.0.0.0`; published ports bind only `127.0.0.1` on the Mac. Host/Origin validation and separate MCP/review tokens remain enabled. No public endpoint was opened.

## Run and inspect

Run commands in the project directory:

```sh
docker compose up -d --build --wait
docker compose ps
docker compose logs --tail 5 review
docker compose exec mcp python /app/scripts/smoke_http.py --workspace /data
docker compose stop
```

The review log prints the usable local URL. Its token changes when that service starts; the previous port-52456 URL is obsolete. The MCP health check performs authenticated initialize, tools/list and workspace_status. The review health check checks its TCP listener; the authenticated review page was separately verified with HTTP GET. `unless-stopped` restarts services while Docker Engine is available; launching Docker at OS login was not configured in this task.

## Historical 0.1.0 verification and regression evidence

- The causal application change adds `--host` to both CLI services and passes it to their real listeners. Direct execution still defaults to `127.0.0.1`. Host and Origin allowlists were not relaxed.
- Immediately rerunning the original failing command with the changed source started the real server on `0.0.0.0:18776`. Official SDK initialize, tools/list and workspace_status passed: protocol `2025-11-25`, 19 tools, revision 0. The temporary listener was then stopped.
- The nearby real HTTP authentication case passed with `RESEARCH_RAG_TEST_BIND_HOST=0.0.0.0`. An initial review test invocation used the wrong class name (`ReviewIntegration`) and failed at test discovery; rerunning the existing `HumanReviewIntegration` class passed. No application patch was made for that invocation error.
- [All 20 existing integration tests](container-tests-2026-09-20.txt) passed in **32.932 seconds** inside the built Linux image, including all eight stages, real PDF ingestion/retrieval, CSV calculations, review state transitions, backup/restore and live Crossref. The final image rebuild added only provenance documents; application and dependency build layers were cached unchanged.
- Temporary Compose containers on ports 18776/18777 passed host-to-container MCP and authenticated review GET checks before cutover. Only the two verified project Python processes were stopped. The temporary verification containers/network were removed after the final containers became healthy.
- [Final host-to-container MCP smoke](container-http-smoke-2026-09-20.json): initialize, tools/list and `workspace_status({})` passed at `http://127.0.0.1:8776/mcp`; protocol `2025-11-25`, **19 tools**, revision **0**. The actual workspace remains empty; no research documents or draft artifacts were inserted into it by these checks.
- Final published-port access checks: missing bearer **401**, foreign Origin **403**, foreign Host **421**; review GET with its separate token **200**, without token **403**. No real human-review decision was submitted.
- [Runtime inspection](container-runtime-2026-09-20.json) confirmed both containers healthy, loopback-only port publishing, persistent bind mounts, unchanged bearer token, and the same IDs/names/states for all **17** pre-existing local containers. No shared Mac Studio resources were accessed.

To repeat the existing suite against the installed image using temporary test workspaces:

```sh
docker compose run --rm --no-deps --entrypoint python \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/README.md:/app/README.md:ro" \
  -e RESEARCH_RAG_LIVE_TESTS=1 -e RESEARCH_RAG_TEST_BIND_HOST=0.0.0.0 \
  mcp -m unittest discover -s tests -v
```

The current 0.2.0 evidence is linked above; the preceding 20-test and 19-tool records are historical. These checks assess the actual implementation and container networking. They do not establish Claude Desktop acceptance, Windows/amd64 compatibility, or the scientific quality of generated answers. Assessment was performed by Codex, with deterministic protocol checks and no external model calls.
