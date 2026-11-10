# Release Automation and Supply Chain

**Sprint 11 — 2026-11-10**

This document covers the two release paths added in Sprint 11:

1. **SBOM, strict lockfile validation, and Critical-CVE gating**.
2. **Draft release notes from merged PR titles and SemVer tagging on publish**.

No workflow publishes packages to PyPI or npm. Generated SBOMs are never
committed to the source tree.

## 1. Supply-chain workflow

`.github/workflows/supply-chain.yml` runs on pushes to `main`, pull requests
(including stacked sprint PRs), and manual dispatches. It has read-only
`contents: read` permissions.

### Python lock

`docs/requirements-production.lock` is the hash-locked transitive closure of
`docs/requirements-production.txt`. It is regenerated with:

```bash
uv pip compile docs/requirements-production.txt --generate-hashes \
  --python-version 3.12 --no-header --no-emit-index-url \
  --no-emit-find-links -o docs/requirements-production.lock
```

CI proves the lock with a clean virtual environment:

```bash
python3 -m venv .venv-supply-chain
.venv-supply-chain/bin/python -m pip install --require-hashes --no-deps \
  -r docs/requirements-production.lock
.venv-supply-chain/bin/python -m pip check
```

`--require-hashes` rejects any package whose artifact hash is not in the lock.
`--no-deps` ensures the lock already contains the complete closure; `pip check`
then verifies that closure is internally consistent.

### npm lock

`npm ci` is the lockfile gate. The root `package.json` pins every declared
dependency exactly, and `package-lock.json` is the only accepted install source
for CI. A stale lockfile fails `npm ci` before an SBOM is produced.

### SBOM generation

Both generators emit **CycloneDX 1.5 JSON**:

| Ecosystem | Generator | Input | Output |
|---|---|---|---|
| Python | `cyclonedx-bom==8.0.1` (`cyclonedx-py requirements`) | `docs/requirements-production.lock` | `artifacts/sbom/python.cdx.json` |
| npm | `@cyclonedx/cyclonedx-npm@7.0.0` | `package.json` + `package-lock.json` | `artifacts/sbom/npm.cdx.json` |

The workflow uploads them as the `sbom-python-cyclonedx` and
`sbom-npm-cyclonedx` Actions artifacts, retained for 90 days. The local
entrypoint is:

```bash
python3 -m pip install cyclonedx-bom==8.0.1
npm ci
bash scripts/generate-sboms.sh artifacts/sbom
```

### Vulnerability gate

* Python: `pip-audit -r docs/requirements-production.lock --strict --desc`
  fails on **any** known advisory affecting the locked tree. This is stricter
  than the requested Critical-only threshold.
* npm: `npm audit --audit-level=critical` fails at **Critical** severity.

The audit JSON is uploaded alongside the SBOM even when the gate fails.

## 2. Release notes and tagging

### Conventional PR titles

Release Drafter v7 parses conventional PR titles directly, so no label is
required and there is no separate autolabeler workflow. Labels remain optional
fallbacks for maintainers (`feature`, `bug`, `dependencies`, etc.).

| PR title | Category | SemVer effect |
|---|---|---|
| `feat:` / `feat(scope):` | Features | minor |
| `fix:` | Bug Fixes | patch |
| `perf:` | Performance | patch |
| `refactor:` | Refactoring | patch |
| `docs:` | Documentation | patch |
| `test:` | Tests | patch |
| `ci:` | CI | patch |
| `chore:` | Maintenance | patch |
| `chore(deps):` / `build(deps):` | Dependencies | patch |
| type with `!:` | Breaking change | major |
| `type(security|auth|secrets|cve):` | matcher review | label fallback only |

The highest matching increment wins. Release Drafter uses the last **published**
release as its comparison baseline. Because this repository has no published
release or SemVer tag yet, the first dry run reports `v0.0.1` with no changes and
asks for manual review. Once a baseline release exists, the same parser covers
every merged PR in the selected range, including PRs that predate this workflow.

### Release Drafter

`.github/workflows/release-drafter.yml` runs on every push to `main`. It uses
`release-drafter/release-drafter@v7` with only:

```yaml
permissions:
  contents: write
  pull-requests: read
```

It creates or updates a **draft** release. It never publishes it. The draft
name and tag templates are `v$RESOLVED_VERSION`; a human still reviews the
notes in the GitHub UI and clicks **Publish release**.

### SemVer tag on publish

Publishing the draft normally creates the tag at the release target. The
`Tag Published Release` workflow
(`.github/workflows/publish-release-tag.yml`) is the guard: it rejects
non-SemVer tags, verifies an existing tag points at the release commit, and
creates/pushes an annotated tag only if the published release has none. It
runs with only `contents: write`.

## 3. Representative draft from prior sprint titles

This is the shape a Release Drafter draft will use once the Sprint 3–10 PRs are
in the release comparison range. It is illustrative: the first actual draft has
no previous release baseline, so the version and contents must be reviewed
manually before publishing.

```markdown
## v0.71.0

### 🚀 Features
- feat: add privacy export, erasure, and PII retention controls (#35) — @NgethSereyboth
- feat: consolidate async delivery and add durable retries (#34) — @NgethSereyboth
- feat: bound outbound calls and resource pressure (#33) — @NgethSereyboth
- feat: surface request references in errors and logs (#30) — @NgethSereyboth

### ⚡ Performance
- perf: split check-in startup and inline critical CSS (#36) — @NgethSereyboth
- perf: tune SQLite and remove hot-path query duplication (#32) — @NgethSereyboth

### ♻️ Refactoring
- refactor: reduce Python complexity and dead code (#29) — @NgethSereyboth

### 🧪 Tests
- test: add strict core API contracts (#31) — @NgethSereyboth

## Contributors
@NgethSereyboth

**Full Changelog**: https://github.com/NgethSereyboth/online-invitation-platform/compare/...v0.71.0
```

## 4. Verification commands

```bash
# Python hash lock (same command as CI)
python3 -m venv .venv-supply-chain
.venv-supply-chain/bin/python -m pip install --require-hashes --no-deps \
  -r docs/requirements-production.lock
.venv-supply-chain/bin/python -m pip check

# npm lock (same command as CI)
npm ci

# Both SBOMs (CycloneDX 1.5 JSON)
bash scripts/generate-sboms.sh artifacts/sbom

# Workflow YAML parse
python3 - <<'PY'
import yaml
for path in (
    ".github/workflows/supply-chain.yml",
    ".github/workflows/release-drafter.yml",
    ".github/workflows/publish-release-tag.yml",
    ".github/release-drafter.yml",
):
    yaml.safe_load(open(path, encoding="utf-8"))
    print("YAML_OK", path)
PY
```
