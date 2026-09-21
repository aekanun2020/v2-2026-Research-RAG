# Semantic retrieval and chunk management

Version 0.2.4 adds local BGE reranking of 50 E5/hybrid candidates and first-page relevance diagnostics. Automatic score filtering is disabled after a held-out false negative. Embeddings, active chunks and source identities remain unchanged. See the [quality report, exact questions and before/after evidence](retrieval-quality-2026-09-20.md), [MCP parameters](tools.md) and [reranker provenance](../third-party/bge-reranker-model/README.md). The results below describe the earlier embedding/chunk implementation.

Scope: implement the user's requested semantic search, source/document identifiers linked to full papers, chunk management, automatic indexing on import, and retain the canonical manuscript IDs already implemented. Run in the standalone local Docker Compose project. No external model API, GPU, proxy, replacement dependency, or shared Mac Studio workload is involved.

Before application changes, an actual import of the existing real brms test PDF followed by the Thai query “การประมาณค่าแบบเบย์สำหรับข้อมูลที่มีโครงสร้างหลายระดับ” returned **0 lexical hits**. See [preserved baseline](semantic-before-2026-09-20.json). The root cause is concrete: retrieval.py only scores matching terms and the MCP schema offers no semantic mode; there are no embedding records or chunk-management tools. No full-text semantic representation exists in the baseline.

The embedding model is selected from its original publisher: `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions. The original model card declares MIT and lists Thai and English. Exact upstream metadata and notices are preserved under [embedding model provenance](../third-party/embedding-model/). The [model manifest](https://github.com/aekanun2020/2026-Research-RAG/blob/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/src/research_rag_mcp/model_manifest.json) pins asset hashes before download. Local inference uses ONNX Runtime CPUExecutionProvider only. The model produces embeddings, not answer evaluations; Codex inspects semantic results itself.

Implementation and validation results will be added as each real integration check completes.

## Implemented behavior in 0.2.0

The final model selection is **multilingual-e5-base**, 768 dimensions, revision `d128750597153bb5987e10b1c3493a34e5a4502a`. The small model mentioned above is the preserved initial experiment. [Codex's assessment](semantic-assessment-2026-09-20.md) explains the observed improvement and unresolved ranking cases.

- Import persists immutable original bytes, page text, document/source/text identity, an active chunk set and its CPU embeddings. Original file hashes, text hashes and vector hashes are checked. Source versions are explicitly linked, never guessed.
- `retrieve_evidence` exposes lexical, semantic and default hybrid modes. Semantic uses exact cosine; hybrid uses reciprocal rank fusion with k=60. Scores are not probabilities. Search defaults to the latest source version per logical document and active chunks; explicit source_ids allow historical evidence.
- Eleven additional tools manage document inventory, chunk browsing/context/inspection, candidate rechunking/activation, status/reasons, evidence usage and index rebuild/status. Together with the existing workflow, the server exposes 30 tools. See [complete contracts](tools.md).
- SQLite stores float32 vectors with the evidence history; there is no dedicated vector DB or ANN index in this release. This simplifies consistent backups but scans selected vectors per query. Large-corpus capacity is not established.
- Chunks, originals and manuscript history are retained. Citation identity uses exact source/page/character spans, so changing chunk sets does not rewrite citations. Chunk exclusion applies to the selected chunk/set, not permanent source-text redaction; inspect new sets before activation.
- Backups include SQLite embeddings and source bytes. Model weights are pinned in the image and downloaded separately for direct Python execution. Restore verifies hashes into a new directory.

See [ingestion and responsibilities](ingestion.md), [focused container checks](semantic-focused-2026-09-20.txt), and [migration evidence](semantic-migration-2026-09-20.json). The migration preserves old request fingerprints when optional document_id is omitted: [before failure](migration-retry-before-2026-09-20.json) and [same-case result after fix](migration-retry-after-2026-09-20.json). [The migration verifier](https://github.com/aekanun2020/2026-Research-RAG/blob/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/scripts/verify_migration.py) requires a workspace produced by the real old runtime; it does not fabricate schema/data.

## HTTP client regression

The broader suite initially passed 27 cases and failed 2 import requests with `SSE stream ended without a response`: [preserved failure](semantic-suite-before-timeout-2026-09-20.txt). Both clients overrode the SDK's recommended HTTP client with a default httpx2 client, whose read timeout is 5 seconds. CPU embedding took longer. The SDK source in installed mcp 2.2.0 specifies 30-second connect/write/pool and 300-second read for Streamable HTTP.

Only those client timeout settings were corrected to `httpx2.Timeout(30, read=300)`; the server, import operation and embedding work were unchanged in this experiment. Both original failing cases then passed: [targeted rerun](semantic-timeout-regression-2026-09-20.txt). No proxy, fallback, fake embedding or skipped import was introduced. This is also documented in the client/ingestion instructions.

Final-model checks: [nine focused container cases](semantic-base-focused-2026-09-20.txt), including the original Thai-query locator regression, passed with external networking disabled. [Actual legacy-to-final migration](semantic-final-migration-2026-09-20.json) preserved all 77 old chunk IDs, eight checked citations and the exact original import retry response, then indexed all chunks with the selected base model.

The [final full suite](semantic-final-suite-2026-09-20.txt) passed all 30 cases in 227.681 seconds. [Packaged application hashes](semantic-image-source-hashes-2026-09-20.json) matched all 13 local Python/JSON files before deployment. This verifies implementation/integration, not general semantic accuracy or live Claude Desktop acceptance.
