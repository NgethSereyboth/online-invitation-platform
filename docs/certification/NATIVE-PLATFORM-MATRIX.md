# Native Platform Matrix — Windows + Linux 3× each

> **Phase 3 deliverable.** Companion file to [`CERTIFICATION.md`](./CERTIFICATION.md) §1. This document defines the clean-install / upgrade / rollback procedure for each of the six target operating systems, and the acceptance gates that must hold on each.
>
> **Existing automated coverage.** Two real-server tests already assert portability across the matrix:
> - `tests/v14_live_server_acceptance_test.py` — full walkthrough against the real HTTP server: register → create invitation → upload asset → publish → submit RSVP → check-in. Used as the **Linux acceptance gate** on all three Linux platforms.
> - `tests/v16_windows_ui_hardening_test.py` — deterministic Windows portability checks: CRLF audit on built route bundles, Windows-only tokens in `windows-ui-v16.css`/`windows-ui-v16.js`, `SIGBREAK` handler in `server.py`, `PYTHONUTF8` + `PYTHONIOENCODING` env in `run_review_checks.py`/`release_check.py`, graceful-shutdown `CTRL_BREAK_EVENT` assertion. Used as the **Windows acceptance gate** on all three Windows platforms.
>
> **Bilingual note.** The install scripts emit bilingual EN+KH status banners where the user-facing terminal supports it (`scripts/setup-einvite-complete.ps1` uses `[Console]::OutputEncoding` to render Khmer via the platform UTF-8 path; `deploy/linux/install-einvite-laptop.sh` uses `printf` with `\xE1\x9E\x80` escapes). Both scripts leave the Khmer banners disabled if the locale is not UTF-8.

---

## 1. Target platforms

| ID | OS family | Distribution / version | Installer | Architecture |
|----|-----------|------------------------|-----------|--------------|
| N1 | Windows | Windows 11 (consumer, 23H2 or later) | `scripts/setup-einvite-complete.ps1` | x86_64 |
| N2 | Windows | Windows Server 2022 | `scripts/setup-einvite-complete.ps1` + `deploy/windows/start-einvite-windows-server.ps1` | x86_64 |
| N3 | Windows | Windows Server 2025 (or current at time of drill) | `scripts/setup-einvite-complete.ps1` | x86_64 |
| N4 | Linux | Ubuntu 22.04 LTS (Jammy) | `deploy/linux/install-einvite-laptop.sh` | x86_64 / arm64 |
| N5 | Linux | Ubuntu 24.04 LTS (Noble) | `deploy/linux/install-einvite-laptop.sh` | x86_64 / arm64 |
| N6 | Linux | Debian 12 (Bookworm) | `deploy/linux/install-einvite-laptop.sh` | x86_64 / arm64 |

> The Windows installer (`scripts/setup-einvite-complete.ps1`) is the unified entry point for all three Windows targets. `deploy/windows/start-einvite-windows-server.ps1` is an additional launcher used on Server SKUs that pre-binds to the server's host allowlist + a non-default port range (see `deploy/windows/Caddyfile` for the HTTPS-terminating configuration).

---

## 2. Acceptance gates (identical across all six platforms)

A platform is certified only when **all six** of the following hold.

| # | Gate | How to verify |
|---|------|---------------|
| G1 | Server boots and prints the startup banner | `E-invitation-website: http://<host>:<port>` in `data/logs/server.log` (Linux) or `data\logs\server.log` (Windows). |
| G2 | Health endpoint returns 200 within 10 s of boot | `curl -fsS http://127.0.0.1:<port>/api/health/live` (Linux) or `Invoke-WebRequest http://127.0.0.1:<port>/api/health/live` (Windows). |
| G3 | All 16 server-rendered HTML pages return 200 + `script-src 'self'` CSP | `python3 tests/v14_live_server_acceptance_test.py` (Linux) — the test asserts CSP on every route in its `routes` list. On Windows, run `python tests\v14_live_server_acceptance_test.py` after starting the server; the same assertions hold. |
| G4 | Deterministic test suite passes | Linux: `python3 tests/v16_windows_ui_hardening_test.py` (CRLF + SIGBREAK + UTF-8 env) + `python3 tests/security_regression_test.py` + `python3 tests/v0_52_security_boundary_test.py`. Windows: same three tests under `python` (the v16 test was authored to assert Windows-specific tokens from a Linux runner too — see `tests/v16_windows_ui_hardening_test.py` lines 35-45). |
| G5 | On-startup fail-closed malware scanner is detected | Linux: `command -v clamdscan` or `command -v clamd` is on PATH; `clamdscan --version` succeeds; `security_scanner_v54.scan_bytes(b"EICAR-...")` returns a `MalwareDetected` verdict. Windows: `MpCmdRun.exe` is on PATH (Microsoft Defender enabled); same EICAR test passes. **On any platform, the server refuses to boot unless either ClamAV or Defender is detected** — set `EINVITE_ALLOW_NO_SCANNER=1` only in an isolated dev sandbox. |
| G6 | Production preflight returns 0 | `python3 src/python/production_preflight.py --env-file .env.production --check-dependencies` (Linux) or `python src\python\production_preflight.py --env-file .env.production --check-dependencies` (Windows). |

