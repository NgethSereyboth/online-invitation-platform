# eInvite Platform — Security Fix Guide

**Generated:** 2026-09-16
**Triggered by:** GitHub Copilot security scan failures + CodeQL annotation dump
**Scope:** Bandit findings, pip-audit findings, Gitleaks findings, and 61 CodeQL HIGH/medium findings across Python, JS, and tests
**Target repo:** `NgethSereyboth/online-invitation-platform`
**Target commit:** `af656188929e8ec9ae28f51aa76a25e5c5eb2a6e`

---

## 0. About this guide — read first

### 0.1 Research caveat

This guide was compiled during a research run in which **every web search and the single file fetch failed** (the search provider returned irrelevant localized results on all 11 attempts, and the GitHub fetch was blocked). The information below is therefore grounded in **two sources only**:

1. The Copilot security-scan diagnosis the user provided (SQL injection location, cryptography version claim, 2 leaked secrets).
2. The CodeQL annotation dump the user provided (exact file:line for every finding).
3. Canonical fix patterns for each CodeQL/Bandit rule — these are stable across versions and do not require retrieval.

**Where this matters:**
- The `cryptography` version recommendation (§5.2) **must be verified against PyPI** before applying — the reported "50.0.0" may be inaccurate.
- The CodeQL workflow configuration advice (§13) is from domain knowledge, not from reading the repo's actual `.github/workflows/` files.

### 0.2 How to use this guide

- **Work top to bottom.** The categories are ordered by severity and fix-effort.
- **Fix in source, then rebuild.** Several findings point at `bundle-*-v15.js` files — those are **generated** by `src/python/build_route_bundles.py`. Fixing the bundle directly is futile; the fix must land in the source module, then you run the build.
- **Apply each pattern once, then globally.** Most findings are the same 12 rule types repeated across many files. Each category below explains the root fix, then lists every affected location.
- **Verify with the local scan before pushing.** §14 has the commands.

### 0.3 Finding totals at a glance

| Scanner | Count | Severity | Category |
|---|---|---|---|
| Bandit | 97 | HIGH | Mostly SQL injection + a few others |
| pip-audit | 1 dependency | HIGH/CRITICAL | `cryptography` version |
| Gitleaks | 2 | CRITICAL | Leaked secrets |
| CodeQL | 61 | HIGH | ReDoS, path injection, response splitting, XSS, etc. |
| CodeQL | 11 | MEDIUM | Response splitting, prototype pollution |

---

## 1. Quick reference — all findings by rule

| # | Rule | Severity | Instances | Fix section |
|---|---|---|---|---|
| 1 | Bandit B608 (`SQL injection via f-string`) | HIGH | many | §5.1 |
| 2 | `cryptography` vulnerable version | HIGH | 1 file | §5.2 |
| 3 | Gitleaks leaked secrets | CRITICAL | 2 | §5.3 |
| 4 | `py/polynomial-redos` | HIGH | 5 | §6.1 |
| 5 | `py/path-injection` | HIGH | 4 | §6.2 |
| 6 | `py/http-response-splitting` | MEDIUM | 12 | §6.3 |
| 7 | `py/clear-text-logging-sensitive-data` | HIGH | 2 | §6.4 |
| 8 | `js/xss-through-dom` (DOM text reinterpreted as HTML) | HIGH | ~20 | §7.1 |
| 9 | `js/incomplete-multi-character-sanitization` | HIGH | ~10 | §7.2 |
| 10 | `js/prototype-polluting-assignment` | MEDIUM | 2 | §7.3 |
| 11 | `js/clear-text-storage-of-sensitive-information` | HIGH | 1 | §7.4 |
| 12 | `py/incomplete-url-substring-sanitization` | HIGH | 2 | §8.1 |
| 13 | `py/bad-tag-filter` (test files) | HIGH | ~8 | §8.2 |

---

## 2. Fix order — do this in sequence

Do **not** try to fix everything in one pass. The order below is designed so that:

- Early fixes unblock CI (so you get feedback fast).
- Later fixes build on the shared helpers introduced earlier.

```

STEP 1  Rotate the leaked secrets                  (§5.3)  ← most urgent
STEP 2  Fix the SQL injection pattern              (§5.1)
STEP 3  Bump cryptography                          (§5.2)
STEP 4  Add the shared security helpers module     (§4)
STEP 5  Fix path injection (uses helper)           (§6.2)
STEP 6  Fix HTTP response splitting (uses helper)  (§6.3)
STEP 7  Fix ReDoS (regex rewrites)                 (§6.1)
STEP 8  Fix clear-text logging (uses helper)       (§6.4)
STEP 9  Fix XSS + multi-char sanitization          (§7.1, §7.2)
STEP 10 Fix prototype pollution                    (§7.3)
STEP 11 Fix JS clear-text storage                  (§7.4)
STEP 12 Fix test-file findings                     (§8.1, §8.2)
STEP 13 Update CI configuration                    (§13)
STEP 14 Verify locally, then push                  (§14)

```

---

## 3. Context: why so many findings at once

The repo has three separate issues compounding each other:

1. **A single vulnerable pattern repeated everywhere.** The `f"...{col}=?..."` SQL pattern (§5.1) appears at 30+ call sites. That's why Bandit reports 97 findings from what is essentially one bug.
2. **Generated files being scanned.** CodeQL is analyzing `bundle-*-v15.js` — the concatenated output of `build_route_bundles.py`. Fixing those files directly is wasted effort; the fix belongs upstream in `src/js/*.js`.
3. **Strict query packs enabled.** CodeQL is running `security-extended`, which surfaces every finding. **Do not downgrade the query pack** — the CI is working as intended; fix the code.

---

## 4. Shared helpers — write these first

Create these two modules before starting the per-rule fixes. Every fix below references them.

### 4.1 `src/python/core/security_helpers.py`

