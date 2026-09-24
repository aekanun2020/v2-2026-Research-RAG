# New VM deployment

Use only the authorized VM count, specifications and project. A price/plan request is not permission to provision; an instruction to create the agreed machines is. Reuse existing authorization without asking again.

## Plan

1. Resolve source commit and inspect actual Compose/runtime configuration. Ground users, independent workspaces, concurrent imports, data capacity and runtime. The [profile](deployment-profile.md) is historical, not capacity proof.
2. Inventory matching VMs/disks/IPs, quotas and policies; avoid duplicates. If a machine image was chosen, verify its provenance then use [clone workflow](clone-and-start.md).
3. Specify count/type/zone, boot/data size **and type**, retention, static IP and ingress/public-access decision. For pricing, fetch current official GCP rates and dated exchange rate for THB. Itemize runtime, retained disks/IPs/images and egress; never reuse old estimates as current.
4. Check effective permissions for concrete actions (instance/disk creation, selected network use, IPs, metadata, SSH). API enablement, firewall/IAM and billing changes are separate scope. Missing permissions require the precise blocker/manual step, not a different project or repeated provisioning attempts.
5. For this self-contained classroom application with no GCP API dependency, match the no-service-account pattern. If a workload requires an account, resolve its scope and SSH access explicitly. The user controls firewall changes for this deployment.

## Provision

Create the [activity record](verification-and-records.md) before mutation. Build concrete gcloud argument arrays from verified inputs and inspect local command help for supported flags. Include project, configuration and zone explicitly.

- Create only authorized CPU VM(s), OS image and independent boot/data disks. Match the device name to the installer and deliberately retain the data disk. Never attach accelerators.
- Configure the approved OS Login method. Use/reserve the intended static address only within authorization and effective permissions. Do not create extra addresses while retrying failures.
- Use verified existing ingress tags/rules. If manual ingress is missing, report exact tag/protocol/port needs; do not route around it with a different tunnel or service.
- After every command, save outcome/operation ID and inspect actual state. For a partial failure, inventory what exists and preserve disks/data. No blind recreation or destructive implicit rollback.
- Authenticate SSH host keys against trusted evidence before guest access. Never print key/token material.

## Install on a verified fresh host

1. Match intended data disk by GCP resource, guest device/serial, size, mount state and signatures (`lsblk`, `blkid`, `wipefs -n`). Format only an explicitly authorized, verified blank disk. Absence of a filesystem alone does not prove a disk is disposable. Never fresh-bootstrap a clone or shared Docker host.
2. Mount at `/srv/research-rag` using verified UUID and persistent fstab. Match app-data ownership to Compose UID/GID. Configure both Docker and containerd storage on the data disk with systemd mount dependencies; inspect existing workloads before any daemon operation.
3. Archive source from the selected commit, hash it, transfer and verify the hash before extraction under source-SHA. Use the actual Compose build path and restricted runtime.env; never log full secret-containing configuration.
4. Start real Qdrant/Ollama, obtain/verify the pinned CPU embedding model/dimensions, build app and start MCP/review with health checks. Keep app ports loopback-only, database/model ports unpublished. Use noninteractive Compose exec correctly in streamed scripts.
5. Set restart policies/storage dependencies. Do not leave a disruptive bootstrap script active on every boot. Verify mount/ownership before completion.
6. Apply [HTTPS](clone-and-start.md#https) and [acceptance](verification-and-records.md#acceptance). Log import/test data mutations; use authorized real documents in clearly named test workspaces.

The old repository bootstrap needs correction before reuse; see [known traps](deployment-profile.md). Never describe the new-resource/fresh-install procedure as live-tested solely because configuring existing clones passed.
