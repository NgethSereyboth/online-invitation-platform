# Attack Story: `merge.prepare_job`

| Field | Value |
|---|---|
| **Tool ID** | `merge.prepare_job` |
| **Group** | `merge` |
| **Risk tier** | `high` |
| **Permission tier** | `manage` |
| **Executor** | `client` |
| **Binding** | `POST /api/platform/v52/data-merge/jobs` (platform-api) |
| **Reversible** | `False` |
| **Confirmation required** | `True` |
| **Source file** | `ai_agent/tools.py` (in `_defs()`, after `publishing.configure_environment`) |
| **Binding file** | `ai_agent/capabilities.py:TOOL_BINDINGS["merge.prepare_job"]` |
| **Feature gate** | `dataMerge` (`ai_agent/capabilities.py:FEATURE_TOOL_PREFIXES["dataMerge"] = ("merge.",)`) — only available when the `data_merge_jobs_v47` table exists. |

### 1. What it touches

- **Data**: `data_merge_sources` (read — source schema + row data), `data_merge_jobs_v47` (write — job record + status), `data_merge_variants` (write — one row per generated variant), `invitations` (write — when `mode="prepare-publications"` creates a new invitation per row), `guests` (write — when `mode="prepare-delivery"` creates a guest per row).
- **Services**: `POST /api/platform/v52/data-merge/jobs` enqueues a `bulk-generation-v47` background job (`future_platform_v52/service.py` registers the handler). The job processes up to 5000 rows, generates variants, and optionally creates invitations / guests / publications in bulk.
- **Files**: each variant may reference a generated asset (e.g. personalized QR-code image, per-row branded cover). These assets are written to the workspace's object storage.
- **Side effects**: bulk creation of invitations, guests, or publications. May trigger downstream email / SMS dispatch if `mode="prepare-delivery"` enqueues messages. Workspace budget consumption is amplified by the row count.

### 2. Worst case if malicious

If a prompt-injected or compromised agent successfully invoked `merge.prepare_job` with attacker-controlled `rows` (up to 5000 entries) and `mode="prepare-publications"`, the attacker could:

- **Bulk-publish 5000 invitations** in a single job, each with a unique slug, flooding the public invitation index and the host's billing webhook (if billing is metered per publication).
- **Bulk-create 5000 guest records** with attacker-chosen PII (names, emails, phone numbers), polluting the guest list with synthetic data that obscures real RSVPs and triggers bulk-email confirmation flows to attacker-controlled addresses.
- **Exfiltrate source data**: the `rows` array can contain arbitrary JSON. If the merge job emits per-row URLs that include row data (e.g. `?name={row.name}&email={row.email}`), the platform becomes an open redirect / SSRF proxy.
- **Resource exhaustion**: 5000-row merges each spawning an asset generation + an invitation creation can exhaust storage quota, job-queue capacity, and external-provider rate limits in under a minute.
- **Publication timing attack**: schedule 5000 invitations to publish simultaneously at a future timestamp, creating a coordinated traffic spike that DDoS's the host's infrastructure or the platform's shared services.

Blast radius: **workspace-wide** (5000 invitations under one workspace), **potentially cross-workspace if the source is a shared data source**. Data affected: **bulk PII + bulk publication + bulk billing + storage abuse**.

### 3. Containment

- **Schema validation**: `sourceId` is a stable-id. `mode` is constrained to the enum `["preview", "generate-drafts", "prepare-publications", "prepare-delivery"]`. `rows` is a bounded array (max 5000 entries). `configuration` is a free-form object (additional properties allowed — Phase 1b should add a schema).
- **Permission tier**: `manage` — owner / manager only.
- **Confirmation boundary**: `reversible=False, confirmation=True, risk="high"` → `destructiveAccepted=True` required.
- **Feature gate**: requires the `data_merge_jobs_v47` table.
- **Authorization token**: 30-second single-use, bound to the exact plan index.
- **HTTP-binding match**: `http_request_matches_tool` verifies `POST /api/platform/v52/data-merge/jobs`.
- **Background job**: `bulk-generation-v47` runs in the bounded job queue with retry limits, idempotency keys, and cancellation. The job can be cancelled mid-flight (`platform_v32/jobs.py::JobQueue.cancel`).
- **Workspace budget guard**: `ai_agent/service.py:_budget_guard()` checks the workspace AI routing policy budget before the job is enqueued.
- **Audit event**: `ai.plan_confirmed` / `ai.tool_authorized` with `metadata={"sourceId": ..., "mode": ..., "rowCount": len(rows)}`.

### 4. Reversible

- **No**: per `ToolDefinition.reversible = False`.
- **How to undo**: bulk-created invitations / guests / publications must be deleted individually or via a workspace-scoped bulk-delete operation (not currently a registered AI tool — must be performed through the admin UI). Generated variants remain in `data_merge_variants` for forensic review.
- **Time to undo**: minutes-to-hours for 5000 records, depending on the bulk-delete performance.
- **Side effects of undo**: if any of the bulk-created invitations were already published, they must be unpublished before deletion. Guest PII captured through their RSVP forms remains in the `rsvps` table until a privacy request purges it.

### 5. Mitigation (Phase 1a + future)

- **Resource-scoped permission**: `workspace:{id}:data-merge:prepare`, `workspace:{id}:data-merge:execute` (separate grants — preparing a job does not authorize running it). Per-source: `merge-source:{sourceId}:use`.
- **JIT elevation**: 5-minute TTL grant with mandatory `reason`. **Row-count threshold**: any merge with `rowCount > 100` requires an additional out-of-band email confirmation to the host.
- **Per-mode risk weighting**: `prepare-publications` and `prepare-delivery` are higher-risk than `preview` and `generate-drafts` — they should require a stricter JIT grant (e.g. 2-minute TTL instead of 5).
- **Configuration schema** (Phase 1b): constrain the `configuration` object to a typed schema that explicitly forbids `url`, `endpoint`, `destination`, `redirect`, `callback` keys (consistent with `FORBIDDEN_KEYS`).
- **Anomaly detection**: dashboard detects when a merge job's `rowCount` exceeds the host's historical baseline by > 3 standard deviations, or when the merge runs off-hours.
- **Dry-run mode**: any `mode` other than `preview` must first complete a `preview` run; the host must explicitly confirm the preview output before the production run is authorized.

### 6. Test coverage

- `tests/v28_agent_tool_contract_test.py` — registry contract.
- `tests/v28_agent_server_contract_test.py` — plan + authorize + consume flow.
- `tests/v28_agent_conversation_browser_test.py` — confirmation UX.
- `tests/v53_1_ai_project_operator_backend_test.py` — operator backend (which exercises a merge-like flow).

Gap: no test covers the 5000-row resource-exhaustion attack. Add a row-count threshold test in Phase 1b.

### 7. AISVS cross-reference

- `C9.2.4` — destructive confirmation.
- `C9.3.5` — non-reversible + confirmation.
- `C9.7.2` — max tool calls per plan (the merge job itself is bounded by `max_actions_per_job`).
- `C9.7.5` — workspace budget policy.
- `C10.2.1` — HTTP binding match.
- `C10.3.2` — JIT elevation (Phase 1a).
- `C10.6.2` — no `url` / `endpoint` / `destination` in `configuration` (Phase 1b schema).