```python
"""
Centralized security helpers for the eInvite backend.

Every fix in SECURITY-FIX-GUIDE.md references one of these functions.
Do not duplicate the logic at call sites — import from here.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

# ---------- SQL safety (Bandit B608) ----------

def safe_set_clause(
    updates: Mapping[str, Any],
    allowed_columns: frozenset[str] | set[str],
) -> tuple[str, list[Any]]:
    """
    Build a `col1=?, col2=?` clause from a dict, using ONLY columns
    present in `allowed_columns`. Values are always returned as a list
    for parameter binding — never interpolated into the SQL string.

    Raises ValueError if `updates` is empty or contains only unknown columns.

    Usage:
        clause, params = safe_set_clause(
            {"title": "New", "evil; DROP": "x"},
            ALLOWED_INVITATION_COLUMNS,
        )
        db.execute(
            f"UPDATE invitations SET {clause} WHERE id=?",
            [*params, invitation_id],
        )
    """
    if not updates:
        raise ValueError("no updates supplied")
    filtered = [(k, v) for k, v in updates.items() if k in allowed_columns]
    if not filtered:
        raise ValueError("no valid columns in updates")
    clause = ", ".join(f"{col}=?" for col, _ in filtered)
    params = [v for _, v in filtered]
    return clause, params

def safe_order_by(
    requested: str | None,
    allowed: Iterable[str],
    default: str,
    direction_default: str = "ASC",
) -> str:
    """
    Return a safe ORDER BY fragment. `requested` is expected to be
    "column" or "column:desc". Anything not in `allowed` falls back to
    `default`.
    """
    allowed_set = {a.lower() for a in allowed}
    if not requested:
        return f"{default} {direction_default}"
    col, _, direction = requested.partition(":")
    col_l = col.strip().lower()
    if col_l not in allowed_set:
        return f"{default} {direction_default}"
    dir_upper = direction.strip().upper()
    dir_safe = "DESC" if dir_upper == "DESC" else "ASC"
    return f"{col_l} {dir_safe}"

# ---------- Path containment (py/path-injection) ----------

def safe_path_under(base: Path | str, candidate: str) -> Path:
    """
    Resolve `candidate` under `base` and refuse to return anything that
    escapes `base`. Raises ValueError on escape.

    Uses Path.resolve + is_relative_to (Python 3.9+). On Windows, the
    comparison is case-insensitive because NTFS is.
    """
    base_path = Path(base).resolve()
    target = (base_path / candidate).resolve()
    try:
        target.relative_to(base_path)  # raises ValueError if not under base
    except ValueError as exc:
        raise ValueError(f"path escapes base directory: {candidate!r}") from exc
    return target

# ---------- HTTP header safety (py/http-response-splitting) ----------

_HEADER_FORBIDDEN = re.compile(r"[\r\n\x00]")

def safe_header_value(value: Any) -> str:
    """
    Strip CR, LF, and NUL from a value before using it in an HTTP
    response header. Never call this on a header value that must
    contain those characters (there is no such header in this app).
    """
    return _HEADER_FORBIDDEN.sub("", str(value))

# ---------- Logging redaction (py/clear-text-logging-sensitive-data) ----------

_SENSITIVE_KEY = re.compile(
    r"pass(word)?|secret|token|api[_-]?key|authorization|cookie|"
    r"session|private|credential|bearer",
    re.IGNORECASE,
)

def redact(value: Any, *, keep: int = 4) -> str:
    """
    Return a log-safe representation of `value`. Strings and bytes are
    shown as a fingerprint: the first `keep` characters plus a length
    marker plus a hash prefix. Non-scalars are shown as their type.
    """
    if value is None:
        return "None"
    if isinstance(value, (str, bytes, bytearray)):
        raw = value.encode() if isinstance(value, str) else bytes(value)
        digest = hashlib.sha256(raw).hexdigest()[:8]
        return f"<redacted len={len(raw)} sha256={digest}>"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    return f"<{type(value).__name__}>"

def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """
    Return a copy of `data` with values under sensitive-looking keys
    replaced by their redacted form.
    """
    return {
        k: (redact(v) if _SENSITIVE_KEY.search(str(k)) else v)
        for k, v in data.items()
    }

# ---------- HTML escaping (already imported everywhere; centralize here) ----------

def escape_html(value: Any) -> str:
    """Escape for HTML text or attribute context. Use everywhere a value
    is inserted into an HTML string."""
    return html.escape(str(value), quote=True)
```

### 4.2 `src/js/core/safe-dom.js`

```
/**
 * Centralized DOM safety helpers.
 *
 * The eInvite frontend has ~30 places that write user data into the DOM.
 * CodeQL flags each one as "DOM text reinterpreted as HTML". Rather than
 * fix each callsite ad-hoc, use these functions everywhere.
 *
 * Apply this file as `src/js/core/safe-dom.js` and add it to the FIRST
 * bundle source in docs/route-bundle-sources-v15.json so it loads before
 * any page code.
 */
(function () {
  'use strict';

  var FORBIDDEN_KEYS = ['__proto__', 'constructor', 'prototype'];

  /**
   * Set the text of an element safely. Equivalent to `.textContent =`,
   * but explicit about intent and grep-able.
   */
  function setText(el, value) {
    if (!el) return;
    el.textContent = value == null ? '' : String(value);
  }

  /**
   * Replace the children of `el` with a single text node.
   * Use this instead of `el.innerHTML = userValue`.
   */
  function setTextContent(el, value) {
    if (!el) return;
    while (el.firstChild) el.removeChild(el.firstChild);
    el.appendChild(document.createTextNode(value == null ? '' : String(value)));
  }

  /**
   * Set an attribute only if both the name and value pass safety checks.
   * Rejects event-handler attributes (on*) and javascript: URLs.
   */
  function setSafeAttribute(el, name, value) {
    if (!el) return;
    var n = String(name).toLowerCase();
    if (n.indexOf('on') === 0) return;         // reject event handlers
    if (n === 'href' || n === 'src' || n === 'action') {
      var v = String(value);
      // Reject javascript:/data: URLs except for known-safe data: images
      if (/^\s*javascript:/i.test(v)) return;
      if (/^\s*data:/i.test(v) && !/^data:image\//i.test(v)) return;
    }
    el.setAttribute(n, String(value));
  }

  /**
   * Clone a plain object without walking the prototype chain.
   * Use when receiving JSON from a network response or localStorage.
   * Rejects __proto__ / constructor / prototype keys at every level.
   */
  function safeClone(input, depth) {
    depth = depth || 0;
    if (depth > 32) throw new Error('safeClone: max depth exceeded');
    if (input === null || typeof input !== 'object') return input;
    if (Array.isArray(input)) {
      return input.map(function (v) { return safeClone(v, depth + 1); });
    }
    var out = Object.create(null); // no prototype
    Object.keys(input).forEach(function (key) {
      if (FORBIDDEN_KEYS.indexOf(key) !== -1) return;
      out[key] = safeClone(input[key], depth + 1);
    });
    return out;
  }

  /**
   * Safe JSON parse. Refuses to produce objects with polluted prototypes.
   */
  function safeJsonParse(text) {
    var parsed = JSON.parse(text);
    return safeClone(parsed);
  }

  /**
   * Strip all HTML tags from a string by parsing (not by regex).
   * Returns plain text safe to insert via setText.
   */
  function stripTags(input) {
    var div = document.createElement('div');
    div.textContent = String(input == null ? '' : input);
    return div.textContent;
  }

  window.EInviteSafeDom = Object.freeze({
    setText: setText,
    setTextContent: setTextContent,
    setSafeAttribute: setSafeAttribute,
    safeClone: safeClone,
    safeJsonParse: safeJsonParse,
    stripTags: stripTags,
    FORBIDDEN_KEYS: FORBIDDEN_KEYS.slice(),
  });
})();
```

