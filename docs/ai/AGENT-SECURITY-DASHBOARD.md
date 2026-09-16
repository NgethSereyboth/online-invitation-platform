# Agent-Security Dashboard — Spec

> **Status**: Phase 1a design document.
> **Scope**: Anomaly detection on AI tool-invocation patterns + admin dashboard for forensic review.
> **AISVS driver**: C9.6.4 (anomaly detection on tool-invocation patterns), C9.6.5 (per-tool outcome metrics queryable for governance review), C10.7.3 (plans queryable by user / invitation / status for forensic review).
> **Codebase ground truth**:
> - Audit event source: `audit_events` table (hash-chained + immutable — `src/python/server.py:1137`, triggers at `src/python/server.py:1206-1207`).
> - Audit event writer: `src/python/server.py::write_audit_event` (line 1376).
> - AI subsystem audit callback: `ai_agent/service.py::_emit_audit` (line 64).
> - Existing admin audit endpoint: `src/python/server.py::studio_operations_audit` (line 5758).
> - Existing admin page: `src/html/admin.html` (4 tabs: users / templates / invitations / ai).
> - Existing analytics pattern: `src/js/analytics.js` (vanilla JS, fetch + render, no chart library — uses CSS bars).
> - Per-tool outcomes: `ai_tool_outcomes` table (`ai_agent/storage.py`).

## 1. Detection rules

The dashboard evaluates four detection rules. Each rule has a **window** (time range), a **threshold** (numeric condition), and an **action** (what to do when the rule fires).

### 1.1 Unusual volume (spike detection)

| Field | Value |
|---|---|
| **Rule ID** | `volume_spike` |
| **Window** | 5 minutes (rolling), compared against a 30-day baseline of the same actor + tool. |
| **Threshold** | The number of tool invocations by `(user_id, tool_id)` in the last 5 minutes exceeds `max(baseline_mean + 3 * baseline_stddev, baseline_p99 * 1.5, 5)`. The minimum of 5 prevents false positives on low-volume tools. |
| **Baseline** | Computed daily via a background job (per-tool, per-user statistics stored in `agent_security_baselines` table — see §3.2). The baseline is recomputed at 03:00 host-local time. |
| **Detection source** | `audit_events` table — count of `action LIKE 'ai.%'` events grouped by `(user_id, metadata_json->>'toolId')` over the last 5 minutes. |
| **Action** | Emit a `security.anomaly.volume_spike` audit event with `metadata={"userId": ..., "toolId": ..., "windowSeconds": 300, "observedCount": N, "baselineMean": ..., "baselineP99": ...}`. The dashboard surfaces the anomaly in the "Active anomalies" panel. If the spike is on a JIT-eligible tool, additionally emit a `security.jit_volume_spike` audit event. |
| **Severity** | `medium` by default; `high` if the tool is JIT-eligible AND `observedCount > 10 * baselineMean`. |

### 1.2 Off-hours bulk operations

| Field | Value |
|---|---|
| **Rule ID** | `off_hours_bulk` |
| **Window** | Single event (no rolling window). |
| **Threshold** | A tool invocation occurs outside the workspace's configured business hours (default 08:00-20:00 host-local, configurable per workspace via `workspaces.settings_json.businessHours`) AND the tool is one of: `merge.prepare_job`, `publish.prepare`, `publishing.configure_environment`, `plugin.configure`, `event.prepare_automation`, `message.prepare_send`. |
| **Detection source** | `audit_events` table — `action = 'ai.tool_authorization_consumed'` joined with `jit_elevations` (Phase 1a Stage 3) or with the tool's `risk` field. |
| **Action** | Emit a `security.anomaly.off_hours_bulk` audit event with `metadata={"userId": ..., "toolId": ..., "hourLocal": H, "businessHours": "08:00-20:00"}`. The dashboard surfaces the anomaly with a "Review off-hours operation" call-to-action. |
| **Severity** | `low` if the workspace has no business-hours configuration; `medium` if the operation is within 1 hour of the business-hours boundary; `high` if the operation is more than 2 hours outside the boundary. |

### 1.3 Permission-denied spikes

