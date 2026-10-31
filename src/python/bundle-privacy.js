;/*! core/i18n.js — EInvite global i18n resolver (FOIL-safe, synchronous)
 * v0.68.3 (ROADMAP-v0.54-to-v1.0 §4.1)
 *
 * Responsibilities:
 *   - Source of truth for UI language = <html lang>.
 *   - Persisted to localStorage key `einvite-lang` ('en'|'km').
 *   - First-visit default: navigator.language starts with `km` -> Khmer, else English.
 *   - Exposes EInviteI18n.get()/set()/t()/langText()/subscribe().
 *   - Backwards-compatible alias EInviteI18N.getLocale() (the 23 page modules already
 *     call window.EInviteI18N?.getLocale?.(); this makes them resolve through the
 *     single resolver instead of falling back to <html lang>).
 *   - Dispatches a synchronous `einvite:lang-changed` CustomEvent on <html> so any
 *     bilingual surface can re-render, and notifies subscribers.
 *   - Injects a bilingual language switch into every <header> (shared header + the
 *     editor app-bar). The switch itself is the one place both languages coexist.
 *   - Walks [data-en][data-km] form fields and sets placeholder/aria-label to the
 *     active language (text labels are handled by the .i18n-en/.i18n-km CSS hiding
 *     convention, no JS needed there).
 *
 * This file is designed to be the FIRST script in every page bundle (it is listed
 * first in earlyScripts and as the first entry of each page's `scripts`). It runs
 * synchronously in <head> (bundles are loaded blocking in <head>) so <html lang> is
 * correct before first paint -> no FOIL flash of both languages. Every public
 * method is guarded so a missing DOM / storage / navigator never throws.
 */
