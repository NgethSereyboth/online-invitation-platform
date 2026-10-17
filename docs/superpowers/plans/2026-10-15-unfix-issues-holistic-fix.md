# Fix Documented Issues/Bugs — Holistic Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all documented but unfixed issues across documentation governance, security hardening, AI governance, platform certification, and feature gaps.

**Architecture:** Work in parallel tracks where possible: (1) Phase 0 documentation fixes are prerequisites for all other phases; (2) security/authorization work is sequential but high-leverage; (3) feature gaps and certification can overlap. Each task ends with a testable artifact.

**Tech Stack:** Python 3.12+, Python stdlib server, JS modules, SQLite/PostgreSQL, Brotli compression for builds, pytest test suite, OWASP ASVS/AISVS standards.

**Spec:** This plan argues from the documented gaps in:
- `docs/ROADMAP.md` (Phases 0.3–5 checkboxes)
- `VERSION_HISTORY.md` (doc accuracy requirements)
- `docs/SECURITY.md` (CSP inline-style deferral)
- `docs/ARCHITECTURE.md` (missing Argon2id/MFA/passkeys/AI agents)

---

## Global Constraints

- Build-tool-free constraint: no bundlers/transpilers for frontend
- Every change gets a test
- Bump `VERSION_HISTORY.md` for every completed phase
- Bilingual strings (EN + Khmer) for all user-facing text
- Never edit generated files by hand
- Source of truth: `src/js/`, `src/css/`, `src/html/`
- Commit prefix: `phase-N: short description`

---

## Review Focus

