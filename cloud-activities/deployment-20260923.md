# Six-group Research-RAG deployment — 23 September 2026

## Authorization and scope

User: “สร้างเลยครับ 6 เครื่อง ตาม spec”. Six groups of five learners, each learner uses their own Claude Sonnet account and independent workspace. This is the Research-RAG repository, not the older Network Forensics lab. Public unauthenticated exposure awaits a separate answer. No firewall rule, IAM, billing-account activation/upgrade, GPU, or managed database changes are included.

## Verified starting state at 22:02 Asia/Bangkok (15:02 UTC)

- GCP project `bigdatainpractice1`, gcloud configuration `bigdatainpractice`, account `thaimcpagent@gmail.com`.
- Instance, disk and reserved-address inventories: empty.
- Regional E2 CPU quota: 72, usage 0; proposed use 48. Billing enabled; trial/paid account classification unknown. Never activate or upgrade a trial.
- Existing default network; existing SSH rule allows TCP22. HTTP/HTTPS rules already exist and apply only to corresponding tags. User retains firewall management.
- Source repository: https://github.com/aekanun2020/v2-2026-Research-RAG, only branch `codex/claude-workspace-ingestion`, application source commit `dc36545165f38481a07e15285d9293faa891697a` (latest change adds license/disclaimer; runtime unchanged from inspected predecessor).
- Ubuntu image: `ubuntu-os-cloud/ubuntu-2404-noble-amd64-v20260918`.

## Intended resources and configuration

- `research-rag-g01` through `research-rag-g06`, zone `asia-southeast1-b`, e2-standard-8, 8 vCPU/32 GiB each; no accelerators.
- 30 GiB pd-balanced boot disk per VM, auto-delete with VM.
- New 100 GiB pd-balanced data disk per VM, device `rag-data`, retained when VM deleted; mount `/srv/research-rag`. Docker data root and application data live on this disk.
- Six regional static IPv4 addresses named after each VM with `-ip` suffix. No public service until authorization and successful validation.
- No attached service account, no API scopes. SSH via existing local Google Compute public key in instance metadata; block inherited project SSH keys.
- Docker Compose from the pinned application commit; MCP and review bound to loopback; Qdrant and Ollama not published; CPU-only embedding model. Five independent learner workspaces per VM to be created by learners, not automatically pre-populated with documents.
- Bootstrap installs Docker, mounts only the explicitly created blank data disk and configures persistent storage. Startup is idempotent but must be removed from metadata after successful bootstrap to avoid stopping Docker on later starts.

## Costs and cleanup

Estimate at USD/THB 33.206: VM costs THB65.88/hour for all six; four compute hours THB263.52. Disks + attached IPv4 retained 24 hours THB117.58. Total THB381.10 before tax, egress, domain, backup and client model fees. Additional setup hours cost extra. Actual bills may use a different conversion. No automatic shutdown/deletion is authorized or configured.

Stop VMs after explicit user direction to stop CPU billing; disks and addresses continue billing. Data disks are retained intentionally. Releasing IPs/deleting disks requires explicit cleanup scope and preserving required learner data. No rollback deletes retained data silently.

## Execution and verification

Each mutation is recorded in a timestamped sibling Markdown file before execution, with command result captured afterward. Application deployment, remote file writes, tests that create data and removal of startup metadata also require records. Read-only probes are distinguished from mutations. Final inventory, receipts and readiness will be linked here when known.

### Current outcome — 2026-09-23T15:05:10.374011+00:00

Blocked by missing IAM permissions before any billable resource was created. [Failed reservation](20260923T150333Z-f76d1e.md) · [IAM findings](iam-blocker-20260923.md). No VM, disk, firewall, service account or billing-account change was made.

### User created one VM first

[Verified manual creation and deviations](user-created-student1-20260923.md). This is a user-performed change, not a Codex provisioning success. Installation awaits SSH access; no guest changes have been made.

### First-machine private deployment accepted

[Actual results and limitations](../docs/gcp/readiness-20260923.md): baseline 36 checks, five-workspace concurrency 98 checks, post-restart retrieval 5/5. Application remains loopback-only. Caddy/HTTPS, public authorization, network tags and static address remain pending. No additional VM was created. See manual machine record for actual pd-standard disks and zone a.
