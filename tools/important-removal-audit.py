#!/usr/bin/env python3
"""important-removal-audit.py — prove a CSS edit changed *only* `!important` tokens.

Why this exists
---------------
The `!important` demotion work edits hand-written CSS, then a generator rebuilds
sixteen route bundles plus a page manifest. A rebuild is a black box: if it also
reordered rules, reformatted a block, or picked up an unrelated source edit, the
diff would *look* like a demotion while shipping something else. Line-based review
cannot establish that in a bundle — the bundles are one line each, so `git diff`
prints the whole file.

This tool answers the question mechanically, per changed file:

  * a CSS/JS file must be **byte-identical to HEAD after deleting every
    `!important` token**. Then the edit is exactly its removals, and the count of
    removals and the byte delta are reported.
  * a generated JSON manifest must differ **only** in size and digest fields, and
    those must agree with the files on disk: every recorded `*Bytes` must equal the
    current file's size, every recorded `*Sha256` must equal its current digest, and
    each size delta must equal the byte delta measured for the file it describes.

A manifest that was hand-edited, or one whose digests no longer match its files,
fails here rather than in a review someone has to re-do by hand.

Usage
-----
    python3 tools/important-removal-audit.py                 # vs HEAD
    python3 tools/important-removal-audit.py --rev=<rev>     # vs another revision

Exit status: 0 when every changed file is explained, 1 otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Manifest fields that legitimately move when a source file's weight changes.
SIZE_KEYS = {"bytes", "size", "totalBytes", "scriptBytes", "styleBytes", "cssBytes", "jsBytes", "gzipBytes"}
DIGEST_KEYS = {"sha256", "scriptSha256", "styleSha256", "cssSha256", "jsSha256", "digest", "hash"}


def head_bytes(rev: str, path: str) -> bytes:
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"], cwd=REPO_ROOT, capture_output=True
    )
    return proc.stdout if proc.returncode == 0 else b""


def changed_entries(rev: str) -> list[tuple[str, str, str | None]]:
    """[(status, path, old_path)] from `git diff --name-status -M <rev>`.

    Rename detection matters here: a rename batch moves ten CSS files and their
    mirrors, and a tool that could only see "deleted file / untracked file" would
    report every one of them as an unexplained change. With `-M` the rename arrives
    as `R100 old -> new`, which this tool verifies by comparing the two blobs.
    """
    proc = subprocess.run(
        ["git", "diff", "--name-status", "-M", rev], cwd=REPO_ROOT, capture_output=True, text=True
    )
    entries: list[tuple[str, str, str | None]] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if parts[0].startswith("R") or parts[0].startswith("C"):
            entries.append((parts[0], parts[2], parts[1]))
        else:
            entries.append((parts[0], parts[1], None))
    return entries


def blob(rev: str, path: str) -> bytes:
    proc = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=REPO_ROOT, capture_output=True)
    return proc.stdout if proc.returncode == 0 else b""


def index_document(node, prefix="", parent=None, out=None) -> dict:
    """Index a JSON document to {dotted path: (scalar, parent container)}.

    The parent container is kept because a manifest's size and digest fields name
    the file they describe in a *sibling* key (`javascript`, `stylesheet`, ...);
    finding that file means looking at the entry the field lives in.

    Keys are joined with `.`, so a page named `designer.html` addresses its fields as
    `pages.designer.html.bytes`. Building the index and looking it up use the same
    convention, which is why the dots inside a key are harmless here.
    """
    if out is None:
        out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            index_document(value, f"{prefix}.{key}" if prefix else str(key), node, out)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            index_document(value, f"{prefix}[{i}]", node, out)
    else:
        out[prefix] = (node, parent)
    return out


def flatten(node) -> dict:
    """{dotted path: scalar} — enough for the values that came from the older revision."""
    return {key: value for key, (value, _parent) in index_document(node).items()}


def audit_css(path: str, rev: str) -> tuple[bool, str]:
    before = head_bytes(rev, path).decode("utf-8", "replace")
    after = (REPO_ROOT / path).read_text(encoding="utf-8")
    removed = before.count("!important") - after.count("!important")
    stripped = before.replace("!important", "") == after.replace("!important", "")
    delta = len(after) - len(before)
    if stripped:
        return True, f"identical after !important strip; removed={removed}  bytes delta={delta:+d}"
    return False, f"NOT EXPLAINED BY !important (removed={removed}, bytes delta={delta:+d})"


# A generated bundle is served from more than one tree; the generator writes each
# artifact to every tree that needs it. Resolution order for a recorded file name.
CANDIDATE_ROOTS = ("src/python", "src/js", "src/css", "docs", ".")

# Sibling keys whose value names the file an entry's size/digest fields describe.
FILE_LIST_KEYS = ("javascript", "stylesheet", "scripts", "styles", "files", "assets")


def resolve(name: str) -> Path | None:
    """Resolve a file name recorded in a manifest to a path in this checkout."""
    for root in CANDIDATE_ROOTS:
        candidate = REPO_ROOT / root / name
        if candidate.is_file():
            return candidate
    return None


def describe(entry, leaf: str) -> list[str]:
    """The file names an entry records sizes/digests for.

    The field's own name narrows the set: `styleSha256` describes the entry's
    stylesheet, `scriptBytes` its javascript, and an unqualified `bytes`/`sha256`
    describes everything the entry lists. Without that narrowing a style digest is
    also compared against the script bundle, which always fails.
    """
    if not isinstance(entry, dict):
        return []
    wanted = FILE_LIST_KEYS
    if leaf.lower().startswith("style") or leaf.lower().startswith("css"):
        wanted = ("stylesheet", "styles", "files", "assets")
    elif leaf.lower().startswith("script") or leaf.lower().startswith("js"):
        wanted = ("javascript", "scripts", "files", "assets")
    names: list[str] = []
    for key in wanted:
        value = entry.get(key)
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            names.extend(str(v) for v in value)
    return names


def audit_manifest(path: str, rev: str, renames: dict[str, str]) -> tuple[bool, str]:
    """Every difference must be a size or digest field, and it must be *true*.

    Two independent claims are checked, not just the shape of the diff:

      * a digest field must equal sha256() of the file it names, read now;
      * a size field's delta must equal the summed byte delta of the files its entry
        names, measured against the same revision — i.e. the manifest must describe
        the rebuild that just happened, not a remembered number.

    `renames` is the diff's own rename map. A manifest that records *source names*
    (`route-bundle-sources-v15.json` is the hand-maintained one) legitimately moves
    those strings when a batch renames a file, and only when the move is exactly
    `old-name -> new-name` for a rename this diff performed is it accepted.
    """
    before = json.loads(head_bytes(rev, path).decode("utf-8"))
    after = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    flat_before = flatten(before)
    indexed_after = index_document(after)
    problems: list[str] = []
    moved: list[str] = []

    for key in sorted(set(flat_before) | set(indexed_after)):
        old = flat_before.get(key)
        new, parent = indexed_after.get(key, (None, None))
        if old == new:
            continue
        leaf = key.rsplit(".", 1)[-1].rstrip("]").split("[")[0]
        if leaf in SIZE_KEYS:
            if not (isinstance(old, int) and isinstance(new, int)):
                problems.append(f"{key}: non-integer size change {old!r} -> {new!r}")
                continue
            names = describe(parent, leaf)
            expected = 0
            for name in names:
                target = resolve(name)
                if target is not None:
                    rel = target.relative_to(REPO_ROOT).as_posix()
                    expected += target.stat().st_size - len(head_bytes(rev, rel))
            if expected != new - old:
                problems.append(
                    f"{key}: recorded {old} -> {new} ({new - old:+d}) but its files moved {expected:+d}"
                )
            else:
                moved.append(f"{key} {old} -> {new} ({new - old:+d})")
        elif leaf in DIGEST_KEYS:
            names = describe(parent, leaf)
            checked = 0
            for name in names:
                target = resolve(name)
                if target is None or target.suffix not in (".css", ".js"):
                    continue
                have = hashlib.sha256(target.read_bytes()).hexdigest()
                if have != new:
                    problems.append(f"{key}: recorded {str(new)[:12]}… != sha256({target.name}) {have[:12]}…")
                checked += 1
            if checked == 0:
                problems.append(f"{key}: no file named by its entry to check the digest against")
            else:
                moved.append(f"{key} {str(old)[:12]}… -> {str(new)[:12]}… ({checked} file(s) verified)")
        elif old is not None and renames.get(str(old)) == str(new):
            moved.append(f"{key} source name {old} -> {new} (a rename in this diff)")
        else:
            problems.append(f"{key}: unexpected field changed {old!r} -> {new!r}")

    if problems:
        return False, "; ".join(problems[:3])
    return True, f"{len(moved)} size/digest/source-name field(s) moved; {moved[0] if moved else 'no change'}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="important-removal-audit.py")
    parser.add_argument("--rev", default="HEAD", help="revision to compare against (default HEAD)")
    args = parser.parse_args(argv)

    entries = changed_entries(args.rev)
    failures: list[str] = []
    counts = {"modified": 0, "renamed": 0, "manifest": 0}

    # CSS/JS first: a manifest's size fields are checked by re-measuring the files it
    # names against the same revision, so its audit does not depend on this order.
    for status, path, old_path in entries:
        if not path.endswith((".css", ".js")):
            continue
        if status.startswith(("R", "C")) and old_path is not None:
            same = blob(args.rev, old_path) == (REPO_ROOT / path).read_bytes()
            note = f"renamed from {old_path}; content {'identical' if same else 'CHANGED'}"
            print(f"  {'ok  ' if same else 'FAIL'} {path:<56} {note}")
            counts["renamed"] += 1
            if not same:
                failures.append(path)
            continue
        if status == "M":
            ok, note = audit_css(path, args.rev)
            print(f"  {'ok  ' if ok else 'FAIL'} {path:<56} {note}")
            counts["modified"] += 1
            if not ok:
                failures.append(path)
            continue
        print(f"  FAIL {path:<56} status {status}: neither a modification nor a rename — a CSS/JS file was added or deleted")
        failures.append(path)

    rename_map = {
        Path(old).name: Path(path).name
        for status, path, old in entries
        if status.startswith(("R", "C")) and old is not None
    }
    for status, path, _old in entries:
        if path.endswith(".json") and status == "M":
            ok, note = audit_manifest(path, args.rev, rename_map)
            print(f"  {'ok  ' if ok else 'FAIL'} {path:<56} {note}")
            counts["manifest"] += 1
            if not ok:
                failures.append(path)

    total = sum(counts.values())
    print(
        f"\nimportant-removal-audit: vs {args.rev} — {total} changed CSS/JS/JSON entry(s) "
        f"({counts['modified']} modified, {counts['renamed']} renamed, {counts['manifest']} manifest(s)); failures={len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