| Field | Value |
|---|---|
| **Rule ID** | `permission_denied_spike` |
| **Window** | 1 hour (rolling). |
| **Threshold** | The number of `ai.tool_permission_denied` audit events for a single `user_id` in the last hour exceeds `max(10, baseline_mean * 3)`. |
| **Detection source** | `audit_events` table — count of `action = 'ai.tool_permission_denied'` events grouped by `user_id` over the last hour. |
| **Action** | Emit a `security.anomaly.permission_denied_spike` audit event with `metadata={"userId": ..., "windowSeconds": 3600, "observedCount": N, "deniedToolIds": [...]}`. If the spike is from a single IP address (more than 80% of denials from one IP), additionally flag as a potential brute-force attempt and emit `security.brute_force_suspected`. |
| **Severity** | `medium` by default; `high` if the denials span more than 5 distinct tool IDs (broad capability probing); `critical` if brute-force is suspected. |

### 1.4 Repeated confirmation-boundary hits

| Field | Value |
|---|---|
| **Rule ID** | `confirmation_boundary_repeat` |
| **Window** | 10 minutes (rolling). |
| **Threshold** | The number of `ai.plan_confirmed` audit events for the same `(user_id, toolId)` pair where the plan was subsequently `cancelled` or `stale` exceeds 3 in 10 minutes. This pattern indicates the user (or an attacker) is repeatedly trying to confirm a high-risk operation but the plan keeps getting invalidated or cancelled — a sign of either a confused user or an attacker probing the confirmation boundary. |
| **Detection source** | `audit_events` table — sequence of `ai.plan_confirmed`, `ai.plan_cancelled`, `ai.plan_failed` events joined by `metadata_json->>'planId'`. |
| **Action** | Emit a `security.anomaly.confirmation_boundary_repeat` audit event with `metadata={"userId": ..., "toolId": ..., "windowSeconds": 600, "repeatCount": N}`. The dashboard surfaces a "User may need assistance" call-to-action linking to the agent's conversation log. |
| **Severity** | `low` by default; `medium` if the tool is JIT-eligible; `high` if the repeat count exceeds 10. |

## 2. Data sources

### 2.1 Primary source: `audit_events` table

The dashboard queries the existing hash-chained, immutable `audit_events` table (`src/python/server.py:1137`). No new audit events are required for the basic detection rules — they re-use the existing `ai.plan_proposed`, `ai.plan_confirmed`, `ai.tool_authorized`, `ai.tool_authorization_consumed`, `ai.plan_completed`, `ai.plan_failed`, `ai.plan_cancelled` events.

The new audit event types emitted by the dashboard itself are:

- `security.anomaly.volume_spike`
- `security.anomaly.off_hours_bulk`
- `security.anomaly.permission_denied_spike`
- `security.anomaly.confirmation_boundary_repeat`
- `security.brute_force_suspected`
- `security.jit_volume_spike`
- `security.jit.requested` / `security.jit.granted` / `security.jit.denied` / `security.jit.expired` / `security.jit.revoked` (these are the JIT audit events from `docs/ai/JIT-ELEVATION.md` §3.2, aliased for the dashboard)

These events are written to the same `audit_events` table and inherit the hash-chaining + immutability guarantees.

### 2.2 Secondary source: `ai_tool_outcomes` table

The `ai_tool_outcomes` table (`ai_agent/storage.py`) records per-tool success/error_code. This table is the source for:

- Per-tool success rate (for the "Tools" panel — see §4.3).
- Per-tool error-code distribution (for the drill-down view).

### 2.3 Tertiary source: `jit_elevations` table (Phase 1a Stage 3)

The `jit_elevations` table (from `docs/ai/JIT-ELEVATION.md` §3.1) is the source for:

- Active JIT grants (for the "Active JIT" panel — see §4.4).
- JIT request → grant → consume latency.
- JIT denial rate.

### 2.4 Baseline storage: `agent_security_baselines` table

Stores the rolling 30-day baseline statistics per `(user_id, tool_id)` for the spike-detection rule.

```sql
CREATE TABLE IF NOT EXISTS agent_security_baselines(
    user_id TEXT NOT NULL,
    tool_id TEXT NOT NULL,
    window_seconds INTEGER NOT NULL,           -- 300 for 5-minute windows, 3600 for hourly
    baseline_mean REAL NOT NULL DEFAULT 0,
    baseline_stddev REAL NOT NULL DEFAULT 0,
    baseline_p99 REAL NOT NULL DEFAULT 0,
    sample_count INTEGER NOT NULL DEFAULT 0,
    computed_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, tool_id, window_seconds)
);
```

