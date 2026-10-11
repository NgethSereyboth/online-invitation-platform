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
  function makeSwitch() {
    var wrap = doc.createElement("div");
    wrap.className = "language-switch";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Select interface language");
    var enBtn = doc.createElement("button");
    enBtn.type = "button"; enBtn.id = "lang-en"; enBtn.setAttribute("data-lang", "en");
    enBtn.setAttribute("aria-label", "Switch to English"); enBtn.textContent = "English";
    var kmBtn = doc.createElement("button");
    kmBtn.type = "button"; kmBtn.id = "lang-km"; kmBtn.setAttribute("data-lang", "km");
    kmBtn.setAttribute("aria-label", "ប្ដូះបើកភាសាខ្មែរ"); kmBtn.textContent = "ខ្មែរ";
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
  function injectSwitches() {
    if (!doc.querySelectorAll) return;
    var headers = doc.querySelectorAll("header");
    var lang = get();
    for (var i = 0; i < headers.length; i++) {
      var h = headers[i];
      if (h.querySelector(".language-switch")) continue;
      var sw = makeSwitch();
      sw.addEventListener("click", function (e) {
        var b = e.target.closest("[data-lang]");
        if (!b) return;
        EInviteI18n.set(b.getAttribute("data-lang"));
      });
      h.appendChild(sw);
      syncSwitch(sw, lang);
    }
    applyFormFields();
  }
  function boot() {
    try { injectSwitches(); } catch (e) { /* keep going */ }
  }

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
      if (get() === lang) { applyHtmlLang(lang); applyFormFields(); return lang; }
      emit(lang);
      applyFormFields();
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
      if (mode === "km") return '<span class="i18n i18n-km khmer-text" lang="km">' + escHTML(kmv) + '</span>';
      return '<span class="i18n i18n-en">' + escHTML(en) + '</span>' +
             '<span class="i18n i18n-km khmer-text" lang="km">' + escHTML(kmv) + '</span>';
    },
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
 * ui/app-shell.js — V55 application shell behaviour (dispatch §2).
 *
 * Deliberately tiny and dependency-free. It owns exactly three things:
 *
 *   1. Rail collapse  — [data-rail-toggle] toggles `body.rail-collapsed`
 *      (persisted in localStorage['einvite-rail-collapsed']).
 *   2. Rail drawer    — below 768px the rail becomes a drawer; [data-drawer-toggle]
 *      toggles `body.rail-open`, which is also closed on Escape, on an outside
 *      click, and on hashchange.
 *   3. Appearance     — [data-theme-toggle] cycles light/dark using the SAME
 *      storage key as core/theme.js (`einvite-theme-mode`), so pages that do not
 *      load modern-ui.js (public.html, checkin.html) still get a working toggle.
 *
 * Accessibility: the toggle buttons carry aria-expanded and the rail is a
 * landmark; nothing here traps focus or blocks pointer events when closed.
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
      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph) glyph.textContent = collapsed ? '»' : '«';
    });
  }
  function applyRailOpen(open) {
    body.classList.toggle('rail-open', !!open);
    document.querySelectorAll('[data-drawer-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!!open));
    });
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
      var glyph = btn.querySelector('[data-theme-glyph]');
      if (glyph) glyph.textContent = next === 'dark' ? '☾' : '☀';
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