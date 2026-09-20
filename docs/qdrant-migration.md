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

[Upstream provenance](../third-party/reference-rag/README.md). Implementation and validation are pending; no readiness or quality improvement is claimed yet.
