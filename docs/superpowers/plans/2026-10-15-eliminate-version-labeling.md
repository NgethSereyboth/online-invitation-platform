# Eliminate Version Labeling from UI/Pages/Functions — Plan

> **SUPERSEDED (2026-10-16).** Replaced by
> [`2026-10-16-version-free-source-names.md`](2026-10-16-version-free-source-names.md).
>
> This document was an open-ended audit with no endpoint. Its single concrete
> item — the release-version disclosure on `/api/health/live` — was already
> implemented when it was written, and the user-visible release labels it was
> looking for did not exist. The replacement plan pins the real problem down to
> version suffixes in *file names* and adds two guards plus a measurable end
> state. Kept for its audit notes only; do not execute the phases below.

> **For implementation:** Follow `CONTRIBUTING.md` and the focused verification steps below. This is an audit plan; do not execute unrelated phases as a blanket cleanup.

**Goal:** Remove confirmed product-release labels from user-facing interfaces and confirmed product-release disclosures from unauthenticated responses. This is not a request to remove compatibility or implementation versions.

**Architecture:** Review each release-looking occurrence in context. Change only text that is actually rendered to users or included as product-release branding in a public response. Preserve schema/API/protocol versions, module and asset identifiers, migration numbers, plugin/template/resource revisions, and operational build metadata unless a separately reviewed compatibility change explicitly requires otherwise.

**Tech Stack:** Python server and static JavaScript/CSS frontend. Search and build from the repository root. `src/js/`, `src/css/`, and `src/html/` are sources of truth; generated route bundles and the `src/python/` runtime mirror are produced with the supported `python3 build.py` entry point.

**Spec:** Acceptance is behavioral: confirmed release branding is absent from the specific user-facing/public surfaces under review, while health semantics and supported versioned contracts remain unchanged. A repository-wide ban on version-shaped strings is explicitly out of scope.

---

## Global Constraints

- Never edit generated files by hand. Follow `CONTRIBUTING.md`: make frontend changes in `src/js/`, `src/css/`, or `src/html/`; rebuild with the repo-root `build.py` entry point. `src/python/` contains served runtime mirrors of frontend assets.
- Add or update a focused regression test for each confirmed behavior change; do not create a test whose purpose is merely to find version-like strings.
- Preserve bilingual content when changing user-facing text; prefer removing a confirmed release badge over replacing it with new copy.
- Do not commit, stage unrelated changes, or claim unrelated verification as part of this plan.
- After edits under `src/js/` or `src/css/`, run `python3 build.py bundles` and `python3 build.py bundles --check`. Run `python3 build.py all --check` for final generated-artifact integrity; investigate reported drift rather than silently regenerating or ignoring it.

---

## Review Focus

Review candidates, not presumed defects:
1. **Public health/API responses:** verify actual unauthenticated payloads, especially `/api/health/live`, `/api/health/ready`, and `/api/status`; preserve diagnostics and compatibility fields unless independently unsafe.
2. **Rendered frontend:** inspect actual badge, title, footer, and page copy in source modules/HTML, not just version-looking tokens in bundles.
3. **Other user-facing output:** inspect errors or startup messages only when they can reach end users.
4. **Build/dependency metadata:** treat it as internal unless a serving path or UI demonstrably exposes it; do not edit package versions or generated filenames as cosmetic cleanup.

---

## Phase 0 — Discovery & Inventory

### Task 0.1: Locate release-label candidates

**Scope:** Source and runtime paths that can affect a user-visible surface or public response. Start with `src/js/`, `src/css/`, `src/html/`, and relevant routes in `src/python/`; inspect deploy files only when they influence what is served.

**Output:** A concise occurrence list containing path, context, exposure evidence, and a preliminary keep/review/remove disposition. Do not create a permanent version-string inventory test or a required `docs/superpowers/tmp/` artifact.

- [ ] **Step 1: Search source and runtime paths** with repository code search or a portable Python scan. Use version-shaped matches only to locate candidates; review actual render/response behavior to catch nonnumeric labels and avoid treating compatibility identifiers as defects.
- [ ] **Step 2: Treat generated matches as pointers to their source.** Never make generated bundles or the `src/python/` mirror separate edit targets.
- [ ] **Step 3: Record only relevant candidates and the evidence needed for classification** in task notes or a scoped review artifact when the list is large.

---

### Task 0.2: Classify occurrences

