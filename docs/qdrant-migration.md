# Qdrant migration — work in progress

Authorization: user selected the fixed-2026-rag-mcp-server-streamablehttp repository, requested missing research capabilities and Thai lexical matching, and explicitly chose complete removal of SQLite on 2026-09-21.

## Preserved requirements

- Qdrant vectors, local CPU Ollama embeddings, PyThaiNLP BM25 and RRF from the selected base. No BGE reranking in this selected architecture.
- Document/source/text/chunk/manuscript identities, exact original page spans, source hashes, chunk history, revisions, idempotency, eight research stages, separate human review and export.
- No SQLite runtime. Transactional revisioned JSON workspace state with interprocess locking and atomic replacement; Qdrant stores the vector search index.
- Import and verification only through real MCP tools. No mocks or external model judges.
- Existing live service/data stays in place until migration and tests pass.

## Before state and observed failures

User reported 12 concurrent agents: 9 obtained no evidence; 3 obtained partial results. NLAH lexical succeeded 4/4, hybrid failed 6/6. Import timed out three times; exact-key retries were reported not to duplicate documents. These are user-reported results, not newly reproduced by Codex. CPU BGE causality remains unproven.

A prior single-query MCP diagnostic recorded 0.2611 seconds with rerank=false, then was interrupted by user instruction before the rerank comparison completed. This is not an isolated SQLite measurement.

Live MCP 0.2.4 currently reports revision 36 and 22 imported papers. No manuscript/project is present in this research-rag workspace. The separate tts-research workspace is outside scope.

## Inbox deletion

Explicit user exception permitted direct deletion without MCP and without backup. Live Docker mount verified the inbox at `2026-TTS-AI/codex-research-rag-mcp/.data/inbox`. Deleted 233 regular files (868039542 bytes); verified zero remaining entries and retained the directory. Imported source copies and all other workspace data were untouched.

## Provenance and validation

[Upstream provenance](../third-party/reference-rag/README.md). [Upstream MCP baseline](qdrant-upstream-baseline-2026-09-21.json): 17 repository documents, 128 chunks, import 12.469s, Thai lexical 0.0045s and hybrid 0.0224s. These are the repository's own sample documents, not the 22-paper research corpus. Codex inspected the refund-query output: the top hit was a job announcement, so this timing is not evidence of good relevance. Initial connection before Uvicorn finished startup failed; the same client completed after startup without code changes.

Original code evidence requiring integration changes: Qdrant filters were a TODO; dimension mismatch automatically deleted/recreated the collection; the HTTP tool schema omitted search_mode; components could silently degrade hybrid to one retriever. The integration implements actual filters, rejects destructive dimension mismatch, publishes real SDK-generated schemas, and errors on component failure. The baseline logged client 1.15.1/server 1.18.3 incompatibility; the new lock aligns client 1.18.0.

Implementation and full validation remain in progress; no research-corpus quality improvement is claimed yet.

## Targeted Thai lexical regression

[Before MCP evidence](qdrant-thai-lexical-before-2026-09-21.json): against the original 128-chunk upstream corpus, `PDPA` and `2562` returned the actual customer-service policy, while `pdpa` and `๒๕๖๒` returned no results. The tokenizer passed text directly to newmm without case folding or digit normalization. The first patch changes only normalization of matching tokens (NFKC, case folding, Thai digits to Arabic digits); originals and quote offsets stay unchanged. The original failure cases are rerun against the same Qdrant collection before broader integration tests.

The original failing lexical cases now pass through the real MCP endpoint: [after responses and nearby queries](qdrant-thai-lexical-after-2026-09-21.json). `pdpa` returns byte-identical result text to `PDPA`, and `๒๕๖๒` to `2562`, using the unchanged 128-chunk reference collection. The first regression-image build failed because a Dockerfile outside the project caused Docker to inspect unrelated `/tmp` metadata; moving the Dockerfile into the project resolved that build-context issue. No service or test dependency was replaced.

