# Read-only verification after VM boot — 24 September 2026

- Verification timestamp: 2026-09-24T00:26:13.458606+00:00 (UTC); local timezone Asia/Bangkok, UTC+07:00.
- User request: “start vm และทำให้ใช้ได้เหมือนเดิม”.
- Project: `bigdatainpractice1`; acting cloud account: `thaimcpagent@gmail.com`.
- VM: `student1-research-rag`; zone: `asia-southeast1-a`.
- Initial state: GCP already reported RUNNING before any start command. SSH uptime was approximately 2 minutes. Codex did not start or restart the VM or change its configuration in this task. The actor who started it was not established by this check.
- Read-only actions: gcloud instances describe and addresses list, SSH uptime/docker ps/findmnt/df/systemctl, native HTTPS MCP initialize/tools/list/workspace_status/list_workspaces/retrieve_evidence/read_source_page.
- Static address: `student1-research-rag`, `34.142.222.110`, IN_USE by this VM. No address was reserved or modified by Codex in this task.
- Runtime: all five containers running; MCP and review healthy; Docker and containerd active. Caddy running. MCP/review remain on loopback ports 9076/9077.
- Storage: `/dev/sdb` mounted ext4 at `/srv/research-rag`, 98 GiB filesystem, 8.1 GiB used, 90 GiB available. Boot filesystem 29 GiB, 2.7 GiB used.
- Outcome: native MCP HTTPS passed with verified TLS 1.3, 45 tools, real retrieval from an existing test workspace and two exact citation spans. No new source/workspace/import was created.
- [Full external protocol and retrieval evidence](../docs/gcp/evidence/external-https-after-boot-20260924.json).
- Limits: no Claude Desktop UI test; no fresh load test; no claim that every learner document was inspected. This task observed the service after boot, without initiating the power cycle.
- Cost: VM is running; existing compute, disk and IP charges continue. No new billable resource was provisioned. No rollback needed because no infrastructure/application mutation was performed.
