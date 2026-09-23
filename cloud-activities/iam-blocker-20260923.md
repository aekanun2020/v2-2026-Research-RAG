# Provisioning blocked by IAM — 23 September 2026

Read-only inspection after the failed creation attempt; no IAM changes were made by Codex.

Project: `bigdatainpractice1`. Account: `thaimcpagent@gmail.com`.

Current direct project roles:
- `roles/viewer`
- `roles/compute.osAdminLogin`
- `roles/iap.tunnelResourceAccessor`

`projects.testIamPermissions` granted only these requested permissions:
- `compute.addresses.get`
- `compute.disks.get`
- `compute.instances.get`
- `compute.regionOperations.get`
- `compute.zoneOperations.get`

Missing requested permissions:
- `compute.addresses.create`, `compute.addresses.use`, `compute.addresses.delete`
- `compute.disks.create`, `compute.disks.use`
- `compute.instances.create`, `compute.instances.setMetadata`, `compute.instances.setTags`, `compute.instances.setLabels`
- `compute.instances.delete`, `compute.instances.start`, `compute.instances.stop`
- `compute.subnetworks.use`, `compute.subnetworks.useExternalIp`

## Required user action

Grant `roles/compute.instanceAdmin.v1` to this account on this project, plus a project custom role containing `compute.addresses.create` and `compute.addresses.delete`. The predefined role was inspected live: it includes disk/instance creation, address use/get/list and subnetwork use/external-IP use, but excludes address create/delete. Delete permission is for later explicitly authorized cleanup, not authorization to delete now.

The user may instead reserve the six named regional static addresses manually and grant only Instance Admin for the remaining work. Do not change firewall roles/rules, attach a service account, upgrade billing, or grant Owner/Editor to work around this failure.

## State

All six requested addresses failed creation. The post-failure address inventory was empty. VM and disk creation have not been attempted. No billable resources were created by this attempt. Public/no-auth authorization question remains separate and pending.
