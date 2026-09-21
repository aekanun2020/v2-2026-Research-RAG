# Academic paper chunking — isolated 0.4.0 branch

Branch: `codex/academic-paper-chunking`, based on `4901196`. The user authorized implementation and explicitly required no shared containers with the earlier version. This change implements the previously proposed Markdown sections plus sentence splitting; PDF text uses sentence splitting within each preserved page because reliable PDF section extraction is not available in this implementation.

## Behavior

- Actual, unmodified LlamaIndex **0.14.24** `SentenceSplitter`, with **512 tokens including two special tokens**, up to **64 content tokens of overlap**, and paragraph/sentence boundaries preferred. Long sentences may be divided to fit. These are explicit application settings, not LlamaIndex defaults.
- Actual `MarkdownNodeParser` runs first for `.md` files. Each resulting section is split independently; overlap does not cross its section boundary. Parsed headings and section spans are retained as metadata.
- Markdown's parser can normalize whitespace. The implementation verifies the entire non-whitespace character sequence and maps its boundaries back to original positions. Stored and embedded text always comes from an exact original slice. A content rewrite or omitted nonblank text fails instead of producing an invented locator.
- Nomic's pinned official WordPiece tokenizer counts tokens locally, with truncation disabled. Its vocabulary IDs and special token IDs match the installed GGUF after accounting for GGUF's WordPiece string representation. [Identity inspection](chunking-tokenizer-identity-2026-09-21.json). This is asset verification, not proof of token-by-token equivalence for every Unicode input.
- English sentence segmentation uses the English Punkt data bundled in LlamaIndex; text containing Thai uses PyThaiNLP CRF sentence segmentation. No external model is called for chunking, and no sentence-segmentation assets are downloaded at runtime. The Thai lexical tokenizer remains separate.
- PDF/TXT/CSV/JSON have no inferred section labels. PDF chunks remain inside original extracted pages. Existing extraction, source hashes and exact page offsets remain unchanged; OCR, two-column ordering, tables/equations and cross-page sentence continuity are not solved by this change.
- New sets receive new IDs and retain old sets and citations. `read_chunk` exposes the chunking method, version, unit, tokenizer hash, token count and section metadata. Only an explicitly activated set is used for search.
- The embedding model is unchanged. This does not resolve the previously measured Thai-to-English semantic retrieval failure.

## MCP contract

New imports use the defaults above. `rechunk_document` accepts `chunk_size_tokens` (64–2048, including special tokens) and `chunk_overlap_tokens` (0 up to strictly less than half the content budget). The 0.3.0 character parameters `size`/`overlap` are no longer input fields in 0.4.0; the explicit names prevent silently interpreting characters as tokens. Saved old sets remain readable with their original method/settings.

Call `rechunk_document`, poll `job_status`, read the candidate with `list_chunks(chunk_set_id=...)` / `read_chunk`, then call `activate_chunk_set` with a fresh revision and key. `inspect_document_chunks` checks the active set's original-text coverage. See [full tool contracts](tools.md).

## Separate deployment

| Service | Old 0.3.0 project | New 0.4.0 project |
|---|---|---|
| Compose project | `codex-research-rag-next` | `codex-rag-chunking` |
| MCP | `127.0.0.1:8876/mcp` | `127.0.0.1:8976/mcp` |
| Human review | `127.0.0.1:8877` | `127.0.0.1:8977` |
| Qdrant | Its own container and volume | New container and new volume |
| Ollama | Its own container and volume | New container and new volume, model pulled separately |
| Data directory | `.data` | `.chunking-data` |
| App image tag | `codex-research-rag-mcp:0.3.0` | `codex-research-rag-chunking:0.4.0` |

[Container/network/mount verification](chunking-container-isolation-2026-09-21.json) · [packaged source hashes matching the checkout](chunking-final-image-hashes-2026-09-21.json). Both projects run on local Docker `desktop-linux`. No Mac Studio resources were accessed. Shared image layers in Docker's image cache do not represent shared service containers or writable volumes.