---

## 3. Per-platform procedure

### 3.1 Windows 11 (consumer)

**Install:**
```powershell
# Run an elevated PowerShell prompt (Win+X → Terminal (Admin)).
cd C:\Path\To\einvite-platform
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-einvite-complete.ps1
```
The script:
1. Enables `Developer Mode` (for symlink support — `src/js/*` files use the symlink-free flat layout, but `route-bundles-v15.json` is regenerated by `build_route_bundles.py` which respects symlinks if present).
2. Installs Python 3.11+ via winget (or detects an existing install).
3. Creates `.venv\` and installs `requirements-production.txt`.
4. Generates `.env` (V54 security defaults: HTTP-only loopback, `EINVITE_ALLOWED_HOSTS=localhost 127.0.0.1`, `EINVITE_ALLOW_NO_SCANNER=0` — Defender is auto-detected as the malware scanner).
5. Runs `production_preflight.py --check-dependencies`.
6. Starts the server as a background job and opens the browser.

**Upgrade V53.1 → V54:**
1. Stop the running server: `Get-Process python | Where-Object { $_.Path -like '*einvite*' } | Stop-Process`.
2. `git pull origin main` (or unzip the V54 release archive over the existing tree).
3. `.venv\Scripts\python.exe -m pip install -r requirements-production.txt --upgrade`.
4. `.venv\Scripts\python.exe src\python\production_preflight.py --env-file .env.production --check-dependencies`.
5. Start the server again. The schema migration is automatic on boot (see `server.py::ensure_schema` — `PRAGMA table_info` introspection + `ALTER TABLE` for V54.x columns; no manual migration step is required for V53.1 → V54).
6. Verify G1–G6.

**Rollback V54 → V53.1:**
1. Stop the server.
2. `git checkout v53.1` (or unzip the V53.1 release archive).
3. Restore the V53.1 database from the pre-upgrade backup (`backup_restore.py restore backups/pre-v54-<stamp>.zip /tmp/restore --force` — the V54 schema migrations are **additive only** (new columns, new tables); the V53.1 server will simply ignore the extra columns, so a schema rollback is not strictly required. However, **rows written by V54 features** (e.g. `album_photos`, `invitation_edit_history`, `signup_sheets`, `polls`, `delivery_attempts`) will not be visible to V53.1 — they will persist in the DB but V53.1 has no route handlers for them.
4. Start the server. Verify G1–G6.
5. Document the rollback in `docs/certification/rollback-log-<platform>.md` (created on drill day).

---

### 3.2 Windows Server 2022

**Install:**
```powershell
# Server Manager → Local Server → Enable "Internet Information Services" is NOT required —
# eInvite runs its own stdlib http.server on port 8080 by default. Caddy is optional for HTTPS.
cd C:\einvite-platform
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup-einvite-complete.ps1
.\deploy\windows\start-einvite-windows-server.ps1 -Port 8080 -Host 0.0.0.0
```
The `start-einvite-windows-server.ps1` launcher is the Server SKU companion: it binds to the LAN IP (configurable), opens the Windows Defender Firewall rule for the chosen port (`New-NetFirewallRule`), and registers the server as a Scheduled Task that runs at logon with `Highest` privileges.

**Upgrade V53.1 → V54:** Same as §3.1, plus:
1. Stop the Scheduled Task: `Unregister-ScheduledTask -TaskName eInvite-Server -Confirm:$false`.
2. After the upgrade, re-register the Scheduled Task: `.\deploy\windows\start-einvite-windows-server.ps1 -RegisterTask`.

**Rollback V54 → V53.1:** Same as §3.1, plus re-register the Scheduled Task pointing at the V53.1 tree.

---

### 3.3 Windows Server 2025 (or current)

> Windows Server 2025 introduces mandatory SMB signing by default and tightens the default Windows Defender Application Control policy. Neither affects eInvite (the server has no SMB dependency; the Defender configuration is auto-detected by `security_scanner_v54.py`).

**Install / Upgrade / Rollback:** Identical to §3.2. Run the `tests/v16_windows_ui_hardening_test.py` test before declaring the platform certified — it asserts the `SIGBREAK` handler and `CTRL_BREAK_EVENT` graceful-shutdown path that Server 2025 enforces more strictly than Server 2022.

---

### 3.4 Ubuntu 22.04 LTS (Jammy)

**Install:**
```bash
sudo bash deploy/linux/install-einvite-laptop.sh --port 8080 --install-system-packages
```
The script:
1. Installs system packages via `apt-get`: `python3 python3-venv python3-pip python3-dev curl ca-certificates git clamav-daemon clamav-freshclam firewalld`.
2. Enables and starts `clamav-daemon` + `clamav-freshclam` via `systemctl`.
3. Runs `freshclam --no-dns` once to populate the virus database.
4. Creates `.venv/`, installs `requirements-production.txt`.
5. Creates `data/` subdirectories with mode 0750 (`data/logs data/uploads data/backups data/db`).
6. Generates `.env.production` (the laptop SQLite path) AND the repo-root `.env` (V54 security defaults — `EINVITE_COOKIE_SECURE=0`, `EINVITE_ALLOWED_HOSTS=localhost 127.0.0.1`, `EINVITE_ALLOW_NO_SCANNER=0`, auto-generate `EINVITE_SECRET_KEY` + `EINVITE_BILLING_WEBHOOK_SECRET` on first launch).
7. Configures `ufw` (Ubuntu ships with ufw available) to allow port 8080/tcp.
8. Runs `production_preflight.py --check-dependencies`.
9. Starts the server in the background via `nohup` and writes the PID to `data/einvite.pid`.
10. Opens the browser via `xdg-open` (or prints the URL if no display server is available).

**Upgrade V53.1 → V54:**
```bash
# Stop the server.
kill $(cat data/einvite.pid)
# Pull V54.
git pull origin main
# Upgrade dependencies (V54 added: security_scanner_v54.py, secrets_v54.py, production_preflight.py —
# these are stdlib-only, so requirements-production.txt is unchanged for V53.1 → V54).
.venv/bin/python -m pip install -r requirements-production.txt --upgrade
# Run preflight.
.venv/bin/python src/python/production_preflight.py --env-file .env.production --check-dependencies
# Start the server.
nohup .venv/bin/python server.py --env-file .env.production --host 0.0.0.0 --port 8080 > data/logs/server.log 2>&1 &
echo $! > data/einvite.pid
# Run the acceptance gate (Linux).
.venv/bin/python tests/v14_live_server_acceptance_test.py
.venv/bin/python tests/v16_windows_ui_hardening_test.py
.venv/bin/python tests/security_regression_test.py
```

**Rollback V54 → V53.1:**
```bash
kill $(cat data/einvite.pid)
git checkout v53.1
# Restore the pre-upgrade SQLite DB if any V54 features wrote rows you want to clean up
# (additive columns are ignored by V53.1 — no schema downgrade is required):
.venv/bin/python src/python/backup_restore.py restore backups/pre-v54-<stamp>.zip data/db --force
nohup .venv/bin/python server.py --env-file .env.production --host 0.0.0.0 --port 8080 > data/logs/server.log 2>&1 &
echo $! > data/einvite.pid
```

---

### 3.5 Ubuntu 24.04 LTS (Noble)

> Ubuntu 24.04 ships Python 3.12 as the default `python3` (Ubuntu 22.04 ships 3.10). The V53.1 → V54 upgrade path is identical to §3.4. Python 3.12 removed several long-deprecated stdlib modules (`imp`, `distutils`, `asynchat`); none are imported by `server.py` or any of its dependencies — verified by `grep -rE "^import (imp|distutils|asynchat|asyncore)" src/python/`.

**Install / Upgrade / Rollback:** Identical to §3.4. The only 24.04-specific note is that `python3-pip` is no longer installed by default — `install-einvite-laptop.sh` already installs it explicitly via `apt-get install python3-pip`.

---

### 3.6 Debian 12 (Bookworm)

> Debian 12 ships Python 3.11 and uses `apt` (not `apt-get` for interactive use, but `apt-get` for scripts — the installer uses `apt-get`). The `clamav-daemon` unit on Debian is named `clamav-daemon.service` (same as Ubuntu); `clamdscan` is in the `clamav-daemon` package. `firewalld` is available but not installed by default — the installer falls back to `ufw` if `firewalld` is missing.

**Install / Upgrade / Rollback:** Identical to §3.4. The only Debian-specific note is that `apt-get install clamav-daemon` on a fresh Bookworm image requires `apt-get update` first (the installer already does this — see `install-einvite-laptop.sh` line 104).

---

## 4. Existing automated test coverage

These tests are **already in the repository** and are run as part of every Phase 3 acceptance gate.

### 4.1 `tests/v14_live_server_acceptance_test.py`

A 210-line real-HTTP walkthrough against the running server. Asserts:
- The dashboard loads with `script-src 'self'` CSP and no `require-trusted-types-for` directive (line 45-46).
- A user can register, log in, log out, and log in again with a fresh session cookie (lines 47-56).
- An invitation can be created from a built-in template, with bilingual fields (`names: 'Serey & Sophea'` + `namesKm: 'សិរី និង សុភា'` — line 93).
- An asset can be uploaded and listed (line 110).
- The invitation can be published and the public page renders with the bilingual names (line 144).
- The RSVP form submits via `POST /api/public/{slug}/rsvps` and the host sees the row in `/api/invitations/{id}/rsvps` (lines 164-169).
- A password-protected access mode can be enabled (line 181).
- The V16 timeline + Studio Ops dialog render without runtime errors.
- All secondary routes (`/invitations/{id}/materials`, `/responses`, `/analytics`, `/checkin`, `/account.html`, `/templates.html`) return HTTP 200 with the correct CSP and no TrustedHTML console errors.

This test is the **primary Linux acceptance gate** for §1 of the certification. It runs on all three Linux platforms (Ubuntu 22.04, Ubuntu 24.04, Debian 12) because the test only depends on a running HTTP server + Playwright Chromium — both are platform-agnostic.

### 4.2 `tests/v16_windows_ui_hardening_test.py`

A 48-line deterministic test (no Playwright, no network). Asserts:
- The route bundles contain no CRLF line endings (line 15) — Windows portability.
- The SHA-256 of every route bundle matches the manifest (line 16) — build integrity.
- `windows-ui-v16.js` and `windows-ui-v16.css` are bundled before `professional-editor-v17.js`/`.css` on the index page (lines 18-19) — load-order contract.
- The Windows-specific CSS tokens (`transform:none!important`, `scrollbar-width:none`, `safe-area-inset-bottom`, `#modal.final-dialog>.close{z-index:10001}`) are present (line 24).
- The Windows-specific JS tokens (`v16ToolbarMore`, `keepActivePageVisible`, `keepActiveToolVisible`, `#eiTimelineLaunch`, `#v13OperationsBtn`) are present (line 26).
- `canvas-plus.js` reads `window.__EINVITE_PAGE||document.body?.dataset.page||` (line 28) — the editor chrome init contract.
- `dashboard-enhancements.js` does NOT use `card.setAttribute('role','button')` (line 30) — a Windows NVDA screen-reader compatibility regression we previously shipped and reverted.
- `server.py` contains `SIGBREAK` (line 38) — Windows uses `SIGBREAK` instead of `SIGINT` for Ctrl-Break; the server registers both.
- `run_review_checks.py` and `release_check.py` set `PYTHONUTF8='1'` + `PYTHONIOENCODING='utf-8'` (line 40) and call `reconfigure(encoding='utf-8',errors='replace')` (line 41) — Windows console UTF-8 normalization (see `docs/PYTHON_9009_FIX_README.txt`).
- `tests/v15_integration_hardening_test.py` references `CTRL_BREAK_EVENT` + `request_graceful_stop` (line 45) — Windows graceful-shutdown path.