## 3. Backend endpoints

All endpoints require an authenticated admin user (`accountRole == "admin"` per `ai_agent/capabilities.py:availability()` line 238-239). The endpoints are added to `src/python/server.py` and exposed under `/api/admin/agent-security/*`.

### 3.1 `GET /api/admin/agent-security/overview`

Returns the high-level metrics for the dashboard's top panel.

**Response shape**:

```json
{
  "windowSeconds": 3600,
  "totals": {
    "toolInvocations": 1234,
    "uniqueUsers": 56,
    "uniqueTools": 42,
    "jitGrantsActive": 3,
    "jitGrantsLast24h": 17,
    "permissionDenied": 8,
    "anomaliesLast24h": 2
  },
  "byRisk": {"low": 800, "medium": 350, "high": 84},
  "byExecutor": {"server": 200, "client": 900, "editor-action": 100, "platform-api": 34},
  "topTools": [
    {"toolId": "object.update", "count": 220, "successRate": 0.99},
    {"toolId": "transform.move", "count": 180, "successRate": 1.0}
  ],
  "topUsers": [
    {"userId": "u-1", "actorEmail": "host@example.com", "count": 45, "distinctTools": 12}
  ],
  "anomalySummary": {
    "volume_spike": 1,
    "off_hours_bulk": 0,
    "permission_denied_spike": 1,
    "confirmation_boundary_repeat": 0
  },
  "immutable": true,
  "hashChained": true
}
```

**Implementation**: a single SQL query against `audit_events` (count by action / risk / executor) joined with `ai_tool_outcomes` (for success rate) and `jit_elevations` (for active JIT count). The query is bounded to the last hour by default; `?window=3600` accepts 300 / 3600 / 86400.

### 3.2 `GET /api/admin/agent-security/anomalies`

Returns the list of anomalies detected in the last 24 hours (or `?window=86400`).

**Response shape**:

```json
{
  "anomalies": [
    {
      "id": "evt-...",
      "type": "volume_spike",
      "severity": "medium",
      "userId": "u-1",
      "actorEmail": "host@example.com",
      "toolId": "guest.delete",
      "observedCount": 12,
      "baselineMean": 1.2,
      "baselineP99": 4.0,
      "windowSeconds": 300,
      "detectedAt": 1710403200000,
      "metadata": {"...": "..."}
    }
  ],
  "windowSeconds": 86400,
  "total": 2
}
```

**Implementation**: `SELECT * FROM audit_events WHERE action LIKE 'security.anomaly.%' AND created_at >= ? ORDER BY created_at DESC LIMIT ?` with `?limit=200` (default).

### 3.3 `GET /api/admin/agent-security/tools/{toolId}/invocations`

Returns the per-tool invocation log for forensic review.

**Path parameter**: `{toolId}` — the tool id (URL-encoded; e.g. `publish.prepare` becomes `publish.prepare`).

**Query parameters**:
- `?window=3600` — time window in seconds (300 / 3600 / 86400 / 604800). Default 86400.
- `?userId=` — filter by user.
- `?invitationId=` — filter by invitation.
- `?status=` — filter by outcome status (`completed` / `failed` / `cancelled`).
- `?limit=200` — max 500.

**Response shape**:

```json
{
  "toolId": "publish.prepare",
  "windowSeconds": 86400,
  "invocations": [
    {
      "id": "evt-...",
      "userId": "u-1",
      "actorEmail": "host@example.com",
      "invitationId": "inv-1",
      "planId": "plan-...",
      "risk": "high",
      "permission": "manage",
      "executor": "server",
      "status": "completed",
      "errorCode": "",
      "ipAddress": "203.0.113.1",
      "createdAt": 1710403200000,
      "metadata": {"...": "..."}
    }
  ],
  "summary": {
    "total": 17,
    "successRate": 0.94,
    "uniqueUsers": 3,
    "uniqueInvitations": 5,
    "errorCodes": {"agent_internal_error": 1}
  }
}
```

