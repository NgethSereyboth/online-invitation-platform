# V19 Advanced Typography Changelog

Release date: 2026-07-28  
Baseline: `e-invitation-platform-stabilized-v18.zip`  
Invitation compatibility: `schemaVersion: 13`

## Added

- Non-destructive text auto-fit that finds the largest font size fitting the current text box.
- Separate persistent maximum and configurable minimum font sizes, allowing text to grow again after content is shortened or the box is enlarged.
- Manual **Fit now** action and live typography status.
- `normal`, `balance`, and `pretty` text wrapping.
- One-, two-, and three-column text layouts with configurable column gap.
- Justified text alignment.
- Automatic Khmer-capable fallback fonts when Khmer characters are present, while retaining the chosen primary font.
- V19 typography persistence through editor state, schema normalization, generated bundles, autosave, reload, undo/redo, preview, and published snapshots.
- Deterministic typography model coverage and a real Chromium typography workflow suite.

## Stabilized

- Layer-row keyboard focus now survives delayed Layers-panel rerenders without a one-frame focus gap.
- Alt/Control/Command layer movement and F2 rename are routed through the remembered layer identity if a rerender temporarily detaches the focused row.
- Deliberate pointer or focus navigation still clears the remembered identity, preventing stale focus from being restored over user intent.

## Compatibility

- Existing V18 invitations render unchanged when the new optional typography fields are absent.
- Invitation `schemaVersion` remains `13`.
- `professional-editor-v17.js/css` names remain for compatibility.
- Generated `bundle-*-v15.js/css`, `route-bundles-v15.json`, and `page-assets-v15.json` names remain for route/cache/deployment compatibility.

## Release gate

The final artifact passed three consecutive Linux executions of:

```text
python release_check.py
```

Every run passed 40 deterministic checks and 18 required browser suites, ending with:

```text
EINVITATION_V19_ALL_REQUIRED_REVIEW_CHECKS_PASSED
EINVITATION_V19_RELEASE_CHECK_PASSED
```

Windows three-run validation remains pending and must be performed with `RUN_V19_RELEASE_CHECK_3X_WINDOWS.ps1`.
