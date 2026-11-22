#!/usr/bin/env python3
"""P2 route inventory for the language-optimization migration (see
`language-optimization-plan-v3.1.md`, precondition P2).

`src/python/server.py` is a hand-written dispatcher: there is no route table.
This tool recovers the inventory mechanically so the freeze is auditable:

  1. index every `def` in the backend and the routes declared inside it,
  2. walk reachability from `do_GET` / `do_POST` / `do_PUT` / `do_DELETE`
     through `self.<helper>(path)` calls (so routes in `_admin_get_dispatch`,
     `platform_v32_get`, `future_v52_post`, `_put_*` … are attributed to the
     right HTTP method),
  3. classify the auth requirement from the handler body's guard symbols,
  4. record the trailing-slash semantics the declaration implies,
  5. optionally probe the live backend (GET only, read-only) to check the
     status class and the trailing-slash behaviour empirically.

Usage:
  python3 tools/route-inventory.py                     # static inventory
  python3 tools/route-inventory.py --probe http://127.0.0.1:4175
  python3 tools/route-inventory.py --json out.json --markdown out.md

Never sends POST/PUT/DELETE, and never probes export/media/image routes: the
probe is read-only and must be safe against the owner's running origin.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "src" / "python" / "server.py"
HTTP_METHODS = ("GET", "POST", "PUT", "DELETE")

# Routes whose probe would generate an artefact, stream a file or fan out work.
# (`export` must be anchored: `/api/canva/export-formats` is a plain JSON route,
# while `/api/account/analytics/export` and `…/data-export/<id>/download` are not.)
PROBE_SKIP = re.compile(
    r"/(media|image|image-cache)/|social-card|/download|\.png|\.svg|\.ics"
    r"|/export(?:$|/|\?)|/backup|/qr|/archive|/bundle|/campaigns/[^/]+/deliveries"
)

DEF_RE = re.compile(r"^(\s*)def\s+(\w+)\s*\(")
CALL_RE = re.compile(r"self\.(\w+)\(")


def load_lines() -> list[str]:
    return SERVER.read_text(encoding="utf-8").splitlines()


def index_defs(lines: list[str]) -> dict[str, dict]:
    """name -> {start, end} using indentation-based body bounds.

    A def ends at the first later line indented at or left of it. The next
    `def` must close the previous block before it opens its own: skipping that
    check was what made every method appear to own every route.
    """
    defs: dict[str, dict] = {}
    current: list[tuple[int, str, int]] = []  # (start, name, indent)

    def close(end: int) -> None:
        start, name, _indent = current.pop()
        stop = end
        while stop > start and not lines[stop - 1].strip():
            stop -= 1
        defs.setdefault(name, {"start": start, "end": stop})

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        m = DEF_RE.match(line)
        if m:
            while current and current[-1][2] >= indent:
                close(i)
            current.append((i, m.group(2), indent))
            continue
        while current and current[-1][2] >= indent:
            close(i)
    while current:
        close(len(lines))
    return defs


def reachable(defs: dict[str, dict], lines: list[str], root: str) -> set[str]:
    """All defs reachable from `root` through self.<name>(path) calls."""
    seen: set[str] = set()
    queue = [root]
    while queue:
        name = queue.pop()
        if name in seen or name not in defs:
            continue
        seen.add(name)
        body = "\n".join(lines[defs[name]["start"] : defs[name]["end"]])
        for callee in CALL_RE.findall(body):
            if callee in defs and callee not in seen:
                queue.append(callee)
    return seen


def handler_bodies(defs: dict[str, dict], lines: list[str]) -> dict[str, str]:
    return {
        name: "\n".join(lines[d["start"] : d["end"]]) for name, d in defs.items()
    }


AUTH_SYMBOLS = (
    ("admin", re.compile(r"require_role\(\s*[\"']admin|require_admin\(")),
    ("scoped", re.compile(r"can_(?:read|edit|manage)_invitation\(|invitation_role\(|self\.owns\(")),
    ("user", re.compile(r"require_user\(|self\.user\(\)|require_upload_permission\(")),
    ("api-key", re.compile(r"api_key_scope|require_api_scope|scoped_api")),
)

PUBLIC_PREFIXES = (
    "/api/public/",
    "/api/health",
    "/_marketplace/",
    "/api/auth/",
    "/api/media/",
    "/api/image/",
    "/uploads/",
    "/i/",
)


def classify_auth(path: str, handler: str, bodies: dict[str, str],
                  edges: dict[str, set[str]] | None = None) -> tuple[str, str]:
    """(class, evidence). Evidence is the symbols found, never an assumption.

    Handlers delegate (`ai_agent_tools` -> `_ai_agent_access` -> `require_user`),
    so the scan follows the same call graph the dispatcher does, up to depth 3,
    and names the callee that supplied the guard.
    """
    if path.startswith("/api/admin/"):
        return "admin", "path under /api/admin"
    plain = re.sub(r"\\+", "", path)
    if (
        plain in ("/", "/api/health")
        or plain.endswith(".html")
        or re.fullmatch(r"/[A-Za-z0-9_.-]+\.html", plain)
    ):
        return "public", "page or health endpoint"
    edges = edges or {}
    scanned: set[str] = set()
    frontier = [handler] if handler else []
    depth = 0
    while frontier and depth < 3:
        nxt: list[str] = []
        for name in frontier:
            if name in scanned:
                continue
            scanned.add(name)
            body = bodies.get(name, "")
            for label, rx in AUTH_SYMBOLS:
                if rx.search(body):
                    where = f" in {name}()" if name != handler else ""
                    return label, label + where
            nxt.extend(sorted(edges.get(name, ())))
        frontier, depth = nxt, depth + 1
    if path.startswith(PUBLIC_PREFIXES):
        return "public", "public prefix, no guard in handler"
    return "unclassified", "no guard symbol in handler or its callees"


def extract_routes() -> list[dict]:
    lines = load_lines()
    defs = index_defs(lines)
    bodies = handler_bodies(defs, lines)
    edges: dict[str, set[str]] = {}
    for name, entry in defs.items():
        edges[name] = {
            callee
            for callee in CALL_RE.findall(
                "\n".join(lines[entry["start"] : entry["end"]])
            )
            if callee in defs
        }
    method_defs: dict[str, set[str]] = {}
    for method in HTTP_METHODS:
        root = f"do_{method}"
        method_defs[method] = reachable(defs, lines, root) if root in defs else set()

    # def -> HTTP methods that reach it
    def_methods: dict[str, list[str]] = {}
    for method, names in method_defs.items():
        for name in names:
            def_methods.setdefault(name, []).append(method)

    routes: dict[tuple, dict] = {}

    def add(method, kind, pattern, handler, trailing, note):
        # A prefix family is only a route once its suffix condition is included:
        # `startswith('/api/invitations/') + endswith('/guests')` is a different
        # route from the `+ endswith('/rsvps')` line next to it.
        key = (method, kind, pattern if kind != "prefix" else pattern + "|" + trailing)
        if key in routes:
            entry = routes[key]
            if handler and handler not in entry["handlers"]:
                entry["handlers"].append(handler)
            return
        auth_class, evidence = classify_auth(
            pattern if kind == "prefix" else pattern, handler, bodies, edges
        )
        if auth_class == "unclassified" and note.split()[0] in (
            "platform_v32_get()", "platform_v32_post()",
            "future_v52_get()", "future_v52_post()",
        ):
            # The guard is inside get_platform_v32_service(), not in server.py.
            auth_class = "platform-service"
            evidence = "guard lives in the platform service dispatch"
        routes[key] = {
            "method": method,
            "kind": kind,
            "pattern": pattern,
            "handlers": [handler] if handler else [],
            "auth": auth_class,
            "auth_evidence": evidence,
            "trailing_slash": trailing,
            "declared_in": note,
        }

    for name, entry in sorted(defs.items(), key=lambda kv: kv[1]["start"]):
        methods = def_methods.get(name)
        if not methods:
            continue
        for i in range(entry["start"], entry["end"]):
            line = lines[i]
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            search_in = line if "self." in line else line + "\n" + nxt
            for method in methods:
                # 1. {"/api/x": self.handler, ...} dispatch dictionaries
                for m in re.finditer(r'"(/[A-Za-z0-9_./-]+)"\s*:\s*self\.(\w+)', line):
                    add(method, "exact", m.group(1), m.group(2), "exact only",
                        f"{name}() dict")
                # 2. path == "/x"
                for m in re.finditer(r'path\s*==\s*"(/[^"]*)"', line):
                    handler = first_handler(search_in, m.end())
                    add(method, "exact", m.group(1), handler, "exact only", f"{name}()")
                # 3. path in {"a", "b"}
                for m in re.finditer(r"path\s+in\s+\{([^}]*)\}", line):
                    for lit in re.findall(r'"(/[^"]*)"', m.group(1)):
                        add(method, "exact", lit, first_handler(search_in, m.end()),
                            "exact only", f"{name}() set")
                # 4. path.startswith("/x")
                for m in re.finditer(r'path\.startswith\(\s*"([^"]*)"\s*\)', line):
                    mods = []
                    tail = line[m.end() :]
                    for e in re.finditer(r'path\.endswith\(\s*"([^"]*)"\s*\)', tail):
                        mods.append(f"endswith {e.group(1)}")
                    for e in re.finditer(r'"([^"]+)"\s+in\s+path', tail):
                        mods.append(f"contains {e.group(1)}")
                    handler = first_handler(search_in, m.end())
                    prefix = m.group(1)
                    trailing = "prefix match"
                    if mods:
                        trailing = f"prefix {prefix.rstrip('/')!r} + " + ", ".join(mods)
                    add(method, "prefix", prefix, handler, trailing, f"{name}()")
                # 5. re.fullmatch(r"...", path)
                for m in re.finditer(
                    r're\.fullmatch\(\s*r?"((?:[^"\\]|\\.)*)"\s*,\s*(?:self\.)?path\s*\)',
                    line,
                ):
                    pattern = m.group(1).replace("\\/", "/")
                    handler = first_handler(search_in, m.end())
                    trailing = "both" if pattern.endswith("/?") else "exact (regex)"
                    add(method, "regex", "/" + pattern.lstrip("^/"), handler,
                        trailing, f"{name}()")

    return sorted(
        routes.values(), key=lambda r: (r["method"], r["pattern"])
    )


NOT_HANDLERS = {
    "json", "send_response", "send_header", "end_headers", "user", "require_user",
    "require_role", "require_admin", "body", "error", "redirect", "html",
}


def first_handler(text: str, after: int) -> str:
    for m in CALL_RE.finditer(text, after):
        if m.group(1) not in NOT_HANDLERS:
            return m.group(1)
    return ""


def probe(routes: list[dict], base: str) -> None:
    base = base.rstrip("/")
    for route in routes:
        if route["method"] != "GET" or PROBE_SKIP.search(route["pattern"]):
            continue
        sample = sample_path(route)
        if not sample:
            continue
        status, ctype = request(base + sample)
        alt = None
        if not sample.endswith("/"):
            alt = request(base + sample + "/")[0]
        route["probe"] = {"path": sample, "status": status, "content_type": ctype,
                          "status_trailing_slash": alt}


def sample_path(route: dict) -> str:
    pattern = route["pattern"]
    if route["kind"] == "exact":
        return pattern
    if route["kind"] == "prefix":
        return pattern + "route-inventory-probe"
    # regex: replace groups with a sentinel, drop optional-slash suffix
    p = pattern.rstrip("$")
    p = re.sub(r"\(\?:[^)]*\)", "probe", p)
    p = re.sub(r"\([^)]*\)", "probe", p)
    p = p.replace("/?", "")
    p = re.sub(r"\\\.", ".", p)
    p = re.sub(r"\[[^\]]*\][+*?]?", "probe", p)
    p = p.replace("^", "")
    if any(ch in p for ch in "?*+[](){}|\\"):
        return ""
    return p


def request(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "route-inventory/1"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            return resp.status, resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", "") if exc.headers else ""
    except Exception as exc:  # connection refused, timeout
        return 0, f"error: {exc}"[:80]


def render_markdown(routes: list[dict], meta: dict) -> str:
    out = ["# Route inventory (P2) — frozen", ""]
    out.append(f"Generated by `tools/route-inventory.py` from `{meta['source']}` "
               f"({meta['server_lines']:,} lines). **{len(routes)} declarations** "
               f"across GET/POST/PUT/DELETE.")
    out.append("")
    out.append(f"Probe: `{meta['probe']}`." if meta["probe"] else "Probe: not run (static only).")
    out.append("")
    counts: dict[str, int] = {}
    for route in routes:
        counts[route["method"]] = counts.get(route["method"], 0) + 1
    out.append("| Method | Declarations |")
    out.append("|---|---|")
    for method in HTTP_METHODS:
        out.append(f"| {method} | {counts.get(method, 0)} |")
    out.append("")
    auth_counts: dict[str, int] = {}
    for route in routes:
        auth_counts[route["auth"]] = auth_counts.get(route["auth"], 0) + 1
    out.append("| Auth class | Declarations |")
    out.append("|---|---|")
    for name, count in sorted(auth_counts.items(), key=lambda kv: -kv[1]):
        out.append(f"| {name} | {count} |")
    out.append("")
    out.append("`auth` is derived from guard symbols in the handler body, not from "
               "documentation. `unclassified` means no guard symbol was found — treat "
               "those rows as needing a manual read before any port.")
    out.append("")
    for method in HTTP_METHODS:
        rows = [r for r in routes if r["method"] == method]
        if not rows:
            continue
        out.append(f"## {method} ({len(rows)})")
        out.append("")
        header = "| Pattern | Kind | Handler | Auth | Evidence | Trailing slash | Declared in |"
        out.append(header)
        out.append("|---|---|---|---|---|---|---|")
        for r in rows:
            probe = ""
            if r.get("probe"):
                p = r["probe"]
                probe = f" · probe {p['status']}"
                if p["status_trailing_slash"] is not None:
                    probe += f" / {p['status_trailing_slash']} with slash"
            out.append(
                "| `{pattern}`{probe} | {kind} | `{handler}` | {auth} | {evidence} | {slash} | {where} |".format(
                    pattern=r["pattern"].replace("|", "\\|"),
                    probe=probe,
                    kind=r["kind"],
                    handler=", ".join(f"{h}()" for h in r["handlers"]) or "—",
                    auth=r["auth"],
                    evidence=r["auth_evidence"].replace("|", "\\|"),
                    slash=r["trailing_slash"].replace("|", "\\|"),
                    where=r["declared_in"],
                )
            )
        out.append("")
    out.append("## Probe legend")
    out.append("")
    out.append("`probe <status>` is a live GET against a running backend with a probe "
               "slug; `/ <status> with slash` is the same path with a trailing slash. "
               "A 401/403 pair on both forms says nothing about routing (auth rejects "
               "before dispatch); only a differing pair does. Routes that generate "
               "artefacts are never probed.")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", metavar="BASE_URL", help="read-only GET probe origin")
    ap.add_argument("--json")
    ap.add_argument("--markdown")
    args = ap.parse_args()

    routes = extract_routes()
    meta = {
        "source": "src/python/server.py",
        "server_lines": len(load_lines()),
        "probe": args.probe or "",
    }
    if args.probe:
        probe(routes, args.probe)

    unclassified = [r for r in routes if r["auth"] == "unclassified"]
    for r in unclassified:
        print(f"UNCLASSIFIED {r['method']:6} {r['pattern']}  ({', '.join(r['handlers'])})",
              file=sys.stderr)

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(
            json.dumps({"meta": meta, "routes": routes}, indent=1), encoding="utf-8"
        )
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(render_markdown(routes, meta), encoding="utf-8")

    by_method = {m: sum(1 for r in routes if r["method"] == m) for m in HTTP_METHODS}
    print(f"ROUTE_INVENTORY {json.dumps({'total': len(routes), 'by_method': by_method, 'unclassified': len(unclassified)})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
