# Dependencies and provenance

For the Docker deployment, see [pinned base images, build tool and original notices](container/README.md).

The eight-stage research workflow was authored for this project. The Qdrant migration now adapts application code from the [explicitly selected RAG upstream](reference-rag/README.md), with hashes and license declaration captured before integration. The sibling `tts_research` package is not a dependency.

Original direct distributions (additional current dependencies are listed in the installed inventory below):

| Distribution | Version | Original upstream | License |
|---|---|---|---|
| mcp | 2.2.0 | [Official Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v2.2.0) | MIT |
| pypdf | 6.18.1 | [py-pdf](https://github.com/py-pdf/pypdf/tree/6.18.1) | BSD-3-Clause |
| uvicorn | 0.52.4 | [Encode](https://github.com/encode/uvicorn/tree/0.52.4) | BSD-3-Clause |

[Installed inventory](dependencies.json) records exact versions, upstream metadata, source-file hashes and captured copyright/license notices, including transitive dependencies. The inventory is captured by the [reproducible script](../scripts/capture_dependencies.py). Packages are installed unchanged; no vendor import commit or local upstream patch applies. Registry archive URLs and hashes are pinned in [uv.lock](../uv.lock). The application has no GPU dependency and makes no external model requests. SQLite is not a runtime backend; Python sqlite3 is imported only inside the explicitly invoked read-only legacy migration. The original application source has no selected distribution license yet.

Protocol and service references (documentation only): [MCP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http), [SDK](https://py.sdk.modelcontextprotocol.io/), [Crossref API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/). Crossref metadata retrieval does not confer rights to download or redistribute publisher full text.

## Current local embedding runtime

- [Pinned Ollama model, exact manifest and license](ollama-model/README.md)
- [Linux inventory 0.3.0](dependencies.json) · [macOS inventory 0.3.0](dependencies-macos-0.3.0.json)
- PyMuPDF 1.28.2 is AGPL-3.0-or-later or commercially licensed; its original notices are included. This project has not selected a separate application distribution license. PyThaiNLP uses Apache-2.0; portalocker uses BSD-3-Clause. Do not describe all dependencies as MIT.

## Historical embedding runtime

- [Original model provenance, pinned revisions/hashes and notices](embedding-model/README.md)
- [Pre-embedding dependency inventory](dependencies-0.1.0.json) — historical; the current inventory includes CPU embedding dependencies.
- [macOS development dependency inventory 0.2.0](dependencies-macos-0.2.0.json) — the main inventory now records the actual Linux container.

## Historical CPU reranker (not loaded by 0.3.0)

- [BGE model and ONNX conversion provenance, hashes and notices](bge-reranker-model/README.md) — active in version 0.2.4; no new Python distribution is added.
- [Rejected GTE experiment provenance](reranker-model/README.md) — retained as history; its weights are not bundled in the runtime.