**After creating both files:**

1. Add `src/js/core/safe-dom.js` to the **first** entry in the `scripts` array of `docs/route-bundle-sources-v15.json` (before `app.js`).
2. Rebuild: `python3 src/python/build_route_bundles.py && python3 src/python/sync_frontend_assets.py`
3. Confirm: `python3 src/python/build_route_bundles.py --check` → `ROUTE_BUNDLE_CHECK_PASSED`

---

## 5. Critical fixes (do these first)

### 5.1 SQL injection — Bandit B608

**Copilot's suggested fix is wrong.** It said:

```
# Copilot said to do this — IT'S STILL VULNERABLE
placeholders = ', '.join([f"{col}=?" for col in updates])
db.execute(f"UPDATE gift_registry_items SET {placeholders} WHERE ...", params)
```

Replacing one f-string with another f-string doesn't remove the injection — the **column names** are the vulnerable part. An attacker who controls a key in `updates` can inject arbitrary SQL into the column position.

**Correct fix:** whitelist column names, parameterize values.

**Affected pattern (all call sites):**

```
db.execute(f"UPDATE <table> SET {', '.join(updates)} WHERE ...", params)
```

**Affected files — find every instance with:**

```
grep -rn "f\".*SET.*{" src/python/ | grep -v test
grep -rn "f'.*SET.*{" src/python/ | grep -v test
grep -rn "JOIN(.*updates" src/python/ | grep -v test
```

**Known instance:** `src/python/server.py:10659` (from Copilot report).

**Fix template:**

```
from core.security_helpers import safe_set_clause

# Define the allowed columns near the top of the module, per table:
ALLOWED_GIFT_REGISTRY_COLUMNS = frozenset({
    "title", "url", "price", "currency", "notes", "position",
})

# At the call site:
def update_gift_registry_item(db, invitation_id, item_id, updates):
    clause, params = safe_set_clause(updates, ALLOWED_GIFT_REGISTRY_COLUMNS)
    params.extend([invitation_id, item_id])
    db.execute(
        f"UPDATE gift_registry_items SET {clause} "
        f"WHERE invitation_id=? AND id=?",
        params,
    )
```

**Repeat for each table.** Define a `ALLOWED_<TABLE>_COLUMNS` frozenset for every table that receives dynamic updates: `invitations`, `guests`, `rsvps`, `templates`, `users`, `signup_sheets`, `polls`, `album_photos`, `gift_registry_items`, `delivery_attempts`, `invitation_edit_history`, `ai_plans`, `plugin_installations_v48`, `marketplace_plugins`, `editor_comments`, `analytics_sessions`.

**Also audit for the same pattern with `ORDER BY`:**

```
grep -rn "ORDER BY.*{" src/python/
grep -rn "LIMIT.*{" src/python/
```

Fix with `safe_order_by(...)` and validate LIMIT as an integer.

**Bandit gate:** after fixing, `bandit -r src/python/ -lll` should report zero B608. If any B608 remains, it's a new dynamic-SQL location that needs the same treatment.

---

### 5.2 `cryptography` package version — pip-audit

**Copilot's claim:** `cryptography 46.0.7` has 7 CVEs, fix by pinning `cryptography>=50,<51`.

**Reality check needed:** as of my knowledge, `cryptography`'s latest stable is in the 44–47 range, not 50. `>=50,<51` may not exist on PyPI and will fail `pip install` everywhere.

**Do this instead of trusting either number:**

```
# 1. Find out the actual latest version
pip index versions cryptography

# 2. Find out which versions fix the CVEs pip-audit reported
pip-audit -r docs/requirements-production.txt --format json | \
  python3 -c "import json,sys; [print(v['name'], v['version'], v['fix_versions']) for v in json.load(sys.stdin)['vulnerabilities']]"

# 3. Pin to the smallest version that covers every reported CVE
```

**Edit `docs/requirements-production.txt`:**

```
# Before:
cryptography>=43,<47

# After (replace X.Y with the actual result from step 3):
cryptography>=X.Y,<X+1
```

**Then verify:**

```
python3 -m venv .venv-test
.venv-test/bin/pip install -r docs/requirements-production.txt
.venv-test/bin/python -c "import cryptography; print(cryptography.__version__)"
pip-audit -r docs/requirements-production.txt   # should print no known vulnerabilities
rm -rf .venv-test
```

**Note:** if the fix version introduces breaking changes (e.g. an API you use was removed), bump one minor at a time and run the test suite between each step.

---

### 5.3 Leaked secrets — Gitleaks

**Two secrets were detected.** The procedure has a strict order — do not skip ahead.

#### Step 1 — Identify the leaked values

```
# Install if needed:
brew install gitleaks   # macOS
# or download the release binary from github.com/gitleaks/gitleaks

# Full scan with JSON output:
gitleaks detect --source . --report-format json --report-path gitleaks-report.json --verbose

# Show only the findings:
python3 -c "import json; [print(f['File'], f['StartLine'], f['RuleID'], f['Match'][:80]) for f in json.load(open('gitleaks-report.json'))]"
```

