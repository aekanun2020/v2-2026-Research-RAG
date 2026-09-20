# Manuscript identity

Requirement recorded on 2026-09-20: user-authored/generated manuscripts must also have an identifier.

The existing canonical manuscript identifier is the saved artifact's `id` (a full UUID hex value). It is allocated by `save_artifact(stage="manuscript")` at first persistence. Revising that manuscript supplies its `artifact_id` and retains the same ID while incrementing `version`. A new manuscript receives a new ID even when the title matches. A renamed title does not identify a new manuscript.

Use that same ID for `read_artifact(artifact_id=...)`, `prepare_submission(manuscript_id=...)`, `export_manuscript(manuscript_id=...)`, and versioned dependencies. A particular revision is identified by the pair `(id, version)`. Workspace revision is the revision of the whole workspace, not the manuscript version. No new alias scheme or database migration is needed.

`draft_manuscript` only prepares context; a manuscript becomes a persisted, identified object when `save_artifact` succeeds. Export-directory UUIDs identify export instances, not manuscripts. Imported source-file hashes identify evidence files, not manuscripts.

## Reproduced gap and correction

Before changing application code, the actual Streamable HTTP test against the existing Linux container saved a manuscript with citations to the real brms PDF and exported it. The Markdown contained the title and version but no manuscript ID. The test failed in **2.572 seconds**, with `AssertionError: 'Manuscript ID: c176fa70fb344b2bb4769fb7668465c3' not found`. See [preserved before output](manuscript-id-before-2026-09-20.txt).

The cause is in `export_manuscript`: the Markdown metadata line included artifact version and workspace revision but omitted the artifact ID. The export response also omitted the ID/version pair. The review renderer used the ID only as an HTML anchor/form field, leaving it absent from visible manuscript metadata.

The change surfaces the existing identity in the Markdown export, the export tool response (`manuscript_id`, `manuscript_version`), and the visible review page. `evidence.json` already preserves it under `manuscript.id` and `manuscript.version`. Existing stored IDs, history and citations remain canonical.

The integration regression uses the real MCP server and source PDF in a temporary workspace. It checks first save, same-key retry, renamed revision, historical read, separate manuscript identity, review HTTP GET, both export revisions and manifest hashes, and backup/restore. Test text is explicitly an unresolved protocol record, not scientific findings or researcher acceptance. No external model is called.

## Verification

Codex assessed this change using deterministic checks of the real implementation; no LLM judge or external model was used.

- [Original failing case after correction](manuscript-id-after-2026-09-20.txt): **1 test passed in 3.131 seconds**, including the real review HTTP page, stable ID on revision, distinct IDs for different manuscripts, and actual backup/restore.
- [Related cases](manuscript-id-related-2026-09-20.txt): **2 tests passed in 4.649 seconds**, covering reviewed export through the separate review application and the eight-stage Streamable HTTP workflow with reconnect/resume.
- [Full Linux container suite](manuscript-id-suite-2026-09-20.txt): **21 tests passed in 35.729 seconds**, including live Crossref. No tests were skipped. The production workspace was not used for test artifacts.
- [Deployment verification](manuscript-id-runtime-2026-09-20.json), 2026-09-20 10:25 ICT: both project containers healthy on image `sha256:2eb281b12c84a4009d2e2080fdb66203e0d0591a5e6cb089fccf29e10a2604c5`; all ten installed source modules match the current source. The production database's logical dump and bearer token match their pre-update fingerprints. All 17 unrelated local containers retain their IDs/names/states.
- [Final endpoint smoke](manuscript-id-http-smoke-2026-09-20.json): authenticated initialize, 19-tool listing and `workspace_status` at `http://127.0.0.1:8776/mcp`. Review HTTP GET returned 200; no real review decision was submitted. The review service's capability URL rotated on restart and can be retrieved with `docker compose logs --tail 5 review`.

The original ID allocation and database schema were already sufficient; this change exposes that canonical identity consistently. No claims are made about semantic search, document/chunk version management, or native Claude Desktop/Windows acceptance from these checks.
