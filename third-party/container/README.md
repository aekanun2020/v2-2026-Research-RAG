# Container provenance — 0.3.0

The actual Linux arm64 runtime was built and exercised through MCP. No native Windows or amd64 run is claimed. Services use CPU only; Qdrant/Ollama expose no host ports.

| Component | Version / immutable image | Upstream |
|---|---|---|
| Python | 3.11.16, `python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9` | [Official Python image](https://hub.docker.com/_/python) |
| Qdrant | 1.18.3, `qdrant/qdrant@sha256:0bd98fa7977f1e75694779359ca4e212822e5a71334e28421182f72f209d5286` | [Qdrant tag](https://github.com/qdrant/qdrant/tree/v1.18.3) |
| Ollama | 0.32.9, `ollama/ollama@sha256:1685741456770df6e3cceb2a945a5f75e020f658d1701509668d6f4688f1dd3f` | [Ollama tag](https://github.com/ollama/ollama/tree/v0.32.9) |
| uv build package | 0.7.8, builder only | [uv tag](https://github.com/astral-sh/uv/tree/0.7.8) |

[Exact tagged notices and hashes](v0.3.0/notices.json): [Qdrant Apache-2.0](v0.3.0/qdrant-LICENSE), [Ollama MIT](v0.3.0/ollama-LICENSE), [uv MIT](v0.3.0/uv-LICENSE-MIT), [uv Apache-2.0](v0.3.0/uv-LICENSE-APACHE). Official runtime images retain their original component notices. Python's standard-library license remains in the image; base-image components are not all MIT.

[Linux installed dependency inventory](../dependencies.json), [macOS development inventory](../dependencies-macos-0.3.0.json), [Ollama model and license](../ollama-model/README.md), [historical 0.2.4 container provenance](HISTORICAL-0.2.4.md). [Dockerfile](../../Dockerfile) and [Compose](../../compose.yaml) are the canonical build/deployment definitions. No credentials or research corpus is included in image layers.
