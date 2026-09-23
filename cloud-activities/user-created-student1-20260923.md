# User-created first VM: read-only inspection

- Checked at: 2026-09-23T15:16:38.603473+00:00
- Creator: user, manually. Codex did not create or modify this VM.
- Project: `bigdatainpractice1`; CLI account: `thaimcpagent@gmail.com`.
- VM: `student1-research-rag`; instance ID `3585360314274566686`; RUNNING.
- Zone: `asia-southeast1-a` (different from proposed zone b, same region).
- Machine: `e2-standard-8`, 8 vCPU / 32 GiB.
- Boot disk `student1-research-rag`: 30 GiB, pd-standard, autoDelete true.
- Data disk `data-disk`: 100 GiB, pd-standard, deviceName data-disk, autoDelete false.
- External IP: `34.142.222.110`; reserved address inventory empty, so not reserved static.
- No accelerators; no attached service account; no HTTP/HTTPS tags.
- Disk type differs from proposed pd-balanced; do not call it the original specification. Guest filesystem and disk contents remain unknown until SSH access.

## SSH access blocker

Instance metadata has only `enable-osconfig`; no instance SSH keys and OS Login not enabled. Project metadata has inherited SSH users, but none match the existing local Google Compute public key. The instance/project metadata settings do not enable OS Login. Current testIamPermissions returned `compute.instances.osAdminLogin` but did not grant instance/project metadata writes, address creation or instance creation.

Requested minimal user action: on this instance, set custom metadata `enable-oslogin=TRUE`. This reuses the account's existing `roles/compute.osAdminLogin`; an OS Login SSH public-key import, if needed, will be separately logged before execution. Do not disable host key verification, guess an inherited username, change IAM, or attempt another user's credential.

No guest connection or guest mutation was performed. Installation is blocked before bootstrap, so the prepared bootstrap script has not been used. It targets device `rag-data` from the original plan and must be adapted to the verified new device `data-disk` after guest disk inspection; never run it unchanged or format a disk with existing data.

## Next steps after access

Read-only inspect filesystem, mounts, existing services, sudo and Docker before any changes. Record all changes before execution. Install and verify private services first. Public unauthenticated exposure is still pending authorization for this repository. User manages firewall; no firewall change by Codex. Five additional VMs have not been created and the latest user direction is to prepare one first.

## Access restored and disk inspected

User manually enabled OS Login. Verified POSIX identity `thaimcpagent_gmail_com`, existing registered Google Compute SSH key, and passwordless sudo. Host ED25519 fingerprint `SHA256:Dwqh9oWNw4hfjoTDPN8zy4Hx8LUwtOumLinTIYGimWU` verified against authenticated GCP serial-console output before using StrictHostKeyChecking=yes. An initial accept-new invocation was rejected by automatic review before execution; no cloud mutation occurred from that rejected invocation.

Guest inspection: Ubuntu 24.04.5 LTS; no Docker; only DNS/SSH listeners; data-disk /dev/sdb 100 GiB with no partitions/filesystem/signatures. Authorized next mutation: format only this verified blank data-disk as ext4, mount /srv/research-rag, install Docker and place its storage on the data disk. Boot disk remains the OS disk. No firewall changes or public exposure.
