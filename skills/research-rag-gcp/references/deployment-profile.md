# Deployment profile — observed 24 September 2026

Historical evidence, not current inventory, a fixed public endpoint, or permission to deploy.

- Canonical repo: https://github.com/aekanun2020/v2-2026-Research-RAG
- Observed branch `codex/claude-workspace-ingestion`; resolve intended ref to a SHA before transferring source.
- Deployed app source `dc36545165f38481a07e15285d9293faa891697a`, app 0.5.0, `compose.agents.yaml`, Compose project `codex-rag-agents`.
- Classroom project/config/account: `bigdatainpractice1` / `bigdatainpractice` / `thaimcpagent@gmail.com`. Do not silently reuse for another assignment.
- Existing size: e2-standard-8, 8 vCPU/32 GiB, boot 30 GiB, separate data 100 GiB. Student1 actual disks were pd-standard; pd-balanced was a proposal. Recheck actual type/capacity and workload for every VM.
- Ubuntu 24.04; CPU embeddings nomic-embed-text, 768 dimensions. Claude runs in learners' accounts, not on these servers.
- Singapore region; student1/student4 zone a, student2 b, student3 c at inspection. Names do not determine zones.

## Guest layout

- Data mount `/srv/research-rag`; subdirectories `app-data`, `docker`, `containerd`, `deploy`, `edge`.
- Source `/srv/research-rag/deploy/source-<SHA>`; settings `/srv/research-rag/deploy/runtime.env`. Read only selected settings, not full potential secrets.
- MCP `codex-rag-agents-mcp-1`: `127.0.0.1:9076`; review: `127.0.0.1:9077`. Qdrant/Ollama ports not published.
- Caddy `/srv/research-rag/edge/compose.yaml`, project `research-rag-edge`, container `research-rag-edge-caddy-1`, host networking; persistent TLS data/config in edge/data and edge/config.
- Five services use `restart: unless-stopped`; Docker/containerd enabled with `RequiresMountsFor=/srv/research-rag`.
- Actual embedding options use `num_gpu: 0`. Verify CPU options in the selected version, not only VM accelerator inventory.

Recorded digests (verify; no automatic upgrade):

| Component | SHA-256 |
|---|---|
| App 0.5.0 image | `5558a8d415727da94625f930a8bf68ec20f77d6769e158246328420764691d2b` |
| Qdrant image | `0bd98fa7977f1e75694779359ca4e212822e5a71334e28421182f72f209d5286` |
| Ollama image | `1685741456770df6e3cceb2a945a5f75e020f658d1701509668d6f4688f1dd3f` |
| Caddy image | `6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b` |
| Model manifest | `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` |


## Evidence and known traps

- [Initial resource creation](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/codex/claude-workspace-ingestion/cloud-activities/deployment-20260923.md) failed for IAM. User created the VMs; do not claim automatic VM provisioning succeeded here.
- [Initial tests](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/codex/claude-workspace-ingestion/docs/gcp/readiness-20260923.md): five concurrent PDF imports then 25 queries. Not proof for 30 users on one VM, arbitrary corpora or a four-hour class.
- [Student2](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/codex/claude-workspace-ingestion/cloud-activities/student2-20260924.md): attached service account caused a missing OS Login prerequisite; user removed it, SSH succeeded.
- [Student4](https://github.com/aekanun2020/v2-2026-Research-RAG/blob/codex/claude-workspace-ingestion/cloud-activities/student4-20260924.md): inherited hostname/origin corrected; native 45-tool MCP, retrieval and eight public/local checks passed.
- At repo commit `258da0d`, `scripts/gcp/bootstrap.sh` contains literal leading `+` patch markers, including its heredoc terminator. **Do not run it directly or call it a validated general installer.** Correct the actual bootstrap with a reproduced failure and appropriate verification within authorized implementation scope before using it. Per-machine scripts also hard-code targets; inspect/adapt guards from live facts, never execute another machine's script unchanged.
- Docker 29 has a separate containerd image store: Docker data-root alone did not move it off the boot disk.
- `docker compose exec -T` can consume the remainder of a streamed shell script. Add `--interactive=false` for commands that should not read stdin. Use `docker exec -i` intentionally only when forwarding input, e.g. a Python script.

Never treat a temporary checkout or a previous public IP as a reusable default.
