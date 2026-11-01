# Open Dependabot vulnerabilities

**Snapshot:** 2026-11-01T04:53Z · **Repository:** `NgethSereyboth/online-invitation-platform` (public) · **Default branch:** `main` at `50721ef72fd4f7aab9c825e64ba1a0ad5183dc90`

**Source:** GitHub REST `GET /repos/NgethSereyboth/online-invitation-platform/dependabot/alerts?state=open&per_page=100`, plus `npm audit --package-lock-only` on the current `chore/cleanup` branch. Raw snapshots are in `artifacts/security/` (not committed).

This is the complete inventory behind GitHub's **92 vulnerabilities on the default branch** notice. The count includes duplicate alerts for the same advisory in more than one manifest; it is not 92 independent vulnerabilities.

## At a glance

| Metric | Value |
|---|---:|
| Open alerts | **92** |
| Unique advisories (GHSA) | **49** |
| Critical / high / medium / low alerts | **13 / 49 / 29 / 1** |
| Unique critical / high / medium / low advisories | **6 / 26 / 16 / 1** |
| Runtime / development alerts | **85 / 7** |
| Unique packages | **7** (`Pillow`, `Brotli`, `extract-zip`, `tmp`, `minimatch`, `qs`, `uuid`) |
| Manifests in the count | `docs/requirements-production.txt` (42), `requirements.txt` (42), `tools/requirements.txt` (1), `package-lock.json` (7) |

### Severity breakdown

| Severity | All alerts | Unique advisories | Runtime alerts | Development alerts |
|---|---:|---:|---:|---:|
| Critical | 13 | 6 | 13 | 0 |
| High | 49 | 26 | 46 | 3 |
| Medium | 29 | 16 | 26 | 3 |
| Low | 1 | 1 | 0 | 1 |
| **Total** | **92** | **49** | **85** | **7** |

### Why there are duplicates

