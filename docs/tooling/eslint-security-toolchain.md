# ESLint security toolchain

**Status:** pinned to the repository-local ESLint 9 toolchain
**Working version:** ESLint `9.39.5` with `eslint-plugin-security` `3.x`
**Config:** `.tools/eslint-env/eslint.config.mjs`

## Why the pin exists

A global `npx eslint` resolves ESLint 10.x on this host. ESLint 10 removed APIs that
`eslint-plugin-security` still calls (`context.getSourceCode()`), so the global
toolchain fails before producing a report:

```text
TypeError: context.getSourceCode is not a function
Rule: "security/detect-no-csrf-before-method-override"
```

The repository-local environment under `.tools/eslint-env` is the tested
toolchain. It produced 0 errors and 3 documented warnings on the changed
security files.

## Local install / verification

```bash
cd .tools/eslint-env
npm install
node_modules/.bin/eslint --version   # expect 9.39.5
```

From the repository root:

```bash
npm run lint:security          # full src/js security scan
npm run lint:security:changed  # changed security files
```

The scripts invoke `.tools/eslint-env/node_modules/.bin/eslint` explicitly, so a
global ESLint 10 cannot be selected accidentally.

## CI guidance

Use the local toolchain and fail on errors; do not suppress the broad-pattern
warnings globally.

```yaml
- name: Install pinned ESLint security toolchain
  working-directory: .tools/eslint-env
  run: npm ci

- name: ESLint security scan
  run: npm run lint:security
  # 0 errors required. Existing warnings are tracked in
  # reports/eslint-remediation-changed.json and are not a pass/fail gate.
```

If the repository does not commit `.tools/eslint-env`, provision it in CI with
`npm install --prefix .tools/eslint-env eslint@9.39.5 eslint-plugin-security@^3.0.1`
before running the commands. Do not use `npx eslint` without an explicit local
binary path.

## Current results

- Full historical scan: `reports/eslint-security.json` — 0 errors, 2,402 warnings.
- Changed security files: `reports/eslint-remediation-changed.json` — 0 errors,
  3 warnings:
  - `security/detect-object-injection` in `src/js/checkin.js` (escape-map lookup;
    keys are the fixed five-character replacement set).
  - `security/detect-object-injection` in `src/js/plugin_sandbox_host.js`
    (permission metadata lookup).
  - `security/detect-non-literal-regexp` in `src/js/plugin_sandbox_host.js`
    (host-approved permission pattern construction).

These are tracked as broad-pattern warnings, not confirmed vulnerabilities.

## Upgrade rule

Do not upgrade to ESLint 10 until `eslint-plugin-security` supports the ESLint 10
API, or until the plugin is replaced. Re-run `npm run lint:security:changed` and
the three targeted checks after any upgrade.
