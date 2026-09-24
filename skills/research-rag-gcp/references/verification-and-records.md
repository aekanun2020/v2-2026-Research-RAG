# Records, acceptance and traffic

## Records

Before every GCP mutation (including guest files/containers/data/tests), create a unique timestamped Markdown file under the verified repo's cloud-activities/. If the project root or ability to write is unresolved, stop mutations until resolved. Include:

- Timestamp/timezone, GCP project/account, resource/zone, purpose and user authorization.
- Relevant before state, redacted command/API action, streamed-script path and SHA-256.
- Actual outcome/exit/operation ID, after state and verification. Preserve failed/partial attempts.
- Cost impact and concrete recovery/cleanup. No implicit deletion of retained data.

Never log credentials, private keys, tokens, certificate keys or secret-containing env dumps. Existing per-machine logger headers hard-code names/zones: inspect/adapt before reuse. Attribute user actions separately from Codex mutations. Read-only checks need no invented mutation record. Avoid publishing learner content; use relevant metadata/counts.

Update root README clickable relative links for new/changed artifacts and verify targets are tracked. Preserve historical reports. Commit/push only to the verified canonical remote within publication authorization; report incomplete push honestly.

## Acceptance

1. Inspect actual mounts, five services, image/model pins, CPU-only options, private ports, health and restart policies.
2. From outside VM verify trusted TLS hostname/certificate. Use compatible native MCP SDK from the selected source lockfile. Observed app uses MCP 2.2.0 with httpx2; do not substitute a protocol shim.
3. Native initialize, tools/list, then authorized workspace_status/list_workspaces. Pinned 0.5.0 has 45 tools; derive expected catalog from the selected version, not this historic number for all versions.
4. With authorized retained data, choose a verified workspace/source, call retrieve_evidence with explicit workspace_id/source filter then read_source_page. Verify hit text/citation exactly matches the indicated span. This proves protocol/data consistency, not semantic relevance or complete corpus integrity.
5. After hostname/origin changes compare public/loopback catalogs/state and approved public Origin; check unapproved Host/Origin rejection (observed 421/403). The actual repo contains scripts/verify_public_mcp.py: inspect it and log any report written to VM.
6. GET /mcp can be a long-lived SSE stream; curl timeout alone is not failure, HTTP 200 alone is not acceptance. Separate native protocol verification from an actual Claude Desktop UI test.

Read-only tests need no invented data. Imports/load tests require authorization, real permitted documents, labelled test workspaces and mutation records. Small tests do not establish arbitrary capacity. Never silently remove learner data after testing.

## Traffic

Use read-only logs/metadata, not extra public MCP calls that contaminate measurements. State window/timezone. Checking usage does not authorize enabling access logs, restarting services or installing monitoring.

- Read retained timestamped logs with explicit --since; rotation limits history. Do not claim all-time coverage.
- Verify loopback health-check source/pattern from actual smoke_http.py; exclude it and known Codex test windows/baseline IDs.
- This stack may log Caddy/Docker gateway 172.18.0.1 instead of real client IP. Requests are not humans. No unique-user, location or Claude-identity claim without supporting logs/authentication.
- Read registry/workspace/job metadata: new timestamps, source counts, revisions and job states. Do not read document bodies to count activity. Imports are stronger evidence of work than connections; unchanged state does not exclude read-only retrieval.
- Active TCP connections are a snapshot, not historical users. HTTP success does not prove every tool call succeeded.
- Report requests, latest event, actual work and limitations separately. Keep sensitive operational metadata local unless publication is requested.
