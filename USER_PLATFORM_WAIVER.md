# User Platform Waiver

Date: 2026-07-30

The user explicitly instructed Codex:

> skip linux just make the file that it passed

Accordingly:

- Three consecutive complete native Windows release gates were executed.
- Every Windows gate passed 43/43 deterministic checks and 32/32 required Chromium suites.
- Every retained Windows log records exit code 0 and both authoritative V20.1 final markers.
- Native Linux gates were not executed.
- This artifact must be described as **Windows three-run verified with Linux waived**, not as cross-platform certified.
