# Selected RAG upstream

User-selected source: [fixed-2026-rag-mcp-server-streamablehttp](https://github.com/aekanun2020/fixed-2026-rag-mcp-server-streamablehttp/tree/5e5373a7a0919201b44f5aa78edad069a09974db).

The [pre-import manifest](upstream-manifest.json) pins every upstream file and identifies imported Python files. [Original README](UPSTREAM-README.md) preserves its MIT declaration and reference to its earlier repository. This revision has no standalone LICENSE/NOTICE or copyright notice; none has been fabricated. Dependencies retain their own licenses, recorded separately.

The imported `pyragdoc` code supplies Qdrant storage, Ollama embeddings, Thai lexical retrieval and RRF. Local changes and integration are recorded in Git after the separate source-import commit. This is adaptation of the explicitly selected upstream, not an independently originated implementation of these components.
