#!/bin/bash
set -euo pipefail
cd /srv/research-rag/deploy/source-dc36545165f38481a07e15285d9293faa891697a
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env build mcp
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d --wait --wait-timeout 180 mcp review
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env ps --format json
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env exec -T --interactive=false ollama ollama list
date --iso-8601=seconds > /srv/research-rag/private-deployment-completed
