FROM python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9 AS builder
RUN pip install --no-cache-dir uv==0.7.8
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9 AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY scripts/smoke_http.py /app/scripts/smoke_http.py
COPY third-party /app/third-party
ENV PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["research-rag", "--workspace", "/data"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8776"]
