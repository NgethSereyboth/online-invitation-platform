# Round 8 fix plan

1. Confirm `main` is at `ebb96d4` and only deliberately untracked folders are present. **Done.**
2. Rebuild via `python3 build.py all`, restart `einvite-app`, and compare served and
   source bundle hashes. **Done.**
3. Fetch all open GitHub Dependabot/CodeQL/secret-scanning pages and reconcile each
   advisory against committed pins. **Done: 0 current vulnerable packages.**
4. Run the security scan, npm audit, build check, compileall, all-JS syntax checks, and
   the six-width Playwright sweep from the restarted service. **Done: 225/225.**
5. Record the evidence and owner-held push; commit without pushing. **Done.**
