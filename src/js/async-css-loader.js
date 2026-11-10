(() => {
  'use strict';
  // Async stylesheet activation for the critical-CSS shell. The links are
  // preloaded so the browser starts the request during head parsing; once the
  // response is available this script flips them to rel=stylesheet. Keeping the
  // activation external avoids inline handlers, which the CSP (script-src
  // 'self') would block. Self-hosted stylesheets need no script nonce.
  const pending = new Set(document.querySelectorAll('link[data-async-css]'));
  const activate = (link) => {
    if (!pending.delete(link)) return;
    link.rel = 'stylesheet';
    link.removeAttribute('data-async-css');
  };
  for (const link of pending) {
    link.addEventListener('load', () => activate(link), { once: true });
    // A failed preload should not strand the page without its full stylesheet;
    // rel=stylesheet lets the browser retry through the normal CSS path.
    link.addEventListener('error', () => activate(link), { once: true });
    // The preload can finish before this script is parsed (cache hit). The
    // resource-timing entry is the reliable signal in that case.
    const entry = performance.getEntriesByName(link.href).find((item) => item.responseEnd > 0);
    if (entry) activate(link);
  }
})();
