#!/usr/bin/env python3
"""Redact the disposable session cookie/CSRF token from DAST artifacts.

ZAP reports and its stdout log can echo request headers. The session file and
the ZAP replacer config live outside the uploaded artifact directory; this
script additionally removes the exact cookie/CSRF values from every text
artifact before upload.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

TEXT_SUFFIXES = {".html", ".htm", ".json", ".xml", ".log", ".txt", ".md"}


def redaction_values(session):
    values = {
        session.get("session_cookie", ""),
        session.get("csrf_token", ""),
        session.get("cookie_header", ""),
    }
    expanded = set()
    for value in values:
        if not value:
            continue
        expanded.add(value)
        expanded.add(urllib.parse.quote(value, safe=""))
        expanded.add(urllib.parse.quote_plus(value))
    return sorted((v for v in expanded if len(v) >= 8), key=len, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", required=True)
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()

    session_path = Path(args.session_file)
    if not session_path.is_file():
        print("DAST_REDACTION_SKIPPED: no disposable session file")
        return 0
    try:
        session = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"DAST_REDACTION_FAILED: {exc}", file=sys.stderr)
        return 1

    secrets = redaction_values(session)
    if not secrets:
        print("DAST_REDACTION_SKIPPED: session file has no values")
        return 0
    if not args.artifacts:
        print("DAST_REDACTION_SKIPPED: no artifact directory")
        return 0

    artifacts = Path(args.artifacts)
    if not artifacts.is_dir():
        print(f"DAST_REDACTION_SKIPPED: {artifacts} does not exist")
        return 0

    changed = 0
    replacements = 0
    for path in artifacts.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        original = text
        for secret in secrets:
            occurrences = text.count(secret)
            if occurrences:
                text = text.replace(secret, "[REDACTED]")
                replacements += occurrences
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1

    print(f"DAST_REDACTION_OK files={changed} replacements={replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
