# Standalone repository publication

Prepared at 2026-09-20T23:00:15+07:00 for the user-confirmed private repository [aekanun2020/2026-Research-RAG](https://github.com/aekanun2020/2026-Research-RAG).

## Scope and provenance

The user confirmed publication of the RAG code, documentation and test results, while retaining papers, databases and credentials on the local machine. This is a new repository with an initial snapshot, not a rewritten or imported history of the parent project.

The source is the current working-tree content of `2026-TTS-AI/codex-research-rag-mcp`, version **0.2.4**. The parent repository was [2026-TTS-AI](https://github.com/aekanun2020/2026-TTS-AI), HEAD `acf9dad00b34779eb6e8f0bb79dfb816e0e8ca95`. That HEAD is context only: the RAG files were uncommitted there and this snapshot includes their latest unstaged changes. The [file manifest](repository-export-manifest.json) records their actual SHA-256 values rather than claiming the parent commit contains them.

Included: application source, container configuration, dependency lockfile, scripts, test code, documentation, historical test responses, dependency/model provenance and license notices. Historical test responses include retrieved excerpts, citations, filenames and source IDs. They are retained as test evidence; they are not a restored research workspace. Third-party notices and model metadata remain byte-for-byte unchanged.

Excluded: all source-paper PDFs (including `tests/evidence/brms.pdf`), `.data`, `.env`, bearer/review credentials, databases, inbox, backups, manuscript exports, `.models`, model weights, virtual environments and parent-project files. `.env.example` contains example settings only. See the [real test evidence instructions](../tests/evidence/README.md) to prepare the excluded fixture locally.

## Changes made for publication

- Added the repository URL and standalone clone instructions to the [root README](../README.md), including the distinction between a new checkout and the already populated local installation.
- Extended [.gitignore](../.gitignore) for local research files, model weights and credentials.
- Updated [test evidence navigation](../tests/evidence/README.md) to point to the original publisher instead of a PDF absent from Git.
- Added this record and its [per-file manifest](repository-export-manifest.json).

Application source, tests, dependency versions and container behavior are unchanged. The published test reports are **historical results**, assessed by Codex where indicated; publication does not rerun or relabel them as new model-quality evidence. The [retrieval quality report](retrieval-quality-2026-09-20.md) retains its failures and limitations.

## Existing local installation

The existing containers continue to use `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-TTS-AI/codex-research-rag-mcp` and its `.data` bind mount. This publication does not restart containers, move the 10 imported papers or the 221-file inbox, change MCP configuration, or rotate credentials.

The independent checkout is `/Users/grizzlymacbookpro/Documents/ChatGPT/2026-Research-RAG`. A fresh clone starts without research data. Both locations contain a Compose definition named `codex-research-rag`; do not start the new checkout over an existing installation without explicitly planning the workspace migration. Continue operating the current service from its existing directory.

## Publication verification

Before the initial commit, verify all exported file hashes, excluded file types and credentials, relative links in the project's own documentation, and preservation of the source files and parent index. These checks verify repository contents, not semantic relevance. All new functional checks, if needed, must use the real MCP endpoint; no direct store calls or substitute services are part of this publication.

### Observed pre-commit results

- 275 files selected, with 273 copied source files and two publication documents; the original test PDF is excluded.
- SHA-256 verified for all 274 original project files (including the local-only PDF) and all 273 copied files. All application source, test code, container configuration and third-party notices match the source bytes.
- All 317 relative links checked in the project's own Markdown resolve inside the exported repository. Python syntax checked for 31 files. All 91 JSON artifacts were parsed; the existing `purge-containers-runtime-2026-09-20.json` contains two JSON Lines records and is preserved unchanged.
- No excluded paper/database/model/credential paths or PDF/SQLite file signatures are present. Exact active MCP bearer bytes and common credential patterns were checked without printing values; no matches were found. This is a content check, not a universal security guarantee.
- Parent repository index, root README and all source project file hashes are unchanged.
- A fresh read-only call to the connected MCP `workspace_status({})` succeeded: revision 24, 10 sources, 221 inbox files, and the search index ready. No ingestion, deletion, reindexing, semantic evaluation or container restart was performed for publication.
