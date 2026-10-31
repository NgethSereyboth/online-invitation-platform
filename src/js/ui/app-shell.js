/**
 * ui/app-shell.js — V55 shell: rail collapse, rail drawer, appearance.
 *
 * Collapse persists in localStorage['einvite-rail-collapsed']; the drawer
 * (≤768px) closes on Escape, outside click and hashchange; the theme toggle
 * uses core/theme.js's `einvite-theme-mode`, so pages without modern-ui.js
 * still work. Toggles expose aria-expanded; nothing traps focus.
 */
(function () {
  'use strict';
  if (window.EInviteShell && window.EInviteShell.version >= 55) return;

  var body = document.body;
  var html = document.documentElement;
  var RAIL_KEY = 'einvite-rail-collapsed';
  var THEME_KEY = 'einvite-theme-mode';

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }

  /* --- 1. Rail collapse -------------------------------------------------- */
  function applyRailCollapsed(collapsed) {
    body.classList.toggle('rail-collapsed', !!collapsed);
    document.querySelectorAll('[data-rail-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!collapsed));
      var label = collapsed ? 'Expand navigation' : 'Collapse navigation';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      /* Converted pages rotate an SVG; the editor still uses the text glyph. */
      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph && !glyph.firstElementChild) glyph.textContent = collapsed ? '»' : '«';
    });
  }
  /* QA 2026-10-30 (UI-4): the drawer had no scrim and its off-screen links
     stayed focusable. Add a scrim, mark the closed rail inert on mobile, and
     return focus to the toggle when the drawer closes under the keyboard. */
  function ensureScrim() {
    var scrim = document.querySelector('.app-drawer-scrim');
    if (!scrim) {
      scrim = document.createElement('div');
      scrim.className = 'app-drawer-scrim';
      scrim.setAttribute('aria-hidden', 'true');
      document.body.append(scrim);
    }
    return scrim;
  }
  function applyRailOpen(open) {
    var wasOpen = body.classList.contains('rail-open');
    var rail = document.querySelector('.app-rail');
    body.classList.toggle('rail-open', !!open);
    ensureScrim();
    if (rail) rail.inert = window.matchMedia('(max-width: 768px)').matches && !open;
    document.querySelectorAll('[data-drawer-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!!open));
    });
    if (!open && wasOpen && rail && rail.contains(document.activeElement)) {
      var toggle = document.querySelector('[data-drawer-toggle]');
      if (toggle) toggle.focus();
    }
  }

  /* --- 2. Current page --------------------------------------------------- */
  function markCurrentPage() {
    var here = (location.pathname.split('/').pop() || 'dashboard.html').toLowerCase();
    document.querySelectorAll('.app-rail a[href]').forEach(function (link) {
      var target = link.getAttribute('href').split('#')[0].split('?')[0].toLowerCase();
      if (target && target === here) link.setAttribute('aria-current', 'page');
    });
  }

  /*
   * Pages that show a signed-out flow (dashboard) hide their rail until the
   * signed-in view is revealed, so the login card gets the full canvas. The
   * same flag flips the topbar down to Skeleton B (brand + language + theme).
   */
  function syncAutoRail() {
    var autoRail = document.querySelector('.app-rail[data-rail-auto]');
    var signedIn = document.getElementById('dashboardView');
    var signedInVisible = !signedIn || !signedIn.hidden;
    if (autoRail) autoRail.hidden = !signedInVisible;
    if (signedIn) body.classList.toggle('auth-mode', !signedInVisible);
  }

  function watchAutoRail() {
    var signedIn = document.getElementById('dashboardView');
    if (!signedIn || typeof MutationObserver !== 'function') return;
    new MutationObserver(syncAutoRail).observe(signedIn, { attributes: true, attributeFilter: ['hidden'] });
  }

  /* --- 3. Appearance ----------------------------------------------------- */
  function resolvedTheme() { return html.dataset.theme === 'dark' ? 'dark' : 'light'; }
  function applyTheme(next) {
    html.dataset.theme = next;
    html.dataset.themeMode = next;
    html.style.colorScheme = next;
    write(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(next === 'dark'));
      btn.setAttribute('title', next === 'dark' ? 'Switch to light appearance' : 'Switch to dark appearance');
      /* Both symbols live in the button; the theme attribute on <html> shows the
         right one, so nothing is assigned here. */
    });
  }

  /* --- Wiring ------------------------------------------------------------ */
  document.addEventListener('click', function (event) {
    var railToggle = event.target.closest('[data-rail-toggle]');
    if (railToggle) {
      var collapsed = !body.classList.contains('rail-collapsed');
      applyRailCollapsed(collapsed);
      write(RAIL_KEY, collapsed ? '1' : '0');
      return;
    }
    var drawerToggle = event.target.closest('[data-drawer-toggle]');
    if (drawerToggle) { applyRailOpen(!body.classList.contains('rail-open')); return; }
    var themeToggle = event.target.closest('[data-theme-toggle]');
    if (themeToggle) { applyTheme(resolvedTheme() === 'dark' ? 'light' : 'dark'); return; }
    /* Outside click closes the mobile drawer but never the desktop rail. */
    if (body.classList.contains('rail-open') && !event.target.closest('.app-rail')) applyRailOpen(false);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && body.classList.contains('rail-open')) applyRailOpen(false);
  });
  window.addEventListener('hashchange', function () { applyRailOpen(false); });
  window.addEventListener('resize', function () { if (innerWidth > 768) applyRailOpen(false); });

  function init() {
    markCurrentPage();
    applyRailCollapsed(read(RAIL_KEY) === '1');
    applyRailOpen(false);
    syncAutoRail();
    watchAutoRail();
    applyTheme(read(THEME_KEY) === 'dark' ? 'dark' : 'light');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();

  window.EInviteShell = Object.freeze({
    version: 55,
    collapseRail: applyRailCollapsed,
    openRail: applyRailOpen,
    syncAutoRail: syncAutoRail,
    setTheme: applyTheme
  });
})();

