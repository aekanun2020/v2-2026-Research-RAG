# MCP workspace cleanup — 0.2.3

User request, 2026-09-20: delete all RAG workspace data except the original papers in inbox. Version 0.2.3 adds the permanent scope `all_except_inbox` to the existing two MCP tools. This capability does not establish better retrieval quality.

## Tools and exact scope

`preview_workspace_cleanup(scope)` is read-only. It returns the workspace revision, record counts, source/artifact IDs, preserved data, blockers and `plan_hash`. It does not write a plan, create a backup or authorize deletion.

`cleanup_workspace(scope, plan_hash, expected_revision, idempotency_key)` executes the corresponding explicitly authorized scope. There is no default scope or arbitrary path parameter.

| Scope | Records removed from the live SQLite database | Records retained |
|---|---|---|
| `search_index` | All embeddings, including those for preserved chunk sets | Extracted text, document/source identities, chunks, project, artifacts, reviews and searches |
| `documents` | All documents/source records, extracted pages, chunks, chunk metadata, chunk sets and embeddings | Project and search records; blocked if any artifact or historical artifact version exists |
| `workspace` | All of the above, project fields, artifacts, versions including reviews, searches and prior events | Monotonically increasing revision, cleanup audit event/receipts, retired request-key tombstones |

The three database-only scopes above preserve files in `inbox/`, imported original files in `sources/`, exports, existing backups, authentication tokens and model assets. Source-file counts refer to registered sources; unregistered files are also untouched. This is database cleanup, **not deletion of PDF files or secure erasure**. The original Desktop paper directory is never modified.

For those three database-only scopes, the implementation creates a SQLite/source backup with SHA-256 manifest. A SQLite write reservation holds the selected revision stable while the backup connection snapshots the committed database and source files. Deletes, retirement of old mutation receipts, the revision increment and the cleanup receipt/event commit together. Backup failure stops cleanup without deleting live records. A failed transaction can leave an unused backup directory; that does not mean cleanup succeeded.

The matching plan hash and revision prevent applying an outdated or different scope. Only execute a scope already authorized by the researcher; an index-rebuild request is not permission to clear manuscripts/history. Cleanup does not impersonate a human reviewer.

Exact retries return the same cleanup receipt without making another backup or repeating deletes. Earlier non-cleanup mutation keys become tombstones: retrying a pre-cleanup import/rebuild raises `Idempotency key retired by cleanup` rather than reporting a removed result as present. For new work, read current status and use new keys. Cleanup receipts remain replayable and retain audit pointers to older backups.

After `search_index`, semantic/hybrid retrieval fails explicitly until `rebuild_search_index`; lexical retrieval can still use preserved chunks. After `documents` or `workspace`, import again from inbox. Reimport creates new document/chunk-set/chunk IDs; identical bytes retain their SHA-256 source ID. To recover the former identities/history, restore the backup into a new directory with the existing restore CLI. There is no MCP restore tool yet.

## Permanent scope: all_except_inbox

`preview_workspace_cleanup(scope="all_except_inbox")` inventories every data file outside inbox, including unregistered files, source copies, exports, backups and import logs. The plan binds filenames, sizes and SHA-256 hashes, all database deletion counts, the workspace revision, and an aggregate hash of every inbox filename and its file hash. Symbolic links, special files and nested mounts are rejected. The caller cannot supply an arbitrary deletion path.

`cleanup_workspace` with this scope permanently removes all research records, project fields, historical versions, reviews, searches, events and old request receipts; it removes every data file outside inbox. **No new backup is created.** All inbox file bytes remain. The server bearer token, runtime SQLite database/schema, increasing revision and one minimal operational cleanup receipt remain so the server can continue operating and exact retries remain inert. Empty sources, exports and backups directories remain available for future use. Application code, configuration, model assets and development evidence outside the data workspace are not targets. The Desktop original-paper directory is never touched.

Database deletion and a durable pending-cleanup job commit first; filesystem deletion follows. These are not one atomic transaction. A filesystem failure returns `status: incomplete`, `database_cleared: true`, and exact `resume_with` arguments. New writes, backups, exports and previews are blocked while a job is pending. `workspace_status.pending_cleanup` also supplies the original arguments. The job survives service restart. Resolve the reported filesystem conflict and retry those exact arguments.

