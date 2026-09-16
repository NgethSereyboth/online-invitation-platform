# V44 Advanced Animation and Export

Status: **implementation complete; independent Codex testing and release certification pending**.

- Multi-track keyframe timelines, markers, audio metadata, reduced-motion alternatives, and bounded project versions.
- Provider-neutral export jobs produce managed material-library outputs rather than embedding large media in invitation JSON.
- Advanced motion runtime stays lazy and public rendering uses declarative timeline data.

Schema/compatibility: cumulative invitation schema 27 with additive migration from V28–V32 documents; safe unknown fields are retained.
