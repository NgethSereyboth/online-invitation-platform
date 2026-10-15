/*
 * yjs-bridge-v54.js — publishes the vendored Y.js bundle as `window.Y`.
 *
 * vendor/yjs/y.js is an ES module, and the CSP (`script-src 'self'`) forbids
 * inline scripts. This file is concatenated into the page's classic route
 * bundle, so it uses dynamic import() instead of a static `import` statement.
 * The /vendor/yjs/y.js <link rel="modulepreload"> with its SRI hash in the page
 * head makes this import use the integrity-checked copy.
 */
(() => {
  if (window.Y) return;
  import('/vendor/yjs/y.js').then(
    (Y) => {
      window.Y = Y;
      if (typeof Y.Doc !== 'function') {
        console.error('[yjs-bridge] Y.Doc is missing: the vendored Y.js bundle did not load.');
      }
    },
    (error) => console.error('[yjs-bridge] Failed to load Y.js:', error)
  );
})();
