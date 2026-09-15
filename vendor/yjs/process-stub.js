// vendor/yjs/process-stub.js — V54.30 Phase 4b vendored
//
// Minimal browser-side stub for the /node/process.mjs import that esm.sh's
// Y.js bundle references. lib0 (bundled into y.js) only uses process for
// Node-side detection (process.env, process.argv, process.stdout.isTTY,
// process.release.name) — an empty object makes all those probes return
// undefined, which lib0 handles gracefully by falling back to browser
// defaults.
//
// The file extension is `.js` (NOT `.mjs`) so the server's
// public_static_path() allowlist permits serving it (see download.sh
// comment block above for the rationale). ES modules can have any
// extension — the browser uses the response's Content-Type header
// (text/javascript) to determine module vs. classic, not the suffix.
//
// Do NOT add real Node.js polyfills here. If a future Y.js bump genuinely
// requires a polyfill, vendored the polyfill separately and update this stub.
export default {};
