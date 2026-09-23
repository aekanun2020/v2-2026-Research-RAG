#!/bin/bash
set -euo pipefail
mountpoint -q /srv/research-rag
test -f /srv/research-rag/private-deployment-completed
test ! -e /srv/research-rag/edge
mkdir -p /srv/research-rag/edge/data /srv/research-rag/edge/config
chmod 700 /srv/research-rag/edge/data /srv/research-rag/edge/config
docker pull caddy:2-alpine
edge_image=$(docker image inspect caddy:2-alpine --format '{{index .RepoDigests 0}}')
case "$edge_image" in caddy@sha256:*) ;; *) exit 1;; esac
printf '%s\n' "$edge_image" > /srv/research-rag/edge/image-digest.txt
cat > /srv/research-rag/edge/Caddyfile <<'EOF'
{
    admin off
}

34-142-222-110.sslip.io {
    @mcp path /mcp /mcp/*
    handle @mcp {
        reverse_proxy 127.0.0.1:9076 {
            flush_interval -1
        }
    }
    handle {
        respond "Not Found" 404
    }
}
EOF
cat > /srv/research-rag/edge/compose.yaml <<EOF
name: research-rag-edge
services:
  caddy:
    image: $edge_image
    network_mode: host
    restart: unless-stopped
    read_only: true
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    security_opt: [no-new-privileges:true]
    tmpfs: [/tmp]
    volumes:
      - /srv/research-rag/edge/Caddyfile:/etc/caddy/Caddyfile:ro
      - /srv/research-rag/edge/data:/data
      - /srv/research-rag/edge/config:/config
    logging:
      driver: json-file
      options: {max-size: 5m, max-file: '2'}
EOF
docker run --rm --network none --mount type=bind,src=/srv/research-rag/edge/Caddyfile,dst=/etc/caddy/Caddyfile,readonly "$edge_image" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
cp -p /srv/research-rag/deploy/runtime.env /srv/research-rag/deploy/runtime.env.before-https
sed -i 's|^RAG_PUBLIC_ORIGIN=.*|RAG_PUBLIC_ORIGIN=https://34-142-222-110.sslip.io|' /srv/research-rag/deploy/runtime.env
cd /srv/research-rag/deploy/source-dc36545165f38481a07e15285d9293faa891697a
docker compose -f compose.agents.yaml --env-file /srv/research-rag/deploy/runtime.env up -d --no-deps --wait --wait-timeout 180 mcp
printf 'Prepared Caddy image: %s\n' "$edge_image"
echo 'HTTPS prepared; Caddy not started yet. Await verified ingress tags.'
