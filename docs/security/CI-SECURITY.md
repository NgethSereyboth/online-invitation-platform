# CI Security Scanning Policy (ROADMAP-V2 §2.7 / ASVS L2 Chapter 10)

> ASVS L2 Chapter 10 ("Communications" + "Malware" + "Secure Deployment")
> scored uniformly "fail" in the v54 gap analysis
> (`docs/security/ASVS-L2-GAP-ANALYSIS.md`). This document closes that gap by
> defining the CI gate, the local scan entrypoint, the SBOM format and
> storage location, the CODEOWNERS policy, and the procedure for waiving
> specific findings.

**Last updated:** V54.27 (sec-7)
**Maintainer:** `@maintainer` (replace with the actual GitHub handle / team slug — see §5)

---

## 1. What this CI gate covers

| # | Scan | Tool | What it checks | Fail threshold |
|---|------|------|----------------|----------------|
| 1 | SAST | [`bandit`](https://bandit.readthedocs.io) `-r src/python ai_agent platform_v32 future_platform_v52 -ll` | Python AST patterns: `exec()`/`eval()` on dynamic input, hardcoded passwords, weak crypto (`hashlib.md5`), `shell=True` on untrusted input, assert-as-security-check, YAML unsafe loaders, etc. | HIGH severity (bandit `-ll` reports only HIGH and exits non-zero if any are found) |
| 2 | SCA / dependency audit | [`pip-audit`](https://github.com/pypa/pip-audit) `-r docs/requirements-production.txt --desc` | Known CVEs / GHSAs against every pinned production dependency, via the PyPA advisory DB + OSV. | HIGH or CRITICAL CVSS |
| 3 | SBOM | [`scripts/generate-sbom.py`](../../scripts/generate-sbom.py) (stdlib-only) | Emits a CycloneDX 1.5 SBOM of every production dependency + checksum + license. Always runs; never fails the build (only warns). | n/a — informational |
| 4 | Secret scanning | [`gitleaks`](https://github.com/gitleaks/gitleaks) `detect --no-git --source .` | AWS keys, GitHub PATs, Slack tokens, private keys, generic high-entropy strings, etc. | Any finding (1+) |
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

---

## 4. The SBOM — format, location, lifecycle

* **Format:** CycloneDX 1.5 JSON.
  `bomFormat: "CycloneDX"`, `specVersion: "1.5"`, `serialNumber: urn:uuid:<uuid4>`.
* **Filename:** `sbom.cdx.json` (written to the repo root by `scripts/security-scan.sh`).
* **Components:** every entry in `docs/requirements-production.txt` becomes a
  `library` component with a `pkg:pypi/{name}@{version}` purl + bom-ref.
* **Checksums:** when the PyPI JSON API is reachable, each component carries
  a `hashes: [{alg: "SHA-256", content: "<hex>"}]` entry — the SHA-256 of
  the resolved wheel/sdist artifact. When PyPI is unreachable (sandbox, air-
  gapped CI runner), the component is emitted without checksums and with a
  `properties: [{name: "einvite:network", value: "pypi-unreachable"}]`
  marker recording the gap. CI re-runs the SBOM with network access at
  release time so published SBOMs always carry checksums.
* **Licenses:** best-effort SPDX id extracted from the PyPI `info.license`
  field (only emitted if it matches the SPDX id pattern; free-form license
  strings are dropped to keep the document validatable).
* **Top-level `metadata.component`:** `pkg:generic/einvite-platform@v54`
  (the application itself — required by CycloneDX 1.5 so consumers can
  distinguish the BOM owner from its dependencies).
* **`dependencies` block:** a single edge from the application component to
  every library component (no inter-package edges — that would require
  resolving the full transitive closure with `pip freeze`; flagged as
  follow-up §10).
* **Storage:** committed as an artifact on every CI run; not committed to
  the repo (it would create churn on every dependency bump).
* **Downstream consumers:** the artifact can be ingested by Dependency-Track,
  OWASP DepChain, or any CycloneDX-compatible tool. Re-use of the SBOM for
  license compliance / supply-chain attestation is a §10 follow-up.

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
* `scripts/security-scan.sh` + `scripts/generate-sbom.py` — the scan
  entrypoint + SBOM generator (don't let a PR silently weaken the CI gate).
* `.github/CODEOWNERS` + `.github/workflows/security.yml` — the gate
  itself.

**Action required:** replace `@maintainer` in `.github/CODEOWNERS` with the
actual GitHub handle or team slug (e.g. `@einvite/security-team`) before
enabling branch protection. This is the single most important manual step
after merging this PR — without it, GitHub silently ignores the file.

Once the file is updated, enable **"Require review from Code Owners"** in
the branch protection rule for `main`:

> Settings → Branches → `main` rule → ✅ Require review from Code Owners

---

## 6. SBOM generator — network behaviour + failure modes

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
   `scripts/security-scan.sh`. (There is currently a placeholder
   `--ignore-vuln GHSA-PLACEHOLDER-REMOVE-ME` that demonstrates the
   pattern — remove it when adding the first real waiver, or leave it in
   if you have zero waivers and the placeholder `2>/dev/null ||` fallback
   handles it gracefully.)
3. Set an explicit revisit date. Maximum waiver lifetime: 90 days. After
   90 days, the waiver must be re-justified or the dependency upgraded.

### 7.2 `bandit` waivers (SAST findings)

For bandit findings that are false positives or accepted risks:

1. Add a `# nosec` comment on the offending line (with a brief reason).
   Example: `subprocess.run(cmd, shell=True)  # nosec B602 — cmd is a fixed string, not user input`
2. Document the waiver in §7.3 below with the file:line + the reason +
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

> **None.** The first run of `security-scan.sh` (V54.27) found no findings
> because the SAST / SCA / secret tools aren't installed in the sandbox.
> CI will populate this table on first run; any waivers added afterwards
> must be recorded here.

| Tool | Finding | GHSA / rule ID | File:line | Reason | Waived on | Revisit by |
|------|---------|----------------|-----------|--------|-----------|------------|
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

* **Inter-package dependency edges in the SBOM.** The current SBOM only
  lists direct dependencies from `docs/requirements-production.txt` — it
  doesn't resolve the transitive closure (would require `pip freeze` or
  the `pip-requirements-parser` graph walker). A future iteration could
  resolve the full tree and emit `dependencies: [{ref: ..., dependsOn:
  [...]}]` edges between library components. Flagged as §2.7 follow-up.
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
  from old commits that have already been rotated.
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

* `src/python/server.py` — NOT modified (sec-8 owns).
* `src/html/*.html` — NOT modified (vendor owns).
* `src/js/*.js` / `src/css/*.css` — NOT modified (UI is done).
* `ai_agent/`, `platform_v32/`, `future_platform_v52/` — NOT modified
  (scanned by bandit, but no source changes).

---

## 12. Change history

| Date | Version | Change |
|------|---------|--------|
| 2026-09-15 | V54.27 | Initial version — created `scripts/security-scan.sh`, `scripts/generate-sbom.py`, `.github/CODEOWNERS`, `.github/workflows/security.yml`, and this document. Closes ROADMAP-V2 §2.7 (ASVS L2 Chapter 10). |
