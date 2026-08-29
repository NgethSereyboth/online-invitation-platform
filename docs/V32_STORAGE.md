# V32 Storage and Media Architecture

`platform_v32/storage.py` provides local and optional boto3-backed S3-compatible adapters for AWS S3, R2 and MinIO. Object keys are server generated and workspace scoped. Originals remain private. Download URLs are short-lived; upload sessions validate ownership, MIME, size and checksum, and support signed single or multipart upload flows. Object versions, sessions, checksums, status and retention metadata are durable.

The existing material pipeline remains compatible. Expensive raster/media/social/backup jobs are durable, idempotent, cancellable and worker-executable. Local development uses the filesystem and existing upload endpoints without paid credentials.
