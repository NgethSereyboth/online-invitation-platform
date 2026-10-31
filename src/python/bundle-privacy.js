;
























(function (global) {
  "use strict";


  if (global.EInviteI18n && global.EInviteI18N && global.EInviteI18N.version) return;
  if (global.EInviteI18n && global.EInviteI18n.version >= 1) return;

  var doc = global.document;
  var STORAGE_KEY = "einvite-lang";


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



    return persistedLang() || htmlLang();
  }


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






    syncSwitch(null, lang);
  }





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


  function escHTML(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }




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

  function applyOptions() { try { EInviteI18n.applyOptionLabels(); } catch (e) { /* keep going */ } }


  var EInviteI18n = {
    version: "1.0",
    STORAGE_KEY: STORAGE_KEY,
    get: get,
    getLocale: get, // backward-compat: EInviteI18N?.getLocale()
    set: function (lang) {
      lang = lang === "km" ? "km" : lang === "en" ? "en" : navigatorLang();


      if (get() === lang) { applyHtmlLang(lang); applyFormFields(); applyOptions(); return lang; }
      emit(lang);
      applyFormFields();
      applyOptions();
      return lang;
    },


    t: function (key, strings, params) {
      var lang = get();
      var dict = (strings && (strings[lang] || strings.en)) || {};
      var s = dict[key];
      if ((s === undefined || s === null) && strings && strings.en) s = strings.en[key];
      if (s === undefined || s === null) s = key;


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




    langText: function (en, km, mode) {
      var kmv = km != null ? km : en;
      if (mode === "en") return '<span class="i18n i18n-en">' + escHTML(en) + '</span>';
      if (mode === "km") return '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
      return '<span class="i18n i18n-en">' + escHTML(en) + '</span>' +
             '<span class="i18n i18n-km khmer-text" lang="km" lang="km">' + escHTML(kmv) + '</span>';
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


  global.EInviteI18N = {
    version: "1.0",
    getLocale: get,
    set: EInviteI18n.set,
    t: EInviteI18n.t,
  };




  try {
    doc.addEventListener("einvite:lang-changed", boot);
  } catch (e) { /* noop */ }


  var initLang = persistedLang() || navigatorLang();
  applyHtmlLang(initLang);
  applyFormFields();
  if (doc && doc.addEventListener) {
    doc.addEventListener("DOMContentLoaded", boot);


    if (doc.readyState === "interactive" || doc.readyState === "complete") {
      boot();
    }
  }
})(typeof window !== "undefined" ? window : this);;







(function () {
  'use strict';
  if (window.EInviteShell && window.EInviteShell.version >= 55) return;

  var body = document.body;
  var html = document.documentElement;
  var RAIL_KEY = 'einvite-rail-collapsed';
  var THEME_KEY = 'einvite-theme-mode';

  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }


  function applyRailCollapsed(collapsed) {
    body.classList.toggle('rail-collapsed', !!collapsed);
    document.querySelectorAll('[data-rail-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-expanded', String(!collapsed));
      var label = collapsed ? 'Expand navigation' : 'Collapse navigation';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);

      var glyph = btn.querySelector('[data-rail-glyph]');
      if (glyph && !glyph.firstElementChild) glyph.textContent = collapsed ? '»' : '«';
    });
  }



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


  function markCurrentPage() {
    var here = (location.pathname.split('/').pop() || 'dashboard.html').toLowerCase();
    document.querySelectorAll('.app-rail a[href]').forEach(function (link) {
      var target = link.getAttribute('href').split('#')[0].split('?')[0].toLowerCase();
      if (target && target === here) link.setAttribute('aria-current', 'page');
    });
  }






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


  function resolvedTheme() { return html.dataset.theme === 'dark' ? 'dark' : 'light'; }
  function applyTheme(next) {
    html.dataset.theme = next;
    html.dataset.themeMode = next;
    html.style.colorScheme = next;
    write(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(next === 'dark'));
      btn.setAttribute('title', next === 'dark' ? 'Switch to light appearance' : 'Switch to dark appearance');


    });
  }


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













(() => {
  'use strict';
  if (document.body.classList.contains('guest')) return;


  const header = [...document.querySelectorAll('body > header, body > #app > header, body > .app > header')]
    .find((node) => !node.closest('dialog')) || null;
  if (!header) return;
  header.dataset.appShellWrap = '1';
  const NARROW = 600;


  const TIGHT = 400;


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



      header.style.setProperty('--shell-topbar-pad', '0px 8px');
      header.style.setProperty('--shell-topbar-gap', '0px');



      if (left) {
        left.style.flex = compact ? '0 0 auto' : '1 1 50%';
        left.style.maxWidth = compact ? '44px' : '50%';
        left.style.maxHeight = '44px';
        left.style.minWidth = '0';
        left.style.overflow = 'hidden';
      }


      if (right && right.getBoundingClientRect().width > 0) {
        right.style.order = compact ? '0' : '20';
        right.style.flex = '0 1 auto';
        right.style.minWidth = '0';
      } else if (right) {
        clear(right, RIGHT_PROPS);
        right.style.order = '0';


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



  new MutationObserver(sync).observe(header, { childList: true });
  window.addEventListener('load', sync, { once: true });
  let timer = 0;
  window.addEventListener('resize', () => {
    clearTimeout(timer);
    timer = setTimeout(sync, 120);
  });
})();