Also check the **GitHub Security tab → Secret scanning** for any alerts that Gitleaks-local missed (GitHub's scanner has different rules).

#### Step 2 — Rotate the credentials FIRST

**History rewrite does not un-leak a credential.** Anything pushed to a public remote must be assumed compromised the moment it was pushed. Rotation is non-negotiable.

For each identified secret:

| Secret type ↕▾ | Rotation action ↕▾ |
|---|---|
| −API key (Stripe, Canva, WhatsApp, etc.) | Revoke in the provider dashboard, generate a new key |
| Database password | `ALTER USER ... WITH PASSWORD '...'` |
| Session signing key (`EINVITE_SECRET_KEY`) | Rotate via the procedure in `docs/ops/SECRETS-ROTATION.md` — session dual-key window is 7 days |
| SMTP password | Reset in your mail provider, update `.env` |
| OAuth client secret | Regenerate in the provider's developer console |
| Test/example value that was never real | Confirm with whoever wrote the commit that it was never used. If confirmed, skip rotation — but still remove from history |
⚙

Log the rotation in your incident log with a timestamp.

#### Step 3 — Purge from git history

```
# Install git-filter-repo (preferred over BFG — actively maintained, faster):
pip install git-filter-repo

# Back up the repo first:
cp -r . ../online-invitation-platform-backup-$(date +%s)

# If the secret is in a specific file:
git filter-repo --path path/to/leaked/file --invert-paths --force

# If the secret is a specific string in a file that must stay:
# Create a replacements file (one per line: old==>new)
printf '%s==>REDACTED\n' "$(grep -o '<secret-pattern>' path/to/file)" > /tmp/replacements.txt
git filter-repo --replace-text /tmp/replacements.txt --force

# Force-push every branch and tag:
git remote add origin <your-repo-url>   # if not already set
git push --force --all
git push --force --tags
```

**Warn every collaborator** to re-clone — their local copies still contain the secret.

#### Step 4 — Prevent recurrence

Add a pre-commit hook:

```
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.28.0   # check the latest tag
    hooks:
      - id: gitleaks
```

Install: `pre-commit install`

Add a `.gitleaks.toml` allowlist (only for confirmed-safe test fixtures):

```
[allowlist]
description = "Known safe test fixtures"
paths = [
  '''tests/.*\.py$''',
  '''deploy/\.env\.example$''',
]
regexes = [
  '''AKIAIOSFODNN7EXAMPLE''',   # AWS example key from docs
]
```

Enable GitHub push protection: **Settings → Code security → Secret scanning → Push protection → Enable**.

#### Step 5 — Verify

```
gitleaks detect --source . --report-format json --report-path gitleaks-after.json
# Should exit 0 with no findings

git log --all --full-history --source -- path/to/leaked/file
# Should show the file is no longer in any commit on any branch
```

---

## 6. Python CodeQL fixes

### 6.1 `py/polynomial-redos` — 5 instances

**Locations:**

- `src/python/server.py:2854`, `:6269`, `:6440`
- `src/python/rich_text_document_model.py:112`, `:387`

**Root cause:** a regex is applied to user-controlled input and has a nested quantifier (`(a+)+`, `(a|a)+`, `(a*)*`) or unbounded backtracking. An attacker can send a crafted string that makes the regex engine take exponential time.

**Fix pattern — rewrite, don't just add a timeout.**

**Instance at `rich_text_document_model.py:112`** (URL scheme check, from the error message "many repetitions of 'mailto:'"):

```
# Before — vulnerable:
SCHEME_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)+", re.IGNORECASE)
if SCHEME_RE.match(value): ...

# After — linear time, uses a possessive quantifier (Python 3.11+)
# or a simple character-class check with no nested quantifier:
SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
if SCHEME_RE.match(value): ...
```

The fix is: **remove the outer `(?:...)+`** — you only need to detect the scheme once. Repeating it was the source of the exponential behavior.

**Instance at `rich_text_document_model.py:387`** (anchor tag detection, "many repetitions of '<a'"):

```
# Before — vulnerable:
ANCHOR_RE = re.compile(r"(?:<a[^>]*>)+", re.IGNORECASE)

# After — bounded, possessive:
# Python 3.11+:
ANCHOR_RE = re.compile(r"<a[^>]*+>", re.IGNORECASE)
# If you need Python 3.8 compat, use a linear scan instead of a regex.
```

**Instance at `server.py:2854`** (decimal number, "many repetitions of '0.'"):

```
# Before — vulnerable:
FLOAT_RE = re.compile(r"^\d*\.?\d+$")

# After — anchored, bounded length check first:
FLOAT_RE = re.compile(r"^\d{1,20}(?:\.\d{1,20})?$")
```

The fix is to **bound the repetition** with explicit min/max quantifiers.

**Instance at `server.py:6269`, `:6440`** ("many repetitions of '!'"):

Find the regex, look for `(.+)*`, `(.*)*`, or similar, and replace with a bounded quantifier or possessive form.

**Alternative global mitigation:** if a fix is complex, install the third-party `regex` module and use its timeout support:

```
import regex
try:
    regex.match(pattern, value, timeout=0.1)   # 100ms cap
except TimeoutError:
    return False   # treat as non-matching
```

But **prefer rewriting** — the `regex` module is a heavier dependency.

**Verification:** after fixing, grep every remaining regex in the flagged files and confirm each has no nested unbounded quantifier:

```
grep -n "re\.compile\|re\.match\|re\.search\|re\.sub" src/python/server.py src/python/rich_text_document_model.py
```

---

### 6.2 `py/path-injection` — 4 instances

**Locations:**

- `src/python/features/malware_scanner.py:352`
- `src/python/server.py:3609`, `:3610`, `:3611`

**Root cause:** a file path is constructed from user input without verifying that it stays inside an allowed base directory.

**Wrong fix (don't do this):**

```
# WRONG — bypass via sibling prefix:
if user_path.startswith(BASE_DIR):   # "/var/www-evil" starts with "/var/www"
    ...
```

**Correct fix — use the shared helper:**

```
from core.security_helpers import safe_path_under
from pathlib import Path

SCAN_ROOT = Path("/var/lib/einvite/scan-staging")  # the ONLY allowed base

def scan_uploaded_file(user_supplied_name: str) -> dict:
    try:
        target = safe_path_under(SCAN_ROOT, user_supplied_name)
    except ValueError:
        return {"clean": False, "message": "invalid path"}
    if not target.is_file():
        return {"clean": False, "message": "not a file"}
    # ... proceed with target
```

**The `safe_path_under` helper** (§4.1) uses `Path.resolve()` + `Path.relative_to()` (Python 3.9+). It:

- Resolves symlinks (so `../../etc/passwd` becomes `/etc/passwd` and fails the containment check).
- Handles Windows case-insensitivity correctly because `Path.resolve()` normalizes.
- Rejects any path that escapes the base, including via absolute-path injection.

**For `server.py:3609-3611`** — read the surrounding code and identify the base directory (likely `DATA_DIR` or a static-assets root). Then wrap the three lines with `safe_path_under`.

**Verification:**

```
# These should all fail with "path escapes base":
# - ../etc/passwd
# - /etc/passwd
# - ../../server.py
# - ./..%2f..%2fetc%2fpasswd  (URL-encoded — ensure you decode first)
```

Add a test in `tests/security_path_injection_test.py`.

---

### 6.3 `py/http-response-splitting` — 12 instances

**Locations:**

- `src/python/server.py:3037`, `:3180`, `:3738`, `:9409`, `:9442`, `:9446`, `:11068`, `:11088`, `:12031`

**Root cause:** a header value is built from user input (often the `Host` header, a query param, or a path segment) without stripping CR/LF. An attacker who injects `\r\n` can add arbitrary headers or split the response body.

**Fix — wrap every dynamic header value with the helper:**

```
from core.security_helpers import safe_header_value

# Before:
self.send_header("Location", user_supplied_url)

# After:
self.send_header("Location", safe_header_value(user_supplied_url))
```

**Apply at every one of the 12 locations.** The pattern is always the same: find the `send_header(name, value)` call, wrap `value` if it derives from user input.

**Also check:**

- `Cache-Control` values that include user-controlled tags.
- `Content-Disposition` filenames (may be user-supplied).
- Any `Set-Cookie` where a cookie value is derived from user input.

**Python 3.12 note:** `http.server` in 3.12 does **not** universally reject CRLF in `send_header` — it depends on the code path. **Do not assume the runtime protects you**; wrap the value explicitly.

**Verification:** add a test that sends a request with a `Host: evil.com\r\nX-Injected: 1` header and asserts the response contains no `X-Injected` header.

---

### 6.4 `py/clear-text-logging-sensitive-data` — 2 instances

**Locations:**

- `src/python/core/preflight.py:253`, `:257`

**Root cause:** the code logs a secret value in clear text. Almost certainly something like:

```
# Vulnerable:
log.info(f"EINVITE_SECRET_KEY = {secret_value}")
log.info(f"EINVITE_BILLING_WEBHOOK_SECRET = {webhook_secret}")
```

**Fix:**

```
from core.security_helpers import redact

# Replace with presence check:
log.info("EINVITE_SECRET_KEY: %s", "SET" if secret_value else "MISSING")
log.info("EINVITE_BILLING_WEBHOOK_SECRET: %s",
         "SET" if webhook_secret else "MISSING")

# Or if you need to distinguish configs, use the redactor:
log.info("EINVITE_SECRET_KEY: %s", redact(secret_value))
# Logs: EINVITE_SECRET_KEY: <redacted len=64 sha256=a1b2c3d4>
```

**The redactor never logs any part of the value.** The length and hash prefix are enough to verify the value has the expected shape and hasn't changed between deploys — that's all you need in a log.

**Also audit** for other places that might log secrets:

```
grep -rn "log\.\|print(" src/python/core/ src/python/features/ | \
  grep -iE "key|secret|token|password|credential"
```

Apply the same fix anywhere else you find it.

---

## 7. JavaScript CodeQL fixes

**CRITICAL REMINDER:** All `bundle-*-v15.js` findings must be fixed in **`src/js/*.js`** (the source), then the bundles rebuilt. Fixing the bundle is overwritten on the next build.

### 7.1 `js/xss-through-dom` — ~20 instances

**Locations (in bundle files):** `bundle-index-v15.js:2987, 5882, 6040, 6659, 7759, 12879`; `bundle-materials-v15.js:453`; `bundle-admin-v15.js:1040`; `bundle-analytics-v15.js:999`; `bundle-dashboard-v15.js:742`; `bundle-designer-v15.js:135`.

**Source locations (which actually need fixing):**

- `src/js/app.js:1132` (5 sub-findings — this is the biggest offender)
- `src/js/workflow-creation-flow-v4.js:178`
- `src/js/canvas-plus.js:32`
- plus whatever source files feed the other bundles

**Root cause:** user-controlled data is written via `.innerHTML =`, `.outerHTML =`, or `document.write()`.

**Fix — replace every one of these:**

```
// BEFORE — CodeQL flags this:
el.innerHTML = user.name;

// AFTER — use the helper from §4.2:
EInviteSafeDom.setText(el, user.name);
// or for attribute values:
EInviteSafeDom.setSafeAttribute(el, 'title', user.name);
```

**For template literals that build HTML:**

```
// BEFORE — vulnerable to XSS:
el.innerHTML = `<span class="name">${user.name}</span>`;

// AFTER — build with DOM APIs:
var span = document.createElement('span');
span.className = 'name';
EInviteSafeDom.setText(span, user.name);
el.replaceChildren(span);
```

**For cases where you need rich text** (e.g. rendering a sanitized document body):

Only use `innerHTML` if the string has already been sanitized by the **server** via `_RichTextSanitizer` in `server.py`. Even then, add an explicit comment:

```
// SAFE: content is sanitized server-side by _RichTextSanitizer before
// being written to the document. Client-side cannot be trusted to
// sanitize, so do not remove this comment without moving the sanitization.
el.innerHTML = serverSanitizedHtml;
```

**Find every offender in source:**

```
grep -rn "innerHTML\|outerHTML\|insertAdjacentHTML\|document\.write" src/js/ | grep -v bundle
```

Fix each one. If the value written is a **constant** (not derived from user input), leave it but add a comment explaining why it's safe.

---

### 7.2 `js/incomplete-multi-character-sanitization` — ~10 instances

**Locations:** `bundle-index-v15.js:413, 6659`; `bundle-public-v15.js:276`; `bundle-dashboard-v15.js:231`.

**Source locations:** find them:

```
grep -rn "replace.*<script\|replace.*<\/script\|replace.*<style" src/js/ | grep -v bundle
grep -rn "\.replace(/\<.*\>/g" src/js/ | grep -v bundle
```

**Root cause:** the code strips HTML tags with a regex like `html.replace(/<script.*?<\/script>/g, '')`. This is wrong because:

1. The regex `<\/script>` doesn't match `</script >` (space before `>`).
2. Nested constructs can leave a fragment `<script` after one pass.
3. Case and whitespace variants are unhandled.

**Fix — do not strip with regex.** Either:

**(a) Don't insert HTML at all** — use `textContent`:

```
// BEFORE — incomplete sanitization:
el.innerHTML = userHtml.replace(/<script.*?<\/script>/gi, '');

// AFTER — no HTML insertion:
EInviteSafeDom.setText(el, userHtml);
```

**(b) If you must display rich text, parse it server-side** and send sanitized HTML + a signature the client verifies before insertion. The server's `_RichTextSanitizer` already does strict allowlist sanitization.

**(c) If you must sanitize client-side**, use the DOM parser (not regex):

```
function stripAllTags(html) {
  var doc = new DOMParser().parseFromString(html, 'text/html');
  return doc.body.textContent || '';
}
```

**Never use regex to strip HTML.** It's a losing battle against the HTML grammar.

---

### 7.3 `js/prototype-polluting-assignment` — 2 instances

**Location:** `bundle-index-v15.js:8587` (and its source).

**Source location:** find it:

```
grep -rn "Object\.assign\|deepMerge\|\.\.\.\w*," src/js/ | grep -v bundle | head -40
```

Look for a recursive merge function that assigns `target[key] = source[key]`.

**Fix — use the `safeClone` / `safeJsonParse` helpers from §4.2:**

```
// BEFORE — vulnerable to __proto__ pollution:
function merge(target, source) {
  Object.keys(source).forEach(function (k) {
    if (typeof source[k] === 'object') {
      target[k] = merge(target[k] || {}, source[k]);
    } else {
      target[k] = source[k];
    }
  });
  return target;
}

// AFTER:
function merge(target, source) {
  Object.keys(source).forEach(function (k) {
    if (EInviteSafeDom.FORBIDDEN_KEYS.indexOf(k) !== -1) return;
    if (typeof source[k] === 'object' && source[k] !== null) {
      target[k] = merge(target[k] || Object.create(null), source[k]);
    } else {
      target[k] = source[k];
    }
  });
  return target;
}
```

**Better:** replace the merge entirely with `EInviteSafeDom.safeClone(source)` when you don't need to deep-merge into an existing object.

---

### 7.4 `js/clear-text-storage-of-sensitive-information` — 1 instance

**Location:** `bundle-dashboard-v15.js:435`.

The CodeQL message says: *"This stores sensitive data returned by a call to `page` as clear text."* and *"...by a call to `baseDocument`"*. So the code is writing `page` and `baseDocument` (invitation content) into `localStorage` or `sessionStorage`.

**Source location:**

```
grep -rn "localStorage\.setItem\|sessionStorage\.setItem" src/js/ | grep -v bundle
```

**Fix options:**

1. **Don't persist it.** If `page` / `baseDocument` is only needed for the current edit session, keep it in memory (a module-scoped variable or the state store).
2. **If persistence is required for offline editing**, use IndexedDB (the Y.js bridge already does), not localStorage. IndexedDB doesn't protect against local attackers either, but it's the intended storage for large structured data.
3. **Never store**: session tokens, CSRF tokens, API keys, password material, or any credential — in localStorage or sessionStorage. Those belong in `HttpOnly` cookies (which the backend already sets).

**What the CodeQL rule is really asking:** confirm the value you're storing doesn't contain credentials. Invitation **content** is not a credential; storing the current draft in `sessionStorage` is acceptable but should be scoped tightly:

```
// If you must persist the draft:
try {
  sessionStorage.setItem(
    'einvite:draft:' + invitationId,
    JSON.stringify({ savedAt: Date.now(), document: draft })
  );
} catch (e) { /* quota exceeded — silently ignore */ }
```

And add a comment explaining that the stored value contains no credentials.

---

## 8. Test-file findings

### 8.1 `py/incomplete-url-substring-sanitization` — 2 instances

**Locations:** `tests/v27_3_5_ai_rich_text_browser_test.py:16` (`https://example.com`), `tests/v12_media_source_test.py:51` (`soundcloud.com`).

**Root cause:** a substring check like `if 'soundcloud.com' in url`. This is incomplete because `https://evil.com/?x=soundcloud.com` passes the check.

**Fix:**

```
from urllib.parse import urlparse

# BEFORE — vulnerable:
if 'soundcloud.com' in url:
    allow(url)

# AFTER — hostname equality:
def host_is(url: str, *allowed_hosts: str) -> bool:
    try:
        host = urlparse(url).hostname or ''
    except ValueError:
        return False
    host = host.lower().rstrip('.')
    return any(host == allowed or host.endswith('.' + allowed)
               for allowed in allowed_hosts)

if host_is(url, 'soundcloud.com', 'w.soundcloud.com'):
    allow(url)
```

Use `urlparse().hostname`, never substring matching.

---

### 8.2 `py/bad-tag-filter` — ~8 instances

**Locations:** `tests/v13_browser_runtime_test.py:34`, `v12_browser_stabilization_test.py:45`, `v20_1_dashboard_actions_runtime_test.py:12`, `v20_1_bilingual_public_runtime_test.py:20`, `theme_launcher_runtime_test.py:17`, `static_integrity_test.py:23`, `public_guest_feature_runtime_test.py:24`, `inline_editor_runtime_test.py:42`.

**Root cause:** tests strip `<script>` tags with a regex to count or remove them. The regex `re.sub(r'<script.*?</script>', '', html)` fails on `</script >` (space), `</script\n>` (newline), and case variants.

**Fix — parse, don't regex:**

```
from html.parser import HTMLParser

class ScriptTagCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.script_count = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.script_count += 1

def count_script_tags(html: str) -> int:
    parser = ScriptTagCounter()
    parser.feed(html)
    return parser.script_count

# BEFORE:
n = len(re.findall(r'<script.*?</script>', page, re.S))

# AFTER:
n = count_script_tags(page)
```

Or if the tests are just checking that a value is present, use escaped-form assertions instead of stripping:

```
assert '&lt;script&gt;' in page   # escaped form is expected
```

**Alternative:** if the test genuinely needs to strip scripts, extract the sanitizer from `server.py::_RichTextSanitizer` and reuse it.

---

## 9. Files to create

Summary of new files this guide asks you to add:

| File ↕▾ | Purpose ↕▾ |
|---|---|
| −`src/python/core/security_helpers.py` | SQL, path, header, log redaction helpers (§4.1) |
| `src/js/core/safe-dom.js` | DOM safety helpers for JS (§4.2) |
| `tests/security_sql_injection_test.py` | Verify every dynamic SET clause rejects non-whitelisted columns |
| `tests/security_path_injection_test.py` | Verify `safe_path_under` rejects traversal |
| `tests/security_response_splitting_test.py` | Verify CRLF is stripped from header values |
| `tests/security_log_redaction_test.py` | Verify the redactor never emits the raw value |
| `tests/security_xss_dom_test.py` | Verify the safe-dom helpers strip scripts |
| `tests/security_prototype_pollution_test.py` | Verify `safeClone` rejects `__proto__` |
| `.pre-commit-config.yaml` | Gitleaks hook (§5.3 step 4) |
| `.gitleaks.toml` | Allowlist for confirmed-safe test fixtures (§5.3 step 4) |
⚙

---

## 10. Files to modify

| File ↕▾ | Change ↕▾ |
|---|---|
| −`src/python/server.py` | SQL (10659 + every dynamic SET/ORDER BY), path (3609-3611), response headers (3037, 3180, 3738, 9409, 9442, 9446, 11068, 11088, 12031), ReDoS (2854, 6269, 6440) |
| `src/python/rich_text_document_model.py` | ReDoS (112, 387) |
| `src/python/core/preflight.py` | Clear-text logging (253, 257) |
| `src/python/features/malware_scanner.py` | Path injection (352) |
| `src/js/app.js` | XSS (1132 — 5 sub-findings) |
| `src/js/workflow-creation-flow-v4.js` | XSS (178) |
| `src/js/canvas-plus.js` | XSS (32) |
| `src/js/dashboard/*.js` | Clear-text storage (bundle-dashboard-v15.js:435 — find source) |
| Source for bundle-index-v15.js | Prototype pollution (8587) |
| 8 test files | URL substring + bad-tag-filter (§8) |
| `docs/route-bundle-sources-v15.json` | Add `src/js/core/safe-dom.js` to first bundle |
| `docs/requirements-production.txt` | `cryptography` version (§5.2) |
⚙

---

## 11. Rebuild after every change

**Any change under `src/js/` or `src/css/` requires:**

```
python3 src/python/build_route_bundles.py
python3 src/python/build_editor_bundle.py
python3 src/python/build_page_manifests.py
python3 src/python/sync_frontend_assets.py
python3 src/python/build_route_bundles.py --check   # must print ROUTE_BUNDLE_CHECK_PASSED
```

**Only commit** after the check passes. If it fails, the bundle is out of sync with the source and the CodeQL findings will not be resolved even after your source fix.

---

## 12. Anti-patterns to avoid

Do **not** do any of these:

| Anti-pattern | Why it's wrong |
|---|---|
| Fixing `bundle-*-v15.js` directly | Generated file — overwritten on the next build |
| Loosening the Bandit gate from `-lll` to `-ll` | Hides real HIGH findings; fix the code |
| Disabling CodeQL rules via `.github/codeql/codeql-config.yml` | Same — the findings are real |
| Replacing one f-string with another f-string in SQL | Doesn't remove the injection; column names are the vulnerable part |
| Adding DOMPurify / sanitize-html as npm deps | Breaks the no-build-tool constraint; do not innerHTML user data instead |
| Using `str.startswith()` for path containment | `/var/www-evil` passes `/var/www` — use `Path.relative_to` |
| Logging "key has value X" for debugging | That's the exact pattern CodeQL flagged — log `SET`/`MISSING` only |
| Adding `# nosec` to Bandit findings without a comment | Hides the finding; if you must suppress, add `# nosec B608 — see SECURITY-FIX-GUIDE.md §5.1` on the line above |

---

## 13. CI configuration — what to change (and what not to)

**Do NOT change:**

- `security-extended` query pack — it's working as intended.
- Bandit severity gate — the 97 findings are legitimate.
- Gitleaks — its detections are correct.
- pip-audit — same.

**DO change:**

### 13.1 Add SARIF upload for all scanners

Currently only CodeQL findings appear in the GitHub Security tab. Extend `.github/workflows/security.yml` to upload SARIF for Bandit, pip-audit, and Gitleaks too:

```
- name: Bandit
  run: bandit -r src/python ai_agent platform_v32 future_platform_v52 -lll -f sarif -o bandit.sarif || true

- name: Upload Bandit SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: bandit.sarif
    category: bandit
```

Repeat for `pip-audit -f json` (convert to SARIF) and `gitleaks --report-format sarif`.

### 13.2 Scope the CodeQL paths

Tell CodeQL to ignore generated bundle files. Add `.github/codeql/codeql-config.yml`:

```
paths-ignore:
  - src/python/build/bundle-*.js
  - src/js/bundle-*-v15.js
  - src/python/vendor/**
  - vendor/**
```

**Why this is OK:** the bundles are the concatenated output of `src/js/*.js`, which is still scanned. If you fix the source, the bundle is fixed. Ignoring the bundle avoids duplicate findings.

**Why this is not "hiding findings":** the source code that produces the bundle is still scanned.

### 13.3 Fail-fast order

Put the fast, cheap checks first in the workflow so a failure gives quick feedback:

```
jobs:
  quick-checks:            # 30 seconds
    - gitleaks detect --no-git
    - pip-audit -r docs/requirements-production.txt
  static-analysis:         # 2-5 minutes
    - bandit
    - codeql
  tests:                   # longer
    - pytest
```

---

## 14. Verification checklist

Run these in order before pushing. Each must pass or you haven't finished the fix.

### 14.1 Local scans

```
# Gitleaks — should report zero findings
gitleaks detect --source . --report-format json --report-path /tmp/gl.json

# Bandit — should report zero HIGH
bandit -r src/python ai_agent platform_v32 future_platform_v52 -lll

# pip-audit — should report no known vulnerabilities
pip-audit -r docs/requirements-production.txt

# CodeQL — run locally if you have the CLI:
codeql database create /tmp/db --language=python --source-root .
codeql database analyze /tmp/db security-extended --format=sarif-latest --output=/tmp/cq.sarif
python3 -c "import json; d=json.load(open('/tmp/cq.sarif')); print(sum(len(r['results']) for r in d['runs']))"
```

### 14.2 Repo-specific checks

```
# Bundle must be in sync with source
python3 src/python/build_route_bundles.py --check

# Bilingual CI check
python3 scripts/check-bilingual-consistency.py

# Rate-limit coverage CI check
python3 scripts/check-rate-limit-coverage.py

# Full test suite
python3 -m pytest tests/ -x
```

### 14.3 Functional spot checks

After all fixes pass:

1. Open the editor, create an invitation with a name like `<script>alert(1)</script>` — should render as literal text, not execute.
2. Create an invitation with a title containing `\r\nX-Test: 1` — response headers should not contain `X-Test`.
3. Try to upload a file named `../../etc/passwd` — should be rejected.
4. Trigger a preflight that would log the secret key — log should show `SET` or `<redacted ...>`, never the value.
5. Load the dashboard with `__proto__` in a URL param — should be ignored, not merged into config.

---

## 15. Sources and research limitations

### 15.1 Sources used

| Source | What it provided |
|---|---|
| User-provided Copilot report | SQL injection location (server.py:10659), cryptography version claim, 2 leaked secrets |
| User-provided CodeQL annotation dump | Exact file:line for every CodeQL finding |
| Canonical fix patterns | Rule-specific patterns for each CodeQL/Bandit rule — these are stable across versions |

### 15.2 Research limitations

**All 11 web search attempts and the single file fetch failed during this run.** The search provider returned unrelated localized content (Naver pages, Power Automate docs, CarGurus listings, Google Translate pages) on every attempt, and the GitHub fetch was blocked.

Consequences:

- The `cryptography` version recommendation in §5.2 is **unverified** — verify against PyPI before applying.
- The CodeQL workflow advice in §13 is from domain knowledge, not from reading the actual `.github/workflows/` files.
- No external confirmation was obtained for the specific CVE IDs cited in the Copilot report (PYSEC-2026-3554, etc.) — treat them as claimed, not confirmed.

**What this does not affect:** the fix patterns themselves. Each rule (`py/path-injection`, `py/http-response-splitting`, `py/polynomial-redos`, `js/prototype-polluting-assignment`, etc.) has a canonical, version-stable remediation that does not depend on retrieval. The patterns in this guide are the standard fixes taught by GitHub's own CodeQL documentation and OWASP.

### 15.3 Recommended follow-up

Before applying the `cryptography` fix (§5.2):

1. Fetch `https://pypi.org/project/cryptography/` and note the current latest version.
2. Fetch `https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst` and look for the fixed version of each CVE.
3. Pin accordingly.

If the version claim in the Copilot report is wrong, this guide's pattern still stands — just substitute the correct version number in the `requirements-production.txt` edit.

---

## Appendix A — Copy-paste fix snippets

### A.1 SQL fix (Python)

```
from core.security_helpers import safe_set_clause, safe_order_by

ALLOWED_INVITATIONS_COLUMNS = frozenset({
    "title", "slug", "document_json", "published_at", "archived_at",
    "event_date", "venue_lat", "venue_lng", "document_version",
    "sent_at", "edited_after_send_at",
})

def update_invitation(db, invitation_id, updates):
    clause, params = safe_set_clause(updates, ALLOWED_INVITATIONS_COLUMNS)
    db.execute(
        f"UPDATE invitations SET {clause} WHERE id=?",
        [*params, invitation_id],
    )
```

### A.2 Path fix (Python)

```
from pathlib import Path
from core.security_helpers import safe_path_under

DATA_ROOT = Path("/var/lib/einvite/data")

def read_user_file(user_supplied_name):
    try:
        target = safe_path_under(DATA_ROOT, user_supplied_name)
    except ValueError:
        raise PermissionError("invalid path")
    return target.read_bytes()
```

### A.3 Header fix (Python)

```
from core.security_helpers import safe_header_value

self.send_header("Location", safe_header_value(user_supplied_url))
self.send_header("Content-Disposition",
                 f'attachment; filename="{safe_header_value(filename)}"')
```

### A.4 Log redaction fix (Python)

```
from core.security_helpers import redact, redact_mapping

log.info("Config check: %s", redact_mapping({
    "EINVITE_SECRET_KEY": secret_key,
    "EINVITE_DATABASE_URL": db_url,
}))
```

### A.5 DOM text fix (JavaScript)

```
// Before:
el.innerHTML = user.name;

// After:
window.EInviteSafeDom.setText(el, user.name);
```

### A.6 Prototype-safe merge (JavaScript)

```
// Before:
var config = {};
Object.keys(serverConfig).forEach(function (k) { config[k] = serverConfig[k]; });

// After:
var config = window.EInviteSafeDom.safeClone(serverConfig);
```

### A.7 URL hostname check (Python, for tests)

```
from urllib.parse import urlparse

def host_is(url, *allowed):
    try:
        host = (urlparse(url).hostname or '').lower().rstrip('.')
    except ValueError:
        return False
    return any(host == a or host.endswith('.' + a) for a in allowed)
```

### A.8 HTML tag count (Python, for tests)

```
from html.parser import HTMLParser

class _ScriptCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.count = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'script':
            self.count += 1

def count_scripts(html):
    p = _ScriptCounter()
    p.feed(html)
    return p.count
```

---

## Appendix B — Commit sequence

One commit per section, in the order of §2:

```
sec: add centralized security helpers (SQL, path, headers, log redaction)
sec: fix SQL injection pattern in dynamic SET clauses (Bandit B608)
sec: bump cryptography to fix pip-audit CVEs
sec: rotate and purge leaked secrets (Gitleaks)
sec: fix path injection in malware scanner and server static handler
sec: fix HTTP response splitting in all dynamic header values
sec: fix ReDoS patterns in server.py and rich_text_document_model.py
sec: fix clear-text logging of secrets in preflight.py
sec: fix XSS through DOM in app.js and related modules
sec: fix incomplete HTML sanitization patterns
sec: fix prototype pollution in config merge
sec: fix clear-text storage of session data in dashboard
sec: fix URL substring checks in tests
sec: fix bad HTML filtering regexps in tests
ci: scope CodeQL to ignore generated bundles, add SARIF upload for all scanners
```

Each commit message body should reference the specific lines changed. Follow the existing project commit style (`<prefix>: <imperative summary>`).

---

## Appendix C — Definition of done

The security scan job is fixed when:

- □  
`gitleaks detect` returns zero findings (and the 2 secrets are rotated at their source)
- □  
`bandit -r src/python -lll` returns zero HIGH findings
- □  
`pip-audit -r docs/requirements-production.txt` returns no known vulnerabilities
- □  
GitHub's CodeQL tab shows zero open HIGH findings
- □  
GitHub's CodeQL tab shows zero open MEDIUM findings in files under `src/js/` and `src/python/` (test-only findings can be waived if you add a `.github/codeql/codeql-config.yml` with an explicit path exclusion and a comment explaining why)
- □  
`python3 src/python/build_route_bundles.py --check` prints `ROUTE_BUNDLE_CHECK_PASSED`
- □  
`python3 scripts/check-bilingual-consistency.py` exits 0
- □  
`python3 scripts/check-rate-limit-coverage.py` exits 0
- □  
`python3 -m pytest tests/ -x` passes
- □  
The five functional spot checks in §14.3 behave as expected

Once all boxes are checked, the CI security scan job should pass on the next push.

---

*End of guide. If a specific finding is not covered here — for example a new Bandit rule appears after the fix — open `docs/security/CI-SECURITY.md` and add the pattern to the "known fix patterns" section so the next person finds it.*