Only `status: completed` establishes that target files were removed and every inbox file hash remained unchanged. A completed retry returns the same receipt without deleting later imports. Old mutation keys are deleted in this scope, unlike the tombstones retained by the three database-only scopes. Use new keys for new research work. Filesystem deletion is not a forensic secure-erasure guarantee.

## Version 0.2.3 regression evidence

The original real HTTP call rejected this scope because the public schema allowed only the three database-only scopes: [observed failure](purge-before-2026-09-20.txt). The causal repair adds the permanent scope, its file inventory and resumable deletion job. The same actual HTTP case then passed: [focused result](purge-after-focused-2026-09-20.txt). It verifies removal of real imported PDF copies, exports, backups and import logs, unchanged inbox hashes and bearer token, and inert retry after a new import.

[Related cases](purge-related-2026-09-20.txt) verify changed-file plans and symbolic links are rejected before deletion, and a real directory-permission failure reports incomplete cleanup, blocks new writes, and resumes successfully. These tests use the real MCP server, SQLite, bundled PDF and CPU embeddings, without mocked services or filesystems.

- [Implementation](../src/research_rag_mcp/purge.py) and [real HTTP tests](https://github.com/aekanun2020/2026-Research-RAG/blob/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/tests/test_purge.py)
- [Full source suite](purge-suite-2026-09-20.txt), [installed-container tests](purge-container-tests-2026-09-20.txt), and [build log](purge-build-2026-09-20.txt)
- [Actual schema migration](purge-migration-2026-09-20.json) and [installed source hashes](purge-image-source-hashes-2026-09-20.json)

## Historical 0.2.2 evidence and regression

The original real-HTTP test failed because `tools/list` lacked both cleanup tools: [before implementation](cleanup-before-http-2026-09-20.txt). The first attempt was independently blocked by sandbox localhost restrictions: [sandbox output](cleanup-before-2026-09-20.txt).

An invocation against the pre-existing non-editable installation still loaded 0.2.1: [old-install output](cleanup-after-focused-2026-09-20.txt). Source tests explicitly use `PYTHONPATH=src` to run the real updated server, with real dependencies and files. The original case then passed: [source regression](cleanup-after-source-2026-09-20.txt).

Related checks cover document cleanup/reimport, stale/invalid plans, artifact-history blockers, workspace cleanup/restore, and a real filesystem failure preventing backup creation. The first related run found missing project initialization in the test setup: [related output](cleanup-related-2026-09-20.txt). Adding the required real `start_project` call made that case pass: [focused rerun](cleanup-workspace-after-2026-09-20.txt).

- [Real HTTP tests](https://github.com/aekanun2020/2026-Research-RAG/blob/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/tests/test_cleanup.py) and [implementation](../src/research_rag_mcp/cleanup.py)
- [Full source suite](cleanup-suite-2026-09-20.txt)
- [Installed-container cleanup tests](cleanup-container-tests-2026-09-20.txt)
- [Image build log](cleanup-build-2026-09-20.txt)
- [Installed-image source hashes](cleanup-image-source-hashes-2026-09-20.json): all 15 packaged Python/JSON files match the tested source.
- [Validation status](validation.md)

Destructive tests use temporary workspaces, not the user's 10-paper corpus. No external model judge, fake server or protocol substitute is used.

## Executed production cleanup

The explicitly requested `all_except_inbox` scope completed on 2026-09-20 through the real MCP Streamable HTTP tool using the official SDK. See [the exact tool arguments and receipt](purge-execution-2026-09-20.json), [read-only before preview](purge-runtime-before-2026-09-20.json), [native after-status](purge-native-after-2026-09-20.json), and [deployment record](container-deployment.md). The result is revision 11, zero research sources/chunks/embeddings, zero target data files, and 221 unchanged inbox files. All 27 non-inbox data files were deleted, including old backups; no new backup was created. The native task catalog itself remained stale at 31 tools, so the execution record explicitly identifies the official-SDK MCP call rather than claiming a native call.

## Retrieval baseline remains separate

[Preserved 10-paper Thai retrieval baseline](thai-retrieval-baseline-10-papers-2026-09-20.json) contains the actual 12 queries, 36 passages, exact-span checks, document catalog and Codex's judgments from the preceding evaluation. This is historical output, not a new assessment or a post-fix result: 6/10 topical queries had a directly relevant first hit, 7/10 had one in the top three, and all 36 citations matched extracted text. Both out-of-topic controls returned irrelevant passages. Cleanup alone does not fix these failures.