For each candidate, determine whether it is rendered, returned to an unauthenticated caller, required for compatibility/operations, documentation, or not externally exposed. Record the evidence and rationale for every proposed change; do not treat a version-looking string or its containing file as sufficient evidence.

Classification rules:
- **Release branding:** text actually rendered as a product-release badge/title/footer/message — remove only that label; prefer removing the badge over adding new copy.
- **Public disclosure:** product-release branding returned to an unauthenticated caller — remove only the release-specific field/value and preserve endpoint status, availability, and useful diagnostics.
- **Compatibility version:** schema/API/protocol/module/plugin/template/resource version or migration identifier — keep unless a separate compatibility change is approved.
- **Internal metadata:** build/dependency/artifact version not exposed to users — keep; verify exposure before considering changes.
- **Documentation:** history, plans, and reports — keep accurate; a documented version is not a UI leak.

- [ ] Record exposure evidence and a keep/remove rationale for each candidate selected for action.
- [ ] Confirm every proposed removal has a concrete acceptance check (rendered surface or public response) and that compatibility fields have an explicit keep rationale.

---

## Phase 1 — Review user-facing frontend surfaces

### Task 1.1: Review JavaScript release-label candidates

**Target files:** Only source JS modules confirmed by the occurrence-level inventory to render a product release label or disclose a product release version to users

**Interfaces:**
- Consumes: JavaScript source files and the classified occurrence inventory
- Produces: JavaScript without user-visible product-release branding; compatibility versions remain unchanged

- [ ] **Step 1: Confirm a candidate is actually rendered** by following the source data into a visible page/component. A source match alone is not evidence.
- [ ] **Step 2: Add or update a focused behavior test** for each confirmed label; do not use a blanket source grep as acceptance.
- [ ] **Step 3: Edit only the source module(s)** responsible for that rendered label. Leave module/API `version` properties and protocol behavior intact.
- [ ] **Step 4: Run the focused test and review compatibility candidates** to confirm the visible label is gone and unrelated version contracts remain unchanged.

---

### Task 1.2: Review HTML and manifest exposure

**Target files:** `src/html/*.html` pages and `manifest.webmanifest` only where an occurrence is confirmed to show a product release label in a public interface

**Interfaces:**
- Consumes: HTML source and manifest content, plus the way the server serves it
- Produces: only confirmed public release labels removed; non-visible metadata and compatibility fields retained

- [ ] **Step 1: Inspect actual page titles, badges, footers, and exposed metadata** identified by the inventory.
- [ ] **Step 2: Add or update focused assertions for the concrete HTML/page behavior** if a public label is confirmed.
- [ ] **Step 3: Edit only the source HTML or manifest field that exposes the label.** A meta/build value is not automatically user-visible; verify browser/API exposure before changing it.
- [ ] **Step 4: Run the focused page/manifest checks and verify that non-visible compatibility metadata remains intact.**

---

### Task 1.3: Review CSS-generated labels

**Target files:** CSS source only where it visibly renders a product release label; generated bundles are rebuilt, never edited directly

**Interfaces:**
- Consumes: CSS source and the rendered page where it is used
- Produces: confirmed CSS-rendered release labels removed; unrelated style and identifiers unchanged

- [ ] **Step 1: Inspect only rules that can render text or a release badge** (for example, `content:` declarations or a label-specific selector).
- [ ] **Step 2: Add or update a focused rendered-surface test** if a real CSS-generated label is confirmed.
- [ ] **Step 3: Edit the source CSS only.** Do not alter custom properties, comments, filenames, module names, or generated bundles merely because they contain version-like text.
- [ ] **Step 4: Run `python3 build.py bundles` followed by `python3 build.py bundles --check`, then run the focused test.

---

## Phase 2 — Review public Python responses and messages

### Task 2.1: Keep the public liveness response minimal

**Target files:** `src/python/server.py` liveness route and `tests/health_version_disclosure_test.py`

**Contract:** `GET /api/health/live` returns exactly `{"ok": true, "status": "live"}` regardless of `EINVITE_DISCLOSE_HEALTH_DETAILS`. This does not remove versions from authenticated APIs or unrelated health/readiness diagnostics.

**Verified state (2026-10-16):** The liveness route no longer appends a release version, and the regression test covers diagnostics disabled and enabled. `python -m pytest tests/health_version_disclosure_test.py -q` passed (2 tests). Keep this test as the contract; do not repeat the implementation or broaden the assertion to every `version` key.

