(() => {
  'use strict';
  // route-deferred-loader-v15 — injects the per-route deferred chunk after
  // first paint. Bundled at the head of each route bundle, it derives the
  // deferred bundle name from its own <script> URL (bundle-<page>-v15.js →
  // bundle-<page>-deferred-v15.{js,css}) so no HTML/inline script is needed
  // (CSP: script-src 'self'). The deferred chunk is loaded on browser idle or
  // on the first user interaction, whichever comes first, so on-demand
  // modules never delay first paint or the route-weight budget.
  if (window.EInviteDeferredRouteLoaderV15) return;
  // `ready` resolves once the deferred chunk has been evaluated (or failed to
  // load), so consumers that lazily mount a deferred module can retry on it.
  let resolveReady;
  const ready = new Promise((res) => { resolveReady = res; });
  window.EInviteDeferredRouteLoaderV15 = { version: '15', ready };
  const current = document.currentScript;
  const src = (current && current.src) || '';
  const match = /bundle-([A-Za-z0-9_]+)-v15\.js/.exec(src);
  if (!match) { resolveReady(); return; }
  const prefix = src.slice(0, src.lastIndexOf('/') + 1);
  const stem = match[1];
  let started = false;
  function start() {
    if (started) return;
    started = true;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = `${prefix}bundle-${stem}-deferred-v15.css`;
    document.head.appendChild(link);
    const script = document.createElement('script');
    script.src = `${prefix}bundle-${stem}-deferred-v15.js`;
    script.addEventListener('load', () => resolveReady(), { once: true });
    script.addEventListener('error', () => resolveReady(), { once: true });
    document.head.appendChild(script);
  }
  const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 1));
  idle(start, { timeout: 2000 });
  for (const type of ['pointerdown', 'keydown', 'touchstart']) {
    window.addEventListener(type, start, { once: true, passive: true, capture: true });
  }
})();
