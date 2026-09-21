# Tool contract and eight-stage workflow

MCP requires no access token or Authorization header. Version 0.4.0 changes chunking; version 0.3.0 added durable jobs and the selected upstream entry points to the research tools. All tools are listed by the real MCP `tools/list` endpoint with typed input schemas and JSON object output schemas. `research_workflow` is also exposed as an MCP prompt. Initialize first, then read `workspace_status`. Every persisted write takes the current `expected_revision` and an `idempotency_key`; exact retries return the prior response, while changed inputs cannot reuse a key.

## Shared evidence tools

| Tool | Inputs and behavior |
|---|---|
| `workspace_status` | No inputs. Project, sources, saved artifacts, effective review status, search history and required section keys. |
| `start_project` | Researcher's `topic`, `goal`, `unknowns`; only initializes an empty workspace. |
| `preview_inbox_document` | Read-only `filename` inside inbox, `page_index=0`, `start=0`, `max_chars=12000` (1–20000). Returns original page text, raw PDF metadata, SHA-256, size and page count. Continue a long page with `next_start`. Verify the title before import; unknown metadata stays unknown. No database or index changes. |
| `import_document` | `filename` inside inbox, actual `origin`, `role`, supplied `bibliography` with title and optional authors/year/DOI. PDF or UTF-8 TXT/MD/CSV/JSON. Optional `document_id` links a new source version explicitly. Returns job_id; completed job contains document/source/text/chunk-set IDs after local Ollama/Qdrant indexing. |
| `search_literature` | Public `query`, optional `limit` 1–50 and inclusive publication year bounds. Calls the real Crossref endpoint and persists one page of metadata. |
| `retrieve_evidence` | `query`, optional `roles`, `source_ids`, `limit` 1–30 and `mode`: `hybrid` (default), `semantic`, `lexical`. Returns ranked chunks with exact citations and identities. Latest versions/active chunks by default; explicit source_ids permits historical versions. No rerank/min_rerank_score/candidate_limit parameters in 0.3.0. |
| `read_source_page` | `source_id`, zero-based `page_index`; returns original extracted text and locator convention. |
| `summarize_dataset` | `source_id` of an imported data/results CSV. Computes row/blank/numeric counts and min/max/mean of finite numeric values. |

Version 0.3.0 uses pinned local Ollama nomic-embed-text, Qdrant cosine search, PyThaiNLP BM25 and RRF. No BGE reranker or rerank-related input exists in the new contract. Both hybrid components must succeed. Inspect original evidence; rank scores are not confidence.

Long-running imports, re-chunking and index rebuilds return a durable `job_id`. Poll `job_status` until completed; the original mutation response is in `result`. Interrupted work can be explicitly resumed with `resume_job`; failed work exposes its actual error. Exact submission retries reuse the same job; changed arguments with an old key are rejected. Client timeout does not create another import.

Additional tools: `job_status`, `resume_job`, `migrate_legacy_workspace`, `restore_workspace`, `search_documentation`, `list_sources`, `add_directory`, `add_context`. Directory import requires bibliography for every file instead of inventing titles. Context text defaults to project_note, not observed findings. Migration reads the configured legacy source only and does not copy inbox.

## Document, chunk and index tools

| Tool | Inputs and result |
|---|---|
| `list_documents` | `offset=0`, `limit=50` (max 100). Logical IDs, source versions, original locators, chunk sets. |
| `list_chunks` | `source_id`, optional `chunk_set_id`, `status`, `offset`, `limit`. IDs/spans/status; active set by default. |
| `read_chunk` | `chunk_id`. Full preserved text, identity, original locator, verified citation, chunking configuration, token count, section span and embedding metadata. |
| `get_chunk_context` | `chunk_id`, `before=1`, `after=1` (0–5). Neighbor chunks within the same set plus original page. |
| `inspect_document_chunks` | `source_id`. Hash/span integrity, blank pages, uncovered text, status counts, exact duplicates. No semantic grading. |
| `rechunk_document` | `source_id`, revision/key, `chunk_size_tokens=512` (64–2048, includes 2 special tokens), `chunk_overlap_tokens=64` (below half the content token budget). LlamaIndex SentenceSplitter; MarkdownNodeParser sections first for MD. Creates an indexed candidate set; retains existing sets. |
| `activate_chunk_set` | `chunk_set_id`, revision/key. Changes the source's retrieval set, without changing original page citations. |
| `set_chunk_status` | `chunk_id`, `status=active/excluded/needs_review`, `reason`, revision/key. Preserves text; withheld chunks are excluded from retrieval. Current manuscripts citing withheld chunks in the active set receive a review issue. |
| `find_evidence_usage` | `chunk_id`. Overlapping source/page citations in current and historical artifact/manuscript versions. |
| `search_index_status` | No inputs. Pinned model/provider, local assets, vector integrity/counts, pending index records. |
| `rebuild_search_index` | Revision/key and optional `source_ids`. Verifies originals/spans and explicitly rebuilds embeddings, including retained sets. |
| `preview_workspace_cleanup` | Required `scope=search_index/documents/workspace/all_except_inbox`. Read-only deletion counts, blockers, revision and plan hash; permanent scope includes exact file inventory and inbox hashes. |
| `cleanup_workspace` | Explicit scope, matching `plan_hash`, revision/key. First three scopes back up and clear journal/index records while retaining files. `all_except_inbox` removes all research records and data files except inbox originals, without a backup. Check result status and resume incomplete jobs using their original arguments. See [current migration and cleanup validation](qdrant-migration.md); [0.2.4 contract](workspace-cleanup.md) is historical. |

