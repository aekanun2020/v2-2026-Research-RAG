# Current integration verification

Version 0.5.0 and 0.4.0 behavioral tests call the actual Streamable HTTP MCP service, Qdrant and CPU Ollama. No mock, direct Store test harness, external model judge, or human-review impersonation is used.

- [0.5.0 workspace/download/prompt regression](../scripts/verify_agent_ingestion_mcp.py) · [recorded failures and results](../docs/agent-ingestion/README.md). Each run creates explicitly named validation workspaces; public PDFs are downloaded and imported only through MCP. No original user collection is imported by these tests.
- [Public endpoint protocol and Host/Origin checks](../scripts/verify_public_mcp.py) · [actual ngrok before/after evidence](../docs/agent-ingestion/ngrok.md). Read-only MCP calls, no authentication header, no substitute server.

- [Academic chunking baseline capture](../scripts/capture_chunking_baseline_mcp.py) · [original-case rerun](../scripts/verify_academic_chunking_mcp.py) · [chunking evidence](../docs/academic-chunking.md)
- [Read-only concurrent and Thai retrieval checks](../scripts/verify_qdrant_retrieval_mcp.py)
- [Full workflow/import/chunks/manuscript/cleanup/restore checks](../scripts/verify_qdrant_workflow_mcp.py) — dedicated disposable workspace and Qdrant collection only. This script performs destructive cleanup of its test workspace. Never point it at production.
- [Read-only MCP smoke check](../scripts/smoke_http.py)
- [One-time real legacy migration verification](../scripts/verify_qdrant_migration_mcp.py)
- [Real original evidence provenance](evidence/README.md)
- [Recorded before/after evidence and limitations](../docs/qdrant-migration.md)

The pre-migration SQLite/ONNX tests are historical and require their own 0.2.4 source/dependencies. They are preserved in [the canonical pre-migration commit](https://github.com/aekanun2020/2026-Research-RAG/tree/14b858f77acddd06ff6e6dd83ceba99e848b6fd6/tests), not presented as passing tests for the new runtime.
