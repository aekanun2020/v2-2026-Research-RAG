# Validation — current checks and historical results

Assessor: Codex. Implementation checks, 2026-09-20. No external LLM judge, external inference, fake server, proxy, or simulated service. Versions 0.2.0 through 0.2.3 use the real local CPU embedding model. Native Claude Desktop and Windows are not assessed by the local protocol tests.

## Version 0.2.4 retrieval quality

All ingestion and functional testing for this change used actual MCP tools over Streamable HTTP. Code/model packaging and container administration used the development tools explicitly authorized by the user. No direct Store/model inference test substituted for MCP. The earlier mixed direct/unit suites below are historical and were not rerun as this change's acceptance evidence.

[Codex's report](retrieval-quality-2026-09-20.md) separates relevance from [deterministic exact-span checks](quality-final-candidates-2026-09-20.json). Original topical rank-1 recovery improves 6/10 → 9/10 and top-3 recovery 7/10 → 10/10; 60/60 extracted-page spans match. The untouched final topical subset is 3/4, with H06 unresolved. All four negative controls still return irrelevant candidates. The attempted score gate failed held-out H02 and is disabled by default; it is not counted as a successful abstention feature.

[Semantic/hybrid comparison](quality-mode-comparison-2026-09-20.json) checks identical ordered IDs/text/spans on all 20 queries. The full corpus runs explicitly set min_document_score=0 on the installed candidate; [the final-image no-override H02 check](quality-final-default-2026-09-20.json) verifies that this is the final default. [Final-image MCP contract checks](quality-final-contract-2026-09-20.json) cover original-ranking reproducibility, source/role filters, chunk/context identity, exact citations, explicit cutoffs, invalid inputs and workspace preservation.

The [semantic/chunk HTTP lifecycle case](quality-container-workflow-before-2026-09-20.txt) passed against real imports in an isolated container. The eight-stage case initially timed out during import due to its 30-second MCP client deadline; aligning only that deadline to its existing 300-second HTTP read budget made the [exact case pass](quality-container-workflow-after-2026-09-20.txt), 1 test in 61.706 seconds. Both integration cases used the real installed image with external networking disabled. There is no skipped import, mock, replacement endpoint or external judge.

[Current MCP state](quality-runtime-after-2026-09-20.json), [source hashes](quality-final-image-source-hashes-2026-09-20.json), [data preservation](quality-state-preservation-2026-09-20.json), and [container preservation](quality-containers-after-2026-09-20.json) support deployment claims. These checks do not certify answers, journal readiness, all 221 papers, or native Claude Desktop behavior.

## Version 0.2.3 permanent cleanup

The [permanent cleanup contract](workspace-cleanup.md) implements the explicitly requested deletion of all RAG workspace research data except inbox originals. The [source suite](purge-suite-2026-09-20.txt) ran **39 tests in 101.402 seconds: 38 passed, one opt-in Crossref test skipped**. The [installed Linux container suite](purge-container-tests-2026-09-20.txt) passed **all 7 cleanup cases in 78.933 seconds**, using real Streamable HTTP tools, real PDF ingestion, CPU embeddings, database state and filesystem permission failures with external networking disabled.

The [original failing scope call](purge-before-2026-09-20.txt), [focused successful rerun](purge-after-focused-2026-09-20.txt) and [related cases](purge-related-2026-09-20.txt) preserve the before/after evidence. [Migration verification](purge-migration-2026-09-20.json) restored the actual schema-3 production backup read-only into a temporary container workspace and verified every pre-existing database row was identical after schema-4 migration. [Image hashes](purge-image-source-hashes-2026-09-20.json) verify the installed application matches the tested source.

[Production tool execution](purge-execution-2026-09-20.json) completed the authorized purge and verified every inbox hash; [native after-status](purge-native-after-2026-09-20.json) confirms an empty corpus at revision 11 with all 221 inbox originals. These checks establish cleanup behavior, not improved Thai retrieval relevance. The original 10-paper baseline remains historical.

## Historical version 0.2.2 cleanup

The [cleanup contract](workspace-cleanup.md) records the missing-tool failure and focused repair. The [complete source suite](cleanup-suite-2026-09-20.txt) ran **36 tests in 91.972 seconds: 35 passed, one opt-in live Crossref test skipped**. The [installed-container suite](cleanup-container-tests-2026-09-20.txt) passed all **4 cleanup tests in 42.730 seconds** using real source files, CPU embeddings, SQLite and Streamable HTTP, without external networking.

Covered behavior: read-only preview, embedding deletion/rebuild with stable citations and ranking, backup/restore, duplicate cleanup retries, document removal/reimport, retired import keys, stale/invalid plans, artifact/history blockers, full database cleanup, and actual backup-filesystem failure leaving live records unchanged. The initial workspace test setup lacked the required project initialization; its failed output and corrected focused rerun are retained in the cleanup contract.

[Live 0.2.2 verification](cleanup-runtime-2026-09-20.json) confirms initialize, tools/list with 33 tools, and three read-only preview calls. [Native status and container comparison](cleanup-deployment-checks-2026-09-20.json) confirm unchanged revision 10, 10 sources, 547 indexed chunks, 221 inbox files and 17 unrelated containers. At that historical checkpoint, production cleanup had not executed and the native client catalog still lacked the two new tools.

[The preceding Thai evaluation](thai-retrieval-baseline-10-papers-2026-09-20.json) is preserved as a historical baseline. Retrieval relevance has not been changed or reassessed by this cleanup feature.

## Historical version 0.2.1 inbox preview

The [new read-only MCP tool and regression record](inbox-preview.md) close the
missing pre-import title-reading step. The original actual-HTTP test first failed
with an unknown tool, then passed with identical source bytes and page text after
preview/import. Pagination and inbox-boundary checks also pass. The [full source
suite](inbox-preview-suite-2026-09-20.txt) ran 32 cases in 75.181 seconds: 31 passed,
and the opt-in live Crossref case was skipped. Both new cases also passed against
the [installed Linux image](inbox-preview-container-tests-2026-09-20.txt) in 34.900
seconds without external networking. [Deployment evidence](inbox-preview-runtime-2026-09-20.json)
confirms two healthy 0.2.1 containers and 31 tools in the actual endpoint catalog.
The active Codex task still exposes 30 tools and needs a client catalog refresh.
The user's 221 inbox PDFs remain unimported; no production embeddings were created.

## Historical version 0.2.0 verification

[Live deployment verification](semantic-runtime-2026-09-20.json) confirms both containers healthy, 30 tools over Streamable HTTP, schema 3, preserved bearer and logical records, and all 17 other containers unchanged. Production is empty; nonempty retrieval belongs to the isolated real-source tests below.

**30 integration tests passed in 227.681 seconds** against the installed Linux arm64 image, including real HTTP/stdio, all eight stages, manuscript identity/review/export, semantic/chunk tools, exact source checks, backup/restore and live Crossref. [Full final output](semantic-final-suite-2026-09-20.txt). All 13 packaged Python/JSON source files matched local SHA-256 hashes.

- [Nine focused cases](semantic-base-focused-2026-09-20.txt) passed in **133.963 seconds** in the actual final-model image with `--network none`, including real Streamable HTTP calls to the new management/search tools, actual CPU embeddings, citation-preserving rechunking, document versions, exclusion/review flags, vector-corruption detection/rebuild, idempotency and backup/restore.
- [Migration from the real 0.1.0 image](semantic-final-migration-2026-09-20.json) preserved 77 original chunk IDs, eight checked exact citations and the old import retry response. Missing embeddings correctly raise an explicit error until rebuild; all 77 chunks then index successfully.
- [Codex's direct retrieval inspection](semantic-assessment-2026-09-20.md) and [original query result](semantic-final-query-2026-09-20.json) distinguish the recovered relevant abstract from remaining weak rankings. These integration tests are not semantic quality scores.
- [Preserved HTTP timeout failures](semantic-suite-before-timeout-2026-09-20.txt) and [targeted rerun](semantic-timeout-regression-2026-09-20.txt) record the cause and correction to the actual client configuration. No failing integration was replaced or bypassed.

Historical 0.1.0 manuscript-identity change: **21 tests passed in 35.729 seconds** in the actual Linux container, following the reproduced export-ID failure and targeted checks. See [identity contract, before/after evidence and verification](manuscript-identity.md). The 20-test results below describe the earlier baseline.

## Historical 0.1.0 installed-package result

The initial host-process deployment below has been replaced by [local Docker Compose deployment](container-deployment.md). The same installed application passed **20 tests in 32.932 seconds** in the Linux arm64 image with Python 3.12.14 and listeners bound to `0.0.0.0`, including the live Crossref check. See [container suite output](container-tests-2026-09-20.txt). Native client behavior remains unverified.

**20 tests passed in 26.155 seconds**, including the opt-in live Crossref case. [Full test output](test-results-2026-09-20.txt) has only host-specific absolute paths redacted. Command: `RESEARCH_RAG_LIVE_TESTS=1 .venv/bin/python -m unittest discover -s tests -v`, after rebuilding with `uv sync --locked --offline --no-editable --reinstall-package codex-research-rag-mcp`. No `PYTHONPATH` override was used for final verification.

Verified on macOS arm64, Python 3.12.10, MCP SDK 2.2.0:

- Actual Streamable HTTP initialize, all 19 tools with structured output schemas, calls to all eight stage tools, local ingestion, saved artifacts, and reconnect/resume across independent sessions.
- Live Crossref metadata query through that real MCP endpoint, DOI match and idempotent retry; no mock or cached test service.
- Real PDF/Thai-text retrieval, exact page/character spans, missing-evidence behavior, actual CSV calculations, literature-note matrix and source-role boundaries.
- Revision/idempotency conflicts, history retention, dependency revision and review-withdrawal invalidation, cycle rejection and source tamper rejection.
- Actual separate review HTTP application, original-source download, Origin/Host/bearer boundaries, stale review rejection and reviewed-package export with verified hashes.
- Valid backup/restore and invalid absolute manifest paths; direct stdio uses the same installed implementation.

Repository verification: 50 affected relative Markdown links resolved to tracked files/directories. Changes are confined to the new subdirectory and the parent README navigation. Runtime workspace, bearer token and virtual environment are ignored by Git. Authored files pass the staged whitespace check; verbatim upstream license notices retain their original whitespace and hashes. The installed package was compared byte-for-byte with all source modules.

[Initial host-process endpoint smoke record](http-smoke-2026-09-20.json): `http://127.0.0.1:8776/mcp`, authenticated, initialized protocol **2025-11-25**, 19 tools discovered and `workspace_status` returned revision 0. The workspace was new and empty. The SDK supports other revisions, but this record only asserts the negotiated version actually observed. This historical check used a local Python process with no startup daemon; see the container deployment record for the current runtime.

Codex also inspected two actual retrieval hits for “Bayesian multilevel Stan.” The first was the real brms article's title/abstract and directly relevant to the query. The next included a figure and repeated article heading, demonstrating that lexical rank can retrieve weak context as well. This is a new, narrow Codex inspection, not a semantic benchmark or a quality score.

Unverified: Claude Desktop behavior with generation and review across all stages, Windows/native UI acceptance, researcher learning outcomes, speed/quality against a baseline, large-corpus capacity, semantic citation entailment and full journal compliance. Stage persistence tests deliberately keep scientific content unresolved; test acceptance identities exercise protocol state transitions and do not represent a real researcher's endorsement. Reviewed export currently expects an original results block anchored to project data/results; see [article-type boundary](tools.md#drafts-review-and-export).

## Development failures and targeted corrections

1. First real PDF import in `test_real_pdf_ranked_retrieval_and_exact_spans` failed before retrieval: `sqlite3.OperationalError: table chunks has 6 columns but 7 values were supplied`. The trace identified `Store.import_document`'s INSERT with seven placeholders for six schema columns and six values. The initial store suite had 11 setup errors from this single cause. Correct only that INSERT, then rerun the original real PDF case before related cases.

   After the INSERT correction, the original real-PDF retrieval case passed (1 test); real CSV calculations, Thai retrieval and invalid-citation/import boundaries also passed (3 cases).

2. `test_dependency_review_withdrawal_invalidates_acceptance` reproduced an accepted design remaining `accepted` after its question dependency was reviewed again as `unresolved` (expected `needs_review`). The dependency checker handled rejected/revised dependencies but omitted the unresolved verdict. Extend that exact invalidation condition, then rerun withdrawal and nearby revision/cycle checks.

   The withdrawal case then passed (1 test), followed by the revision/cycle and idempotency/history cases (2 tests).

3. The first real Streamable HTTP workflow completed the eight stages, draft export and backup, but the fresh-session assertion failed because `read_artifact.structured_content` was `None`. A repeat showed the correct persisted artifact in a JSON text block. The installed SDK's `func_metadata` recognizes `dict[str, T]` for structured output, but the tools declared bare `dict`. Declare the actual JSON object return type (`dict[str, Any]`) rather than adding a protocol adapter or changing the returned content, and rerun the same HTTP case.

   The original HTTP workflow then passed, including initialize, 19-tool discovery, all eight stage calls, source import, retrieval, CSV calculation, saved artifacts, export, backup and a new-session read. Authentication/Origin/Host checks and the actual review-UI/export case passed. Direct stdio initially launched the previously installed two-file scaffold (missing `cli.py`); rebuilding the actual distribution corrected installation, and direct stdio passed without adding a shim or changing the client environment.

4. A real backup with a manifest key changed to an absolute path inside the snapshot reached `shutil.copyfile` and raised `SameFileError`, after creating part of the restore directory. Root cause: source containment was checked, but relative-path syntax was not. Validate portable relative paths before creating the destination; rerun the same restore case, then valid backup/restore.

Live Crossref through the actual MCP HTTP endpoint passed: the public brms title query (2017, limit 5) returned DOI `10.18637/jss.v080.i01`; an identical idempotent retry returned the same saved response and left one search record. No full-text reading or model generation is inferred from this.

   The invalid-manifest case passed after the correction, before destination creation. The valid backup/restore case then passed with sources, artifacts and search results preserved.

5. `test_whitespace_is_not_evidence` initially raised no error for an exact single-space span in the real paper. The citation schema checked string length and exact presence, but not non-whitespace content. Add the existing nonempty-text validation to citations and rerun that case before regular citation retrieval.

   Both the original whitespace case and the subsequent real-PDF retrieval case passed.

6. `test_literature_note_rejects_project_material_as_study` initially allowed a project README to supply a literature-note artifact. The generic save path checked citation integrity but not the note's literature-source constraint. After the separate whitespace correction is verified, require one actual literature source per note, with missing dimensions remaining explicitly unresolved. Verify rejection and a real-paper matrix row separately.

   The original project-material rejection passed, followed by the actual-paper matrix case retaining the Stan citation and unresolved population field. All fixes remained in scope and the full installed suite passed afterwards.