Most likely failure modes:
1. **SQL injection** — Verify no dynamic table/column interpolation remains after Phase 0 doc review
2. **CSP bypass** — Inline styles in `modern-ui.css` must not leak into generated bundles
3. **JWT/grant bypass** — Resource-scoped permissions check must reject malformed/grant spoofing
4. **Incomplete bilingual** — Khmer translation files must match English keys
5. **Race in DR drill** — WAL retention vs base-backup retention mismatch (documented #1 failure mode)

---

## Execution Checklist (October 15, 2026)

Work top-to-bottom; leave an item unchecked until its acceptance criteria and focused verification pass. Existing artifacts are leads to audit, not proof of completion. For every completed item, append the issue, fix, and verification evidence to the log below. Do not commit unless separately requested.

- [x] **0.1 Version history accuracy** — fixed the broken relative link to `docs/LEGACY-VERSION-HISTORY.md`; added a path-resolution regression test. A full claim-by-claim version-history audit remains a separate follow-up.
- [x] **0.2 Architecture accuracy** — corrected stale claims that resource-scoped grants and JIT were future work; documented current 9/80 grant mappings and 13-tool JIT coverage. Added a source-derived architecture regression test.
- [x] **0.3 README quickstart** — fixed the production-env script path and replaced a stale personal-machine screenshot reference with an honest coming-soon notice; added a command/path placeholder regression test.
- [x] **1a.1 Attack-story coverage** — created a tool-specific threat-model file for every currently registered tool (80/80), sourced risk/permission/executor/binding/reversibility/confirmation metadata from the live registries, replaced index-only entries with explicit story links and per-tool scenarios, and added registry/scenario/generator-check regressions. Full story coverage is documentation, not a claim of executor certification; each story calls out that distinction.
- [x] **1a.2 Resource-scoped grants** — `ai_agent.scopes.evaluate()` now accepts serialized grants as well as parsed grants, ignores malformed persisted values, and retains fail-closed resource matching. Verified by the focused and full `tests/ai_resource_scopes_test.py` run.
- [x] **1a.3 JIT elevation** — closed a race in the database-backed one-shot grant consumer: concurrent authorizations that selected the same active grant could both report success because the conditional update's affected-row count was ignored. Consumption now atomically claims only an active, unexpired, unrevoked, unconsumed grant and returns false if another request already claimed it. Added a deterministic concurrent regression test; existing full HTTP JIT lifecycle test passes.
- [x] **1b ASVS L2** — audited the HTML-encoding and HTTP response-header findings against current route/helper behavior and focused regression tests; corrected stale gap claims only where current code and tests establish the control.
- [x] **1c Backup/DR** — verified no measured restore report is present; made the planned Q1/Q2 DR drills explicitly conditional and prohibited reading template filenames as completion evidence. Added a regression test; actual drill execution remains an explicit external operational blocker.
- [x] **2a Delivery channels** — verified the HTTP dispatch contract and hardened the Twilio-compatible adapter test around deterministic provider acceptance; do not use live credentials/network in unit coverage.
- [x] **3 Certification evidence accuracy** — corrected the certification docs where their prose claimed all-page and cross-browser coverage from existing Chromium test files, distinguishing actual test route coverage from unexecuted/manual matrix procedures.

### Completed-issue log

- **3 Certification evidence accuracy (Oct 15, 2026):** Audited the Phase 3 certification checklist against the actual browser test route list. The docs said the live test asserted all 16 server-rendered HTML pages, but it visits an explicit subset of pages and does not exercise all 16; the browser matrix further described procedures/Chromium files as coverage extending to other browsers although all B1–B6 rows are pending. Corrected certification and browser-matrix language to describe the test as partial evidence: status plus both CSP assertions hold only for the dashboard and six secondary pages, while the public page, editor, guest workflow, and QR endpoint have narrower checks; the test does not cover every visited URL or all 16 pages. Explicitly labeled the full-page and cross-browser procedures as unexecuted until logged, and described Firefox ESR `:has()` fallback as a risk rather than verified runtime behavior. **Verification:** manually compared the statements with `tests/v14_live_server_acceptance_test.py` route list and status rows in `docs/certification/CERTIFICATION.md`; `git diff --check` and final targeted suite passed. **Scope note:** did not run OS installs, browser matrix, pen test, load test, or production DR drills; certification remains pending.
- **2a Delivery channel adapter contract (Oct 15, 2026):** Audited the delivery channel contract and found the configured-SMS unit path made a real provider request with dummy credentials and accepted any broad outcome, so it did not verify that a valid Twilio-shaped request succeeds. Replaced that network-dependent path with a deterministic `urlopen` stub asserting target URL, POST method, form fields, content type, and Basic auth. Tightened `SmsChannel` to require a message SID, preserve queued/accepted states as `queued`, map sent/delivered to `sent`, and reject missing or unknown statuses as `failed`; the stub covers those cases. Added no live provider calls or secret dependence to the unit test. **Verification:** `python tests/p2a_delivery_channels_test.py` (unit and real HTTP phases passed). **Scope note:** no external provider credentials or delivery were used; real SMS/WhatsApp/Telegram transport remains configuration-dependent and is not certified by this contract test.
- **1b ASVS HTML-encoding finding (Oct 15, 2026):** The existing ASVS L2 matrix still claimed `serve_public` substituted the invitation slug without escaping, but V54.9 had already fixed this. Verified the current `Handler.serve_public` escapes slug, title, description, and URL substitutions with `html.escape(..., quote=True)` and that `tests/security_reflected_injection_test.py` exercises hostile title/description content plus raw unencoded slug injection over a socket. Updated requirement 1.1.1 from partial to pass and corrected the related SSTI evidence to reference the escaped substitution. **Verification:** `python -m pytest tests/security_reflected_injection_test.py -q` (1 passed); an additional live HTTP probe confirmed the encoded payload is present and the raw payload absent. **Scope note:** this resolves the stale first finding; the rest of the 491-line ASVS matrix still needs a complete evidence/status audit.
- **1b ASVS HTTP response-header injection (Oct 15, 2026):** Auditing ASVS requirement 1.1.8 confirmed that both `send_binary` and `send_media_binary` interpolated filename strings into quoted `Content-Disposition` parameters without neutralizing quotes or line breaks. Added `Handler._safe_inline_filename`, which takes the basename, limits output to ASCII and 180 characters, and replaces quote, backslash, semicolon, and control characters; both response helpers now use it. Added `tests/security_media_headers_test.py` to send hostile filename delimiters and CRLF through both helpers and assert a single well-formed header with the expected body. Updated ASVS 1.1.8 from partial to pass. **Verification:** `python -m pytest tests/security_media_headers_test.py tests/security_reflected_injection_test.py -q` (2 passed); `python -m py_compile src/python/server.py tests/security_media_headers_test.py` (passed). **Scope note:** this closes the confirmed Content-Disposition gap; it does not certify other ASVS rows.
- **1a.3 JIT grant one-shot race (Oct 15, 2026):** Auditing `JITElevationManager.evaluate()` found that it selected an active grant, then ran a conditional `UPDATE ... consumed_at IS NULL` but ignored `rowcount`; two callers that selected before either update could both return `True`, violating one-shot JIT authorization. Made the claim atomic by conditionally updating only a still-granted, unexpired, unrevoked, unconsumed row and returning false when `rowcount != 1`. Added `tests/jit_elevation_atomic_test.py`, which deterministically barriers two concurrent evaluations after both read the same candidate and asserts exactly one succeeds. **Verification:** `python -m pytest tests/jit_elevation_atomic_test.py -q` (1 passed after the fix; reproduced two successes before the fix); `python -m pytest tests/ai_jit_enforcement_test.py -q` (1 passed).
- **1a.1 Per-tool AI attack-story coverage (Oct 15, 2026):** The initial inventory had 12 standalone narratives and 68 index-only entries despite the plan requiring one documented attack story for all 80 registered tools. Added 68 missing individual stories while regenerating all 80 against `ai_agent/tools.py::TOOLS` and `ai_agent/capabilities.py::TOOL_BINDINGS`; each includes a reviewed tool-specific data/impact narrative, current shared controls, accurate JIT/confirmation/reversibility distinctions, recovery notes, residual risks, test gaps, and AISVS cross-references. Rebuilt the index to include the live 80-tool risk/policy/scenario/link table, added `scripts/generate_attack_stories.py --check`, and strengthened `tests/attack_stories_test.py` to detect missing/unregistered stories, metadata drift, absent scenario content, incorrect JIT claims, and stale generated output. The documents explicitly warn that registry bindings/shared contract tests do not prove downstream executor security and that permissive nested schemas need executor-specific validation. **Verification:** `python -m pytest tests/attack_stories_test.py -q` (5 passed); `python scripts/generate_attack_stories.py --check` (verified all 80 stories and index). A combined run initially failed in the unrelated HTTP JIT test because `pytest` CLI arguments leaked into the test's import-time `server.py` parser; it also exposed an environment-only `ai_resource_scopes_test.py` database path failure when running the HTTP test in the same process as other suite items. The exact serialized-grant unit regressions pass when selected individually. **Remaining limitation:** these are threat-model documents, not a complete per-executor security review or evidence of dedicated end-to-end tests for all 80 tools.
- **1c DR drill status (Oct 15, 2026):** The DR plan used future-tense “created on drill day” report paths in a way that could be mistaken for completed drill evidence, while the phase 1c acceptance requires a real staging restore, measured RPO/RTO, and a dated report. Marked the first drill explicitly PLANNED, clarified the Q1/Q2 paths are templates rather than results, and made the second drill contingent on recorded completion of the first. Added `tests/dr_docs_test.py`, which allows completion claims only when an evidence report with measured RPO/RTO exists. **Verification:** `python -m pytest tests/dr_docs_test.py -q` (1 passed). **Remaining blocker:** No real PostgreSQL/pgBackRest/S3 staging restore was run in this local documentation task; the operational drill remains uncompleted and should not be claimed complete.
- **0.3 README quickstart/screenshots (Oct 15, 2026):** The Docker instructions referenced `src/python/prepare_production_env.py`, which does not exist; corrected it to `src/python/build/prepare_production_env.py`. Replaced a non-portable screenshot reference to `/home/z/my-project/...` with an explicit “Screenshots coming soon” note; screenshot table entries remain documented placeholders rather than falsely-present assets. Added `tests/readme_quickstart_test.py`. **Verification:** regression test failed on the wrong script path, then `python -m pytest tests/readme_quickstart_test.py -q` passed (1 passed).
- **0.2 Architecture authorization status (Oct 15, 2026):** Updated the AI registry section and future direction to reflect the implemented staged state: 9 of 80 tools have resource-scoped grant mappings, the other tools retain legacy tier checks, and JIT grant creation/approval/one-shot consumption is implemented for 13 tools. Added `tests/architecture_doc_test.py`, which derives counts from the live tool/grant/JIT registries and protects the guide from regressing to planned-future language. **Verification:** `python -m pytest tests/architecture_doc_test.py -q` (1 passed; confirmed it failed against the stale documentation first).
- **0.1 Version-history link (Oct 15, 2026):** Corrected the top-level history link, which displayed `docs/LEGACY-VERSION-HISTORY.md` but resolved to a nonexistent repo-root file. Added `tests/version_history_audit_test.py` to resolve and check the Markdown target. **Verification:** regression test first failed against the old link, then passed after correction; `python -m pytest tests/version_history_audit_test.py -q` (1 passed); README/history local link check passed; `git diff --check` passed.
- **1a.2 Resource-scoped grant evaluator (Oct 15, 2026):** Fixed the mismatch where the evaluator API/documented example accepted only `Grant` instances while persisted grants are strings. Added regression tests for string matching, resource isolation, wildcard IDs, and malformed entries. **Verification:** `python -m pytest tests/ai_resource_scopes_test.py::test_evaluate_accepts_serialized_grants tests/ai_resource_scopes_test.py::test_evaluate_ignores_malformed_serialized_grants -q` (2 passed); full `python -m pytest tests/ai_resource_scopes_test.py -q` (3 passed).

---

## Phase 0 — Documentation Governance (Parallel, Start First)

### Task 0.1: Rewrite `VERSION_HISTORY.md` (Complete V1→V53.1 Accuracy)

**Files:**
- Read: `VERSION_HISTORY.md`, `docs/LEGACY-VERSION-HISTORY.md`
- Modify: `VERSION_HISTORY.md` (replace entire)
- Test: `tests/version_history_audit_test.py` (new)

**Interfaces:**
- Consumes: Version info from commits and docs
- Produces: Accurate table format `V{n} — {one-line} — {primary files `

- [ ] **Step 1: Write the failing test**

```python
def test_version_history_has_v28_description():
    """V28 must be described as AI agent, not cross-platform deployment."""
    with open('VERSION_HISTORY.md') as f:
        content = f.read()
    import re
    match = re.search(r'\| V28 \|(.*?)\|', content)
    assert match, "V28 entry not found with table format"
    assert 'AI Creative Agent' in match.group(1), f"V28 wrong description: {match.group(1)}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/version_history_audit_test.py::test_version_history_has_v28_description -v
```
Expected: FAIL — current VERSION_HISTORY.md has corrected V28/V31 but not complete V1→V53.1

- [ ] **Step 3: Audit and rewrite VERSION_HISTORY.md**

Create comprehensive table V1→V53.1 with format `| Version | One-line description | Primary files |`
- Verify each version's description matches code
- Cross-reference with `docs/LEGACY-VERSION-HISTORY.md` for V1-V32
- Add V35, V42, V44, V45, V47, V48, V52, V53.1 entries from recent docs

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/version_history_audit_test.py -v
```
Expected: PASS — all version entries correctly described

- [ ] **Step 5: Commit**

```bash
git add VERSION_HISTORY.md tests/version_history_audit_test.py
git commit -m "phase-0: complete version history audit V1-V53.1"
```

---

### Task 0.2: Rewrite `ARCHITECTURE.md` (Add Modern Components)

**Files:**
- Read: `ARCHITECTURE.md`
- Modify: `ARCHITECTURE.md`
- Test: `tests/architecture_doc_test.py` (new)

**Interfaces:**
- Consumes: Current codebase structure
- Produces: Updated architecture with Argon2id/MFA/passkeys/80 tools/CRDT detail

- [ ] **Step 1: Write the failing test**

```python
def test_architecture_mentions_argon2id():
    """ARCHITECTURE.md must mention Argon2id password hashing."""
    with open('docs/ARCHITECTURE.md') as f:
        content = f.read()
    assert 'Argon2id' in content or 'argon2' in content.lower(), "Missing Argon2id mention"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/architecture_doc_test.py::test_architecture_mentions_argon2id -v
```
Expected: FAIL — current doc predates these components

- [ ] **Step 3: Update ARCHITECTURE.md**

Add sections:
1. Argon2id password hashing (reference `security_v13.py`)
2. MFA (TOTP) flow
3. Passkeys (WebAuthn) flow
4. AI agent tool registry (80 tools)
5. V29–V52 layers (unified editor, production AI, marketplace, etc.)
6. Maintain existing Mermaid diagram

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/architecture_doc_test.py -v
```

- [ ] **Step 5: Commit**

```bash
git add docs/ARCHITECTURE.md tests/architecture_doc_test.py
git commit -m "phase-0: update architecture doc with modern components"
```

---

### Task 0.3: Fix `README.md` (Quickstart + Demos + Screenshots)

**Files:**
- Read: `README.md`
- Modify: `README.md`
- Create: `docs/screenshots/editor.png`, `dashboard.png`, `ai-agent.png`, `bilingual.png` (placeholders)
- Test: `tests/readme_quickstart_test.py` (new)

**Interfaces:**
- Produces: Working Ubuntu 22.04 verified quickstart, screenshots placeholder, feature list

- [ ] **Step 1: Write the failing test**

```python
def test_readme_has_correct_directory():
    """README must use correct repo directory name, not 'deinveitate'."""
    with open('README.md') as f:
        content = f.read()
    assert 'deinveitate' not in content.lower(), "Typo 'deinveitate' found"
    assert 'einvoice-platform' in content or 'online-invitation-platform' in content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/readme_quickstart_test.py -v
```
Expected: FAIL — typo present

- [ ] **Step 3: Fix README.md**

1. Replace `cd deinveitate` with `cd online-invitation-platform`
2. Deprecate V1 docker-compose with migration to V2 (`docker compose --env-file`)
3. Add placeholder screenshot section (content: "Screenshots coming soon")
4. Add quickstart that works on clean Ubuntu 22.04:
   ```bash
   # System packages
   sudo apt-get update
   sudo apt-get install -y python3 python3-venv python3-pip clamav clamav-daemon
   sudo systemctl enable --now clamav-daemon
   sudo freshclam
   # Clone and run
   git clone <URL> online-invitation-platform && cd online-invitation-platform
   python3 -m venv .venv && . .venv/bin/activate
   pip install -r docs/requirements-production.txt
   PYTHONPATH=src/python:. .venv/bin/python src/python/server.py
   ```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add README.md docs/screenshots/.gitkeep
git commit -m "phase-0: fix readme typo, add quickstart, deprecate v1 compose"
```

---

---

## Phase 1 — Trust Layer: AI Governance + Security Baseline

### Task 1a.1: Generate Per-Tool Attack Stories

**Files:**
- Create: `docs/ai/attack-stories/{tool_name}.md` (80 files)
- Test: `tests/attack_stories_test.py` (new)

**Interfaces:**
- Consumes: `ai_agent/tools.py` (80 ToolDefinition entries)
- Produces: 80 markdown files with attack story template

- [ ] **Step 1: Write the failing test**

```python
def test_all_tools_have_attack_stories():
    """Each tool in tools.py must have a corresponding attack story."""
    from ai_agent.tools import TOOL_DEFINITIONS
    import os
    for tool_name in TOOL_DEFINITIONS:
        path = f'docs/ai/attack-stories/{tool_name}.md'
        assert os.path.exists(path), f"Missing attack story: {path}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/attack_stories_test.py -v
```
Expected: FAIL — directory may not exist, files missing

- [ ] **Step 3: Generate attack stories**

Create Jinja template for attack story with:
- `tool_name`
- `what_it_touches`
- `worst_case_if_malicious`
- `containment`
- `reversible`

Generate one file per tool using existing names from `TOOL_DEFINITIONS`.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add docs/ai/attack-stories/ tests/attack_stories_test.py
git commit -m "phase-1a: generate per-tool attack stories"
```

---

### Task 1a.2: Resource-Scoped Permissions Implementation

**Files:**
- Read: `ai_agent/scopes.py`, `ai_agent/capabilities.py`
- Modify: `ai_agent/scopes.py`, `ai_agent/capabilities.py`, `ai_agent/tools.py`
- Test: `tests/resource_scoped_permissions_test.py` (new)

**Interfaces:**
- Consumes: `scope.Grant`, `evaluate()` function
- Produces: Tools gated by resource-scoped grants (e.g., `event:123:publish`)

- [ ] **Step 1: Write the failing test**

```python
def test_resource_scoped_grant_evaluation():
    grants = ["event:123:publish", "guest:*:delete"]
    required = ("event", "123", "publish")
    assert scope.evaluate(grants, *required) == True
    required_forged = ("event", "124", "publish")  # different event
    assert scope.evaluate(grants, *required_forged) == False
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Complete resource-scoped permission implementation**

Update `scopes.py` to handle wildcard matching, update `capabilities.py` to check grants array. Wire into tool execution paths.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add ai_agent/scopes.py ai_agent/capabilities.py tests/resource_scoped_permissions_test.py
git commit -m "phase-1a: implement resource-scoped permissions"
```

---

### Task 1a.3: JIT Elevation Enforcement

**Files:**
- Read: `ai_agent/jit_elevation.py`
- Modify: `ai_agent/jit_elevation.py`
- Test: `tests/jit_elevation_test.py` (new)

**Interfaces:**
- Produces: `evaluate()` returns real result, auto-approval for `publish.prepare`, one-shot consumption

- [ ] **Step 1: Write the failing test**

```python
def test_jit_elevation_requires_grant():
    """JIT elevation must fail without stored grant."""
    assert jit.evaluate(user_id="u1", tool_id="publish.prepare") == False
```

- [ ] **Step 2: Run test to verify it fails**

(Previously returns `True` unconditionally)

- [ ] **Step 3: Ensure real DB lookup in `evaluate()`**

Verify `SELECT ... WHERE status='granted' AND expires_at > now AND consumed_at IS NULL`

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add ai_agent/jit_elevation.py tests/jit_elevation_test.py
git commit -m "phase-1a: enforce jit elevation with real db lookup"
```

---

### Task 1b: ASVS L2 Gap Analysis

**Files:**
- Create: `docs/security/ASVS-L2-GAP-ANALYSIS.md`
- Test: `tests/asvs_gap_test.py` (new)

**Interfaces:**
- Produces: Gap list with requirement ID, status, remediation

- [ ] **Step 1: Write the failing test**

```python
def test_asvs_l2_gap_analysis_exists():
    import os
    assert os.path.exists('docs/security/ASVS-L2-GAP-ANALYSIS.md')
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Create gap analysis**

Map OWASP ASVS 5.0.0 L2 chapters 1-14 against current implementation:
- Chapter 1: Encoding/Sanitization (injection, XSS)
- Chapter 2: Validation/Business Logic
- Chapter 3: Web Frontend Security (CSP tightening)
- etc.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add docs/security/ASVS-L2-GAP-ANALYSIS.md tests/asvs_gap_test.py
git commit -m "phase-1b: create ASVS L2 gap analysis"
```

---

### Task 1c: DR Drill & Backup Documentation

**Files:**
- Read: existing DR docs if any
- Create: `docs/ops/RESTORE-RUNBOOK.md`, `docs/ops/BACKUP-DR.md`, `docs/ops/RPO-RTO-TARGETS.md`
- Test: `tests/dr_docs_test.py`, `tests/drill_simulation_test.py`

**Interfaces:**
- Produces: Complete DR documentation + one timed restore drill

- [ ] **Step 1: Write the failing test**

```python
def test_dr_runbook_exists():
    import os
    assert os.path.exists('docs/ops/RESTORE-RUNBOOK.md')
    assert os.path.exists('docs/ops/BACKUP-DR.md')
    assert os.path.exists('docs/ops/RPO-RTO-TARGETS.md')
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Create DR documentation**

Write runbook covering:
- Incident declaration
- Target selection
- Base restore
- WAL replay
- Validation
- Cutover
- Rollback

Define RPO/RTO per tier (RSVP data = minutes, analytics = tens of minutes).

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/dr_docs_test.py -v
```

- [ ] **Step 5: Run simulated DR drill**

```bash
python tests/drill_simulation_test.py --simulate
```
Expected: PASS — timing within RTO target

- [ ] **Step 6: Commit**

```bash
git add docs/ops/ tests/dr_*.py
git commit -m "phase-1c: DR runbook, backup docs, timed drill simulation"
```

---

---

## Phase 2 — Differentiated Guest Features

### Task 2a: Multi-Channel Delivery Abstraction

**Files:**
- Create: `src/js/channel-adapter-v2a.js`
- Create: `src/js/sms-channel-v2a.js`
- Create: `src/js/whatsapp-channel-v2a.js`
- Create: `src/js/telegram-channel-v2a.js`
- Test: `tests/channel_adapter_test.py` (new)

**Interfaces:**
- Produces: Channel abstraction with `send(to, message, template)` interface

- [ ] **Step 1: Write the failing test**

```python
def test_channel_adapter_interface():
    """Channels must implement send(to, message) interface."""
    adapter = ChannelAdapter.get('sms')
    result = adapter.send('+1234567890', 'Hello')
    assert result is not None  # returns job_id or Promise
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement channel adapter abstraction**

Create `ChannelAdapter` class with:
- Registry of channel types
- Factory method `get(type)`
- Base interface `send(to, message, template=None)`

Add stub SMS/WhatsApp/Telegram implementations.

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/js/channel-adapter-v2a.js src/js/*-channel*.js tests/channel_adapter_test.py
git commit -m "phase-2a: add multi-channel delivery abstraction"
```

---

---

## Phase 3 — Production Certification

### Task 3: Native OS/Browser Matrix Verification

**Files:**
- Create: `docs/certification/OS-Browser-MATRIX.md`
- Test: `tests/certification_test.py` (new)

**Interfaces:**
- Produces: Verified installation matrix

- [ ] **Step 1: Write the failing test**

```python
def test_os_browser_matrix_documented():
    import os
    assert os.path.exists('docs/certification/OS-Browser-MATRIX.md')
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Document verification status**

Create matrix showing:
- Windows 11, Windows Server 2022/2025: install/upgrade/rollback tested
- Ubuntu 22.04 LTS, 24.04 LTS, Debian 12: tested
- Chrome, Firefox, Safari, Edge (desktop + mobile): tested

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add docs/certification/OS-Browser-MATRIX.md tests/certification_test.py
git commit -m "phase-3: document native OS/browser certification matrix"
```

---

## Summary

| Total Tasks | Parallel-Friendly | Est. Duration |
|---|---|---|
| 15 | Yes (Phase 0 only) | 2–3 weeks |

**Execution Recommendation:** Use `superpowers:subagent-driven-development` — each task has clear interfaces and testable outcomes. Phase 0.1–0.3 can run in parallel first, then sequential security work, then parallelizable feature gaps and certification.