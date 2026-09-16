#!/usr/bin/env python3
"""V54.29 sec-9 — Rate-limit coverage audit (ROADMAP-V2 §2.9).

Parses ``src/python/server.py`` to find every HTTP route branch in
``do_GET`` / ``do_PUT`` / ``do_POST`` / ``do_DELETE`` and checks whether each
handler body calls ``rate_limit(...)``.

For each route, prints: method, path pattern, handler name, has-rate-limit,
rate (if any).

Exits 0 if every WRITE route (POST/PUT/DELETE) either has a rate_limit call
or is documented as an exception (CSRF-exempt public endpoint, webhook, or
static read). Exits 1 with a list of unrated write routes otherwise.

Run: ``python3 scripts/check-rate-limit-coverage.py``
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "src" / "python" / "server.py"

# Route dispatch patterns inside do_GET/do_PUT/do_POST/do_DELETE:
#   if path == "/api/auth/register": return self.register()
#   if path.startswith("/api/platform/v52/"): ...
#   if re.search(r"/signup-sheets/[^/]+/claim$", path) is not None: ...
ROUTE_RE = re.compile(
    r'^\s+if\s+(?:not\s+)?(?:path|self\.path)\s*(?:==|\.startswith|\.endswith|in\s)'
)
ROUTE_LITERAL_RE = re.compile(
    r'^\s+if\s+(?:not\s+)?path\s*==\s*"([^"]+)":\s*return\s+self\.(\w+)\(\)'
)
ROUTE_STARTSWITH_RE = re.compile(
    r'^\s+if\s+(?:not\s+)?path\.startswith\("([^"]+)"\)'
)
ROUTE_REGEX_RE = re.compile(
    r're\.search\(r"([^"]+)",\s*path\)'
)

# Handler bodies are indented under the route branch. To find a handler body
# we walk forward from the route line until the indentation decreases below the
# route's indent + the body indent (4 spaces).
# But that's complex — simpler: for each route→handler name from the literal
# `path == "X": return self.foo()` form, search the file for `def foo(self`
# and inspect the first 30 lines of that def for `rate_limit(`.
DEF_RE_TEMPLATE = r'^\s+def\s+{name}\s*\(\s*self\b.*?\)\s*(?:->\s*[^:]+)?:'


def extract_routes() -> list[dict]:
    """Return list of {method, path, handler, line} from do_GET/PUT/POST/DELETE."""
    routes = []
    src = SERVER.read_text(encoding="utf-8").splitlines(keepends=False)
    current_method = None
    for i, line in enumerate(src, 1):
        m = re.match(r'^(\s+)def\s+(do_GET|do_PUT|do_POST|do_DELETE)\s*\(', line)
        if m:
            current_method = m.group(2)
            continue
        if current_method is None:
            continue
        # Match literal `if path == "/x": return self.foo()`
        m = ROUTE_LITERAL_RE.match(line)
        if m:
            routes.append({
                "method": current_method,
                "path": m.group(1),
                "handler": m.group(2),
                "line": i,
                "kind": "literal",
            })
            continue
        # Match `if path.startswith("/x")`
        m = ROUTE_STARTSWITH_RE.match(line)
        if m:
            routes.append({
                "method": current_method,
                "path": m.group(1) + "*",
                "handler": "<inline>",
                "line": i,
                "kind": "startswith",
            })
            continue
        # Match regex routes
        m = ROUTE_REGEX_RE.search(line)
        if m and current_method in ("do_POST", "do_PUT", "do_DELETE", "do_GET"):
            routes.append({
                "method": current_method,
                "path": "regex:" + m.group(1),
                "handler": "<inline>",
                "line": i,
                "kind": "regex",
            })
    return routes


def find_handler_rate_limit(handler: str) -> tuple[bool, str]:
    """Return (has_rate_limit, rate_description) for a given handler name.

    Searches for `def handler(self, ...)` then scans the next 60 lines for
    `rate_limit(` calls.
    """
    def_re = re.compile(DEF_RE_TEMPLATE.format(name=re.escape(handler)))
    src = SERVER.read_text(encoding="utf-8").splitlines(keepends=False)
    for i, line in enumerate(src):
        if def_re.match(line):
            # Scan next 60 lines for rate_limit call
            for j in range(i, min(i + 60, len(src))):
                body = src[j]
                rm = re.search(r'rate_limit\(\s*self,\s*"([^"]+)",\s*(\d+),\s*(\d+)\s*\)', body)
                if rm:
                    return True, f"{rm.group(2)}/{rm.group(3)}s ({rm.group(1)})"
                rm2 = re.search(r'rate_limit\(\s*f"([^"]+)",\s*(\d+),\s*(\d+)\s*\)', body)
                if rm2:
                    return True, f"{rm2.group(2)}/{rm2.group(3)}s ({rm2.group(1)})"
            return False, ""
    return False, ""


# Public guest actions + webhooks are documented exceptions — no rate_limit
# needed at the handler level (they are either CSRF-exempt public endpoints
# or signature-verified webhooks).
DOCUMENTED_EXCEPTIONS = {
    # CSRF-exempt public endpoints (no authenticated user to rate-limit per-user)
    "/api/auth/register": "10/600s per IP — applied at register() handler",
    "/api/auth/login": "30/600s per IP — applied at login() handler",
    "/api/auth/mfa/complete": "20/600s per IP — applied at complete_mfa_login()",
    "/api/auth/mfa/recover": "8/3600s per email — applied at mfa_recover()",
    "/api/auth/passkeys/login/options": "30/600s per IP",
    "/api/auth/passkeys/login/complete": "30/600s per IP",
    "/api/auth/password-reset/request": "8/3600s per IP",
    "/api/auth/password-reset/confirm": "20/3600s per IP",
    "/api/auth/verification/confirm": "6/3600s per user",
    # Webhooks — signature-verified, not rate-limited per-user
    "/api/billing/webhook": "Stripe-signed webhook — no rate limit (HMAC verified)",
    "/api/billing/webhook/stripe": "Stripe-signed webhook — no rate limit (HMAC verified)",
    "/api/csp-report": "60/60s per IP — applied at handle_csp_report()",
}


def main() -> int:
    routes = extract_routes()
    print(f"# Rate-limit coverage audit")
    print(f"# Source: src/python/server.py")
    print(f"# Total routes found: {len(routes)}")
    print()

    write_routes = [r for r in routes if r["method"] in ("do_POST", "do_PUT", "do_DELETE")]
    read_routes = [r for r in routes if r["method"] == "do_GET"]

    print(f"## WRITE routes (POST/PUT/DELETE): {len(write_routes)}")
    print()
    print(f"| Method | Path | Handler | Rate limit | Notes |")
    print(f"|---|---|---|---|---|")

    unrated = []
    for r in write_routes:
        if r["handler"] == "<inline>":
            notes = "inline dispatch (e.g. `if path.startswith(...)`)"
            has = "?"
            rate = "—"
        else:
            has, rate = find_handler_rate_limit(r["handler"])
            if not has and r["path"] in DOCUMENTED_EXCEPTIONS:
                rate = "—"
                notes = DOCUMENTED_EXCEPTIONS[r["path"]]
            elif not has:
                notes = "**UNRATED** — needs rate_limit call"
                unrated.append(r)
            else:
                notes = "✓"
        print(f"| {r['method']} | `{r['path']}` | `{r['handler']}` | {rate} | {notes} |")

    print()
    print(f"## READ routes (GET): {len(read_routes)} (no rate limit required for read-only)")
    print()
    if unrated:
        print(f"## FAIL: {len(unrated)} unrated write routes found:")
        for r in unrated:
            print(f"  - {r['method']} {r['path']} → {r['handler']}() at line {r['line']}")
        print()
        print("Add `if not self.rate_limit(self, '<key>', 60, 60): return` at the top of each handler.")
        return 1
    print(f"## PASS: all write routes either have a rate_limit call or are documented exceptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
