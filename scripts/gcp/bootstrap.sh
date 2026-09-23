#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/research-rag-bootstrap.log) 2>&1
export DEBIAN_FRONTEND=noninteractive
disk=/dev/disk/by-id/google-data-disk
for attempt in $(seq 1 60); do [ -b "$disk" ] && break; sleep 2; done
test -b "$disk"
# User-created data-disk verified blank with lsblk and wipefs -n on 2026-09-23.
test "$(blockdev --getsize64 "$disk")" -eq 107374182400
if ! blkid "$disk"; then mkfs.ext4 -m 0 -L research-rag-data "$disk"; fi
test "$(blkid -s TYPE -o value "$disk")" = ext4
mkdir -p /srv/research-rag
uuid=$(blkid -s UUID -o value "$disk")
if ! grep -q "UUID=$uuid " /etc/fstab; then
  printf 'UUID=%s /srv/research-rag ext4 defaults 0 2\n' "$uuid" >> /etc/fstab
fi
mountpoint -q /srv/research-rag || mount /srv/research-rag
mkdir -p /srv/research-rag/docker /srv/research-rag/app-data /srv/research-rag/deploy /srv/research-rag/evidence
chown 1000:1000 /srv/research-rag/app-data
apt-get update
apt-get install -y docker.io docker-compose-v2 ca-certificates curl jq
systemctl stop docker.service docker.socket
install -d -m 0755 /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{"data-root":"/srv/research-rag/docker","log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}
EOF
install -d /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/research-rag-data.conf <<'EOF'
[Unit]
RequiresMountsFor=/srv/research-rag
EOF
# Docker 29 uses containerd image storage independently of Docker data-root.
+# Fresh-host bootstrap only: refuse to move any existing image store here.
+systemctl stop containerd
+test ! -d /var/lib/containerd/io.containerd.content.v1.content/blobs
+mkdir -p /srv/research-rag/containerd /etc/systemd/system/containerd.service.d
+cat > /etc/systemd/system/containerd.service.d/research-rag-data.conf <<'EOF'
+[Unit]
+RequiresMountsFor=/srv/research-rag
+[Service]
+ExecStart=
+ExecStart=/usr/bin/containerd --root /srv/research-rag/containerd
+EOF
+systemctl daemon-reload
+systemctl enable --now containerd docker
docker info --format '{{.DockerRootDir}}'
docker compose version
date --iso-8601=seconds > /srv/research-rag/bootstrap-completed
echo RESEARCH_RAG_BOOTSTRAP_COMPLETED
