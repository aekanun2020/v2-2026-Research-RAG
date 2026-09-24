#!/bin/bash
set -euo pipefail
[[ "$(hostname)" == student2-research-rag ]]
mountpoint -q /srv/research-rag
source_dir=/srv/research-rag/deploy/source-dc36545165f38481a07e15285d9293faa891697a
test -f "$source_dir/compose.agents.yaml"
backup_dir=/srv/research-rag/deploy/backup-student2-20260924
test ! -e "$backup_dir"
install -d -m 700 "$backup_dir"
cp -p /srv/research-rag/edge/Caddyfile "$backup_dir/Caddyfile"
cp -p /srv/research-rag/deploy/runtime.env "$backup_dir/runtime.env"
python3 - <<'PY'
from pathlib import Path
for name in ['/srv/research-rag/edge/Caddyfile','/srv/research-rag/deploy/runtime.env']:
 p=Path(name);s=p.read_text();assert s.count('34-142-222-110.sslip.io') == 1,name
 p.write_text(s.replace('34-142-222-110.sslip.io','34-142-163-231.sslip.io'))
PY
docker exec research-rag-edge-caddy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
cd "$source_dir"
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d --wait --wait-timeout 180
cd /srv/research-rag/edge
docker compose up -d --force-recreate --wait --wait-timeout 60
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo 'Student2 hostname correction applied; external TLS/MCP verification required.'