When this code changes, rerun the focused HTTP test. Review `/api/health/ready`, `/api/status`, and other public routes independently by payload semantics, and preserve supported schema/protocol/resource versions.

---

### Task 2.2: Review remaining Python candidates by contract

**Target files:** Public-response serializers, startup/user-facing messages, and modules flagged in the reviewed inventory

**Interfaces:**
- Consumes: Python source files and occurrence classifications
- Produces: Public-facing release labels removed, while compatibility/schema/protocol version fields remain intact

- [ ] **Step 1: Trace each relevant Python candidate** to a public serializer, an actual user-facing message, or a non-public/internal use.
- [ ] **Step 2: Add a focused regression test only for a confirmed public disclosure or user-facing label.** Avoid brittle allowlists of every version literal.
- [ ] **Step 3: Remove only the confirmed product-release branding** and preserve schema, protocol, migration, plugin, template, resource, and authenticated API version contracts.
- [ ] **Step 4: Run the relevant HTTP/unit tests and review unmodified candidates against the classification rationale.

---

## Phase 3 — Preserve release history and classify internal metadata

### Task 3.1: Review documentation and build metadata without treating them as leaks

**Target files:** `VERSION_HISTORY.md`, `docs/LEGACY-VERSION-HISTORY.md`, relevant Markdown history/plans, and only non-Markdown metadata shown to be exposed publicly

**Interfaces:**
- Consumes: the occurrence inventory and documentation/metadata exposure paths
- Produces: accurate release history plus explicit keep/remove rationales for any exposed metadata

- [ ] **Step 1: Preserve historical release references** in history, plans, and reports; do not require release-like strings to occur only in Markdown.
- [ ] **Step 2: Trace any JSON/build/dependency metadata candidate** to the server or UI before changing it. Keep operational values and generated artifact identifiers that are not exposed.
- [ ] **Step 3: If a metadata field is publicly exposed as product-release branding, add a focused test for that exposure and change only that field.**

---

## Phase 4 — Focused final verification

### Task 4.1: Verify changed behavior and generated artifacts

**Interfaces:**
- Consumes: confirmed changes and their regression tests
- Produces: test/build results and a short list of remaining candidates kept by contract; no claim that all version strings were removed

- [ ] **Step 1: Run each focused regression test** for the confirmed UI or public-response changes, including `python -m pytest tests/health_version_disclosure_test.py -q` for liveness.
- [ ] **Step 2: Run `python3 build.py all --check`** and inspect any stale-artifact report. If drift is unrelated, report it; do not label the build as passing or regenerate unrelated files without review.
- [ ] **Step 3: Run the broader relevant test suite** (`python3 -m pytest tests/ -q`) when practical; report failures/skips and distinguish unrelated environment issues.
- [ ] **Step 4: Review the final diff and the classified candidate list.** Confirm each removed item had evidence of exposure, each retained compatibility version has a rationale, and generated files were produced by the supported build.

---

## Summary Matrix

| Phase | Target | Deliverable / acceptance |
|---|---|---|
| 0 | Discovery and classification | Occurrence-level candidates with exposure evidence and keep/remove rationale |
| 1 | Confirmed frontend labels | Only demonstrated rendered release branding removed; focused UI checks pass |
| 2 | Public responses/messages | Only confirmed product-release disclosure removed; endpoint semantics and contracts preserved |
| 3 | Documentation/internal metadata | History retained; metadata changed only when an exposure path is proven |
| 4 | Final verification | Focused tests, reviewed diff, supported build check, and remaining candidates explained |

**Execution recommendation:** Start from observed interface behavior and trace the data flow; use search to locate likely sources. Keep changes scoped to confirmed exposure. Do not remove, rename, or claim to eliminate all version-shaped strings.

---

**Execution status (2026-10-16):** The `/api/health/live` release-version disclosure repair is present in the workspace. `tests/health_version_disclosure_test.py` covers diagnostics disabled and enabled; `python -m pytest tests/health_version_disclosure_test.py -q` passed (2 tests). The rest of this document is a review backlog, not evidence that all other candidate surfaces have been exhaustively audited. The latest `python build.py all --check` reports stale mirror `src/python/route-deferred-loader-v15.js`; this is not a passing build result and should be investigated before claiming full generated-artifact integrity.

**Plan file:** `docs/superpowers/plans/2026-10-15-eliminate-version-labeling.md`
