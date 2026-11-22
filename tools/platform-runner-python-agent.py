#!/usr/bin/env python3
"""Harness probe for platform_v32's JobQueue runner.

Runs the real ``JobQueue._run()`` for one seeded ``platform_jobs`` row, so the
Python side of the parity harness is production code and not a reimplementation.
``EINVITE_WORKER_CONCURRENCY=0`` keeps the service's own worker threads out of
the way; with no ``--job-id`` it only creates the schema.
"""
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
    parser.add_argument("--job-id", default="")
    args = parser.parse_args()

    os.environ["EINVITE_DATABASE_URL"] = args.database_url
    os.environ["EINVITE_DATA_DIR"] = args.data_dir
    os.environ["EINVITE_WORKER_CONCURRENCY"] = "0"
    os.environ["EINVITE_FIELD_ENCRYPTION"] = "0"
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src" / "python"))
    import server  # noqa: E402 — configuration above must land first

    service = server.get_platform_v32_service()
    try:
        if args.job_id:
            service.jobs._run(args.job_id)
    finally:
        service.jobs.shutdown(timeout=1)
    print(json.dumps({"ran": bool(args.job_id)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
