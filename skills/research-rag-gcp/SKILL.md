---
name: research-rag-gcp
description: Provision CPU-only GCP VMs for Research-RAG, configure machine-image clones with their own HTTPS MCP endpoint, and check startup or traffic. Use for Research-RAG deployment and operations, not unrelated MCP or forensic labs.
---

# Research-RAG on GCP

Deliver the requested VM and a tested MCP endpoint. This skill is an operating procedure with a read-only inventory helper, not an unattended provisioning program. Creating/installing this skill does not authorize cloud deployment.

## Ground the target

- Verify the actual Git remote, local project root, source ref/commit, GCP project, acting account/configuration, VM name, zone and authorized resource count. Never use the open workspace or CLI defaults as proof of the intended target. Read [deployment profile](references/deployment-profile.md) as historical context, not current inventory or blanket permission.
- Reuse the current user's authorization; do not ask again for approved steps. If a material target or public-exposure decision is missing, stop dependent work and ask. No-login approval from another project does not carry over.
- Never use/recommend GPUs, Cloud SQL for SQL Server, a Free Trial billing upgrade, or workloads in `quixotic-elf-492100-g5`. Missing permissions do not authorize another project or workaround.
- Before each GCP mutation, including guest files, containers, data and VM-side test reports, create a timestamped record in the verified repository's `cloud-activities/`; promptly update outcomes, including partial/failed attempts. See [records and acceptance](references/verification-and-records.md). No secrets in records. Attribute manual changes to the user.

## Select the requested workflow

| Request | Procedure |
|---|---|
| Create VM(s), fresh installation | [New VM deployment](references/new-vm.md) |
| Configure a user-created machine-image clone | [Clone and HTTPS](references/clone-and-start.md) |
| Start/recover an existing VM | [Startup section](references/clone-and-start.md#startup-and-shutdown) |
| Check readiness, users or traffic | [Verification and records](references/verification-and-records.md) |

Start with live read-only inventory. The helper requires explicit selectors:

```sh
python3 /absolute/path/to/research-rag-gcp/scripts/inspect_vm.py \
  --project VERIFIED_PROJECT --configuration VERIFIED_CONFIGURATION \
  --zone VERIFIED_ZONE --vm VERIFIED_VM --output /new/local/report.json
```

Substitute grounded selectors. This helper only reads GCP inventory; it does not SSH, mutate cloud resources or prove application readiness. A missing VM is not permission to create one.

## Operating invariants

- Independent student VMs need separate disk resources and distinct hostnames/origins. Inspect disk resource URLs, not inherited guest labels. Preserve cloned learner data unless cleanup is explicitly requested. Do not stop/image the source VM merely to configure a clone.
- Use the actual selected source and pinned images/model. Do not mix Compose variants or silently upgrade components. No mocks, protocol shims or workaround services to conceal a failing integration.
- Diagnose OS Login failures from account/key/metadata/service-account permission evidence. Do not grant yourself IAM, disable OS Login or detach a service account as an unannounced workaround.
- Verify SSH host keys against trusted GCP evidence and keep strict verification enabled. Reference existing private keys by path only.
- A running container or HTTP 200 is insufficient: require trusted HTTPS and native MCP initialize, tools/list and a representative authorized tools/call. When authorized data exists, check retrieval against source spans. Distinguish native MCP tests from actual Claude Desktop UI tests.
- Report tested URL, service state, verification scope, static/ephemeral IP status and records. Update root README relative links when adding artifacts; publish only to the verified canonical remote within existing authorization.

Example: “ใช้ $research-rag-gcp ตรวจ student5-research-rag ที่ผม clone มา แล้วเปิด HTTPS เหมือนเครื่องก่อน” — discover its actual zone/IP/service account first, never infer them from the number.
