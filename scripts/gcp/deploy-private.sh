#!/bin/bash
set -euo pipefail
test -f /srv/research-rag/bootstrap-completed
mountpoint -q /srv/research-rag
test "$(docker info --format '{{.DockerRootDir}}')" = /srv/research-rag/docker
source_sha=dc36545165f38481a07e15285d9293faa891697a
release=/srv/research-rag/deploy/source-$source_sha
test ! -e "$release"
test "$(sha256sum /home/thaimcpagent_gmail_com/research-rag-source.tar.gz | cut -d ' ' -f1)" = b6851caada264b8105e89ba2c208125dbcec48b88d13634feb5f71e820271ef8
mkdir -p "$release"
tar -xzf /home/thaimcpagent_gmail_com/research-rag-source.tar.gz -C "$release"
cd "$release"
cat > /srv/research-rag/deploy/runtime.env <<'EOF'
AGENTS_UID=1000
AGENTS_GID=1000
AGENTS_DATA_DIR=/srv/research-rag/app-data
RAG_PUBLIC_ORIGIN=
EOF
chmod 600 /srv/research-rag/deploy/runtime.env
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d qdrant ollama
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env exec -T --interactive=false ollama ollama pull nomic-embed-text:latest
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env build mcp
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d --wait --wait-timeout 180 mcp review
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env ps --format json
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env exec -T --interactive=false ollama ollama list
date --iso-8601=seconds > /srv/research-rag/private-deployment-completed