**Implementation**: `SELECT a.*, u.email, o.success, o.error_code FROM audit_events a LEFT JOIN users u ON u.id=a.user_id LEFT JOIN ai_tool_outcomes o ON o.plan_id=a.metadata_json->>'planId' WHERE a.action IN ('ai.tool_authorization_consumed', 'ai.plan_completed', 'ai.plan_failed') AND a.metadata_json->>'toolId'=? AND a.created_at >= ?`.

### 3.4 `GET /api/admin/agent-security/users/{userId}/activity`

Returns the per-user activity log (cross-tool) for forensic review.

**Response shape**: same as §3.3 but grouped by user, not by tool.

### 3.5 `GET /api/admin/agent-security/jit/active`

Returns the list of currently-active JIT grants (Phase 1a Stage 3).

**Response shape**:

```json
{
  "activeGrants": [
    {
      "id": "...",
      "userId": "u-1",
      "actorEmail": "host@example.com",
      "toolId": "publish.prepare",
      "resourceType": "invitation",
      "resourceId": "inv-1",
      "action": "publish",
      "grantedAt": 1710403200000,
      "expiresAt": 1710403500000,
      "secondsRemaining": 240,
      "autoEligible": false,
      "approverId": "admin-1",
      "approvalChannel": "web",
      "reason": "publishing the final invitation"
    }
  ],
  "total": 3
}
```

### 3.6 `POST /api/admin/agent-security/jit/{id}/revoke`

Revokes an active JIT grant. Requires admin role. Body: `{"reason": "..."}`.

Emits the `jit.revoked` audit event via `JITElevationManager.revoke()`.

### 3.7 `GET /api/admin/agent-security/export`

Exports the last 7 days of audit events as a CSV (or NDJSON) for offline forensic analysis. Required for compliance audits.

## 4. Frontend spec

The dashboard is added to the existing admin page at `src/html/admin.html` as a fifth tab: "Agent security". It uses vanilla JS (no chart library — same pattern as `src/js/analytics.js`) and fetches data from the endpoints in §3.

### 4.1 Tab structure

The existing admin page has 4 tabs (users / templates / invitations / ai). Add a fifth:

```html
<button data-admin-tab="agent-security">Agent security</button>
```

Bilingual tooltip (via `title` attribute):
- EN: "Monitor AI tool invocations and detect anomalies."
- KH: "ត្រួតពិនិត្យការហៅឧបករណ៍ AI និងរកឃើញភាពមិនធម្មតា។"

The tab's panel contains four sub-sections:

### 4.2 Sub-section 1: Overview

Top-row metrics (4 cards):

| Card | EN label | KH label | Value source |
|---|---|---|---|
| Tool invocations (24h) | "Tool invocations (24h)" | "ការហៅឧបករណ៍ (24 ម៉ោង)" | `overview.totals.toolInvocations` |
| Active JIT grants | "Active JIT grants" | "ការអនុញ្ញាត JIT សកម្ម" | `overview.totals.jitGrantsActive` |
| Permission denied (1h) | "Permission denied (1h)" | "ការបដិសេធសិទ្ធិ (1 ម៉ោង)" | `overview.totals.permissionDenied` |
| Anomalies (24h) | "Anomalies (24h)" | "ភាពមិនធម្មតា (24 ម៉ោង)" | `overview.totals.anomaliesLast24h` |

Below the cards: two CSS bar charts (no chart library — same pattern as `src/js/analytics.js`):

1. **Invocations by risk tier** — three bars (low / medium / high), colored green / amber / red.
2. **Top 10 tools by invocation count** — horizontal bars, with the tool id as the label and the count as the value. Clicking a bar navigates to §4.3 (per-tool drill-down).

### 4.3 Sub-section 2: Tools

A table of all 80 tools with columns:

| Column | EN | KH |
|---|---|---|
| Tool ID | "Tool ID" | "លេខសម្គាល់ឧបករណ៍" |
| Group | "Group" | "ក្រុម" |
| Risk | "Risk" | "ហានិភ័យ" |
| Permission | "Permission" | "សិទ្ធិ" |
| Invocations (24h) | "Invocations (24h)" | "ការហៅ (24 ម៉ោង)" |
| Success rate | "Success rate" | "អត្រាជោគជ័យ" |
| Unique users | "Unique users" | "អ្នកប្រើពិសេស" |
| Anomalies (24h) | "Anomalies (24h)" | "ភាពមិនធម្មតា (24 ម៉ោង)" |
| Actions | "Actions" | "សកម្មភាព" |