- `requirements.txt` is only `-r docs/requirements-production.txt`, so every Python advisory is reported once for each file: 41 unique Pillow advisories × 2 manifests = 82 alerts.
- `tools/requirements.txt` separately pins the same Brotli release, so the one Brotli advisory appears three times.
- The seven npm alerts come from the older default-branch lockfile. The current branch has a much smaller lockfile; see [Current branch status](#current-branch-status).

## Current branch status

The warning is calculated against the **default branch**, not against the current `chore/cleanup` branch. This distinction changes the practical exposure:

| Dependency | `origin/main` | `chore/cleanup` at snapshot | Default-branch alerts | What it means here |
|---|---:|---:|---:|---|
| Pillow | `12.3.0` | `13.0.0` | 82 | **Already fixed on this branch** by `dac38e0`. The alerts stay open until the change reaches `main` and GitHub rescans it. |
| Brotli | `1.2.0` | `1.2.0` | 3 | **Still present** in both production and tool requirement files; fixed in `1.2.1`. |
| npm chain (`extract-zip`, `tmp`, `minimatch`, `qs`, `uuid`) | present | **not in this lockfile** | 7 | The branch's lockfile update removed these old development chains. The default-branch alerts remain; they are not shipped in the web bundle. |

**Current branch npm audit:** 3 high, development-only findings. These are **not** part of the 92 Dependabot alerts; they are a later lockfile state.

| Package | Installed | Finding | CVSS | Patched |
|---|---:|---|---:|---|
| `zod` | `3.25.76` | [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5): memory exhaustion while validating oversized constrained collections | 7.5 | `4.6.6` |
| `chromium-bidi` | `17.0.2` | Reported through its vulnerable `zod` dependency; no separate advisory in this audit | — | update the dev chain and re-audit |
| `puppeteer-core` | `25.12.0` | Reported through its vulnerable `zod`/`chromium-bidi` chain; no separate advisory in this audit | — | update the dev chain and re-audit |

`npm audit` reports that a fix is available for all three. They are tooling dependencies only: the deployed front end has no npm runtime bundle. Do not apply a force upgrade blindly; review the lockfile diff and rerun the browser tests.

**Current branch conclusion:** the only unique critical runtime advisory still present in the pinned manifests is **Brotli `CVE-2026-111497`**, fixed by upgrading `1.2.0` → `1.2.1`. The five Pillow critical advisories are fixed by the branch's `13.0.0` pin but remain visible on GitHub until that pin lands on `main`.

## Critical advisories

There are 13 critical **alerts**, but only **6 unique critical advisories**. Five are Pillow issues already fixed on the branch; one is the remaining Brotli issue.

| Advisory | Package | CVSS | Affected version | Patched | Alerts | Manifests |
|---|---|---|---|---|---|---|
| [GHSA-9v8h-qqgm-4m35](https://github.com/advisories/GHSA-9v8h-qqgm-4m35) / CVE-2026-111497 | Brotli | not scored | `>= 1.0.3, < 1.2.1` | `1.2.1` | [48](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/48), [93](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/93), [96](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/96) | `docs/requirements-production.txt`; `requirements.txt`; `tools/requirements.txt` |
| [GHSA-332p-7hrc-92wf](https://github.com/advisories/GHSA-332p-7hrc-92wf) / CVE-2026-112393 | Pillow | not scored | `>= 2.0.0, < 13.0.0` | `13.0.0` | [35](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/35), [80](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/80) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-5x8w-8jj5-q52h](https://github.com/advisories/GHSA-5x8w-8jj5-q52h) / CVE-2026-112398 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [50](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/50), [95](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/95) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-8g5g-8vmr-9782](https://github.com/advisories/GHSA-8g5g-8vmr-9782) / CVE-2026-112403 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [10](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/10), [54](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/54) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-v9pv-5gc8-w2m6](https://github.com/advisories/GHSA-v9pv-5gc8-w2m6) / CVE-2026-96639 | Pillow | 9.8 | `>= 11.0.0, < 13.0.0` | `13.0.0` | [40](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/40), [85](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/85) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-w889-685w-c8fh](https://github.com/advisories/GHSA-w889-685w-c8fh) / CVE-2026-112900 | Pillow | not scored | `>= 2.6.0, < 13.0.0` | `13.0.0` | [18](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/18), [63](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/63) | `docs/requirements-production.txt`; `requirements.txt` |

### What each critical issue is

- **Brotli — out-of-bounds write in the decoder.** A crafted Brotli-compressed stream can corrupt adjacent decoder memory, disclose memory, cause a denial of service, or potentially execute code. This is the one critical advisory still present on `chore/cleanup`; it is pinned in `docs/requirements-production.txt` and `tools/requirements.txt`. Fixed in **1.2.1**. Alerts: [48](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/48), [93](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/93), [96](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/96).
- **Pillow — heap overflow when writing TIFF to memory.** Saving a crafted image to a `BytesIO`-style TIFF sink can overflow the heap and leak adjacent memory. Fixed in **13.0.0**; the branch already uses it. Alerts: [35](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/35), [80](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/80).
- **Pillow — FlashPix/FPX JPEG decoder heap overflow.** Opening a crafted FPX file can lead to code execution, according to the advisory. Fixed in **13.0.0**; the branch already uses it. Alerts: [50](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/50), [95](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/95).
- **Pillow — heap buffer overflow in JPEG decoding.** A crafted JPEG can overflow the decode buffer. Pillow is on the image/asset path, so untrusted images deserve attention. Fixed in **13.0.0**; the branch already uses it. Alerts: [10](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/10), [54](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/54).
- **Pillow — stale native image storage across frames.** A multi-frame image can change mode while retaining a smaller buffer, leading to out-of-bounds writes and, in the reported MPO/JPEG path, demonstrated command execution. Highest listed CVSS: **9.8**. Fixed in **13.0.0**; the branch already uses it. Alerts: [40](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/40), [85](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/85).
- **Pillow — Ghostscript argument injection.** A filename beginning with `-` can be interpreted as a Ghostscript option, with a possible route to command execution. Fixed in **13.0.0**; the branch already uses it. Alerts: [18](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/18), [63](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/63).

## High advisories

**49 alerts / 26 unique advisories.**

| Advisory | Package | CVSS | Affected version | Patched | Alerts | Manifests |
|---|---|---|---|---|---|---|
| [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) / CVE-2026-112390 | Pillow | not scored | `>= 7.2.0, < 13.0.0` | `13.0.0` | [25](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/25), [70](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/70) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-27h8-gf7j-v5hc](https://github.com/advisories/GHSA-27h8-gf7j-v5hc) / CVE-2026-112392 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [23](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/23), [68](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/68) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-3j72-p6qg-6xp7](https://github.com/advisories/GHSA-3j72-p6qg-6xp7) / CVE-2026-96642 | Pillow | not scored | `< 13.0.0` | `13.0.0` | [43](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/43), [88](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/88) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-58r4-6rv3-gfh8](https://github.com/advisories/GHSA-58r4-6rv3-gfh8) / CVE-2026-112397 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [9](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/9), [62](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/62) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-5xm2-6676-qcp9](https://github.com/advisories/GHSA-5xm2-6676-qcp9) / CVE-2026-112399 | Pillow | not scored | `>= 8.1.0, < 13.0.0` | `13.0.0` | [32](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/32), [77](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/77) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-65qm-jvmh-6pqg](https://github.com/advisories/GHSA-65qm-jvmh-6pqg) / CVE-2026-112400 | Pillow | not scored | `>= 9.2.0, < 13.0.0` | `13.0.0` | [12](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/12), [61](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/61) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-78g4-xqwv-q3g8](https://github.com/advisories/GHSA-78g4-xqwv-q3g8) | Pillow | 8.1 | `>= 11.1.0, < 13.0.0` | `13.0.0` | [47](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/47), [92](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/92) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-7mwm-ghpf-9vrm](https://github.com/advisories/GHSA-7mwm-ghpf-9vrm) / CVE-2026-112402 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [20](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/20), [65](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/65) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-9v9v-9qvf-h2hj](https://github.com/advisories/GHSA-9v9v-9qvf-h2hj) / CVE-2026-96644 | Pillow | not scored | `< 13.0.0` | `13.0.0` | [45](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/45), [90](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/90) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-c6hw-5grf-ff96](https://github.com/advisories/GHSA-c6hw-5grf-ff96) / CVE-2026-112404 | Pillow | not scored | `>= 8.1.0, < 13.0.0` | `13.0.0` | [14](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/14), [55](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/55) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-cp9v-662q-vvx9](https://github.com/advisories/GHSA-cp9v-662q-vvx9) / CVE-2026-112405 | Pillow | not scored | `>= 12.0.0, < 13.0.0` | `13.0.0` | [22](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/22), [67](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/67) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-f2g6-542v-9j58](https://github.com/advisories/GHSA-f2g6-542v-9j58) / CVE-2026-112406 | Pillow | not scored | `>= 5.1.0, < 13.0.0` | `13.0.0` | [33](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/33), [78](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/78) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-g4qv-2jxx-769h](https://github.com/advisories/GHSA-g4qv-2jxx-769h) / CVE-2026-96643 | Pillow | not scored | `>= 11.0.0, < 13.0.0` | `13.0.0` | [44](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/44), [89](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/89) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-g7cr-3p24-7wf7](https://github.com/advisories/GHSA-g7cr-3p24-7wf7) / CVE-2026-96778 | Pillow | not scored | `>= 9.4.0, < 13.0.0` | `13.0.0` | [46](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/46), [91](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/91) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-g842-9rc4-69pw](https://github.com/advisories/GHSA-g842-9rc4-69pw) / CVE-2026-96637 | Pillow | not scored | `< 13.0.0` | `13.0.0` | [38](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/38), [83](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/83) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-gg2r-wvfm-q9rx](https://github.com/advisories/GHSA-gg2r-wvfm-q9rx) / CVE-2026-112892 | Pillow | not scored | `>= 4.1.0, < 13.0.0` | `13.0.0` | [31](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/31), [76](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/76) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-j4m9-6w36-pw47](https://github.com/advisories/GHSA-j4m9-6w36-pw47) / CVE-2026-112893 | Pillow | not scored | `>= 10.0.0, < 13.0.0` | `13.0.0` | [21](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/21), [66](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/66) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-jg86-v3jv-hrpm](https://github.com/advisories/GHSA-jg86-v3jv-hrpm) / CVE-2026-112894 | Pillow | not scored | `>= 5.1.0, < 13.0.0` | `13.0.0` | [30](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/30), [75](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/75) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-mrfp-p49p-3hf2](https://github.com/advisories/GHSA-mrfp-p49p-3hf2) / CVE-2026-96640 | Pillow | not scored | `>= 5.1.0, < 13.0.0` | `13.0.0` | [41](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/41), [86](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/86) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-p4wg-p73j-c528](https://github.com/advisories/GHSA-p4wg-p73j-c528) / CVE-2026-112895 | Pillow | not scored | `>= 5.1.0, < 13.0.0` | `13.0.0` | [16](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/16), [57](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/57) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-pchr-8j38-3x4p](https://github.com/advisories/GHSA-pchr-8j38-3x4p) / CVE-2026-112896 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [11](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/11), [58](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/58) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-q45j-58j2-45rg](https://github.com/advisories/GHSA-q45j-58j2-45rg) / CVE-2026-112897 | Pillow | not scored | `>= 5.3.0, < 13.0.0` | `13.0.0` | [15](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/15), [59](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/59) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-xvh5-g6gv-559v](https://github.com/advisories/GHSA-xvh5-g6gv-559v) / CVE-2026-112902 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [36](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/36), [81](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/81) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-7pqw-9j4j-h8q3](https://github.com/advisories/GHSA-7pqw-9j4j-h8q3) / CVE-2026-19693 | extract-zip | 8.1 | `<= 2.0.1` | `—` | [6](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/6) | `package-lock.json` |
| [GHSA-jmr9-qjv8-65gv](https://github.com/advisories/GHSA-jmr9-qjv8-65gv) / CVE-2026-56876 | extract-zip | 8.1 | `<= 2.0.1` | `—` | [5](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/5) | `package-lock.json` |
| [GHSA-ph9p-34f9-6g65](https://github.com/advisories/GHSA-ph9p-34f9-6g65) / CVE-2026-44705 | tmp | not scored | `< 0.2.6` | `0.2.6` | [4](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/4) | `package-lock.json` |

All 23 unique Pillow high advisories are fixed by `13.0.0` on this branch. The three npm high alerts belong to the old default-branch lockfile and are development-only; the current branch audit is described above.

## Medium advisories

**29 alerts / 16 unique advisories.**

| Advisory | Package | CVSS | Affected version | Patched | Alerts | Manifests |
|---|---|---|---|---|---|---|
| [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c) / CVE-2026-96638 | Pillow | 6.5 | `>= 9.1.0, < 13.0.0` | `13.0.0` | [39](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/39), [84](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/84) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-254f-3936-288h](https://github.com/advisories/GHSA-254f-3936-288h) / CVE-2026-112391 | Pillow | not scored | `>= 5.1.0, < 13.0.0` | `13.0.0` | [29](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/29), [74](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/74) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-4558-3h8r-v8xp](https://github.com/advisories/GHSA-4558-3h8r-v8xp) / CVE-2026-112394 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [19](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/19), [64](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/64) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) / CVE-2026-112395 | Pillow | 6.5 | `>= 8.2.0, < 13.0.0` | `13.0.0` | [13](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/13), [56](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/56) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-4rm8-3hmm-39fg](https://github.com/advisories/GHSA-4rm8-3hmm-39fg) / CVE-2026-96641 | Pillow | 6.5 | `< 13.0.0` | `13.0.0` | [42](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/42), [87](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/87) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-4rr5-89j8-mwwm](https://github.com/advisories/GHSA-4rr5-89j8-mwwm) / CVE-2026-112396 | Pillow | 5.9 | `>= 11.3.0, < 13.0.0` | `13.0.0` | [34](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/34), [79](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/79) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-654x-cwwv-5j9c](https://github.com/advisories/GHSA-654x-cwwv-5j9c) / CVE-2026-114501 | Pillow | not scored | `>= 11.2.1, < 13.0.0` | `13.0.0` | [49](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/49), [94](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/94) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-74r2-7ff9-mjj2](https://github.com/advisories/GHSA-74r2-7ff9-mjj2) / CVE-2026-112401 | Pillow | not scored | `>= 5.4.0, < 13.0.0` | `13.0.0` | [26](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/26), [71](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/71) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-fc9g-5qg7-mf45](https://github.com/advisories/GHSA-fc9g-5qg7-mf45) / CVE-2026-112891 | Pillow | not scored | `>= 9.2.0, < 13.0.0` | `13.0.0` | [24](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/24), [69](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/69) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-p8hx-v2p6-rp84](https://github.com/advisories/GHSA-p8hx-v2p6-rp84) / CVE-2026-96636 | Pillow | 6.5 | `< 13.0.0` | `13.0.0` | [37](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/37), [82](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/82) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-rfgq-q3w2-pmv2](https://github.com/advisories/GHSA-rfgq-q3w2-pmv2) / CVE-2026-112898 | Pillow | not scored | `>= 9.1.0, < 13.0.0` | `13.0.0` | [27](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/27), [72](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/72) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-vx6w-vv9f-6gvg](https://github.com/advisories/GHSA-vx6w-vv9f-6gvg) / CVE-2026-112899 | Pillow | not scored | `>= 2.3.0, <= 12.3.0` | `13.0.0` | [17](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/17), [60](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/60) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8) / CVE-2026-112901 | Pillow | not scored | `<= 12.3.0` | `13.0.0` | [28](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/28), [73](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/73) | `docs/requirements-production.txt`; `requirements.txt` |
| [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) / CVE-2026-118764 | minimatch | not scored | `< 11.0.1` | `11.0.1` | [98](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/98) | `package-lock.json` |
| [GHSA-6pq8-jhm2-2vcw](https://github.com/advisories/GHSA-6pq8-jhm2-2vcw) / CVE-2026-110816 | qs | 5.3 | `>= 6.7.0, <= 6.16.0` | `6.16.1` | [97](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/97) | `package-lock.json` |
| [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq) / CVE-2026-41907 | uuid | 7.5 | `< 11.1.1` | `11.1.1` | [3](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/3) | `package-lock.json` |

All 13 unique Pillow medium advisories are fixed by `13.0.0` on this branch. The three npm medium alerts are in the old default-branch lockfile and development-only.

## Low advisory

**1 alert / 1 unique advisory.**

| Advisory | Package | CVSS | Affected version | Patched | Alerts | Manifests |
|---|---|---|---|---|---|---|
| [GHSA-52f5-9888-hmc6](https://github.com/advisories/GHSA-52f5-9888-hmc6) / CVE-2025-54798 | tmp | 2.5 | `<= 0.2.3` | `0.2.4` | [2](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/2) | `package-lock.json` |

`tmp` is a development-only transitive dependency in the old default-branch lockfile. The current branch lockfile no longer contains it.

## Complete alert index (all 92)

Every row is one open Dependabot alert on the default branch. Duplicate rows are separate manifest reports of the same advisory, not separate vulnerabilities.

| Alert | Severity | Package | Installed | Manifest | Advisory | Patched |
|---|---|---|---|---|---|---|
| [48](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/48) | Critical | Brotli | `= 1.2.0` | `docs/requirements-production.txt` | [GHSA-9v8h-qqgm-4m35](https://github.com/advisories/GHSA-9v8h-qqgm-4m35) / CVE-2026-111497 | `1.2.1` |
| [93](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/93) | Critical | Brotli | `= 1.2.0` | `requirements.txt` | [GHSA-9v8h-qqgm-4m35](https://github.com/advisories/GHSA-9v8h-qqgm-4m35) / CVE-2026-111497 | `1.2.1` |
| [96](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/96) | Critical | Brotli | `= 1.2.0` | `tools/requirements.txt` | [GHSA-9v8h-qqgm-4m35](https://github.com/advisories/GHSA-9v8h-qqgm-4m35) / CVE-2026-111497 | `1.2.1` |
| [10](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/10) | Critical | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-8g5g-8vmr-9782](https://github.com/advisories/GHSA-8g5g-8vmr-9782) / CVE-2026-112403 | `13.0.0` |
| [18](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/18) | Critical | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-w889-685w-c8fh](https://github.com/advisories/GHSA-w889-685w-c8fh) / CVE-2026-112900 | `13.0.0` |
| [35](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/35) | Critical | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-332p-7hrc-92wf](https://github.com/advisories/GHSA-332p-7hrc-92wf) / CVE-2026-112393 | `13.0.0` |
| [40](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/40) | Critical | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-v9pv-5gc8-w2m6](https://github.com/advisories/GHSA-v9pv-5gc8-w2m6) / CVE-2026-96639 | `13.0.0` |
| [50](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/50) | Critical | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-5x8w-8jj5-q52h](https://github.com/advisories/GHSA-5x8w-8jj5-q52h) / CVE-2026-112398 | `13.0.0` |
| [54](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/54) | Critical | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-8g5g-8vmr-9782](https://github.com/advisories/GHSA-8g5g-8vmr-9782) / CVE-2026-112403 | `13.0.0` |
| [63](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/63) | Critical | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-w889-685w-c8fh](https://github.com/advisories/GHSA-w889-685w-c8fh) / CVE-2026-112900 | `13.0.0` |
| [80](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/80) | Critical | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-332p-7hrc-92wf](https://github.com/advisories/GHSA-332p-7hrc-92wf) / CVE-2026-112393 | `13.0.0` |
| [85](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/85) | Critical | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-v9pv-5gc8-w2m6](https://github.com/advisories/GHSA-v9pv-5gc8-w2m6) / CVE-2026-96639 | `13.0.0` |
| [95](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/95) | Critical | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-5x8w-8jj5-q52h](https://github.com/advisories/GHSA-5x8w-8jj5-q52h) / CVE-2026-112398 | `13.0.0` |
| [9](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/9) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-58r4-6rv3-gfh8](https://github.com/advisories/GHSA-58r4-6rv3-gfh8) / CVE-2026-112397 | `13.0.0` |
| [11](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/11) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-pchr-8j38-3x4p](https://github.com/advisories/GHSA-pchr-8j38-3x4p) / CVE-2026-112896 | `13.0.0` |
| [12](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/12) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-65qm-jvmh-6pqg](https://github.com/advisories/GHSA-65qm-jvmh-6pqg) / CVE-2026-112400 | `13.0.0` |
| [14](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/14) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-c6hw-5grf-ff96](https://github.com/advisories/GHSA-c6hw-5grf-ff96) / CVE-2026-112404 | `13.0.0` |
| [15](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/15) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-q45j-58j2-45rg](https://github.com/advisories/GHSA-q45j-58j2-45rg) / CVE-2026-112897 | `13.0.0` |
| [16](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/16) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-p4wg-p73j-c528](https://github.com/advisories/GHSA-p4wg-p73j-c528) / CVE-2026-112895 | `13.0.0` |
| [20](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/20) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-7mwm-ghpf-9vrm](https://github.com/advisories/GHSA-7mwm-ghpf-9vrm) / CVE-2026-112402 | `13.0.0` |
| [21](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/21) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-j4m9-6w36-pw47](https://github.com/advisories/GHSA-j4m9-6w36-pw47) / CVE-2026-112893 | `13.0.0` |
| [22](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/22) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-cp9v-662q-vvx9](https://github.com/advisories/GHSA-cp9v-662q-vvx9) / CVE-2026-112405 | `13.0.0` |
| [23](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/23) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-27h8-gf7j-v5hc](https://github.com/advisories/GHSA-27h8-gf7j-v5hc) / CVE-2026-112392 | `13.0.0` |
| [25](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/25) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) / CVE-2026-112390 | `13.0.0` |
| [30](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/30) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-jg86-v3jv-hrpm](https://github.com/advisories/GHSA-jg86-v3jv-hrpm) / CVE-2026-112894 | `13.0.0` |
| [31](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/31) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-gg2r-wvfm-q9rx](https://github.com/advisories/GHSA-gg2r-wvfm-q9rx) / CVE-2026-112892 | `13.0.0` |
| [32](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/32) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-5xm2-6676-qcp9](https://github.com/advisories/GHSA-5xm2-6676-qcp9) / CVE-2026-112399 | `13.0.0` |
| [33](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/33) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-f2g6-542v-9j58](https://github.com/advisories/GHSA-f2g6-542v-9j58) / CVE-2026-112406 | `13.0.0` |
| [36](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/36) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-xvh5-g6gv-559v](https://github.com/advisories/GHSA-xvh5-g6gv-559v) / CVE-2026-112902 | `13.0.0` |
| [38](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/38) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-g842-9rc4-69pw](https://github.com/advisories/GHSA-g842-9rc4-69pw) / CVE-2026-96637 | `13.0.0` |
| [41](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/41) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-mrfp-p49p-3hf2](https://github.com/advisories/GHSA-mrfp-p49p-3hf2) / CVE-2026-96640 | `13.0.0` |
| [43](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/43) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-3j72-p6qg-6xp7](https://github.com/advisories/GHSA-3j72-p6qg-6xp7) / CVE-2026-96642 | `13.0.0` |
| [44](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/44) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-g4qv-2jxx-769h](https://github.com/advisories/GHSA-g4qv-2jxx-769h) / CVE-2026-96643 | `13.0.0` |
| [45](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/45) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-9v9v-9qvf-h2hj](https://github.com/advisories/GHSA-9v9v-9qvf-h2hj) / CVE-2026-96644 | `13.0.0` |
| [46](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/46) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-g7cr-3p24-7wf7](https://github.com/advisories/GHSA-g7cr-3p24-7wf7) / CVE-2026-96778 | `13.0.0` |
| [47](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/47) | High | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-78g4-xqwv-q3g8](https://github.com/advisories/GHSA-78g4-xqwv-q3g8) | `13.0.0` |
| [55](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/55) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-c6hw-5grf-ff96](https://github.com/advisories/GHSA-c6hw-5grf-ff96) / CVE-2026-112404 | `13.0.0` |
| [57](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/57) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-p4wg-p73j-c528](https://github.com/advisories/GHSA-p4wg-p73j-c528) / CVE-2026-112895 | `13.0.0` |
| [58](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/58) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-pchr-8j38-3x4p](https://github.com/advisories/GHSA-pchr-8j38-3x4p) / CVE-2026-112896 | `13.0.0` |
| [59](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/59) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-q45j-58j2-45rg](https://github.com/advisories/GHSA-q45j-58j2-45rg) / CVE-2026-112897 | `13.0.0` |
| [61](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/61) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-65qm-jvmh-6pqg](https://github.com/advisories/GHSA-65qm-jvmh-6pqg) / CVE-2026-112400 | `13.0.0` |
| [62](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/62) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-58r4-6rv3-gfh8](https://github.com/advisories/GHSA-58r4-6rv3-gfh8) / CVE-2026-112397 | `13.0.0` |
| [65](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/65) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-7mwm-ghpf-9vrm](https://github.com/advisories/GHSA-7mwm-ghpf-9vrm) / CVE-2026-112402 | `13.0.0` |
| [66](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/66) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-j4m9-6w36-pw47](https://github.com/advisories/GHSA-j4m9-6w36-pw47) / CVE-2026-112893 | `13.0.0` |
| [67](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/67) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-cp9v-662q-vvx9](https://github.com/advisories/GHSA-cp9v-662q-vvx9) / CVE-2026-112405 | `13.0.0` |
| [68](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/68) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-27h8-gf7j-v5hc](https://github.com/advisories/GHSA-27h8-gf7j-v5hc) / CVE-2026-112392 | `13.0.0` |
| [70](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/70) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) / CVE-2026-112390 | `13.0.0` |
| [75](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/75) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-jg86-v3jv-hrpm](https://github.com/advisories/GHSA-jg86-v3jv-hrpm) / CVE-2026-112894 | `13.0.0` |
| [76](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/76) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-gg2r-wvfm-q9rx](https://github.com/advisories/GHSA-gg2r-wvfm-q9rx) / CVE-2026-112892 | `13.0.0` |
| [77](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/77) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-5xm2-6676-qcp9](https://github.com/advisories/GHSA-5xm2-6676-qcp9) / CVE-2026-112399 | `13.0.0` |
| [78](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/78) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-f2g6-542v-9j58](https://github.com/advisories/GHSA-f2g6-542v-9j58) / CVE-2026-112406 | `13.0.0` |
| [81](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/81) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-xvh5-g6gv-559v](https://github.com/advisories/GHSA-xvh5-g6gv-559v) / CVE-2026-112902 | `13.0.0` |
| [83](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/83) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-g842-9rc4-69pw](https://github.com/advisories/GHSA-g842-9rc4-69pw) / CVE-2026-96637 | `13.0.0` |
| [86](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/86) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-mrfp-p49p-3hf2](https://github.com/advisories/GHSA-mrfp-p49p-3hf2) / CVE-2026-96640 | `13.0.0` |
| [88](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/88) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-3j72-p6qg-6xp7](https://github.com/advisories/GHSA-3j72-p6qg-6xp7) / CVE-2026-96642 | `13.0.0` |
| [89](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/89) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-g4qv-2jxx-769h](https://github.com/advisories/GHSA-g4qv-2jxx-769h) / CVE-2026-96643 | `13.0.0` |
| [90](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/90) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-9v9v-9qvf-h2hj](https://github.com/advisories/GHSA-9v9v-9qvf-h2hj) / CVE-2026-96644 | `13.0.0` |
| [91](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/91) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-g7cr-3p24-7wf7](https://github.com/advisories/GHSA-g7cr-3p24-7wf7) / CVE-2026-96778 | `13.0.0` |
| [92](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/92) | High | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-78g4-xqwv-q3g8](https://github.com/advisories/GHSA-78g4-xqwv-q3g8) | `13.0.0` |
| [5](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/5) | High | extract-zip | `2.0.1` | `package-lock.json` | [GHSA-jmr9-qjv8-65gv](https://github.com/advisories/GHSA-jmr9-qjv8-65gv) / CVE-2026-56876 | `—` |
| [6](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/6) | High | extract-zip | `2.0.1` | `package-lock.json` | [GHSA-7pqw-9j4j-h8q3](https://github.com/advisories/GHSA-7pqw-9j4j-h8q3) / CVE-2026-19693 | `—` |
| [4](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/4) | High | tmp | `0.0.33` | `package-lock.json` | [GHSA-ph9p-34f9-6g65](https://github.com/advisories/GHSA-ph9p-34f9-6g65) / CVE-2026-44705 | `0.2.6` |
| [13](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/13) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) / CVE-2026-112395 | `13.0.0` |
| [17](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/17) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-vx6w-vv9f-6gvg](https://github.com/advisories/GHSA-vx6w-vv9f-6gvg) / CVE-2026-112899 | `13.0.0` |
| [19](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/19) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-4558-3h8r-v8xp](https://github.com/advisories/GHSA-4558-3h8r-v8xp) / CVE-2026-112394 | `13.0.0` |
| [24](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/24) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-fc9g-5qg7-mf45](https://github.com/advisories/GHSA-fc9g-5qg7-mf45) / CVE-2026-112891 | `13.0.0` |
| [26](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/26) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-74r2-7ff9-mjj2](https://github.com/advisories/GHSA-74r2-7ff9-mjj2) / CVE-2026-112401 | `13.0.0` |
| [27](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/27) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-rfgq-q3w2-pmv2](https://github.com/advisories/GHSA-rfgq-q3w2-pmv2) / CVE-2026-112898 | `13.0.0` |
| [28](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/28) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8) / CVE-2026-112901 | `13.0.0` |
| [29](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/29) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-254f-3936-288h](https://github.com/advisories/GHSA-254f-3936-288h) / CVE-2026-112391 | `13.0.0` |
| [34](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/34) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-4rr5-89j8-mwwm](https://github.com/advisories/GHSA-4rr5-89j8-mwwm) / CVE-2026-112396 | `13.0.0` |
| [37](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/37) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-p8hx-v2p6-rp84](https://github.com/advisories/GHSA-p8hx-v2p6-rp84) / CVE-2026-96636 | `13.0.0` |
| [39](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/39) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c) / CVE-2026-96638 | `13.0.0` |
| [42](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/42) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-4rm8-3hmm-39fg](https://github.com/advisories/GHSA-4rm8-3hmm-39fg) / CVE-2026-96641 | `13.0.0` |
| [49](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/49) | Medium | Pillow | `= 12.3.0` | `docs/requirements-production.txt` | [GHSA-654x-cwwv-5j9c](https://github.com/advisories/GHSA-654x-cwwv-5j9c) / CVE-2026-114501 | `13.0.0` |
| [56](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/56) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) / CVE-2026-112395 | `13.0.0` |
| [60](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/60) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-vx6w-vv9f-6gvg](https://github.com/advisories/GHSA-vx6w-vv9f-6gvg) / CVE-2026-112899 | `13.0.0` |
| [64](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/64) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-4558-3h8r-v8xp](https://github.com/advisories/GHSA-4558-3h8r-v8xp) / CVE-2026-112394 | `13.0.0` |
| [69](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/69) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-fc9g-5qg7-mf45](https://github.com/advisories/GHSA-fc9g-5qg7-mf45) / CVE-2026-112891 | `13.0.0` |
| [71](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/71) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-74r2-7ff9-mjj2](https://github.com/advisories/GHSA-74r2-7ff9-mjj2) / CVE-2026-112401 | `13.0.0` |
| [72](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/72) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-rfgq-q3w2-pmv2](https://github.com/advisories/GHSA-rfgq-q3w2-pmv2) / CVE-2026-112898 | `13.0.0` |
| [73](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/73) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8) / CVE-2026-112901 | `13.0.0` |
| [74](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/74) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-254f-3936-288h](https://github.com/advisories/GHSA-254f-3936-288h) / CVE-2026-112391 | `13.0.0` |
| [79](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/79) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-4rr5-89j8-mwwm](https://github.com/advisories/GHSA-4rr5-89j8-mwwm) / CVE-2026-112396 | `13.0.0` |
| [82](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/82) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-p8hx-v2p6-rp84](https://github.com/advisories/GHSA-p8hx-v2p6-rp84) / CVE-2026-96636 | `13.0.0` |
| [84](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/84) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c) / CVE-2026-96638 | `13.0.0` |
| [87](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/87) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-4rm8-3hmm-39fg](https://github.com/advisories/GHSA-4rm8-3hmm-39fg) / CVE-2026-96641 | `13.0.0` |
| [94](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/94) | Medium | Pillow | `= 12.3.0` | `requirements.txt` | [GHSA-654x-cwwv-5j9c](https://github.com/advisories/GHSA-654x-cwwv-5j9c) / CVE-2026-114501 | `13.0.0` |
| [98](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/98) | Medium | minimatch | `3.1.5` | `package-lock.json` | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) / CVE-2026-118764 | `11.0.1` |
| [97](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/97) | Medium | qs | `6.16.0` | `package-lock.json` | [GHSA-6pq8-jhm2-2vcw](https://github.com/advisories/GHSA-6pq8-jhm2-2vcw) / CVE-2026-110816 | `6.16.1` |
| [3](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/3) | Medium | uuid | `8.3.2` | `package-lock.json` | [GHSA-w5hq-g745-h8pq](https://github.com/advisories/GHSA-w5hq-g745-h8pq) / CVE-2026-41907 | `11.1.1` |
| [2](https://github.com/NgethSereyboth/online-invitation-platform/security/dependabot/2) | Low | tmp | `0.0.33` | `package-lock.json` | [GHSA-52f5-9888-hmc6](https://github.com/advisories/GHSA-52f5-9888-hmc6) / CVE-2025-54798 | `0.2.4` |

## Recommended order of work

1. **Upgrade Brotli to `1.2.1`** in `docs/requirements-production.txt` and `tools/requirements.txt`. `requirements.txt` includes the production file, so it does not need a separate pin. Recreate the environment, run the suite, scan with `pip-audit`, and deploy. This is the only unique critical runtime advisory still on the branch.
2. **Land the Pillow `13.0.0` bump on `main`.** It is already committed on this branch as `dac38e0`. After GitHub rescans the default branch, the 82 Pillow alerts should close. If merging the whole branch is not appropriate, cherry-pick that commit.
3. **Regenerate the default-branch npm lockfile.** The current branch lockfile has already removed the seven old chains. Merge or cherry-pick that lockfile update so the default-branch alerts can close; no production JavaScript bundle depends on these packages.
4. **Resolve the current dev-only zod chain.** Run `npm audit` and review the `npm audit fix` diff before accepting it. The issue is in tooling (`puppeteer-core`/`chromium-bidi`/`zod`), not in the deployed site; rerun the browser tests afterward.
5. **Prevent recurrence.** Run `pip-audit -r docs/requirements-production.txt` and `npm audit --package-lock-only` in CI. Keep Dependabot security updates enabled, and group alerts by package so duplicate manifests do not inflate the count.

## Verification commands

```bash
# Python: after changing the pins
python3 -m pip install -r requirements-dev.txt
pip-audit -r docs/requirements-production.txt
python3 -m pytest -q

# Node development tooling
npm audit
npm audit --package-lock-only

# Project gates
python3 build.py all --check
python3 build.py bundles --check
```

Do not deploy until the new pins are installed in the runtime and the build/tests pass. A version change in a requirements file does not update an already-running environment by itself.

## Limitations

- GitHub reports these alerts against the **default branch**. The current branch's manifest state is called out separately; the alert count will not drop until the default branch changes and is rescanned.
- The count is a dependency-graph count, not a count of exploitable attack paths. Severity and CVSS are advisory metadata; runtime exposure depends on which image/Brotli processing paths accept untrusted input.
- A missing CVSS score is shown as **not scored**, not as zero risk.
- The seven npm alerts are development-only in the old lockfile. That does not make them harmless, but they are not in the deployed front end.
- This inventory is a point-in-time snapshot. Re-run the API command and `npm audit` before making release decisions.

## Reproduction

```bash
gh api --paginate -q '.[]' \
  -H 'Accept: application/vnd.github+json' \
  'repos/NgethSereyboth/online-invitation-platform/dependabot/alerts?state=open&per_page=100' \
  > artifacts/security/dependabot-open.ndjson
npm audit --package-lock-only --json > artifacts/security/npm-audit-current.json
```

Advisory links in the tables point to GitHub's public advisory pages; alert links point to the repository's Dependabot alert pages (repository access required).
