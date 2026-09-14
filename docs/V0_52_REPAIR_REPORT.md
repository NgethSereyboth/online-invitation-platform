# V0.52 Cumulative Repair Report

## Release identity

- Repair baseline: `e-invitation-platform-intelligent-event-ecosystem-v0.52-repaired(2).zip`
- Baseline SHA-256: `a42ae49bc3cc9ca00e4899f25f0d7eae9938aea4d11e6e7693213ed148fd59c1`
- Public version: `0.52`
- Internal milestone: `52`
- Document schema: `27` (unchanged)
- Compatibility floor: `V27.3.5` (unchanged)
- README SHA-256: `f3c158d37f1ab2367a4bd0565c230535369596431709cbbd3cb234c324633330` (unchanged)

## Independent-audit defects repaired in this pass

1. **AI/backend conversation crash** — `ai_agent/context.py` queried nonexistent `invitation_comments.status`. It now uses the canonical portable `resolved=0` contract while preserving total/open comment counts. `server.py` now has a safe pre-stream boundary and sanitized `agent_internal_error` handling, while `ai_agent/service.py` finalizes jobs and reservations exactly once across completion, cancellation, disconnect, provider/tool errors and unexpected failures.
2. **Dashboard project-cover navigation** — `final-polish.js` no longer recursively clicks the cover's own `[data-edit]`; the visible cover dispatches through the explicit `.actions [data-edit]` control. Archived/disabled behavior, keyboard activation and Project actions → Edit remain intact.
3. **False autosave-offline status** — `app.js::saveServerDraft()` previously named its invitation snapshot parameter `document`, shadowing the browser `document`; the HTTP save succeeded, then the local status update threw and falsely entered the offline branch. The parameter is now `documentSnapshot`, newest pending edits are preserved, idle callbacks are cancellable, transient retries are bounded, revision/auth/validation failures remain distinct, and only sanitized diagnostic codes/status are exposed to tests.
4. **Windows deterministic cleanup** — `tests/v0_52_asset_identity_test.py` deterministically closes SQLite handles and waits for killed server processes.
5. **Current dependency marker** — `tests/v20_1_stabilization_contract_test.py` accepts the exact `V0.52 dependency preflight passed.` marker while retaining WOFF2/dependency verification.
6. **Current dashboard smoke path** — `tests/ui_smoke_test.py` targets the visible Create control and verifies both project-cover and Project actions → Edit navigation.
7. **Generated-bundle budget repair** — redundant generated `SOURCE:` comments were removed from route bundles while the canonical source list and bundle SHA-256 integrity remain enforced by manifests/tests. No budget was raised.

## New regression coverage

- `tests/v0_52_ai_real_server_test.py` — clean SQLite + real HTTP AI thread/message/NDJSON flow, unresolved-comment context, persisted conversation, sanitized response and exactly-once completed job state.
- `tests/v0_52_ai_live_browser_test.py` — real served-app AI panel conversation path for an unrestricted Chromium environment.
- `tests/v0_52_dashboard_cover_navigation_test.py` — real served dashboard cover and action-menu navigation.
- `tests/v0_52_autosave_status_test.py` — two quick real served edits, latest SQLite draft, truthful Server connected state and reload persistence.

## Modified canonical source/tooling

- `ai_agent/context.py`
- `ai_agent/service.py`
- `server.py`
- `app.js`
- `final-polish.js`
- `build_route_bundles.py`
- `run_review_checks.py`

Generated route bundles/manifests were regenerated from those canonical sources. Relevant release tests were updated only where the product contract intentionally changed (current V0.52 marker, nullish revision semantics, generated-bundle source-manifest integrity, current visible dashboard controls, deterministic cleanup).

## Migration impact

No schema-number migration is introduced. Schema remains 27. Existing asset-reference migration, tenant/workspace boundaries, publication readiness, snapshots, rich text, Khmer support, RSVP modes and V29–V0.52 compatibility remain intact.

## Final route measurements before package freeze

- Canonical editor bundle: **1,413,344 / 1,420,000 bytes** — **6,656 bytes headroom**.
- Complete `index.html` startup assets: **1,417,331 bytes**.
- Public invitation route: **233,585 / 260,000 bytes** — **26,415 bytes headroom**.

## Validation status

- **90 of 90 registered deterministic entries passed** in focused/batched or isolated execution, including `tests/v27_3_5_release_evidence_test.py` after the complete internal SHA-256 manifest was frozen.
- The internal release manifest covers all eligible packaged files and is revalidated after final metadata updates.
- Real HTTP AI integration passes in this environment.
- Real served-browser navigation cannot be executed here because Chromium blocks HTTP navigation before application code with `net::ERR_BLOCKED_BY_ADMINISTRATOR`; the three new real-server browser regressions remain registered and must run in the unrestricted independent audit.
- `python run_review_checks.py --continue-on-failure --fast-workers 8` was attempted; the environment terminated the long-running command at its wall-clock ceiling after the visible deterministic phase had reported only passes. The full 90 deterministic entries were therefore completed through focused/batched or isolated runs rather than falsely claiming a completed one-command gate.
- Each new served-browser regression was also executed directly and each stopped at its initial `page.goto()` with `net::ERR_BLOCKED_BY_ADMINISTRATOR`, before application code.

## Remaining production setup / certification

External AI providers, S3/R2/MinIO, DNS/certificate automation, production media encoders, messaging, payments, malware scanning, monitoring/tracing, distributed queues and plugin signing still require deployment credentials/configuration. Native Windows/Linux/browser/device certification, unrestricted served-browser matrix, penetration testing, load/scale testing, physical-GPU benchmarking and disaster-recovery drills remain pending. No release certification is claimed.
