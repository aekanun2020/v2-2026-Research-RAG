#!/bin/bash
set -euo pipefail
mountpoint -q /srv/research-rag
test -f /srv/research-rag/private-deployment-completed
test ! -e /srv/research-rag/containerd
test ! -f /etc/containerd/config.toml
cd /srv/research-rag/deploy/source-dc36545165f38481a07e15285d9293faa891697a
docker image ls --no-trunc --format '{{.ID}}' | sort -u > /srv/research-rag/evidence/images-before-containerd-move.txt
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env stop
systemctl stop docker.service docker.socket containerd.service
test -z "$(pgrep -x containerd-shim || true)"
mv /var/lib/containerd /srv/research-rag/containerd
mkdir -p /etc/systemd/system/containerd.service.d
cat > /etc/systemd/system/containerd.service.d/research-rag-data.conf <<'EOF'
[Unit]
RequiresMountsFor=/srv/research-rag
[Service]
ExecStart=
ExecStart=/usr/bin/containerd --root /srv/research-rag/containerd
EOF
systemctl daemon-reload
systemctl start containerd docker
docker image ls --no-trunc --format '{{.ID}}' | sort -u > /srv/research-rag/evidence/images-after-containerd-move.txt
diff -u /srv/research-rag/evidence/images-before-containerd-move.txt /srv/research-rag/evidence/images-after-containerd-move.txt
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d --wait --wait-timeout 180
ps -C containerd -o args=
df -h / /srv/research-rag
du -sh /srv/research-rag/containerd /srv/research-rag/docker
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env ps --format json
