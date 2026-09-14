# V48 Plugin Platform

Status: **implementation complete; independent Codex testing and release certification pending**.

- Declarative manifests, allow-listed permissions, allow-listed extension points, workspace installations, grants, revocation, and compatibility metadata.
- Plugin runtime accepts schemas and product-owned callbacks only; executable HTML, JavaScript, SQL, paths, and arbitrary network destinations are rejected.
- Public plugin blocks render through safe text/data primitives.

Schema/compatibility: cumulative invitation schema 27 with additive migration from V28–V32 documents; safe unknown fields are retained.
