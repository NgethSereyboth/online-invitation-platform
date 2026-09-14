# V47 Data Merge and Bulk Generation

Status: **implementation complete; independent Codex testing and release certification pending**.

- Bounded source definitions, column mappings, validation metadata, checksums, and row-count limits.
- Idempotent durable bulk jobs create personalized variants without one unbounded browser request.
- Generated variants remain linked to the original structured invitation and source row identity.

Schema/compatibility: cumulative invitation schema 27 with additive migration from V28–V32 documents; safe unknown fields are retained.