Each row has a "View invocations" link (EN: "View invocations" / KH: "មើលការហៅ") that navigates to §3.3's per-tool drill-down.

### 4.4 Sub-section 3: Active JIT grants

A live-updating table (polls `/api/admin/agent-security/jit/active` every 5 seconds). Columns:

| Column | EN | KH |
|---|---|---|
| User | "User" | "អ្នកប្រើ" |
| Tool | "Tool" | "ឧបករណ៍" |
| Resource | "Resource" | "ធនធាន" |
| Granted at | "Granted at" | "បានផ្ដល់នៅ" |
| Expires in | "Expires in" | "ផុតកំណត់ក្នុង" |
| Reason | "Reason" | "ហេតុផល" |
| Approver | "Approver" | "អ្នកអនុម័ត" |
| Actions | "Actions" | "សកម្មភាព" |

Each row has a "Revoke" button (EN: "Revoke" / KH: "ដកហូត") that calls `POST /api/admin/agent-security/jit/{id}/revoke` with a reason prompt.

The "Expires in" column counts down in real time (every second). When a grant expires, the row is removed automatically.

### 4.5 Sub-section 4: Anomalies

A timeline (newest first) of anomalies detected in the last 24 hours. Each anomaly card shows:

| Field | EN label | KH label |
|---|---|---|
| Type | "Type" | "ប្រភេទ" |
| Severity | "Severity" | "សភាពធ្ងន់ធ្ងរ" |
| Detected at | "Detected at" | "បានរកឃើញនៅ" |
| User | "User" | "អ្នកប្រើ" |
| Tool | "Tool" | "ឧបករណ៍" |
| Description | "Description" | "ការពិពណ៌នា" |
| Observed count | "Observed count" | "ចំនួនដែលបានអង្កេត" |
| Baseline | "Baseline" | "មូលដ្ឋាន" |

Severity colors: `low` (gray) / `medium` (amber) / `high` (red) / `critical` (dark red).

Each card has a "Investigate" button (EN: "Investigate" / KH: "ស្រាវជ្រាវ") that links to the per-user activity endpoint (§3.4).

### 4.6 Localization strings

All user-facing strings are bilingual (EN + KH) per ROADMAP ground rule 5. The strings are stored in the existing i18n registry (`src/js/i18n.js` — to be added in Phase 2b; for Phase 1a, the strings are inlined with both variants in the HTML `data-en` and `data-km` attributes, and the existing language toggle in `src/js/theme-init.js` swaps them).

Example HTML:

```html
<span data-en="Tool invocations (24h)" data-km="ការហៅឧបករណ៍ (24 ម៉ោង)">Tool invocations (24h)</span>
```

## 5. Backend implementation skeleton

The endpoints are implemented in a new module `ai_agent/security_dashboard.py` (skeleton only in Phase 1a — wiring into `src/python/server.py` is deferred to Phase 1a Stage 3).

```python
# ai_agent/security_dashboard.py (illustrative skeleton — not committed in Phase 1a)
from __future__ import annotations
from typing import Any, Callable
import json

class SecurityDashboard:
    def __init__(self, connect: Callable[[], Any], audit: Callable[..., Any] | None = None):
        self.connect = connect
        self.audit = audit

    def overview(self, window_seconds: int = 3600) -> dict[str, Any]:
        # SELECT count(*) FROM audit_events WHERE action LIKE 'ai.%' AND created_at >= ?
        # GROUP BY risk, executor, toolId, userId
        # JOIN ai_tool_outcomes ON plan_id for success rate
        # JOIN jit_elevations WHERE status='granted' for active JIT count
        ...

    def anomalies(self, window_seconds: int = 86400, limit: int = 200) -> dict[str, Any]:
        # SELECT * FROM audit_events WHERE action LIKE 'security.anomaly.%' AND created_at >= ?
        ...

    def tool_invocations(self, tool_id: str, window_seconds: int = 86400,
                        user_id: str = "", invitation_id: str = "",
                        status: str = "", limit: int = 200) -> dict[str, Any]:
        # SELECT a.*, u.email, o.success, o.error_code
        # FROM audit_events a
        # LEFT JOIN users u ON u.id = a.user_id
        # LEFT JOIN ai_tool_outcomes o ON o.plan_id = json_extract(a.metadata_json, '$.planId')
        # WHERE a.action IN ('ai.tool_authorization_consumed', 'ai.plan_completed', 'ai.plan_failed')
        #   AND json_extract(a.metadata_json, '$.toolId') = ?
        #   AND a.created_at >= ?
        ...

    def active_jit(self) -> dict[str, Any]:
        # SELECT j.*, u.email FROM jit_elevations j LEFT JOIN users u ON u.id = j.user_id
        # WHERE j.status = 'granted' AND j.expires_at > ?
        ...

    def revoke_jit(self, elevation_id: str, revoked_by: str, reason: str) -> dict[str, Any]:
        # Delegate to JITElevationManager.revoke()
        ...
```

