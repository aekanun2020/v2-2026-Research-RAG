# BGE reranker provenance

Original model: [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3/tree/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e). The inspected [model card](original-README.md), [configuration](original-config.json), [tokenizer configuration](original-tokenizer_config.json) and [metadata](original-metadata.json) were recorded before integration. The original model card declares Apache-2.0; [license text](LICENSE-2.0.txt) is preserved from the Apache Software Foundation.

Runtime assets are obtained directly from their conversion publisher, [onnx-community/bge-reranker-v2-m3-ONNX](https://huggingface.co/onnx-community/bge-reranker-v2-m3-ONNX/tree/6f5ff65298512715a1e669753bc754d2bc8f367b). Its [card](onnx-README.md) names the original BAAI model. [Metadata](onnx-metadata.json), [configuration](onnx-config.json), [tokenizer configuration](onnx-tokenizer_config.json) and [manifest of asset hashes](manifest.json) identify the exact consumed files and revision. The converter does not pin the original weight commit; the inspected original revision is not claimed to be the conversion input. These are third-party ONNX assets, not a BAAI ONNX release.

The int8 model and tokenizer are consumed unchanged. No original/converter Python code is copied or executed. Our [runtime](../../src/research_rag_mcp/reranking.py) uses ONNX Runtime on CPU, verifies every asset hash and performs no external inference. The [downloader](../../scripts/download_reranker.py) pins the repository revision and fails on hash mismatch. Reranking orders candidates; Codex separately assesses relevance and evidence.

Integration is uncommitted development; no integration commit has been assigned. Original artifacts remain verbatim; our code is separate in Git.