/*
 * PW-13 / UI-3: at ≤600 the topbar carried brand, launcher, Admin, Designer
 * workspace, appearance, drawer, account and both language pills on one
 * non-wrapping row (740px of content in a 390px bar), so the language switch
 * painted past the viewport.
 *
 * The CSS route is blocked: app-shell.css is inside @layer components, and every
 * unlayered sheet that repeats `body:not(.guest) > header` beats it — including
 * the generated route bundle, which concatenates sources in manifest order. A
 * deterministic shell hook keeps the wrap correct at any width without another
 * !important and without depending on which sheet happens to load last.
 */
(() => {
  'use strict';
  if (document.body.classList.contains('guest')) return;
  // The app bar is a direct child of body on the shell routes, but a wrapper
  // (#app) on some pages; look for it either way and never pick a dialog header.
  const header = [...document.querySelectorAll('body > header, body > #app > header, body > .app > header')]
    .find((node) => !node.closest('dialog')) || null;
  if (!header) return;
  header.dataset.appShellWrap = '1';
  const NARROW = 600;
  // UX-1 keeps the bar ≤96px at ≤400. Two comfortable 44px rows plus 6px of
  // padding is the only arithmetic that fits without shrinking tap targets.
  const TIGHT = 400;
  // At 320 the Khmer brand + page cluster + language pills cannot share 304px
  // even on two rows. Below 360 the brand text yields its width to them.
  const COMPACT = 360;
  const HEADER_PROPS = ['flexWrap', 'height', 'minHeight', 'overflow', 'rowGap'];
  const LEFT_PROPS = ['flex', 'maxWidth', 'maxHeight', 'minWidth', 'overflow'];
  const RIGHT_PROPS = ['order', 'flex', 'minWidth', 'height', 'maxHeight', 'alignItems', 'overflow'];
  const SWITCH_PROPS = ['flex', 'order', 'justifyContent', 'margin', 'background', 'border', 'boxShadow', 'padding', 'height', 'alignItems'];
  const clear = (node, props) => props.forEach((key) => { node.style[key] = ''; });
  function sync() {
    const narrow = window.innerWidth <= NARROW;
    const tight = window.innerWidth <= TIGHT;
    const compact = window.innerWidth <= COMPACT;
    const langSwitch = header.querySelector(':scope > .language-switch');
    const left = header.querySelector(':scope > .app-topbar-left');
    const right = header.querySelector(':scope > .app-topbar-right');
    if (!narrow) {
      clear(header, HEADER_PROPS);
      if (left) clear(left, LEFT_PROPS);
      if (right) clear(right, RIGHT_PROPS);
      if (langSwitch) clear(langSwitch, SWITCH_PROPS);
      header.style.removeProperty('--shell-topbar-pad');
      header.style.removeProperty('--shell-topbar-gap');
      return;
    }
    header.style.flexWrap = 'wrap';
    header.style.height = 'auto';
    header.style.minHeight = '56px';
    header.style.overflow = 'visible';
    header.style.rowGap = tight ? '0' : '4px';
    if (tight) {
      // The unlayered narrow-header rule wins padding/gap with !important; it
      // reads these variables, so the hook can compress the bar without adding
      // a second !important. Two rows of 44–48 plus the 1px border stay ≤95.
      header.style.setProperty('--shell-topbar-pad', '0px 8px');
      header.style.setProperty('--shell-topbar-gap', '0px');
      // Row 1: rail toggle + brand + theme + drawer. Row 2: language + the
      // page cluster. A half-width brand forces exactly that split instead of
      // a third row on the Khmer templates page.
      if (left) {
        left.style.flex = compact ? '0 0 auto' : '1 1 50%';
        left.style.maxWidth = compact ? '44px' : '50%';
        left.style.maxHeight = '44px';
        left.style.minWidth = '0';
        left.style.overflow = 'hidden';
      }
      // An empty right cluster (dashboard hides it) must not claim a flex line:
      // giving it a height created a blank row between the brand and language rows.
      if (right && right.getBoundingClientRect().width > 0) {
        right.style.order = compact ? '0' : '20';
        right.style.flex = '0 1 auto';
        right.style.minWidth = '0';
      } else if (right) {
        clear(right, RIGHT_PROPS);
        right.style.order = '0';
        // An empty cluster still claimed a 44 px flex line; hide it entirely so
        // the bar is brand row + language row, not three rows.
        right.style.display = 'none';
      }
    } else {
      header.style.removeProperty('--shell-topbar-pad');
      header.style.removeProperty('--shell-topbar-gap');
      if (left) clear(left, LEFT_PROPS);
      if (right) { clear(right, RIGHT_PROPS); right.style.order = '0'; right.style.display = ''; }
    }
    if (langSwitch) {
      langSwitch.style.order = '20';
      langSwitch.style.justifyContent = 'flex-end';
      langSwitch.style.margin = '0';
      langSwitch.style.padding = '0';
      langSwitch.style.background = 'transparent';
      langSwitch.style.border = '0';
      langSwitch.style.boxShadow = 'none';
      langSwitch.style.flex = tight && !compact ? '0 0 auto' : '1 0 100%';
    }
  }
  sync();
  // The language switch is injected after this script on some routes (it had no
  // inline style at all in the first measurement). Re-sync when it lands, not
  // only on the next window resize.
  new MutationObserver(sync).observe(header, { childList: true });
  window.addEventListener('load', sync, { once: true });
  let timer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(timer);
    timer = setTimeout(sync, 120);
  });
})();