## 6. Detection-rule implementation skeleton

The four detection rules are implemented in `ai_agent/security_rules.py` (skeleton only in Phase 1a — wired into the audit-event writer in Phase 1a Stage 3).

```python
# ai_agent/security_rules.py (illustrative skeleton — not committed in Phase 1a)
from __future__ import annotations
from typing import Any, Callable
import time

class SecurityRuleEngine:
    """Evaluates the four detection rules against the audit_events table.

    Designed to be called by a background job every 60 seconds, OR by the
    audit-event writer synchronously after each ai.* event (low-overhead rules).
    """

    def __init__(self, connect: Callable[[], Any], audit: Callable[..., Any] | None = None):
        self.connect = connect
        self.audit = audit

    def evaluate_all(self) -> int:
        """Run all four rules. Returns the number of anomalies detected."""
        count = 0
        count += self._rule_volume_spike()
        count += self._rule_off_hours_bulk()
        count += self._rule_permission_denied_spike()
        count += self._rule_confirmation_boundary_repeat()
        return count

    def _rule_volume_spike(self) -> int:
        """Rule 1.1: unusual volume (spike detection)."""
        ...

    def _rule_off_hours_bulk(self) -> int:
        """Rule 1.2: off-hours bulk operations."""
        ...

    def _rule_permission_denied_spike(self) -> int:
        """Rule 1.3: permission-denied spikes."""
        ...

    def _rule_confirmation_boundary_repeat(self) -> int:
        """Rule 1.4: repeated confirmation-boundary hits."""
        ...
```

## 7. Background scheduler

A background job (registered in `platform_v32/jobs.py::JobQueue`) runs the rule engine every 60 seconds. The job is registered as `agent-security-sweep`:

```python
# platform_v32/service.py (additive registration — Phase 1a Stage 3)
self.jobs.register('agent-security-sweep', self._agent_security_sweep_job)

def _agent_security_sweep_job(self, job):
    from ai_agent.security_rules import SecurityRuleEngine
    engine = SecurityRuleEngine(self.connect, self.audit)
    anomalies = engine.evaluate_all()
    return {"anomalies": anomalies}
```

The same job also calls `JITElevationManager.sweep_expired()` to transition expired JIT grants.

## 8. Acceptance criteria

- [ ] `agent_security_baselines` table exists on SQLite + PostgreSQL.
- [ ] Four detection rules implemented in `ai_agent/security_rules.py` with unit tests covering the threshold boundary for each rule.
- [ ] `GET /api/admin/agent-security/overview` returns the response shape in §3.1 within 500ms for a 1-hour window with 10 000 audit events.
- [ ] `GET /api/admin/agent-security/anomalies` returns the response shape in §3.2.
- [ ] `GET /api/admin/agent-security/tools/{toolId}/invocations` returns the response shape in §3.3.
- [ ] `GET /api/admin/agent-security/jit/active` returns the response shape in §3.5.
- [ ] `POST /api/admin/agent-security/jit/{id}/revoke` revokes the grant and emits `jit.revoked` audit event.
- [ ] Admin HTML page (`src/html/admin.html`) has a fifth tab "Agent security" with the four sub-sections in §4.
- [ ] All user-facing strings have EN + KH variants (per ROADMAP ground rule 5).
- [ ] Background `agent-security-sweep` job runs every 60 seconds and transitions expired JIT grants.
- [ ] AISVS C9.6.4 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
- [ ] AISVS C9.6.5 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
- [ ] AISVS C10.7.3 status upgraded from `partial` to `pass` in `docs/ai/AISVS-C9-C10-MAPPING.md`.
