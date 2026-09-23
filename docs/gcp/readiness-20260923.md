# Student 1 private deployment acceptance — 23 September 2026

**Private MCP service passed the checks below. Public HTTPS and learner Claude integration are not ready/verified. Only one VM exists; the other five have not been created.**

## Actual target and scope

`student1-research-rag`, `bigdatainpractice1`, `asia-southeast1-a`, external IP `34.142.222.110` (ephemeral at inspection), e2-standard-8, 8 vCPU / 32 GiB. The user created the VM and enabled OS Login. Both disks are pd-standard (30 GiB boot / 100 GiB data), not the originally proposed pd-balanced. No GPU or service account is attached.

Codex installed Docker, mounted the verified blank data disk, placed application data, Docker data and containerd images there, and deployed the repository's actual Compose 0.5.0. The application source is pinned to `dc36545165f38481a07e15285d9293faa891697a`. No application logic was patched, no external model API was used, and no compatibility service or mock was introduced.

## Observed results

| Check | Result | Evidence |
|---|---|---|
| Real MCP baseline: workspace separation, PDF download/import, retrieval, source spans, rejection paths | 36 checks passed | [Full baseline](evidence/baseline-20260923.json) |
| Five independent native MCP sessions, five distinct workspaces and Qdrant collections | 98 deterministic checks passed | [Full concurrency report](evidence/five-workspaces-20260923.json) |
| Five simultaneous real PDF imports | All completed in 66.46–69.55 seconds, measured from import call until polling observed completion | Same concurrency report |
| 25 hybrid queries in five synchronized rounds | Median 0.267 s; nearest-rank P95 0.485 s; maximum 0.509 s | Same concurrency report |
| Actual service restart and retained data | All five PDF sources still retrievable with exact citation spans | [Post-restart report](evidence/after-restart-20260923.json) |
| Final processes, ports, disk space and CPU-only runtime | MCP/review healthy; Qdrant/Ollama running; app ports bound to loopback | [Runtime snapshot](evidence/final-runtime-20260923.txt) |

Test PDF: *Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence*, [MIT public source](https://economics.mit.edu/sites/default/files/inline-files/Noy_Zhang_1_0.pdf), 532,994 bytes, 15 pages, SHA-256 `3a85c26cf0560425d0d1d60c0cd574c0c38c17ac0dee1f1d2010123f3a1a9736`. Each concurrency workspace imported this real PDF; the import reports 21 chunks. Test workspaces are retained with explicit READINESS TEST names; learners create their own workspaces.

Assessor: Codex inspected the current reports and runtime evidence. Scripts performed deterministic protocol, job-state, identity and source-span checks. No semantic relevance/faithfulness grading was performed and no external LLM judge was used.

## Limits and pending public access

- Tests ran using the native MCP SDK from a client container on the same VM, over loopback. The reported latency excludes Internet/Claude network latency and Claude response generation.
- This is one 15-page PDF per workspace, simultaneous import followed by simultaneous search. It is not a four-hour soak, a mixed import/search load test, or proof for arbitrary large corpora or 30 clients on one machine.
- Data separation is verified for explicit workspace routing; workspace IDs are not per-user authorization. Authentication is absent in the current application.
- Caddy/public HTTPS has not been installed/exposed yet. Public no-auth permission for this repository remains pending; prior lab authorization was not reused.
- Existing GCP rules allow HTTP/HTTPS only for `http-server` / `https-server` tags. The VM currently has neither. The user manages firewall and metadata/tags; Codex has not changed any GCP firewall rule.
- Reserve the current address if a stable endpoint is required; no static address was created by Codex. No automatic stop is configured. The currently running VM incurs compute costs.

## Storage correction and records

Docker 29 used containerd's separate root on the boot disk despite Docker data-root being on the data disk. This was reproduced, then the actual containerd root was moved with services stopped. Image IDs matched before/after, boot disk usage fell, and real MCP tests plus restart checks passed. [Before/after cause and evidence](../../cloud-activities/containerd-storage-before-20260923.md).

[All cloud activities](../../cloud-activities/README.md) include the earlier denied IP-creation attempt, remote writes, package installation, deployment, partial stdin-consumption issue and correction, data-store relocation, test-data creation and restart. The manual VM/OS Login changes are explicitly attributed to the user.
