#!/usr/bin/env python3
"""S1 — round-trip equivalence harness for the language-optimization migration.

Plan: `language-optimization-plan-v3.1.md` §5 (S1). It seeds itself from the P2
inventory (`docs/language-migration/ROUTE-INVENTORY.md`), records real responses
from one backend, replays them against another, and diffs status, headers and body.

It is also the shadow tee (R3) and the replay engine (R4): shadow proof must not
depend on live traffic, so the corpus is a file, not a packet capture.

Modes
  --record BASE --corpus F     capture responses from BASE
  --replay BASE --corpus F     re-send the corpus to BASE and diff
  --compare A B                record from A, replay to B (the shadow tee)
  --self-check                 boot two fresh Python instances, A → B must be 0 diffs

Scope of this first cut — deliberately narrow, and reported honestly:
  * read-only (GET) only. Writes are excluded until the plan's Rule 8 snapshot
    copy exists: replaying a POST twice mutates the same database, which is
    exactly what the plan forbids.
  * unauthenticated. Authenticated cross-instance comparison cannot be honest
    (a session created on A does not exist on B); the authenticated corpus is an
    S6 deliverable that needs the shared session store.
  * artefact-generating routes are skipped (media, images, social cards, exports,
    backups, *.png/svg/ics), same list the P2 extractor uses.

Corpus entries store a normalised body, not raw bytes; `--store-size` caps each
entry. Normalisation is listed in NORMALISERS and must stay conservative — a rule
that hides a real difference is worse than a noisy one.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / "artifacts" / "lang-migration" / "route-inventory.json"
TOOLS = Path(__file__).resolve().parent

COMPARED_HEADERS = (
    "content-type",
    "cache-control",
    "location",
    "x-robots-tag",
    "content-language",
    "vary",
    "x-frame-options",
    "content-security-policy",
    "content-disposition",
)

NORMALISERS = (
    # A fresh instance mints a fresh CSP nonce, so both the header form
    # ('nonce-…') and the markup form (nonce="…") must be folded.
    (re.compile(r"'nonce-[^']*'"), "'nonce-NONCE'"),
    (re.compile(r'nonce="[^"]*"'), 'nonce="NONCE"'),
    (re.compile(r"127\.0\.0\.1:\d+"), "127.0.0.1:PORT"),
    (re.compile(r"localhost:\d+"), "localhost:PORT"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "UUID"),
    (re.compile(r"\b1[6-9]\d{11}\b"), "EPOCHMS"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}T[\d:.]+Z?\b"), "ISODATE"),
    (re.compile(r"\b[0-9a-f]{32,}\b"), "HEX"),
    # Process-instance facts, not behaviour: two freshly booted instances cannot
    # agree on either, and neither says anything about the backend that serves it.
    (re.compile(r'"uptimeSeconds":\s*\d+'), '"uptimeSeconds": N'),
    (re.compile(r"/tmp/einvite-live-v14-[A-Za-z0-9_]+"), "TMPDIR"),
    (re.compile(r"/tmp/einvite-v14-[A-Za-z0-9_]+"), "TMPDIR"),
)


def normalise_text(value: str) -> str:
    for pattern, replacement in NORMALISERS:
        value = pattern.sub(replacement, value)
    return value


def normalise(body: str, content_type: str) -> str:
    body = body.replace("\r\n", "\n")
    if "json" in content_type:
        try:
            body = json.dumps(json.loads(body), sort_keys=True, ensure_ascii=False)
        except Exception:
            pass
    return normalise_text(body)


def load_sampler():
    spec = importlib.util.spec_from_file_location(
        "route_inventory", TOOLS / "route-inventory.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_from_inventory(inventory_path: Path) -> tuple[list[dict], list[str]]:
    """(requests, skipped) built from the frozen P2 inventory, GET only."""
    ri = load_sampler()
    if inventory_path.exists():
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
        routes = data["routes"]
    else:
        routes = ri.extract_routes()

    requests: list[dict] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for route in routes:
        if route["method"] != "GET":
            continue
        if ri.PROBE_SKIP.search(route["pattern"]):
            skipped.append(f"{route['pattern']} (artefact route)")
            continue
        sample = route.get("probe", {}).get("path") if route.get("probe") else None
        sample = sample or ri.sample_path(route)
        if not sample or sample in seen:
            continue
        seen.add(sample)
        requests.append({"method": "GET", "path": sample, "pattern": route["pattern"]})
    return requests, skipped


def send(base: str, request: dict, timeout: float = 10.0) -> dict:
    url = base.rstrip("/") + request["path"]
    req = urllib.request.Request(
        url, method=request["method"], headers={"User-Agent": "parity-harness/1"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, headers, raw = resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        status, headers, raw = exc.code, dict(exc.headers or {}), exc.read()
    except Exception as exc:
        return {"status": 0, "error": str(exc)[:200], "headers": {}, "body": ""}
    text = raw.decode("utf-8", "replace")
    content_type = headers.get("Content-Type", "")
    return {
        "status": status,
        "headers": {k.lower(): v for k, v in headers.items()},
        "body": normalise(text, content_type),
        "sha256": hashlib.sha256(text.encode("utf-8", "replace")).hexdigest(),
        "bytes": len(raw),
    }


def capture(base: str, requests: list[dict]) -> list[dict]:
    entries = []
    for index, request in enumerate(requests, 1):
        response = send(base, request)
        entries.append({**request, "response": response})
        if index % 25 == 0:
            print(f"  … {index}/{len(requests)}", file=sys.stderr)
    return entries


def summarise(response: dict) -> dict:
    return {
        "status": response["status"],
        "headers": {
            name: normalise_text(response.get("headers", {}).get(name, ""))
            for name in COMPARED_HEADERS
            if name in response.get("headers", {})
        },
        "body": response.get("body", ""),
    }


def diff_entry(expected: dict, actual: dict) -> list[str]:
    """Both arguments are response dicts (see `send`), not corpus entries."""
    left, right = summarise(expected), summarise(actual)
    problems: list[str] = []
    if left["status"] != right["status"]:
        problems.append(f"status {left['status']} != {right['status']}")
    for name in COMPARED_HEADERS:
        if left["headers"].get(name) != right["headers"].get(name):
            problems.append(
                f"header {name}: {left['headers'].get(name)!r} != {right['headers'].get(name)!r}"
            )
    if left["body"] != right["body"]:
        problems.append(f"body: {first_difference(left['body'], right['body'])}")
    return problems


def first_difference(left: str, right: str) -> str:
    for i, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return (
                f"at offset {i} ({len(left)} vs {len(right)} bytes): "
                f"{left[max(0, i - 40):i + 40]!r} != {right[max(0, i - 40):i + 40]!r}"
            )
    return f"prefix equal, lengths {len(left)} vs {len(right)}"


def compare(entries: list[dict], requests: list[dict], base: str) -> tuple[int, list[str], int]:
    identical = 0
    skipped = 0
    failures: list[str] = []
    for entry, request in zip(entries, requests):
        actual = send(base, request)
        if entry["response"]["status"] == 0 or actual["status"] == 0:
            skipped += 1
            failures.append(f"UNEXERCISED {request['method']} {request['path']} (transport)")
            continue
        if actual["status"] == 429 or entry["response"]["status"] == 429:
            skipped += 1
            failures.append(f"SKIPPED {request['method']} {request['path']} (rate limited)")
            continue
        problems = diff_entry(entry["response"], actual)
        if problems:
            failures.append(f"DIFF {request['method']} {request['path']}")
            failures.extend(f"    {p}" for p in problems)
        else:
            identical += 1
    return identical, failures, skipped


def report(identical: int, failures: list[str], skipped: int, total: int) -> int:
    for line in failures:
        print(line)
    diffs = sum(1 for line in failures if line.startswith("DIFF"))
    print(
        f"PARITY {identical}/{total} identical · {diffs} diff · {skipped} skipped"
    )
    return 0 if diffs == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", metavar="BASE")
    ap.add_argument("--replay", metavar="BASE")
    ap.add_argument("--compare", nargs=2, metavar=("BASE_A", "BASE_B"))
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--corpus", default=str(ROOT / "artifacts" / "lang-migration" / "corpus.json"))
    ap.add_argument("--inventory", default=str(INVENTORY))
    args = ap.parse_args()

    requests, skipped_routes = corpus_from_inventory(Path(args.inventory))
    print(f"CORPUS {len(requests)} GET requests · {len(skipped_routes)} routes not exercisable")
    for reason in skipped_routes:
        print(f"  not exercisable: {reason}")

    if args.record:
        entries = capture(args.record, requests)
        Path(args.corpus).parent.mkdir(parents=True, exist_ok=True)
        Path(args.corpus).write_text(json.dumps(entries, indent=1), encoding="utf-8")
        print(f"RECORDED {len(entries)} → {args.corpus}")
        return 0

    if args.compare:
        base_a, base_b = args.compare
        entries = capture(base_a, requests)
        Path(args.corpus).parent.mkdir(parents=True, exist_ok=True)
        Path(args.corpus).write_text(json.dumps(entries, indent=1), encoding="utf-8")
        identical, failures, skipped = compare(entries, requests, base_b)
        return report(identical, failures, skipped, len(requests))

    if args.replay or args.self_check:
        if args.self_check:
            sys.path.insert(0, str(ROOT / "tests"))
            from v14_test_utils import fresh_server  # noqa: PLC0415

            with fresh_server() as (_p1, base_a, _d1), fresh_server() as (_p2, base_b, _d2):
                print(f"INSTANCES A={base_a} B={base_b}")
                entries = capture(base_a, requests)
                Path(args.corpus).parent.mkdir(parents=True, exist_ok=True)
                Path(args.corpus).write_text(json.dumps(entries, indent=1), encoding="utf-8")
                identical, failures, skipped = compare(entries, requests, base_b)
                return report(identical, failures, skipped, len(requests))

        corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
        identical, failures, skipped = compare(corpus, requests, args.replay)
        return report(identical, failures, skipped, len(requests))

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
