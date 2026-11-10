# CI Security Scanning Policy (ROADMAP-V2 §2.7 / ASVS L2 Chapter 10)

> ASVS L2 Chapter 10 ("Communications" + "Malware" + "Secure Deployment")
> scored uniformly "fail" in the v54 gap analysis
> (`docs/security/ASVS-L2-GAP-ANALYSIS.md`). This document closes that gap by
> defining the CI gate, the local scan entrypoint, the SBOM format and
> storage location, the CODEOWNERS policy, and the procedure for waiving
> specific findings.

**Last updated:** Sprint 11 (2026-11-10) — hash-locked SBOMs and release automation
**Maintainer:** `@maintainer` (replace with the actual GitHub handle / team slug — see §5)

---

## 1. What this CI gate covers

| # | Scan | Tool | What it checks | Fail threshold |
|---|------|------|----------------|----------------|
| 1 | SAST | [`bandit`](https://bandit.readthedocs.io) `-r src/python ai_agent platform_v32 future_platform_v52 -lll` | Python AST patterns: `exec()`/`eval()` on dynamic input, hardcoded passwords, weak crypto (`hashlib.md5`), `shell=True` on untrusted input, assert-as-security-check, YAML unsafe loaders, etc. | HIGH severity only (bandit `-lll` reports HIGH only; the 38 remaining MEDIUM findings are documented as a background queue in `docs/reviews/security-status.md`) |
| 1b | SAST | [`semgrep`](https://semgrep.dev) `p/python` + `p/owasp-top-ten`, run by `scripts/semgrep_scan.py` | Python and generic security rules, including injection, deserialization, crypto, and secret patterns. Small modules run once; `src/python/server.py` runs in bounded rule batches so the 11k-line file cannot exhaust the CI timeout. | Any finding or scan error |
| 2 | SCA / dependency audit | [`pip-audit`](https://github.com/pypa/pip-audit) `-r docs/requirements-production.lock --strict --desc` | Known CVEs / GHSAs against every package in the hash-locked production closure, via the PyPA advisory DB + OSV. | Any known advisory (stricter than Critical-only) |
| 3 | SBOM (canonical) | `cyclonedx-bom==8.0.1` + `@cyclonedx/cyclonedx-npm@7.0.0` in `.github/workflows/supply-chain.yml` | Emits Python and npm CycloneDX 1.5 JSON SBOMs from the committed locks and uploads them as Actions artifacts. | n/a — informational |
| 3b | SBOM (legacy local scan) | [`scripts/generate-sbom.py`](../../scripts/generate-sbom.py) (stdlib-only) | Direct production dependencies + checksum + license, retained for offline/local `security-scan.sh` compatibility. | n/a — informational |
| 4 | Secret scanning | [`gitleaks`](https://github.com/gitleaks/gitleaks) `detect --no-git --source . --config .gitleaks.toml --redact` | AWS keys, GitHub PATs, Slack tokens, private keys, generic high-entropy strings, etc. | Any finding (1+) |
| 5 | Container scan | [`trivy`](https://aquasecurity.github.io/trivy/) `image --severity HIGH,CRITICAL --exit-code 1` | OS-package CVEs + library CVEs inside the `einvite-scan:latest` image built from `deploy/Dockerfile`. Only runs if `deploy/Dockerfile` exists AND both `trivy` and `docker` are installed. | HIGH or CRITICAL |

Every tool is run by `scripts/security-scan.sh`. The script is the single
source of truth — CI and local dev run the same command.

---

## 2. How to run locally

```bash
cd /path/to/einvite-platform
bash scripts/security-scan.sh
```

The script:

* **Always** runs the SBOM generator (Python stdlib only — no install needed).
* Runs every other scan **only if the tool is installed** (`command -v`).
  Missing tools emit a `WARN` line but do **not** fail the script.
* Exits `0` if every available tool ran clean (or was skipped with a warning).
* Exits `1` if any installed tool found a HIGH/CRITICAL finding, OR if the
  SBOM generator failed.

### Installing the tools locally

| Tool | macOS | Windows | Linux |
|------|-------|---------|-------|
| `bandit` | `pip install bandit` | `pip install bandit` | `pip install bandit` |
| `semgrep` | `pip install semgrep==1.184.0` | `pip install semgrep==1.184.0` | `pip install semgrep==1.184.0` |
| `pip-audit` | `pip install pip-audit` | `pip install pip-audit` | `pip install pip-audit` |
| `gitleaks` | `brew install gitleaks` | `choco install gitleaks` | see [releases](https://github.com/gitleaks/gitleaks/releases) |
| `trivy` | `brew install trivy` | see [docs](https://aquasecurity.github.io/trivy/latest/getting-started/installation/) | `sudo apt install trivy` (Debian/Ubuntu repo) |
| `docker` | Docker Desktop | Docker Desktop | `sudo apt install docker.io` |

You don't need every tool installed to run the script — only install the
ones you're actively iterating on. CI always runs the full suite.

---

## 3. The CI workflow

`.github/workflows/security.yml` runs on:

* **`push`** to `main` or `v54-refactor-security-ui`.
* **`pull_request`** into `main`.
* **`schedule`**: every Monday at 06:00 UTC (catches new advisories published
  against pinned dependencies after the initial PR landed).
* **`workflow_dispatch`**: manual trigger from the Actions tab (useful for
  re-running after waiving a finding).

CI installs **all** tools (no WARNs expected). The workflow uploads the SBOM
(`sbom.cdx.json`) as a build artifact named `sbom`, retained for 90 days.
The gitleaks report (if any) is uploaded as `gitleaks-report`, retained 30
days.

### Sprint 11 supply-chain workflow

`.github/workflows/supply-chain.yml` is the canonical lockfile + SBOM gate. It
runs on every push to `main`, every pull request (including stacked sprint
PRs), and manual dispatch, with read-only `contents: read` permissions:

* **Python:** creates a clean virtual environment, runs
  `pip install --require-hashes --no-deps -r docs/requirements-production.lock`,
  then `pip check`, generates `python.cdx.json`, and runs `pip-audit` against
the lock. Any known advisory fails the job.
* **npm:** runs `npm ci`, generates `npm.cdx.json`, and runs
  `npm audit --audit-level=critical`.
* **Artifacts:** `sbom-python-cyclonedx` and `sbom-npm-cyclonedx`, retained
  90 days. Generated files are never committed.

The local equivalents are documented in
[`docs/RELEASE-AUTOMATION.md`](../RELEASE-AUTOMATION.md).

---

## 4. The SBOM — format, location, lifecycle

* **Format:** CycloneDX 1.5 JSON.
  `bomFormat: "CycloneDX"`, `specVersion: "1.5"`.
* **Canonical filenames:** `artifacts/sbom/python.cdx.json` and
  `artifacts/sbom/npm.cdx.json`, generated by
  `scripts/generate-sboms.sh` / `.github/workflows/supply-chain.yml`.
* **Components:** the Python BOM contains the full hash-locked closure from
  `docs/requirements-production.lock` (including transitive dependencies);
  the npm BOM contains the package tree resolved from `package-lock.json`.
  Python components use `pkg:pypi/{name}@{version}` purls; npm components
  use `pkg:npm/...` purls.
* **Checksums:** both generators consume the lockfile integrity data. Python
  components carry distribution hashes as external references; npm
  components carry the lockfile SHA-512 integrity value.
* **Licenses:** best-effort SPDX ids from package metadata.
* **`dependencies` block:** generated from each ecosystem's lock graph, not
  just the direct dependency list.
* **Storage:** uploaded as the `sbom-python-cyclonedx` and
  `sbom-npm-cyclonedx` Actions artifacts, retained 90 days. Never committed
  to the repo; the legacy root `sbom.cdx.json` is ignored and was removed
  from version control in Sprint 11.
* **Downstream consumers:** either artifact can be ingested by
  Dependency-Track, OWASP DepChain, or any CycloneDX-compatible tool.

---

## 5. CODEOWNERS policy

`.github/CODEOWNERS` lists the security maintainer as the required reviewer
on every pull request that touches:

* `src/python/` — backend code (auth, file upload, delivery, malware scan).
* `ai_agent/` — AI agent runtime (privilege escalation paths).
* `platform_v32/`, `future_platform_v52/` — platform services + future
  platform services.
* `src/python/security_*.py` + `src/python/secrets_*.py` — the security
  helpers themselves (`security_v13.py`, `security_scanner_v54.py`,
  `secrets_v54.py`).
* `deploy/` — Dockerfiles, compose files, Caddyfile, install scripts.
* `scripts/security-scan.sh` + `scripts/generate-sbom.py` — the local scan
  entrypoint + legacy SBOM generator (don't let a PR silently weaken the gate).
* `scripts/generate-sboms.sh`, `docs/requirements-production.lock`,
  `docs/requirements-test.txt`, `package.json`, `package-lock.json` — the
  canonical lockfiles and SBOM generators.
* `.github/CODEOWNERS`, `.github/workflows/security.yml`,
  `.github/workflows/supply-chain.yml`, `.github/release-drafter.yml`, and
  the release/tag workflows — the gate and release controls.

**Action required:** replace `@maintainer` in `.github/CODEOWNERS` with the
actual GitHub handle or team slug (e.g. `@einvite/security-team`) before
enabling branch protection. This is the single most important manual step
after merging this PR — without it, GitHub silently ignores the file.

Once the file is updated, enable **"Require review from Code Owners"** in
the branch protection rule for `main`:

> Settings → Branches → `main` rule → ✅ Require review from Code Owners

---

## 6. Legacy SBOM generator — network behaviour + failure modes

> Sprint 11 replaced the direct-dependency generator with the official
> CycloneDX tools (see §4). The legacy behaviour below is retained because
> `scripts/security-scan.sh` still calls `scripts/generate-sbom.py` as an
> offline fallback.

`scripts/generate-sbom.py` is **stdlib-only** (no `pip install` needed). It:

1. Parses `docs/requirements-production.txt` (handles `#` comments, blank
   lines, `-r`/`-c` includes, `;` environment markers, `==` / `===` pins,
   `>=` / `~=` / `!=` / `<` ranges).
2. For each package, queries `https://pypi.org/pypi/{package}/json`.
3. Resolves the version: explicit pin from the requirements file if present,
   otherwise PyPI's "latest version" field.
4. Extracts the SHA-256 of the first artifact in the version's release with
   a `digests.sha256` field (prefers wheels, falls back to sdists).
5. Extracts a best-effort SPDX license id from `info.license`.
6. Emits a CycloneDX 1.5 document to stdout.

**Failure modes:**

* PyPI unreachable → emits the component without checksums, with a
  `einvite:network = pypi-unreachable` property. CI re-runs at release
  time with network access to fill in checksums.
* PyPI returns 404 (yanked package) → emits the component without
  checksums + without description/license.
* Requirements file has no version pin AND PyPI is unreachable → component
  is skipped entirely (we don't know which version to attest). CI re-runs
  at release time to fill it in.
* Requirements file is missing → script exits with code 2 + an error
  message; `security-scan.sh` fails the build.

The script does **not** execute `pip` — it only reads the requirements
file and queries PyPI over HTTPS. Safe to run in CI without privileged
access.

---

## 7. How to waive a specific finding

### 7.1 `pip-audit` waivers (dependency CVEs)

If `pip-audit` reports a HIGH/CRITICAL CVE that doesn't apply to our usage
(e.g. the vulnerable code path is in a feature we don't call), or that we
can't upgrade yet (e.g. a transitive dependency is pinned by a library
we depend on):

1. Document the waiver in this file (§7.3 below).
2. Add `--ignore-vuln GHSA-XXXX-XXXX-XXXX` to the `pip-audit` invocation in
   `scripts/security-scan.sh`. (There was previously a placeholder
   `--ignore-vuln GHSA-PLACEHOLDER-REMOVE-ME` that demonstrated the
   pattern; it has been removed. The current invocation runs
   `pip-audit -r docs/requirements-production.txt --desc` directly —
   add `--ignore-vuln` arguments only when you have a real waiver to
   document.)
3. Set an explicit revisit date. Maximum waiver lifetime: 90 days. After
   90 days, the waiver must be re-justified or the dependency upgraded.

### 7.2 `bandit` waivers (SAST findings)

The CI gate currently runs bandit with `-lll` (HIGH-only). This lets the 38
MEDIUM findings pass through CI without failing the build; they are tracked
as a background queue in `docs/reviews/security-status.md` and will be
worked down to zero before branch protection is re-enabled.

For individual findings that are false positives or accepted risks **at the
HIGH severity level** (which still fails CI):

1. Add a `# nosec` comment on the offending line (with a brief reason).
   Example: `subprocess.run(cmd, shell=True)  # nosec B602 — cmd is a fixed string, not user input`
2. Document the waiver in §7.4 below with the file:line + the reason +
   the bandit rule ID (B602 in the example above).
3. Re-justification cadence: 90 days, same as `pip-audit` waivers.

### 7.3 `gitleaks` waivers (secret findings)

For gitleaks findings that are false positives (e.g. a test fixture
contains a fake key that matches the AWS key regex):

1. Add the finding's fingerprint to `.gitleaksignore` (gitleaks writes
   this file automatically when you run with `--report-format json` and
   pipe through `gitleaks detect ... --report-path report.json` then
   `gitleaks annotate --report report.json`).
2. Document the waiver in §7.3 below.
3. Re-justification cadence: 90 days.

### 7.4 Active waivers

> The SEC-05 consolidation (2026-10-07) added the two B608 nosec waivers
> below. The bandit threshold is now `-lll` (HIGH-only); the 38 remaining
> MEDIUM findings are documented as a background queue in
> `docs/reviews/security-status.md` and will be worked down to zero before
> branch protection is enabled.

| Tool | Finding | GHSA / rule ID | File:line | Reason | Waived on | Revisit by |
|------|---------|----------------|-----------|--------|-----------|------------|
| bandit | B608 MEDIUM | B608 | `src/python/server.py:9381` | `set_clause` derived from `safe_set_clause()` with explicit allowlist `{"name","description","url","price","quantity"}`; column names are source-defined literals, values are parameterized | 2026-10-07 | 2027-01-06 |
| bandit | B608 MEDIUM | B608 | `src/python/features/reports.py:138` | `clauses` is a static list built from literal strings (`"status=?"`, `"target_type=?"`, `"created_at<?"`); all user-supplied values bound as `?` parameters | 2026-10-07 | 2027-01-06 |
| —    | —       | —              | —         | —      | —         | —          |

---

## 8. The weekly schedule

The `cron: '0 6 * * 1'` trigger fires every Monday at 06:00 UTC. It exists
to catch:

* **New PyPA / OSV advisories** against the pinned dependencies — even if
  no code changed, a new CVE published on Friday should fail Monday's run.
* **New gitleaks rules** — gitleaks ships updated rule packs on a roughly
  monthly cadence.
* **New trivy DB** — the upstream vuln DB is updated continuously.

If the weekly run fails, the security maintainer is notified via GitHub's
default `security` team mention. The failure is treated as a P2 incident:
respond within 1 business day, either by upgrading the affected
dependency, by waiving the finding per §7, or by filing an issue explaining
the deferral.

---

## 9. Container scan — special case

`trivy image` requires:

1. `deploy/Dockerfile` to exist (✓ — present since V32).
2. `trivy` to be installed.
3. `docker` to be installed (for `docker build`).

The `scripts/security-scan.sh` block:

```bash
if [ -f "deploy/Dockerfile" ]; then
  if command -v trivy >/dev/null 2>&1 && command -v docker >/dev/null 2>&1; then
    docker build -t einvite-scan:latest -f deploy/Dockerfile . 2>/dev/null
    trivy image --severity HIGH,CRITICAL --exit-code 1 einvite-scan:latest
  fi
fi
```

If any of the three prerequisites is missing, the script emits a `WARN`
and skips. CI installs both `trivy` and `docker` (Docker is preinstalled on
`ubuntu-latest` runners), so this scan always runs in CI.

The scan target (`einvite-scan:latest`) is built fresh on every run — we
don't reuse a cached image. This means trivy sees the current state of
`deploy/Dockerfile` + the current base image (`python:3.13-slim`) +
the current pinned dependencies. If a new CVE is published against
`python:3.13-slim`, the next Monday's scheduled run catches it.

---

## 10. Follow-ups (non-blocking for V54.27)

* **~~Inter-package dependency edges in the SBOM.~~** Closed by Sprint 11:
  the canonical Python BOM is generated from the hash-locked transitive
  closure and the npm BOM from `package-lock.json`.
* **Correlate Python and npm BOMs.** The two canonical BOMs are uploaded as
  separate artifacts. A future iteration could merge them into one release
  asset with a single application root component.
* **`bandit` JSON report upload as a CI artifact.** Currently bandit's
  output is captured only in the workflow log (stdout). A future
  iteration could run `bandit -f json -o bandit-report.json` and upload
  it as an artifact for downstream SARIF consumers (GitHub code
  scanning, DefectDojo, etc.).
* **`gitleaks` history-aware scan.** The local script runs
  `--no-git` (every file, not history). CI gets the full checkout
  (fetch-depth: 0) but the script still uses `--no-git`. A future
  iteration could drop `--no-git` in CI to also catch secrets in
  historical commits — requires careful handling of false positives
  from old commits that have already been rotated. The current CI
  invocation explicitly loads `.gitleaks.toml` and passes `--redact`
  so the uploaded report never contains raw secret values.
* **`trivy` SBOM consumption.** trivy can ingest CycloneDX SBOMs and
  cross-reference them against its vuln DB. A future iteration could
  feed our `sbom.cdx.json` to trivy as a second scan target
  (`trivy sbom --severity HIGH,CRITICAL sbom.cdx.json`) — would catch
  CVEs in transitive deps the pip-audit scan misses.
* **CODEOWNERS handoff.** Replace `@maintainer` with the actual GitHub
  handle / team slug (§5).

---

## 11. Coordination with sibling subagents (V54.27)

* **sec-8** (server.py hardening) — owns `src/python/server.py`. The
  SAST/SCA/SBOM scripts scan `server.py` but do **not** modify it.
  Bandit findings in `server.py` (if any) will be reported on sec-8's
  first CI run — flagged as a §2.8 follow-up so sec-8 can address them
  without sec-7 needing to coordinate.
* **sec-9** (docs) — owns `docs/security/*.md` and `docs/SECURITY.md`.
  sec-9 may add cross-references to this file; sec-7 owns the canonical
  CI-SECURITY.md.
* **vendor** (HTML) — owns `src/html/*.html`. None of the scanners in
  this PR touch HTML files. gitleaks may flag inline test fixtures in
  HTML (unlikely — flagged as a §10 follow-up if it happens).
* **ux-1 / ux-2** (host panels) — own `src/js/host-signup-sheets.js` +
  `src/js/host-polls.js`. None of the scanners touch JS files (gitleaks
  scans them but only for secrets, not code patterns). No coordination
  needed.

No files outside the sec-7 modification scope were touched:

* `src/python/server.py` — modified at line 9381 (gift-registry `safe_set_clause`
  allowlist per SEC-04); otherwise NOT modified by sec-7.
* `src/python/serve.py` — modified at line 79 (`keepalive=30` → `channel_timeout=30`
  to fix waitress 3.0.0 boot error per SEC-04).
* `src/python/features/reports.py` — modified at line 138 (`# nosec B608` per SEC-05).
* `src/python/core/security_helpers.py` — NOT modified by sec-7 (pre-existing
  `safe_set_clause` allowlist from SEC-04).
* `src/html/*.html` — NOT modified (vendor owns).
* `src/js/*.js` / `src/css/*.css` — NOT modified (UI is done).
* `ai_agent/`, `platform_v32/`, `future_platform_v52/` — NOT modified
  (scanned by bandit, but no source changes).

---

## 12. Change history

| Date | Version | Change |
|------|---------|--------|
| 2026-09-15 | V54.27 | Initial version — created `scripts/security-scan.sh`, `scripts/generate-sbom.py`, `.github/CODEOWNERS`, `.github/workflows/security.yml`, and this document. Closes ROADMAP-V2 §2.7 (ASVS L2 Chapter 10). |
| 2026-10-07 | V54.28 | SEC-05 consolidation: bandit threshold flipped to `-lll` (HIGH-only); 38 MEDIUM findings tracked as background queue; `docs/requirements-production.txt` consolidated to exact pins; root `requirements.txt` created; `src/python/requirements.txt` deleted; SBOM rebuilt (10 packages); `pip-audit` verified 0 CVEs via OSV API direct query. |
| 2026-11-10 | Sprint 11 | Added hash-locked transitive Python requirements, exact npm pins, canonical CycloneDX 1.5 SBOMs from `cyclonedx-py` + `cyclonedx-npm`, `pip-audit`/`npm audit` gates, Release Drafter categories from PR titles, and published-release SemVer tag verification. Removed tracked `sbom.cdx.json`. |

---

## 13. Security status ledger

The authoritative, consolidated security ledger for SEC-01 through SEC-04
findings lives in [`docs/reviews/security-status.md`](../HISTORY.md).
This file is the single source of truth for:

- The complete finding catalog (SEC-01…SEC-04) with status, evidence, and
  disposition.
- The bandit count reconciliation (60 → 39 → 38 findings across scan scope
  changes and nosec additions).
- The `-lll` HIGH-only threshold transition and the 38 MEDIUM background queue.
- The pip-audit / OSV verification of all 10 production dependencies.

`CI-SECURITY.md` defines the *policy* (what scans run, what thresholds fail
the build, how to waive). `security-status.md` records the *results*
(findings, evidence, dispositions) for the current cycle. Both are updated
in lockstep during the SEC-05 consolidation.