Additional required behavior: PyThaiNLP is mandatory and hybrid component errors propagate. The reference's whitespace/one-retriever fallback paths are removed rather than reporting reduced functionality as success.

## Container startup regression and MCP authentication

The first packaged mandatory-PyThaiNLP build failed to start: its cache defaulted to `/pythainlp-data` on a read-only root filesystem. [Observed failure](qdrant-startup-before-2026-09-21.txt). The only causal change was `PYTHAINLP_DATA=/tmp/pythainlp-data` in the actual container's writable tmpfs. [The same MCP initialization/list/status check then passed](qdrant-startup-after-2026-09-21.json).

User explicitly requested no MCP access tokens on 2026-09-21. Before removal, a token-free request to the old MCP returned HTTP 401. The new server removes the bearer middleware and credential generation rather than shipping an optional authentication bypass. The separate human-review capability is not an MCP access token.

## Durable-job retry regression

[First real workflow run](qdrant-workflow-2026-09-21-run1.json) measured initial PDF import acknowledgement at 0.0095s, but the exact-key repeat took 14.5505s. `Jobs.submit` acquired the journal writer lock before looking up the durable job receipt; the worker held that lock during embedding. The causal patch reads an existing receipt before requesting the writer lock, retaining fingerprint validation. The regression requires both initial submission and exact-key repeat to finish within five seconds on the same actual ELMo PDF. No timeout was raised in this 14.55s observation, but the acknowledgement requirement failed.

[Second workflow run](qdrant-workflow-2026-09-21-run2.json) confirms the retry fix: initial acknowledgement 0.00949s; exact repeat 0.01060s, same job ID. Later in that run, reimport of the actual CSV measurement text failed with `Existing context file integrity mismatch`. The existing file retained CRLF bytes, but `Path.read_text()` normalized them to LF before comparison. The sole causal patch compares UTF-8 bytes to UTF-8 bytes. The failed job is explicitly resumed through MCP after deployment.

Restore revision regression: run 1 cleared the workspace at revision 15 and restored a revision-14 snapshot back to revision 15. Source/vector restoration succeeded, but reuse of revision 15 could allow a stale write. Root cause: restore replaced the current revision with the snapshot revision before incrementing. The isolated correction increments `max(current_revision, snapshot_revision)`. The regression now requires restored revision to be strictly greater than the pre-restore revision, in addition to exact IDs/history/index readiness.

## Thai semantic quality: failed with the selected original model

[All 40 actual MCP responses](qdrant-thai-quality-2026-09-21.json) test the original 20 Thai questions in semantic and hybrid mode on the same original ten-paper subset. The new corpus contains 22 papers, but this comparison explicitly filters to the original ten IDs. All returned spans match their original pages. All 20 questions return the same top chunk in both modes.

