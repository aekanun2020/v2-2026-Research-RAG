# Research-RAG GCP skill validation — 24 September 2026

Assessor: Codex, newly inspected instructions and actual tool results. No external LLM judge, mock GCP or simulated deployment used.

Package: [research-rag-gcp](../../skills/research-rag-gcp/SKILL.md). It supplies a guided deployment/clone/startup workflow and a read-only inventory helper; it is not a fully automated one-command provisioner.

## Executed checks

- Skill Creator quick_validate.py: passed using a temporary Python environment with PyYAML 6.0.3. Default/local and bundled Python initially lacked yaml; no validator shim was used.
- All intra-skill relative references resolve; generated scaffold placeholders removed.
- Helper --help and Python AST parsing passed.
- Prohibited-project guard: rejected locally before any gcloud command or report creation. The prohibited project was not accessed.
- Invalid-selector guard: rejected a shell-metacharacter-containing VM selector locally, without a cloud call.
- Existing-evidence guard: refused to overwrite an existing report; original bytes preserved.
- Actual helper invocation targeted only the previously verified student4 in bigdatainpractice1/asia-southeast1-a. Config account read succeeded. VM describe returned resource not found; helper exited 1 and saved the failed action/result. A direct repeat of the same read command confirmed the GCP resource was not found. No replacement VM was created.
- Initial automatic permission review timed out without executing that live read; one permitted retry executed it. No cloud mutation occurred during skill development or validation.

[Actual failed-inventory report](evidence/skill-inventory-student4-20260924.json). Its status is a real missing-target result, not a passed positive inventory test. The successful full inventory path, new VM provisioning and fresh bootstrap were not live-tested in this skill-authoring task. Earlier actual clone/HTTPS acceptance is linked as historical evidence, not relabelled as a new skill test.

## Codex instruction review

Inspected the procedures against these scenarios; this is document review, not a claim that an independent agent or a cloud deployment executed them:

| Scenario | Required behavior in skill |
|---|---|
| Plan/pricing request | Produce current grounded estimate; do not provision |
| New user-created clone in an unexpected zone | Rediscover target, disk resources/IP/SSH; preserve data; change only demonstrated hostname/origin issue |
| SSH denial with attached service account | Verify precise prerequisite, report scoped manual option; no self-grant/disable-login workaround |
| VM already running | Inspect services; do not claim a start or restart unnecessarily |
| No-login approval exists in a different project | Resolve this deployment's actual exposure decision |
| Asking whether users connected | Read logs/metadata, exclude health/tests, no monitoring configuration changes or inference of human counts |
| Old bootstrap artifact contains literal patch markers | Do not execute it blindly or claim a validated fresh installer |

The source repository bootstrap was inspected and documented as unsafe to reuse directly at commit 258da0d; it was not changed in this skill-only task. Existing per-machine scripts remain historical target-specific implementations.

## Installation and distribution

Canonical source is versioned under skills/research-rag-gcp. Local discoverable installation target is /Users/grizzlymacbookpro/.codex/skills/research-rag-gcp. Installation must preserve file bytes and not overwrite an unrelated existing skill. Cloud privileges are not granted by installation; future mutations remain constrained by current authorization and cloud-activities records.

Installation completed at the stated local target. All seven installed files matched repository source SHA-256 values, and Skill Creator quick_validate.py passed again against the installed directory.