IDs are not interchangeable: document_id identifies a logical work; source_id is the file-byte SHA-256; source_version orders explicitly linked files; text_revision_id identifies extracted pages; chunk_set_id identifies a split configuration; chunk_id identifies one preserved span in that set. Manuscripts retain their independent artifact id/version. See [ingestion flow](ingestion.md).

## Stage-specific tools and persisted deliverables

The first seven tools accept `query` and optional `limit` and return current evidence plus stage-specific views. They prepare generation context for the connected client. The client must write the actual deliverable and call `save_artifact`; a context packet alone is not a completed research task.

| Stage tool | Saved stage | Required section keys | Additional live context |
|---|---|---|---|
| `explore_topics` | `exploration` | landscape, candidate_topics, reading_plan | Literature inventory, source matrix and discovery coverage |
| `map_research_gaps` | `gaps` | comparison, candidate_gaps, search_limits | Source-by-dimension matrix, missing fields and actual search logs |
| `formulate_question` | `question` | research_question, objectives, contribution, feasibility | Saved topics/gaps and source evidence |
| `design_study` | `design` | study_design, sampling, measurement, analysis_plan, ethics | Prior questions, methods evidence and saved designs |
| `track_execution` | `execution` | activity, observations, deviations, next_actions | Project evidence and versioned execution records |
| `interpret_results` | `analysis` | results, comparison, limitations | Project results separated from literature and real dataset inventory |
| `draft_manuscript` | `manuscript` | title, abstract, introduction, methods, results, discussion, conclusion | Project/literature evidence, existing results and prior artifacts |
| `prepare_submission` | `submission` | venue, checklist, cover_letter, ai_disclosure | Takes `manuscript_id`, `guideline_source_id`, optional `submission_id`; returns actual blockers and original guideline metadata |

To populate the literature matrix, use `save_artifact(stage="literature_note")` with sections `research_question`, `population`, `method`, `findings`, `limitations`. Record missing fields as unresolved. Use one note per report and avoid implying that distinct reports are independent studies. The matrix retains note versions and review status, including stale or rejected interpretations, rather than silently treating them as established evidence.

## Drafts, review and export

`save_artifact` takes `stage`, `title`, `blocks`, `limitations`, `dependency_ids`, the write revision/key, and optional `artifact_id` for a revision. A block has `section`, `text`, `basis`, and `citations`:

- `evidence`: factual statement based on cited source text; at least one citation required.
- `analysis_result`: actual result supported by at least one source with role data/results; citations required.
- `proposal`: an explicitly proposed interpretation, design or action.
- `researcher_input`: what the researcher actually supplied; never fabricate attribution.
- `unresolved`: missing or insufficient evidence. Prevents human acceptance until revised.

Multiple blocks can belong to the same section. Additional section keys are allowed. The initial manuscript contract follows a conventional seven-section structure; other article structures can use extra sections but must retain the required keys and describe applicability. Reviewed submission checks currently expect a results block anchored to project data/results, including real outputs of an evidence synthesis. A narrative/conceptual paper without such results can be drafted/exported as draft, but is not automatically supported by that reviewed-export check.

Use `dependency_ids` for every earlier artifact relied on. These become version references; revising the source artifact makes dependents stale. Importing a new source also invalidates old contexts conservatively. Revise stale dependencies before downstream artifacts, then review again. `read_artifact` reads current status or an explicitly historical version. A client's prose claiming acceptance cannot change a review state.

Manuscripts use the saved artifact's full `id` as their canonical identifier. First save returns `result.id`; use that same value as `artifact_id` when revising/reading and as `manuscript_id` when preparing/exporting a submission. Revisions keep the ID and increase `version`. The review page displays the ID, and exported Markdown prints `Manuscript ID`. `export_manuscript` also returns `manuscript_id` and `manuscript_version`; `evidence.json` retains them as `manuscript.id` and `manuscript.version`. An export directory identifies an export instance, not a new manuscript. See [identity contract and regression](manuscript-identity.md).

Only the separate local review UI accepts/rejects/marks unresolved; there is no review tool. Reviewers inspect original source text, limitations and dependency versions. Accepted artifacts with a changed dependency require review again. Current MCP tests never operate the human review UI; native researcher acceptance remains a separate manual check.

`export_manuscript(manuscript_id, expected_revision, mode="draft")` writes a Markdown manuscript, source bibliography, evidence JSON and hash manifest. `mode="reviewed"` additionally requires `submission_id` and `guideline_source_id`, an accepted current manuscript and submission artifact, an explicit dependency on the manuscript version, citation of the selected guidelines, and no mechanical blockers. It also exports cover letter, disclosure and checklist. Unknown bibliography fields remain explicitly unknown rather than fabricated. Formatting is generic Markdown, not guaranteed journal typesetting.

`backup_workspace` creates a consistent JSON journal/original-source/actual-Qdrant-vector snapshot with a SHA-256 manifest. `restore_workspace` restores a snapshot under backups only into an empty workspace and dedicated empty Qdrant collection, via a durable job. Source/manuscript identities are retained and the current revision advances. Neither export nor backup sends files elsewhere.
