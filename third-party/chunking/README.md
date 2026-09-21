# Chunking dependencies and provenance

The application calls unmodified upstream parser APIs. It does not vendor a rewritten substitute for LlamaIndex. The integration and exact-offset mapping in [chunking.py](../../src/research_rag_mcp/chunking.py) were authored for this project's source-preservation requirements.

- **LlamaIndex core 0.14.24**, [official upstream](https://github.com/run-llama/llama_index), installed from PyPI. [Archive URL/hash and parser file hashes captured before integration](llamaindex-provenance.json), [original MIT license](LLAMAINDEX-LICENSE).
- **Tokenizers 0.23.2**, [official upstream tag](https://github.com/huggingface/tokenizers/tree/v0.23.2). The installed wheel did not include a LICENSE file, so the [original license](TOKENIZERS-LICENSE) was obtained directly from that tag; [URL and hash](tokenizers-license-provenance.json).
- **Nomic tokenizer**, [official model repository](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5/tree/e9b6763023c676ca8431644204f50c2b100d9aab). [Exact commit and original asset hashes](tokenizer-provenance.json). Only the unchanged `tokenizer.json` is bundled as [the local tokenizer asset](../../src/research_rag_mcp/assets/nomic-tokenizer.json); no weights are added. The model card declares Apache-2.0; [the original model license from its Ollama distribution](../ollama-model/LICENSE) is retained. The HF revision did not contain a separate LICENSE/NOTICE file.
- **PyThaiNLP 5.3.7** supplies CRF sentence segmentation and its packaged model; **python-crfsuite 0.9.12** executes it on CPU. English Punkt data comes from the pinned LlamaIndex wheel. [Versions, original notices and language-asset hashes](dependencies.json).

Package archive hashes and all transitive versions are pinned in [uv.lock](../../uv.lock). LlamaIndex core brings optional SQL/SQLite-related libraries as transitive dependencies; this application does not select their storage backends. Research state continues to use the JSON journal and Qdrant, with no SQLite database created for chunking. No GPU resources, external model API calls or automatic model substitution are used.

[Behavior, separate containers and MCP results](../../docs/academic-chunking.md).

[Actual Linux image dependency inventory and captured notices](linux/dependencies.json) records all 100 installed distributions. These files were inspected in the new container; no research workspace was modified to collect them.
