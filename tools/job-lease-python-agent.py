#!/usr/bin/env python3
"""Harness driver for Python's production job queue claim.

Imports server.py and calls claim_background_job(), the same function the
Python workers use, so a cross-backend claim race is settled by the real code
rather than a copy of its SQL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--worker", default="python-agent")
    parser.add_argument("--mode", default="drain")
    parser.add_argument("--kind", default="harness.lease")
    parser.add_argument("--max-claims", type=int, default=100)
    parser.add_argument("--start-at", type=float, default=0.0)
    args = parser.parse_args()

    # server.py reads its configuration at import time.
    os.environ["EINVITE_DATABASE_URL"] = args.database_url
    os.environ["EINVITE_DATA_DIR"] = args.data_dir
    os.environ.setdefault("EINVITE_FIELD_ENCRYPTION", "0")
    # src/python first: the repository-root server.py is a dev wrapper that
    # would execute the real module as __main__ and parse this agent's argv.
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src" / "python"))
    import server  # noqa: E402 — configuration above must land first

    if args.start_at:
        time.sleep(max(0.0, args.start_at - time.time()))

    if args.mode == "claim":
        job = server.claim_background_job([args.kind])
        print(json.dumps({"worker": args.worker, "job": job}, default=str))
        return 0
    if args.mode in ("platform-drain", "platform-claim"):
        from platform_v32.jobs import JobQueue

        queue = JobQueue(server.connect, workers=0)
        queue.register(args.kind, lambda payload, progress, cancelled: {"ok": True})
        if args.mode == "platform-claim":
            job_id = queue._claim_pending()
            print(json.dumps({"worker": args.worker, "job": {"id": job_id} if job_id else None}))
            return 0
        claims = []
        misses = 0
        while len(claims) < args.max_claims and misses < 3:
            job_id = queue._claim_pending()
            if not job_id:
                misses += 1
                time.sleep(0.02)
                continue
            misses = 0
            claims.append({"id": job_id})
            queue._run(job_id)
            time.sleep(0.005)
        print(json.dumps({"worker": args.worker, "claims": claims}))
        return 0
    if args.mode != "drain":
        raise SystemExit(f"unknown mode: {args.mode}")

    claims = []
    misses = 0
    while len(claims) < args.max_claims and misses < 3:
        job = server.claim_background_job([args.kind])
        if not job:
            misses += 1
            time.sleep(0.02)
            continue
        misses = 0
        claims.append({"id": job["id"], "attempts": job["attempts"]})
        server.complete_background_job(job["id"])
        time.sleep(0.005)
    print(json.dumps({"worker": args.worker, "claims": claims}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
