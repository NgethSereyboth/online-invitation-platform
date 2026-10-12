# tools/playwright-check — the step-0b browser check, isolated

The brief for this pass required

    node -e "require('playwright').chromium.launch()"

to pass. It could not, for two reasons that are both recorded in
`docs/reviews/analytics-and-unanimity-report.md`: the application does not depend on
Playwright (so the module does not resolve from the repository root) and the
Playwright that was reachable from the Python virtualenv had no browser binary
downloaded. The fix is deliberately **not** a change to the application's
`package.json` / `package-lock.json`, which are owned by the app:

| file | why it is here |
| --- | --- |
| `package.json` | a private, tool-local manifest so `require('playwright')` resolves from this directory |
| `launch-check.mjs` | the check itself: bare `chromium.launch()`, then load a served page and read its title |
| `.gitignore` | keeps the 2-package `node_modules/` out of the repository |

Install (browser goes to `~/.cache/ms-playwright`, outside the repository):

    cd tools/playwright-check
    npm install playwright
    npx playwright install chromium

Run:

    node launch-check.mjs                    # from this directory
    node tools/playwright-check/launch-check.mjs   # from the repository root

Prints `PLAYWRIGHT_LAUNCH_OK version=…`; exits non-zero when the module or the
launch is unavailable. It uses Playwright's own Chromium, not `/usr/bin/google-chrome`,
so a passing check means what the brief asked for rather than the system browser
answering under a different name.
