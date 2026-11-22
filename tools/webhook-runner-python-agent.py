#!/usr/bin/env python3
"""Harness probe for Python's production background-job processors."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MEDIA_KINDS = ("image.derivatives",)


def run_media_jobs(server, limit: int, now_ms: int) -> int:
    """media_worker.main()'s claim/run/complete-or-fail loop at a fixed clock."""
    import media_worker

    processed = 0
    for _ in range(max(0, int(limit))):
        job = server.claim_background_job(kinds=list(MEDIA_KINDS), now_ms=now_ms)
        if not job:
            break
        try:
            media_worker.run_job(job)
            server.complete_background_job(job["id"], now_ms=now_ms)
        except Exception as exc:
            server.fail_background_job(job["id"], exc, retry=True, now_ms=now_ms)
        processed += 1
    return processed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--now-ms", type=int, required=True)
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--allow-private", default="true")
    parser.add_argument(
        "--kind",
        choices=("webhook.deliver", "storage.delete", "image.derivatives"),
        default="webhook.deliver",
    )
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

    if args.kind == "storage.delete":
        processed = server.process_storage_delete_jobs(limit=args.limit, now_ms=args.now_ms)
    elif args.kind in MEDIA_KINDS:
        processed = run_media_jobs(server, args.limit, args.now_ms)
    else:
        processed = server.process_webhook_jobs(limit=args.limit, now_ms=args.now_ms)
    print(json.dumps({"processed": processed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
