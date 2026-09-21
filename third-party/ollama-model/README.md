# Pinned local Ollama embedding model

- Model: `nomic-embed-text:latest`, 768 dimensions, CPU options `num_gpu=0`, `num_thread=2`.
- Manifest digest: `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`. [Exact installed manifest](manifest.json).
- Model layer SHA-256: `970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6`.
- [Original Apache-2.0 license blob](LICENSE), SHA-256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`, copied byte-for-byte from the installed registry model. No weights or tokenizer bytes are modified.
- [Official Ollama model](https://ollama.com/library/nomic-embed-text) and [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5). Weights are fetched by Ollama, not redistributed in this Git repository.

This is the selected repository's original model. The integration currently preserves its no-prefix embedding path for the controlled baseline. Its English-model limitation caused the [Thai quality test to fail](../../docs/qdrant-migration.md); neither Thai word segmentation nor Qdrant makes this model multilingual. Model and task-prefix changes require a new fingerprint and reindex, never silent reuse of incompatible vectors.
