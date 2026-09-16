# eInvite Plugin Moderation Pipeline (V54.6 / Phase 4a)

> **Status**: Phase 4a design document. Companion to `PLUGIN-SPEC.md`, `PLUGIN-SIGNING.md`, `PLUGIN-SANDBOX.md`.
> **Scope**: Defines the four-stage moderation pipeline (automated pre-upload checks → human review → post-approval takedown → user reports) plus the Verified Vendor badge program.
> **Design principle** (ROADMAP §7 4a): eInvite's users are non-technical event hosts. They cannot evaluate plugin security themselves; the marketplace must do it for them. JetBrains does almost no review for the long tail of third-party plugins — that is the model to avoid.

---

## 1. Pipeline overview

```
┌─────────────────────────────┐
│ 1. Author submits plugin    │
│    (manifest + bundle +      │
│     author Ed25519 sig)     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 2. Automated pre-upload     │  ◀── §3
│    checks (CI-like)         │
│    PASS / FAIL              │
└──────────────┬──────────────┘
               │ PASS
               ▼
┌─────────────────────────────┐
│ 3. Human review (4 audits)  │  ◀── §4
│    PASS / REJECT / RESUBMIT  │
└──────────────┬──────────────┘
               │ PASS
               ▼
┌─────────────────────────────┐
│ 4. Marketplace CA signs     │  ◀── PLUGIN-SIGNING.md §4
│    + publishes to catalog    │
└──────────────┬──────────────┘
               │
               ▼
        Marketplace listing
               │
               ▼
┌─────────────────────────────┐
│ 5. Post-approval monitoring  │  ◀── §4.3 (takedown) + §6 (reports)
│    (CRL + user reports)      │
└─────────────────────────────┘
```

A submission can fail at any gate. Failures at gates 2–4 are returned to the author with a specific reason. Re-submission requires a new manifest version bump (per `PLUGIN-SPEC.md` §7.1).

---

## 2. Submission contract

### 2.1 Endpoint

`POST /_marketplace/plugins/submit` accepts a multipart upload:

- `manifest.json` (UTF-8 JSON, max 64 KiB) — must already carry the author Ed25519 `signature` block.
- `bundle.tar.gz` (gzip, max 5 MB) — contains the entrypoint + assets, excluding the manifest itself.
- `submission_metadata.json` (UTF-8 JSON, max 8 KiB) — author contact info, source repository URL, design notes, optional verification documents for Verified Vendor badge (see §5).

### 2.2 Authentication

The author authenticates with their eInvite account (existing Argon2id + MFA flow from V54). The `vendor_id` in the manifest must match the `vendor_id` on the author's marketplace profile.

### 2.3 Submission rate limit

- Per author: max 5 submissions per day, max 20 active submissions in the queue at any time.
- Per IP: max 10 submissions per hour (defends against sock-puppet registration).
- Hit the limit → HTTP 429 with `Retry-After` header.

---

## 3. Automated pre-upload checks

The automated pipeline runs in a sandboxed CI-like environment. Every check produces a PASS / WARN / FAIL. A single FAIL rejects the submission and returns the specific check + offending pattern to the author. WARNs are surfaced to the human reviewer but do not auto-reject.

### 3.1 Manifest schema validation

- Validates `manifest.json` against `plugins/sdk/manifest.schema.json` (see `PLUGIN-SPEC.md` §6).
- FAILs on any schema violation.
- Rejects unknown top-level fields (`additionalProperties: false`).
- Rejects forbidden field names anywhere in the recursive tree (`PLUGIN-SPEC.md` §2.3): `script, javascript, code, eval, html, cssText, filesystemPath, networkUrl, sql, srcdoc, onload, onclick, innerHTML, outerHTML, document_cookie, window_location`. Matches the V48 runtime's existing forbidden set in `src/js/plugin-runtime-v48.js:forbidden` (extended with the additional DOM-API tokens).
- Rejects manifests deeper than 12 levels of nesting or with arrays longer than 500 entries (matches V48 runtime `scan()` depth/length caps).

### 3.2 Dependency audit

- Every external URL referenced in the manifest (e.g. `homepage`, `repository`, `icon_256` thumbnail URLs, screenshot URLs) is fetched server-side and matched against an allow-list of CDN domains (`notofonts.github.io`, `fonts.gstatic.com`, `cdn.jsdelivr.net` for known-safe OSS libraries).
- The bundle is unpacked and every `import` / `require` / `<script src=...>` statement is parsed. External URLs (any URL that is not relative to the bundle root) are extracted.
- FAILs on any external URL not on the allow-list.
- FAILs on any external URL that uses `http://` (only `https://` is permitted).
- FAILs on any URL containing a query parameter (`?` or `#`) — the marketplace cannot review URLs that take arbitrary parameters at runtime.
- WARNs on any external dependency that has had a CVE in the last 90 days (fetched from OSV.dev).

