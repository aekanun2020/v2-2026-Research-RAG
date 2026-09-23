# Research-RAG: GCP classroom deployment

Status: first private MCP deployment verified. [Acceptance results and limitations](readiness-20260923.md). No public classroom endpoint has been accepted yet.

## Actual first machine

The user manually created `student1-research-rag` in project `bigdatainpractice1`, zone `asia-southeast1-a`: e2-standard-8 (8 vCPU, 32 GiB RAM), 30 GiB boot disk and 100 GiB data disk. Both disks are **pd-standard**, differing from the earlier pd-balanced proposal. The external IP was ephemeral at inspection. There is no GPU or attached service account. Codex did not create this VM or enable OS Login; the user performed both actions.

Application source is pinned to `dc36545165f38481a07e15285d9293faa891697a` on the sole branch `codex/claude-workspace-ingestion` of [v2-2026-Research-RAG](https://github.com/aekanun2020/v2-2026-Research-RAG). Source archive SHA-256: `b6851caada264b8105e89ba2c208125dbcec48b88d13634feb5f71e820271ef8`.

Data disk mounts at `/srv/research-rag`; application data is `/srv/research-rag/app-data`, Docker root is `/srv/research-rag/docker`, containerd image storage is `/srv/research-rag/containerd`, and pinned source is below `/srv/research-rag/deploy/`. Docker named volumes therefore also reside on the data disk. This disk is retained if the VM is deleted, but retention is not a backup.

MCP binds to `127.0.0.1:9076/mcp`; review binds to `127.0.0.1:9077`. Qdrant and Ollama have no published host ports. Do not publish the review page without addressing its own access requirements. No firewall rules were modified. Public exposure/authentication for this repository awaits the user's explicit decision.

## Learner workflow

One VM is intended per group of five. Every learner uses their own Claude account and creates their own workspace via `create_workspace`. Suggested display names are `g01-u01` through `g01-u05` for group 1. A display name is **not** the workspace ID: use the `ws-...` ID returned by the tool on every subsequent scoped call. Call `list_workspaces` again if the registry revision is stale while several learners create workspaces together.

Never share the default workspace for independent student work. Individual workspace IDs separate application data but do not enforce access control. Other users of the same endpoint can invoke tools against another workspace if they know its ID. Public no-auth service must use public/non-sensitive lab material and requires authorization for this deployment.

Five workspaces can submit separate jobs; CPU, RAM and the embedding service are still shared within that VM. One workspace allows one active ingestion job. Claude runs in each learner's own account; this server performs local CPU embeddings and retrieval, not paid external LLM synthesis.

## Validation scope

- Existing real MCP ingestion regression: initialize, catalog, workspace isolation, public PDF download, explicit import, hybrid retrieval and exact source spans.
- [Five-workspace concurrency test](../../scripts/gcp/verify_five_workspaces.py): five actual MCP clients download/import a real MIT-hosted paper, then issue 25 hybrid retrieval requests in synchronized rounds. It records hashes, times and exact citation-span checks. It does not grade semantic quality or simulate a four-hour class.
- No external LLM or mock dependency is used. Test workspaces are named `READINESS TEST ...`; students should create new workspaces.
- A result for one VM does not establish readiness of the other five VMs. Larger/multiple PDFs and different client traffic require separate capacity assessment.

## Operations and evidence

- [Cloud activity records](../../cloud-activities/README.md)
- [User-created VM and read-only inspection](../../cloud-activities/user-created-student1-20260923.md)
- [Deployment bootstrap](../../scripts/gcp/bootstrap.sh) — specific to the verified blank `data-disk`; do not run blindly on another disk or an existing Docker host.
- [Private container deployment](../../scripts/gcp/deploy-private.sh)
- [Mutation logger](../../scripts/gcp/log_action.py)

VMs continue to incur compute costs until stopped. No automatic stop is configured. Stopping does not stop disk/IP charges; deleting a VM does not remove this retained data disk. Cleanup requires explicit user direction and preservation of required learner work.