(function (global) {
  "use strict";
  // Guard against double-injection (earlyScripts + per-page scripts, or a future
  // head <script src>).
  if (global.EInviteI18n && global.EInviteI18N && global.EInviteI18N.version) return;
  if (global.EInviteI18n && global.EInviteI18n.version >= 1) return;

  var doc = global.document;
  var STORAGE_KEY = "einvite-lang";

  // --- Language detection ----------------------------------------------------
  function navigatorLang() {
    try {
      var nav = global.navigator && global.navigator.language;
      if (!nav) {
        var langs = global.navigator && global.navigator.languages;
        if (langs && langs.length) nav = langs[0];
      }
      if (String(nav || "").toLowerCase().indexOf("km") === 0) return "km";
    } catch (e) { /* noop */ }
    return "en";
  }
  function htmlLang() {
    try {
      var l = (doc.documentElement && doc.documentElement.lang) || "";
      return String(l).toLowerCase().indexOf("km") === 0 ? "km" : "en";
    } catch (e) { return navigatorLang(); }
  }
  function persistedLang() {
    try {
      if (!global.localStorage) return null;
      var v = global.localStorage.getItem(STORAGE_KEY);
      if (v === "km" || v === "en") return v;
    } catch (e) { /* storage disabled (private mode etc.) */ }
    return null;
  }
  function applyHtmlLang(lang) {
    try {
      if (doc.documentElement && doc.documentElement.lang !== lang) {
        doc.documentElement.lang = lang;
      }
    } catch (e) { /* noop */ }
  }
  function get() {
    // Persisted user choice wins; otherwise the live <html lang> wins (set by the
    // public page observer, the head inline, or the previous switch click); finally
    // the navigator default.
    return persistedLang() || htmlLang();
  }

  // --- Persistence + notification -------------------------------------------
  var subscribers = [];
  function persist(lang) {
    try { global.localStorage && global.localStorage.setItem(STORAGE_KEY, lang); }
    catch (e) { /* storage disabled */ }
  }
  function emit(lang) {
    applyHtmlLang(lang);
    persist(lang);
    try {
      var ev = new global.Event("einvite:lang-changed", { bubbles: true });
      ev.lang = lang;
      doc.dispatchEvent(ev);
    } catch (e) { /* older DOM; fall back to a manual property change */ }
    for (var i = 0; i < subscribers.length; i++) {
      try { subscribers[i](lang, get); } catch (e) { /* keep other subscribers alive */ }
    }
    // Re-sync every injected language switch after a real language change.
    // The `einvite:lang-changed` event re-runs boot()->injectSwitches(), but
    // injectSwitches() skips any <header> that already holds a switch, so
    // without this refresh the buttons' aria-pressed / active class stay frozen
    // at the pre-click value and read as inverted on the now-inactive button.
    // syncSwitch(null, lang) covers all switches across all <header> elements.
    syncSwitch(null, lang);
  }

  // --- Form-field helper (placeholder/aria-label for [data-en][data-km]) ----
  // Text labels (label/span/button/h2/th) are NOT touched here: the
  // `.i18n-en`/`.i18n-km` CSS convention hides the inactive span, so no JS is
  // needed for them and they re-render live on toggle via CSS.
  function applyFormFields(root) {
    var scope = root || doc;
    if (!scope.querySelectorAll) return;
    var lang = get();
    var fields = scope.querySelectorAll("[data-en][data-km]");
    for (var i = 0; i < fields.length; i++) {
      var el = fields[i];
      var tag = el.tagName;
      if (tag !== "INPUT" && tag !== "TEXTAREA" && tag !== "SELECT") continue;
      var en = el.getAttribute("data-en") || "";
      var km = el.getAttribute("data-km") || en;
      var val = lang === "km" ? km : en;
      if (tag === "INPUT" || tag === "TEXTAREA") el.placeholder = val;
      if (el.getAttribute("aria-label") !== null) el.setAttribute("aria-label", val);
      el.setAttribute("lang", lang === "km" ? "km" : "en");
    }
  }

  // --- Language switch injection (into every <header>) ----------------------
  function escHTML(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  // Ids must be unique in a document, and this switch is injected into every <header> — the editor
  // route has six of them (measured: six #lang-km / #lang-en pairs, two of them visible) and
  // dashboard two. Only the first copy claims the ids; every copy carries `data-lang`, which is what
  // the delegated click handler and `syncSwitch` use.
  var switchCount = 0;
  function makeSwitch() {
    var first = switchCount === 0;
    switchCount++;
    var wrap = doc.createElement("div");
    wrap.className = "language-switch";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Select interface language");
    var enBtn = doc.createElement("button");
    enBtn.type = "button"; if (first) enBtn.id = "lang-en"; enBtn.setAttribute("data-lang", "en");
    enBtn.setAttribute("aria-label", "Switch to English"); enBtn.textContent = "English";
    var kmBtn = doc.createElement("button");
    kmBtn.type = "button"; if (first) kmBtn.id = "lang-km"; kmBtn.setAttribute("data-lang", "km");
    kmBtn.setAttribute("aria-label", "ប្ដូះបើកភាសាខ្មែរ"); kmBtn.setAttribute("lang", "km"); kmBtn.textContent = "ខ្មែរ";
    wrap.appendChild(enBtn); wrap.appendChild(kmBtn);
    return wrap;
  }
  function syncSwitch(wrap, lang) {
    var btns = wrap ? wrap.querySelectorAll("[data-lang]") : doc.querySelectorAll(".language-switch [data-lang]");
    for (var i = 0; i < btns.length; i++) {
      var b = btns[i];
      var on = b.getAttribute("data-lang") === lang;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.classList.toggle("active", on);
    }
  }
  // One delegated listener instead of one per injected switch. The editor rebuilds its header
  // (studio topbar, organizeHeader()) after load, so a per-node listener could end up on a node
  // nobody sees while the visible copy — a re-rendered clone of the same markup — had none: clicking
  // ខ្មែរ on index.html changed nothing at all (measured: no state change, no navigation, no visible
  // Khmer copy, while the same button switched languages on the other 15 routes). Delegation
  // survives re-renders and duplicate mounts.
  var delegated = false;
  function onLanguageClick(e) {
    var target = e.target;
    var b = target && target.closest ? target.closest("[data-lang]") : null;
    if (!b || !b.closest || !b.closest(".language-switch")) return;
    e.preventDefault();
    if (global.EInviteI18n && global.EInviteI18n.set) global.EInviteI18n.set(b.getAttribute("data-lang"));
  }
  function injectSwitches() {
    if (!doc.querySelectorAll) return;
    if (!delegated && doc.addEventListener) { doc.addEventListener("click", onLanguageClick); delegated = true; }
    var headers = doc.querySelectorAll("header");
    var lang = get();
    for (var i = 0; i < headers.length; i++) {
      var h = headers[i];
      // Only page chrome gets a switch. A popover or dialog header (workspace launcher, design
      // check, command palette) is a layout heading, not the app bar, and the injected switch
      // landed in the middle of those panels. Clean up any copy injected before this guard.
      if (h.closest("dialog, [role='dialog'], .studio-design-check, .ui-app-launcher-menu, .canvas-header-more-menu, .studio-command-dialog")) {
        var stray = h.querySelector(".language-switch");
        if (stray && stray.parentNode) stray.parentNode.removeChild(stray);
        continue;
      }
      if (h.querySelector(".language-switch")) continue;
      var sw = makeSwitch();
      h.appendChild(sw);
    }
    var all = doc.querySelectorAll(".language-switch");
    for (var j = 0; j < all.length; j++) syncSwitch(all[j], lang);
    applyFormFields();
  }
  function boot() {
    try { injectSwitches(); } catch (e) { /* keep going */ }
    applyOptions();
  }
  // <option> label rewrite: core/i18n-options.js (route-scoped, FB-03).
  function applyOptions() { try { EInviteI18n.applyOptionLabels(); } catch (e) { /* keep going */ } }

  // --- Public resolver -------------------------------------------------------
  var EInviteI18n = {
    version: "1.0",
    STORAGE_KEY: STORAGE_KEY,
    get: get,
    getLocale: get, // backward-compat: EInviteI18N?.getLocale()
    set: function (lang) {
      lang = lang === "km" ? "km" : lang === "en" ? "en" : navigatorLang();
      // If the language isn't actually changing, just (re)sync the DOM attribute
      // and form fields so a forced re-render is idempotent.
      if (get() === lang) { applyHtmlLang(lang); applyFormFields(); applyOptions(); return lang; }
      emit(lang);
      applyFormFields();
      applyOptions();
      return lang;
    },
    // t(key, STRINGS, params?) — STRINGS is a {en:{...},km:{...}} (per-locale) table.
    // Optional {token:value} params are substituted as {token} -> value.
    t: function (key, strings, params) {
      var lang = get();
      var dict = (strings && (strings[lang] || strings.en)) || {};
      var s = dict[key];
      if ((s === undefined || s === null) && strings && strings.en) s = strings.en[key];
      if (s === undefined || s === null) s = key;
      // Function-valued entries (pageLabel(n), pinLabel(n)) are invoked with the
      // caller args; their own template fills the positional values.
      if (typeof s === "function") { try { return s(params); } catch (e) { return key; } }
      s = String(s);
      if (params && typeof params === "object" && !Array.isArray(params)) {
        var keys = Object.keys(params);
        for (var i = 0; i < keys.length; i++) {
          s = s.split("{" + keys[i] + "}").join(String(params[keys[i]] == null ? "" : params[keys[i]]));
        }
      }
      return s;
    },
    // Backward-compatible langText('en','km',mode) inline shape.
    // 'en'/'km' force a language; anything else (both/guest/host/undefined)
    // renders both spans — the live <html lang> / [data-language] CSS hides the
    // inactive one, so the switch updates the page instantly without re-render.
    langText: function (en, km, mode) {
      var kmv = km != null ? km : en;
      if (mode === "en") return '<span class="i18n i18n-en">' + escHTML(en) + '</span>';
      if (mode === "km") return '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
      return '<span class="i18n i18n-en">' + escHTML(en) + '</span>' +
             '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
    },
    // NW-4.1 note: <option> elements cannot hold the .i18n-en/.i18n-km span
    // convention (the HTML parser strips elements inside <option>), so their
    // bilingual labels ride on data-i18n-en / data-i18n-km attributes rewritten
    // by applyOptionLabels — now route-scoped in core/i18n-options.js (FB-03).
    // The guarded calls above resolve to it only on routes that include it.
    subscribe: function (fn) {
      if (typeof fn === "function" && subscribers.indexOf(fn) === -1) subscribers.push(fn);
      return function () {
        var idx = subscribers.indexOf(fn);
        if (idx > -1) subscribers.splice(idx, 1);
      };
    },
  };

  global.EInviteI18n = EInviteI18n;
  // Alias the uppercase name that 15 pre-existing modules already call via
  // `window.EInviteI18N?.getLocale?.()` so they resolve through this resolver.
  global.EInviteI18N = {
    version: "1.0",
    getLocale: get,
    set: EInviteI18n.set,
    t: EInviteI18n.t,
  };

  // Listen for external language changes (e.g. the public page's per-invitation
  // observer writing <html lang> from root[data-language]) so the switch and
  // form fields stay in sync.
  try {
    doc.addEventListener("einvite:lang-changed", boot);
  } catch (e) { /* noop */ }

  // --- Synchronous init (runs in <head> before first paint) ------------------
  var initLang = persistedLang() || navigatorLang();
  applyHtmlLang(initLang);
  applyFormFields();
  if (doc && doc.addEventListener) {
    doc.addEventListener("DOMContentLoaded", boot);
    // If the bundle is injected after parse, DOMContentLoaded may have already
    // fired; boot immediately as a safety net.
    if (doc.readyState === "interactive" || doc.readyState === "complete") {
      boot();
    }
  }
})(typeof window !== "undefined" ? window : this);;/**
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