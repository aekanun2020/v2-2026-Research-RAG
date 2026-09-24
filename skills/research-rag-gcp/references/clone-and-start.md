# Clone and startup

## Inspect

Read actual name/zone/IP, source machine image, disk URLs, service account, OS Login metadata, tags and static reservation. An inherited boot device label can still say student1; inspect the actual disk resource. No GPUs.

Verify SSH fingerprint against authenticated serial output or another trusted source. ssh-keyscan alone is not authentication. Keep StrictHostKeyChecking=yes; reuse verified key paths without copying key bytes.

For `Permission denied (publickey)`, preserve failure and inspect identity/key registration, metadata and effective permissions. An attached service account requires Service Account User access for OS Login. Do not assume this is the cause without checking, or grant yourself IAM. If the user chooses No service account, wait for the authorized stop/edit/start, rediscover IP and retry the original SSH. Never disable OS Login as a workaround.

Inspect guest mount/free space, containers/images, selected env settings, Caddyfile and restart policies. Preserve cloned workspaces/data; do not fresh-bootstrap or silently clear them. Do not stop/image the source VM just to configure its clone.

## HTTPS

1. Use the user's domain, or derive the sslip.io hostname from verified current IPv4 (dots to hyphens) when that endpoint choice is authorized. Verify DNS and static reservation; disclose ephemeral status. Do not silently reserve/change an IP.
2. Verify public exposure/auth decision and actual ingress. Existing classroom no-login authorization is scoped to this project. Keep review/database/model ports private.
3. Capture the before TLS result and current Caddy hostname/RAG_PUBLIC_ORIGIN. Both commonly remain from the image. If correct and healthy, no change/restart is needed.
4. Before guest backups/writes, create a cloud record. Use a restricted unique backup directory and guards for hostname, mount and source directory. Change only demonstrated causal settings.
5. Set the Caddy hostname and `RAG_PUBLIC_ORIGIN=https://<target-host>` consistently. Route /mcp and /mcp/* to the actual loopback MCP port. Other paths return 404. Preserve pinned Caddy image, persistent TLS data/permissions and disabled admin API. This is the requested TLS gateway, not a protocol substitute. Never print ACME/certificate private keys. Correct routing does not rotate all secrets copied by a machine image; do not claim it does.
6. Validate active Caddy config and Compose without dumping secrets. Recreate MCP if its env changed, ensure dependencies run, and recreate Caddy as appropriate. Admin API is disabled in this deployment. Atomic replacement of a bind-mounted file can leave an old inode in a running container; verify loaded config after recreation.
7. Immediately rerun original TLS/native MCP check with normal certificate verification. If failing, inspect actual DNS/ingress/certificate errors and preserve results before further changes. No TLS bypass, protocol shim, alternate tunnel or unproven patch pile-up.
8. Run [acceptance](verification-and-records.md#acceptance), record outcome/recovery. One retrieved document does not verify the entire cloned corpus.

Actual profile ports/layout and source evidence: [deployment profile](deployment-profile.md). Read the real deployed files before changing them; per-machine scripts are not generic installers.

## Startup and shutdown

- For start requests, inspect state first. Start only the named stopped VM with authorization and a prior record. If RUNNING already, do not claim you started it.
- Check mount before Docker/containerd, all five services, endpoint and representative retrieval. `unless-stopped` configuration is not proof of a future boot; report actual tests separately.
- Start intentionally stopped containers only within the intended verified Compose project. Do not restart other machines/daemons unnecessarily.
- A question about stopping is not authorization to stop. Check current jobs/persistence/IP and advise. Explicit stop instructions require a record and normal graceful stop, with active-work implications considered. No deletion/cleanup implied; disk/IP/image storage charges can remain.

Official references, verify when needed: [OS Login](https://docs.cloud.google.com/compute/docs/oslogin/set-up-oslogin), [stop/start](https://docs.cloud.google.com/compute/docs/instances/stop-start-instance), [static IP](https://docs.cloud.google.com/compute/docs/ip-addresses/configure-static-external-ip-address), [Caddy HTTPS](https://caddyserver.com/docs/automatic-https), [Docker restart](https://docs.docker.com/engine/containers/start-containers-automatically/).
