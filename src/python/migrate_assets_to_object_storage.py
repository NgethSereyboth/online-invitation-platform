"""Upload locally stored invitation materials to S3-compatible object storage.

The asset database paths remain unchanged. Configure the server with the same bucket,
prefix, and optional public base URL after migration.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sqlite3
from pathlib import Path



def platform_env(name, default=None):
    """Read the current EINVITE_* setting, with legacy SOVAN_* fallback."""
    legacy = name.replace("EINVITE_", "SOVAN_", 1)
    return os.environ.get(name, os.environ.get(legacy, default))

ROOT = Path(__file__).resolve().parent
DATA = Path(platform_env("EINVITE_DATA_DIR", ROOT / "data"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(DATA / "invites.db"))
    parser.add_argument("--uploads", default=str(DATA / "uploads"))
    parser.add_argument("--delete-local", action="store_true")
    args = parser.parse_args()
    bucket = platform_env("EINVITE_OBJECT_STORAGE_BUCKET", "").strip()
    if not bucket:
        raise SystemExit("EINVITE_OBJECT_STORAGE_BUCKET is required")
    try:
        import boto3
    except ImportError as exc:
        raise SystemExit("boto3 is required. Run: pip install -r requirements-production.txt") from exc
    kwargs = {"service_name": "s3", "region_name": platform_env("EINVITE_OBJECT_STORAGE_REGION", "auto")}
    if platform_env("EINVITE_OBJECT_STORAGE_ENDPOINT"):
        kwargs["endpoint_url"] = platform_env("EINVITE_OBJECT_STORAGE_ENDPOINT")
    if platform_env("EINVITE_OBJECT_STORAGE_ACCESS_KEY"):
        kwargs["aws_access_key_id"] = platform_env("EINVITE_OBJECT_STORAGE_ACCESS_KEY")
    if platform_env("EINVITE_OBJECT_STORAGE_SECRET_KEY"):
        kwargs["aws_secret_access_key"] = platform_env("EINVITE_OBJECT_STORAGE_SECRET_KEY")
    client = boto3.client(**kwargs)
    prefix = platform_env("EINVITE_OBJECT_STORAGE_PREFIX", "materials/").strip().strip("/")
    uploads = Path(args.uploads)
    db = sqlite3.connect(args.database)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT id,path,mime,size FROM assets ORDER BY created_at").fetchall()
    migrated = skipped = 0
    for row in rows:
        local = uploads / row["path"]
        if not local.is_file():
            print(f"skip missing: {row['path']}")
            skipped += 1
            continue
        key = f"{prefix}/{row['path']}" if prefix else row["path"]
        client.upload_file(str(local), bucket, key, ExtraArgs={"ContentType": row["mime"] or mimetypes.guess_type(local.name)[0] or "application/octet-stream", "CacheControl": "public,max-age=31536000,immutable"})
        print(f"uploaded {row['path']} -> s3://{bucket}/{key}")
        migrated += 1
        if args.delete_local:
            local.unlink()
    db.close()
    print(f"Completed: {migrated} uploaded, {skipped} skipped.")


if __name__ == "__main__":
    main()