The branch's [default Compose](../compose.yaml) includes only [the isolated configuration](../compose.chunking.yaml). Legacy `RAG_*` environment variables do not choose its paths or ports. Configure [the example environment](../.env.example) as `.env.chunking` and run:

```sh
docker compose --env-file .env.chunking up -d qdrant ollama
docker compose --env-file .env.chunking exec ollama ollama pull nomic-embed-text:latest
docker compose --env-file .env.chunking up -d --build --wait mcp review
```

All four containers belong to the new project. MCP has no access token. Stopping or replacing this stack uses this same explicit environment/Compose project, never the old project.

## Causal changes and observed evidence

1. **Before change:** [original MCP evidence](chunking-before-2026-09-21.json) on the actual ELMo PDF, selected upstream's existing Thai example policy and this repository's README at `4901196`. The old 1,200-character/200-character-overlap method started ELMo chunks inside words (page 0 offset 2958 splits `w|ith-`) and mixed Markdown sections. These are observed source-boundary problems, not model-graded relevance scores.
2. **Sentence splitting only:** [same inputs rerun](chunking-sentence-after-2026-09-21.json). ELMo changed from 62 to 37 chunks, with no internal English word starts, all exact spans and no uncovered nonblank text. Markdown still crossed headings. This remaining failure was preserved before the second change.
3. **Markdown sections added:** [same inputs rerun again](chunking-sections-after-2026-09-21.json). ELMo remains 37 chunks; Thai example policy has 11 and README 8. No Markdown chunk crosses a heading in these inputs. All 56 chunks matched original spans and configured token budgets; old chunks remained readable and candidate activation stayed explicit.
4. **Nearby cases:** [real MCP checks](chunking-nearby-2026-09-21.json) cover 384 tokens without overlap, 64 tokens on mixed Thai/English Markdown, 128 tokens on Thai Markdown, and rejected invalid size/overlap. The script independently recounts tokens and verifies original spans. Segmentation quality for all Thai academic writing is not established.
5. **Workflow regression:** [full real MCP run](chunking-workflow-2026-09-21.json) passed all 61 checks (no failures), covering import/retry, original citations, chunk-set history, all eight stage contexts, manuscript revisions, export restrictions, index rebuild and backup/restore. The test finished by clearing its own research records through MCP, retaining inbox files. [Preparation cleanup](chunking-prepare-workflow-2026-09-21.json) affected only this task's three imported documents in the isolated new stack.

The Thai example policy is an upstream demonstration document, not a real company's policy or research observation. The manuscript in the workflow regression is explicitly marked as an unresolved software integration record. No scientific acceptance is simulated.

Reproduction uses [baseline capture](../scripts/capture_chunking_baseline_mcp.py), [original-case rerun](../scripts/verify_academic_chunking_mcp.py) and [full workflow](../scripts/verify_qdrant_workflow_mcp.py). They call the official MCP SDK over Streamable HTTP; none constructs a Store directly or replaces Qdrant/Ollama. Full intermediate page responses are retained locally; tracked summaries preserve locators, counts, hashes and findings without duplicating the whole PDF.

[Dependencies, original notices and asset hashes](../third-party/chunking/README.md). No external LLM evaluator was used; Codex inspected the reported boundary failure and corrected chunks. No ranking improvement, complete scientific interpretation, native Claude Desktop acceptance or 200-paper sustained-load result is claimed.

## Final endpoint observation

[Final MCP protocol/version/schema check](chunking-final-mcp-2026-09-21.json) verifies the new service as 0.4.0 with 41 tools and token-based rechunk arguments. The new test workspace is empty after the completed workflow. The earlier service remains 0.3.0 with its character-based tool contract.

The first final-check script incorrectly assumed the old workspace would still be empty at revision 38. [Observed result](chunking-final-old-state-observation-2026-09-21.json): the new service was empty at revision 36, while the old service had revision 50 with 12 sources and 1490 indexed chunks. The assertion failed on stale test expectations, not on a shared database or a service error. The script was corrected to record the independently evolving old workspace without modifying it. This task does not establish who imported those old-stack documents. All mutations in this task used the new endpoint only.