[Codex's new manual top-1 assessment](qdrant-thai-codex-assessment-2026-09-21.json): per mode, 0 fully address the question, 2 are partly relevant handwriting context, and 18 are unrelated. The expected paper ranks first for 2/16 in-scope questions; this is not answer correctness. All four out-of-corpus controls return candidates. No automatic confidence threshold or LLM judge is used.

The actual original Nomic model is an English encoder, as described in [Nomic's official model overview](https://home.nomic.ai/embed) and [model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5). Different Thai inputs produced identical result scores for 19/20 questions. This is evidence of a model/language problem; no claim is made that changing the vector database can solve it. PyThaiNLP lexical normalization independently passed. A question has been sent to the user about switching only the embedding model to the multilingual Nomic v2 model, preserving Qdrant/Ollama/BM25/RRF. No unapproved model substitution has been performed.

## Concurrent retrieval and token-free protocol

[Real concurrent run](qdrant-concurrent-2026-09-21.json): 12 independently initialized MCP sessions start hybrid retrieval together, one filtered to each of the twelve newer papers, limit 2. 12/12 complete within the 30s deadline, 3.367–3.611s, with 24 exact page-span checks. Queries use each verified paper title plus `architecture method evaluation limitations`; they are recorded verbatim. This is transport/concurrency/filter evidence, not proof of complex-question relevance or equivalence to every prompt in the user's earlier agents.

[Token-free initialize/tools/list/workspace_status](qdrant-no-token-2026-09-21.json) succeeds with 41 tools and no Authorization header. The separate human-review UI is not an MCP tool and was not operated to impersonate a researcher.

## Focused fixes and complete workflow rerun

- [CSV CRLF original failed job resumed](qdrant-crlf-after-2026-09-21.json): identical actual input completed and all 12 measured rows were available.
- [Restore revision rerun](qdrant-restore-revision-after-2026-09-21.json): revision 22 → cleanup 23 → restore 24, identical source IDs and ready Qdrant index.
- [Final full MCP workflow run](qdrant-workflow-2026-09-21-run3.json): real ELMo PDF, selected upstream Thai policy, attributed publisher-policy excerpt and actual measured CSV; imports/durable reconnect/repeat, batch/context imports, normalization, all eight stage contexts/checks, chunk set/status/history, exact citations, manuscript ID and revisions, draft export, rejected invalid citations/reviewed export, index cleanup/rebuild, backup/restore, and final inbox-preserving cleanup. These are software checks, not generated research findings or researcher acceptance.
- [Live Crossref evidence](qdrant-crossref-2026-09-21.json): a DOI entered as a free-text bibliographic query returned a different paper, so the first assertion failed. This tool is not an exact DOI lookup. The verified article-title query subsequently returned the correct DOI `10.18637/jss.v080.i01` first and its metadata was persisted through MCP. No server code or dependency was changed to force that result.

Not proven by these runs: native Claude Desktop interaction on both operating systems; a human review/acceptance action; 200+ imported papers under sustained load; process-kill recovery mid-vector upsert; partial filesystem failure during restore; Thai semantic quality with a multilingual replacement model. No claim is made that those checks passed.

## Persistent candidate deployment

The canonical repository worktree now lives at `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-TTS-AI/codex-research-rag-qdrant` on branch `codex/qdrant-research-rag`. Candidate MCP: `http://127.0.0.1:8876/mcp`; human review: port 8877. Its local `.env` selects these separate ports and the permanent `.data` path. The migrated workspace is revision 37, 22 papers, 2106 total chunks, with an empty inbox. The actual reference/validation containers were removed after verification; their isolated test volumes are retained.

Candidate MCP does not generate, read, validate or require an access token. The old read-only legacy bind mount is removed after migration; no SQLite file is present in the candidate data directory. The original 0.2.4 containers were subsequently removed at the user's explicit request; see the retirement record below. Their bind-mounted source files and the separate new workspace remain intact.

[Final permanent endpoint check](qdrant-final-endpoint-2026-09-21.json) reinitialized the actual token-free service after moving its data and removing the legacy mount. It verified all 41 tools, revision 37, 22 sources, 2106 ready chunks, empty inbox, and a representative hybrid query whose two quotes exactly match original pages.

## Old container removal 2026-09-21

Completed and verified at 2026-09-21 00:40:58 UTC (07:40:58 Asia/Bangkok), following the user's explicit instruction to delete the `codex-research-rag` containers. The target was grounded in the live `desktop-linux` Docker context and exact Compose project label.

Removed after graceful stop:

- `codex-research-rag-mcp-1` — container `025fa59c7f73`, image 0.2.4.
- `codex-research-rag-review-1` — container `a8ab7aed77ff`, image 0.2.4.

`docker ps -a` filtered by the exact old project label returned no containers afterward. Only those two container IDs were stopped and removed. No images, volumes, networks, source folders or papers were deleted. The four `codex-research-rag-next` container IDs were unchanged and running; MCP/review were healthy.

A real token-free MCP smoke check against `http://127.0.0.1:8876/mcp` successfully performed initialize, tools/list (41 tools), and workspace_status (revision 37). The old 8776/8777 containers are no longer available. The new endpoint and port remain unchanged. This retirement does not resolve the outstanding Thai semantic-quality/model-selection issue.
