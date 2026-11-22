#!/usr/bin/env python3
"""Harness probe for Python's production webhook queue processor."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--now-ms", type=int, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--allow-private", default="true")
    args = parser.parse_args()

    os.environ["EINVITE_DATABASE_URL"] = args.database_url
    os.environ["EINVITE_DATA_DIR"] = args.data_dir
    os.environ["EINVITE_ALLOW_PRIVATE_WEBHOOKS"] = (
        "1" if args.allow_private.strip().lower() in {"1", "true", "yes"} else "0"
    )
    os.environ["EINVITE_BACKGROUND_MEDIA"] = "0"
    os.environ["EINVITE_FIELD_ENCRYPTION"] = "0"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src" / "python"))
    import server  # noqa: E402 — configuration above must land first

    processed = server.process_webhook_jobs(limit=args.limit, now_ms=args.now_ms)
    print(json.dumps({"processed": processed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