This test is the **primary Windows acceptance gate**. It runs identically on all three Windows platforms (Windows 11, Windows Server 2022, Windows Server 2025) because the assertions are file-content checks, not runtime checks.

---

## 5. Cross-references

- [`CERTIFICATION.md`](./CERTIFICATION.md) §1 — executive summary.
- [`scripts/setup-einvite-complete.ps1`](../../scripts/setup-einvite-complete.ps1) — Windows installer.
- [`deploy/linux/install-einvite-laptop.sh`](../../deploy/linux/install-einvite-laptop.sh) — Linux installer.
- [`deploy/windows/start-einvite-windows-server.ps1`](../../deploy/windows/start-einvite-windows-server.ps1) — Windows Server launcher.
- [`deploy/windows/start-einvite-caddy.ps1`](../../deploy/windows/start-einvite-caddy.ps1) — optional HTTPS terminator for Windows.
- [`tests/v14_live_server_acceptance_test.py`](../../tests/v14_live_server_acceptance_test.py) — Linux runtime acceptance gate.
- [`tests/v16_windows_ui_hardening_test.py`](../../tests/v16_windows_ui_hardening_test.py) — Windows portability acceptance gate.
- [`docs/LINUX_LAPTOP_HOSTING.md`](../LINUX_LAPTOP_HOSTING.md) — laptop hosting guide.
- [`docs/FIRST_TIME_INSTALL_AND_HOSTING.md`](../FIRST_TIME_INSTALL_AND_HOSTING.md) — general setup guide.
- [`docs/PRODUCTION_DEPLOYMENT.md`](../PRODUCTION_DEPLOYMENT.md) — production (PostgreSQL + S3) deployment.
- [`docs/PYTHON_9009_FIX_README.txt`](../PYTHON_9009_FIX_README.txt) — Windows console UTF-8 fix background.