### 3.3 Suspicious-pattern detection

Every file in the bundle (`.js`, `.wasm`, `.html`, `.css`, `.json`) is scanned for the following patterns. Each pattern is a FAIL unless explicitly excepted (the exception list is per-pattern and maintained in `plugins/sdk/suspicious_patterns.json` — to be added in the code follow-up):

| Pattern | Regex / detector | Why |
|---|---|---|
| `eval(` | `\beval\s*\(` | Dynamic code execution bypasses manifest CSP. |
| `new Function(` | `new\s+Function\s*\(` | Same as `eval`. |
| `Function(` (constructor) | `\bFunction\s*\(` (excluding `function `) | Same as `eval`. |
| `document.cookie` | `\bdocument\.cookie\b` | Cookie exfiltration. |
| `document.write(` | `\bdocument\.write\s*\(` | DOM injection post-CSP. |
| `window.location` (assignment) | `\bwindow\.location\s*=` | Redirect attack. |
| `innerHTML` (assignment) | `\.innerHTML\s*=` | DOM injection. |
| `outerHTML` (assignment) | `\.outerHTML\s*=` | DOM injection. |
| `setTimeout(... string)` | `setTimeout\s*\(\s*["']` | String-based `setTimeout` = eval. |
| `setInterval(... string)` | `setInterval\s*\(\s*["']` | Same. |
| `fetch(` with hardcoded external URL | `fetch\s*\(\s*["']https?://` (excluding the manifest's allow-listed CDN URLs) | Network exfiltration. |
| `XMLHttpRequest` (raw) | `new\s+XMLHttpRequest\b` | Network exfiltration. |
| `WebSocket` (raw) | `new\s+WebSocket\b` | Network exfiltration. |
| `navigator.serviceWorker` | `\bnavigator\.serviceWorker\b` | Persistent background code outside the sandbox. |
| `Worker(` (constructor) | `new\s+Worker\s*\(` | Spawning nested workers. |
| `SharedWorker(` | `new\s+SharedWorker\b` | Cross-tab worker. |
| `crypto.subtle` | `\bcrypto\.subtle\b` | Direct crypto (host bridge provides signing — plugins should not need raw crypto). |
| `importScripts(` (in a Worker) | `importScripts\s*\(` | Loading remote code post-install. |
| `atob(` followed by `eval`/`Function` within 200 chars | heuristic | Obfuscated payload. |
| Base64 strings > 4 KB | length-based | Possible embedded payload. |
| `WebAssembly.compileStreaming(` | `\bWebAssembly\.compileStreaming\b` | Loading remote WASM. |
| `import(` (dynamic) | `\bimport\s*\(` | Dynamic imports bypass the static dependency audit. |

The scan is byte-pattern based (not AST-based) for two reasons: (1) it works on minified and transpiled code without a JS parser dependency in the marketplace's stdlib-only Python reviewer; (2) it is conservative — false positives are surfaced as WARNs and the human reviewer can override, but never silently allowed through.

### 3.4 Bundle size limit

- Total bundle size (after gzip): 5 MB hard cap.
- Largest single file: 2 MB hard cap.
- WASM modules: 5 MB hard cap (subject to the heap-cap rule from `PLUGIN-SANDBOX.md` §6 — WASM initial memory max 50 MB, but the WASM module itself must be ≤ 5 MB on disk).
- FAILs on any overage.

### 3.5 Entrypoint signature verification

- The manifest's `signature` field is verified against the bundle hash (per `PLUGIN-SIGNING.md` §2.2).
- FAILs if the signature does not verify.
- FAILs if the `author_key_id` does not match the SHA-256 of the declared `signature.public_key`.
- FAILs if the author's public key is not registered with the marketplace (see `PLUGIN-SIGNING.md` §3.3).

### 3.6 CSP audit

- The manifest's `content_security_policy` is checked for forbidden tokens (`'unsafe-inline'`, `'unsafe-eval'`, `'unsafe-hashes'`).
- FAILs if any forbidden token is present.
- WARNs if `connect_src` includes any URL other than `'self'` (the sandbox should not make direct network calls).

### 3.7 Permission audit

- Every entry in `permissions[]` is checked against the grammar in `PLUGIN-SPEC.md` §3.1.
- FAILs on any wildcard (`*`) resource grant.
- FAILs on any action that does not appear in the §3.2 per-resource action table.
- WARNs on permissions that imply exfiltration risk: `invitation:{current}:message:send`, `invitation:{current}:guest:delete`, `asset:upload`, `workspace:{current}:publishing:environment:promote`. These WARNs trigger a mandatory deeper security audit at human review (§4.2).

### 3.8 Bilingual completeness

- Every user-facing string field (`name`, `description`, every `extension_points[].label`) must have both the base (`*_en`) and the Khmer (`*_kh`) variant.
- FAILs if any Khmer variant is missing or empty.
- FAILs if the Khmer variant is byte-identical to the English variant (a common machine-translation failure mode — the marketplace rejects "translate to Khmer by copying the English text").

### 3.9 Summary

The automated pipeline produces a JSON report:

```json
{
  "submission_id": "...",
  "checks": [
    { "name": "manifest_schema", "result": "pass" },
    { "name": "dependency_audit", "result": "pass" },
    { "name": "suspicious_patterns", "result": "fail", "details": { "pattern": "eval(", "file": "scripts/main.js", "line": 42, "col": 8, "snippet": "  const f = eval(userInput);" } },
    { "name": "bundle_size", "result": "pass" },
    { "name": "entrypoint_signature", "result": "pass" },
    { "name": "csp_audit", "result": "pass" },
    { "name": "permission_audit", "result": "warn", "details": { "permissions_flagged": ["invitation:{current}:message:send"] } },
    { "name": "bilingual_completeness", "result": "pass" }
  ],
  "overall": "fail",
  "next_step": "Author must remediate the suspicious_patterns failure and resubmit with a patch version bump."
}
```

A FAIL returns the report to the author. A PASS (or WARN-only) advances the submission to the human review queue.

---

## 4. Human review

Every approved plugin is manually reviewed by a marketplace maintainer. The review is a four-pass audit:

### 4.1 Source code audit

- Maintainer fetches the source repository (declared in `manifest.repository`).
- Walks the codebase: does the plugin's stated purpose match what the code actually does?
- Checks for any code path that the automated scanner might have missed (e.g. dynamic property access: `obj[methodName](args)` where `methodName` is built from string concatenation).
- Verifies the bundle matches the source (rebuilds the bundle from source and confirms the SHA-256 matches the submitted bundle hash).

### 4.2 Permissions audit

- For every permission in `permissions[]`, the maintainer traces at least one code path where the permission is actually used.
- FAILs (REJECT) if the plugin declares a permission it does not use (over-permissioning).
- FAILs (REJECT) if the plugin uses a permission it does not declare (under-declaration — this is also a runtime sandbox violation).
- For the WARN-flagged permissions from §3.7, the maintainer must explicitly justify each use: why does a "confetti animation" plugin need `invitation:{current}:message:send`? (Probably it doesn't — reject.)

### 4.3 Security audit

- Threat-model the plugin: what's the worst case if this plugin is compromised? What data does it touch? Can it exfiltrate guest PII? Can it send unauthorized messages? Can it lock the host out of their invitation?
- Check the sandbox CSP and resource limits — is the requested quota justified?
- For `payment.provider` plugins: verify the payment flow never gives the plugin direct access to card data (PCI scope). The plugin should only ever return a checkout URL — the host embeds it; card data goes directly to the payment processor.
- For `communication.provider` plugins: verify the plugin cannot send to arbitrary recipients (it must dispatch through the host's existing delivery_channels pipeline, which enforces recipient allow-lists per V54.3).
- For `ai.provider` plugins: verify the plugin strips PII before forwarding to the model (the host bridge does this — the maintainer verifies the plugin does not also forward raw PII in its own payload).
- Check the plugin's key management: does the plugin bundle any secrets? (FAIL — secrets must come from the host's existing `secrets_v54.py` vault, not the plugin bundle.)

### 4.4 UX audit

- Maintainer installs the plugin in a staging eInvite instance and exercises it end-to-end.
- Does the plugin's UI match the host's design language? (eInvite uses the V54 design tokens — plugins must not override `--brand`, `--text-1`, etc.)
- Does the plugin work in Khmer? (Maintainer toggles locale to `km` and verifies every visible string is translated.)
- Does the plugin degrade gracefully when its permissions are revoked at runtime? (Maintainer revokes each permission one-by-one and verifies the plugin surfaces a polite error, not a crash.)
- Does the plugin work on a 360×640 mobile viewport? (Mobile-first per the WCAG AA audit `docs/a11y/WCAG-AA-AUDIT.md`.)

### 4.5 Review outcomes

| Outcome | Effect |
|---|---|
| **APPROVED** | Maintainer triggers `POST /_marketplace/plugins/{id}/approve`. Marketplace CA signs (per `PLUGIN-SIGNING.md` §4). Plugin published to catalog. |
| **RESUBMIT** | Submission returned to author with specific changes required. Author bumps patch version and resubmits. Original submission is archived. |
| **REJECT** | Submission refused. Author must bump MINOR version to resubmit (signaling a more substantial change). The rejection reason + reviewer notes are visible to the author. |
| **BAN** | Author account banned (used for repeated malicious submissions). Author's public key is added to the CRL with `reason: key_compromise` (treating the ban as a self-compromise). |

### 4.6 Post-approval takedown

A previously-approved plugin can be taken down at any time:

1. Maintainer triggers `POST /_marketplace/plugins/{id}/takedown` with a reason.
2. The marketplace:
   a. Adds the plugin's marketplace signature to the CRL with `reason: moderation_takedown` (per `PLUGIN-SIGNING.md` §6).
   b. Removes the plugin from the marketplace catalog (already-installed instances remain cached locally).
   c. Sends an email to the author's `author.email` with the takedown reason.
3. Installed instances:
   a. On the next launch-time CRL fetch (within 24 hours), the host detects the plugin in the CRL.
   b. The host disables the plugin (per `PLUGIN-SIGNING.md` §6.3).
   c. The host surfaces a takedown notice in the dashboard with the moderator's reason.
   d. The plugin's sandbox iframe will not load; the plugin's configuration data is preserved for export.
4. The author may appeal by opening a moderation ticket. Appeals are reviewed by a different maintainer than the one who issued the takedown.

### 4.7 SLA

- Median time from submission to first automated-check result: < 60 seconds.
- Median time from automated-pass to human-review completion: < 5 business days.
- Verified Vendor submissions (§5): expedited to < 2 business days.
- Takedown notice to installed hosts: < 24 hours (driven by the CRL fetch cadence).

---

## 5. Verified Vendor badge

### 5.1 Purpose

The Verified Vendor badge distinguishes vendors who have completed identity verification. It does NOT exempt their plugins from the moderation pipeline — every plugin, verified vendor or not, goes through automated + human review. The badge grants:

- Expedited human review (§4.7 SLA).
- A visible badge in the marketplace UI (a blue checkmark + "Verified vendor" / "អ្នកផ្គត់ផ្គង់ដែលបានផ្ទៀងផ្ទាត់" tooltip).
- Higher submission rate limits (20 submissions/day, 100 active submissions).
- Eligibility to declare the `template.provider` and `automation.provider` extension points (per `PLUGIN-SPEC.md` §4.12 / §4.13 — these are gated to verified vendors only because they have marketplace-listing side effects).

### 5.2 Verification requirements

A vendor must submit:

1. **Business license** — a scan of an active business registration from the vendor's jurisdiction. For Cambodian vendors: a Ministry of Commerce registration certificate. For international vendors: the equivalent (e.g. state Secretary of State filing for US, Companies House for UK).
2. **Government-issued photo ID** of the principal contact (passport preferred; national ID accepted). The ID name must match the business license's authorized representative.
3. **Bank account verification** — a recent (≤90 days) bank statement showing the vendor's business name, OR a voided check.
4. **Domain ownership** — a DNS TXT record `_einvite-verify` on the vendor's declared domain matching a token the marketplace issues during the application.

Submissions are made via `POST /_marketplace/vendors/apply-verified` (multipart upload, encrypted at rest with the marketplace CA's encryption key). Documents are reviewed by a marketplace maintainer within 5 business days.

### 5.3 Storage + retention

- Verification documents are stored in the marketplace's encrypted ObjectStorage (per V32 storage abstraction) under `vendor_verification/{vendor_id}/`.
- Access is restricted to marketplace maintainers with the `vendor_verifier` role.
- Documents are retained for the lifetime of the vendor's marketplace account + 7 years (tax/audit requirement in most jurisdictions).
- On vendor account deletion, documents are securely deleted (per V32 data retention policy).

### 5.4 Revocation

A vendor's Verified Vendor status can be revoked:

1. If the vendor's business license expires and is not renewed within 90 days.
2. If the vendor's account is banned (§4.5 BAN).
3. If a court order or law-enforcement request requires it.

Revocation removes the badge from the marketplace UI, reverts the vendor's submission rate limits to the standard tier, and prevents the vendor from submitting NEW `template.provider` / `automation.provider` plugins (existing ones remain but cannot be updated without re-verification).

### 5.5 Public visibility

A vendor's Verified Vendor status is queryable at:

```
GET /_marketplace/vendors/{vendor_id}/verification
→ {
  "vendor_id": "...",
  "verified": true,
  "verified_at": 1789300000,
  "expires_at": 1820900000,
  "jurisdiction": "Cambodia",
  "marketplace_ca_signed_assertion": "..."
}
```

The response is signed by the marketplace CA so hosts and end-users can verify the assertion independently. The `expires_at` matches the business-license expiration date.

---

## 6. User reports

### 6.1 Report submission

Any host can report a plugin from the plugin manager UI:

```
POST /api/plugins/{plugin_id}/report
{
  "reason": "malicious_behavior" | "privacy_violation" | "broken_functionality" | "copyright_infringement" | "other",
  "details": "Free text, max 2000 chars",
  "evidence_urls": ["https://..."]  // optional, max 3 URLs
}
```

The report is submitted via the host's existing authenticated API (Argon2id + MFA per V54). Anonymous reports are NOT accepted (defends against report-spamming attacks against competitors' plugins).

### 6.2 Report triage

- Reports enter the moderation queue.
- The moderation dashboard surfaces plugins ranked by report count in the last 7 days.
- A plugin with ≥3 reports in 7 days OR any report with `reason: malicious_behavior` OR `reason: privacy_violation` is auto-escalated to the front of the review queue.
- Maintainers triage each report: dismiss (with reason) or escalate to a takedown review (§4.6).

### 6.3 Reporter feedback

- The reporter receives an email when the report is triaged (decision: dismissed / under review / plugin taken down).
- Reporters are NOT notified of the specific takedown action taken (to avoid tipping off malicious actors who may be probing the moderation response time).

### 6.4 Anti-abuse

- A single user can submit at most 5 reports per day per plugin.
- A user who has had ≥3 reports dismissed as "frivolous" in the last 30 days is rate-limited to 1 report per day across all plugins.
- Reports that contain legal threats or personally-identifying information about the plugin author are auto-forwarded to legal counsel and the user is informed that their report has been received.

---

## 7. Marketplace maintainer roles

| Role | Capabilities |
|---|---|
| `maintainer.review` | Pull submissions from the queue, run human review, approve / resubmit / reject. |
| `maintainer.takedown` | Issue takedowns (separation of duty: the maintainer who approves a plugin cannot issue its takedown — a different maintainer must). |
| `vendor_verifier` | Review Verified Vendor applications. |
| `ca_signer` | Trigger the marketplace CA signing workstation (physical presence required; 2-person rule). |
| `maintainer.admin` | Manage maintainer accounts, ban authors, manage role assignments. |

All maintainer actions are logged as `moderation.*` audit events (visible in the existing `audit_events` table per V32).

---

## 8. Acceptance criteria

- Automated pre-upload checks run in <60 seconds and reject ≥95% of malicious submissions (the residual <5% are caught by human review).
- Human review SLA: median <5 business days (Verified Vendor: <2).
- Takedown: a taken-down plugin is disabled on every installed host within 24 hours.
- Verified Vendor badge requires 4 artifacts (business license, photo ID, bank statement, domain verification); revoked automatically on business-license expiry.
- User reports: any report with `malicious_behavior` or `privacy_violation` reason is auto-escalated to the front of the queue.
- Every maintainer action is audit-logged.

---

## 9. References

- `docs/plugins/PLUGIN-SPEC.md` — manifest format (drives §3.1 schema validation).
- `docs/plugins/PLUGIN-SIGNING.md` — signature verification (drives §3.5 entrypoint signature check) + CRL (drives §4.6 takedown).
- `docs/plugins/PLUGIN-SANDBOX.md` — runtime isolation (drives §4.3 security audit: the sandbox must enforce what the manifest declares).
- `src/js/plugin-runtime-v48.js:forbidden` — the V48 forbidden-field set extended in §3.3.
- `src/python/security_scanner_v54.py` — the malware scanner applied to `asset:upload` calls from a sandboxed plugin.
- `src/python/secrets_v54.py` — the secrets vault that plugins must NOT bundle (§4.3 security audit).
- `docs/ops/BACKUP-DR.md` — marketplace ObjectStorage backup (vendor verification documents are stored in the same encrypted ObjectStorage).
- `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md` — permission grammar (drives §3.7 permission audit).

*Last updated: Phase 4a (V54.6).*
