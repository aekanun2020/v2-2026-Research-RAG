FROM ghcr.io/astral-sh/uv:0.12.17@sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc AS uv
FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS embedding_model
WORKDIR /download
COPY scripts/download_model.py ./download_model.py
COPY src/research_rag_mcp/model_manifest.json ./model_manifest.json
RUN python download_model.py /models/multilingual-e5-base --manifest /download/model_manifest.json

FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS reranking_model
WORKDIR /download
COPY scripts/download_reranker.py ./download_reranker.py
COPY src/research_rag_mcp/reranker_manifest.json ./reranker_manifest.json
RUN python download_reranker.py /models/bge-reranker-v2-m3-ONNX --manifest /download/reranker_manifest.json

FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 RESEARCH_RAG_MODEL_DIR=/models/multilingual-e5-base RESEARCH_RAG_RERANKER_DIR=/models/bge-reranker-v2-m3-ONNX
WORKDIR /app
RUN groupadd --gid 1000 research && useradd --uid 1000 --gid research --no-create-home research \
    && mkdir /data && chown research:research /data
COPY --from=build /app/.venv /app/.venv
COPY --from=embedding_model /models /models
COPY --from=reranking_model /models /models
COPY scripts/smoke_http.py /app/scripts/smoke_http.py
COPY third-party /app/third-party
USER research
EXPOSE 8776 8777
ENTRYPOINT ["research-rag", "--workspace", "/data"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8776"]
