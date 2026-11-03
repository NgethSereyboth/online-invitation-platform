# Round 7 fix plan

1. **BUG-R7-1 — extensionless page aliases.** Add a closed alias map for the 15 top-level
   pages in `src/python/server.py`; resolve through `serve_html_file` only. Add an HTTP
   regression comparing each alias with its `.html` canonical response. Restart the local
   service and verify 200s. **Done.**
2. **GitHub security feedback.** Fix current-tree high/medium causes without suppressions:
   workflow permissions, preflight redaction, scanner temp path, timeline prototype writes,
   HTTP header values, rich-text regex/fallback, and the npm Puppeteer chain. Add focused
   regressions. **Done; local gate passes.**
3. **Rebuild and verify.** Run `build.py all`, compile checks, local security scan, npm
   audit, then restart `einvite-app` and run the full six-width Playwright harness.
   **Done: 225/225, 0 failures.**
4. **Record and commit.** Add this round's record, update `PROGRESS.md` and the security
   triage document, and commit without pushing. **Done.**
