# Containerd storage placement: reproduced symptom and causal fix

Read-only reproduction during initial image pull on student1-research-rag, 2026-09-23 UTC:

- Docker info reports root `/srv/research-rag/docker`, driver-type `io.containerd.snapshotter.v1`.
- `du -sh`: `/var/lib/containerd` **3.1G**, `/srv/research-rag/docker` **184K**.
- Boot usage increased from 1.9G before installation to 5.3G during pull; data disk still only 26M used.
- containerd 2.2.1 systemd unit runs `/usr/bin/containerd` without --root, and no `/etc/containerd/config.toml` exists.
- `containerd --help` confirms --root selects its storage directory.

Root cause: changing Docker data-root does not relocate containerd's separate image store. Fix only containerd root, retaining exact images. Wait until the first deployment finishes, stop only this new lab's containers, stop runtime, move image store onto data disk, set systemd --root with mount dependency, restart and compare exact image IDs. Then rerun real MCP checks. This is the actual runtime configuration, not a proxy/shim/fallback.

Planned script: [move-containerd-data.sh](../scripts/gcp/move-containerd-data.sh). Bootstrap updated for subsequent fresh VMs with the same root setting; it must not be rerun on this installed host. Mutation will receive its own timestamped activity record before execution. Results pending.

## Verified after fix

Mutation record: [containerd move](20260923T154052Z-263f28.md). Command completed successfully. Exact Docker image IDs before/after matched (`diff` exit 0). Actual containerd process runs with `--root /srv/research-rag/containerd`. Boot usage fell from approximately 11G at copy start to 2.7G afterward; data filesystem uses approximately 8G and has approximately 90G available. MCP and review health checks passed; Qdrant and Ollama running. The existing real MCP ingestion suite is now running as the integration regression.
