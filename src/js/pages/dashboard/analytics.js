/* src/js/pages/dashboard/analytics.js — v0.68.0 (ROADMAP-v0.54-to-v1.0 §6.5)
 *
 * Creator analytics dashboard page. Replaces the v0.58.0 analytics.js
 * shim with a Canvas 2D charts UI:
 *   - 4 stat cards (total views, unique recipients, avg time, RSVP conversion)
 *   - 30-day line chart with RSVP overlay
 *   - Drop-off funnel (view → rsvp.open → rsvp.submit)
 *   - Top referrers table (masks <3 as "Other")
 *   - Scroll depth bar
 *   - Device split donut
 *   - Country list (top 5)
 *   - Privacy controls (disable analytics / purge / export)
 *   - Live activity (behind analytics_live_enabled feature flag)
 *
 * Honours bilingual EN/KH labels. Honours analyticsEnabled flag
 * (the public page checks this before firing events).
 *
 * Backwards-compatible: the existing #analyticsRoot contract from
 * analytics.html (one big render function) is preserved; we render
 * into the same root.
 */
(function (global) {
  "use strict";
  if (global.EInviteAnalyticsDashboard && global.EInviteAnalyticsDashboard.version >= 680) return;

  var STRINGS = {
    en: {
      title: "Invitation Analytics",
      subtitle: "Performance overview for this invitation.",
      totalViews: "Total views",
      uniqueRecipients: "Unique recipients",
      avgTime: "Average time on page",
      rsvpConversion: "RSVP conversion",
      viewsLast30: "Views — last 30 days",
      rsvpBreakdown: "RSVP breakdown",
      guestCheckin: "Guest check-in",
      publishing: "Publishing",
      funnel: "Drop-off funnel",
      topReferrers: "Top referrers",
      scrollDepth: "Average scroll depth",
      deviceSplit: "Device split",
      countrySplit: "Country",
      liveActivity: "Live activity",
      activeSessions: "active sessions",
      lastEvent: "last activity",
      disableAnalytics: "Disable analytics",
      enableAnalytics: "Enable analytics",
      purgeData: "Delete analytics data",
      exportCsv: "Export as CSV",
      exportJson: "Export as JSON",
      loading: "Loading analytics…",
      unavailable: "Analytics unavailable",
      deltaVsPrev: "vs previous 7 days",
      analyticsOff: "Analytics disabled",
      analyticsOffDesc: "The public page will not send events for this invitation.",
      guestsOnList: "guests on list",
      totalRespondingGuests: "total responding guests",
      historicalPreserved: "Historical responses are preserved",
      rsvpDisabled: "Disabled",
      step: "Step",
      count: "Count",
      percent: "Percent",
      loadingLive: "Checking…",
      liveDisabled: "Live activity is disabled on this server.",
      purgeConfirm: "This permanently deletes every session + event for this invitation. Continue?",
      purged: "Analytics data deleted.",
      disabledToast: "Analytics disabled for this invitation.",
      enabledToast: "Analytics re-enabled.",
    },
    km: {
      title: "ស្ថិតិការអានិត្យកម្ម",
      subtitle: "ទិដ្ឋភាពទូទៅនៃសមិទ្ធិផលនៃការអញ្ជើញនេះ។",
      totalViews: "ចំនួនមើលសរុប",
      uniqueRecipients: "ភ្ញៀវផ្ទាល់ខ្លួន",
      avgTime: "ពេលវេលាមធ្យមនៅលើទំព័រ",
      rsvpConversion: "អត្រាឆ្លើយតប RSVP",
      viewsLast30: "ចំនួនមើល — ៣០ ថ្ងៃចុងក្រោយ",
      rsvpBreakdown: "ស្ថិតិ RSVP",
      guestCheckin: "ការចុះឈ្មោះភ្ញៀវ",
      publishing: "ការបោះពុម្ពផ្សាយ",
      funnel: "ស្ថិតិការបោះបង់",
      topReferrers: "ប្រភពដែលនាំមក",
      scrollDepth: "ជម្រៅអានមធ្យម",
      deviceSplit: "ប្រភេទឧបករណ៍",
      countrySplit: "ប្រទេស",
      liveActivity: "សកម្មភាពផ្ទាល់",
      activeSessions: "សម័យសកម្ម",
      lastEvent: "សកម្មភាពចុងក្រោយ",
      disableAnalytics: "បិទស្ថិតិ",
      enableAnalytics: "បើកស្ថិតិ",
      purgeData: "លុបទិន្នន័យស្ថិតិ",
      exportCsv: "នាំចេញជា CSV",
      exportJson: "នាំចេញជា JSON",
      loading: "កំពុងផ្ទុកស្ថិតិ…",
      unavailable: "ស្ថិតិមិនអាចប្រើបាន",
      deltaVsPrev: "ធៀបនឹង ៧ ថ្ងៃមុន",
      analyticsOff: "ស្ថិតិត្រូវបានបិទ",
      analyticsOffDesc: "ទំព័រសាធារណៈនឹងមិនផ្ញើព្រឹត្តិកម្មសម្រាប់ការអញ្ជើញនេះទេ។",
      guestsOnList: "ភ្ញៀវក្នុងបញ្ជី",
      totalRespondingGuests: "ភ្ញៀវឆ្លើយតបសរុប",
      historicalPreserved: "ការឆ្លើយតបប្រវត្តិសាស្ត្រត្រូវបានរក្សាទុក",
      rsvpDisabled: "បិទ",
      step: "ជំហាន",
      count: "ចំនួន",
      percent: "ភាគរយ",
      loadingLive: "កំពុងពិនិត្យ…",
      liveDisabled: "សកម្មភាពផ្ទាល់ត្រូវបានបិទនៅលើម៉ាស៊ីនមេនេះ។",
      purgeConfirm: "របៀបនេះនឹងលុបសម័យ + ព្រឹត្តិកម្មទាំងអស់សម្រាប់ការអញ្ជើញនេះអ一刀មិនអាចត្រឡប់វិញបាន។ បន្តឬ?",
      purged: "ទិន្នន័យស្ថិតិបានលុបចោលហើយ។",
      disabledToast: "ស្ថិតិបានបិទសម្រាប់ការអញ្ជើញនេះ។",
      enabledToast: "ស្ថិតិបានបើកឡើងវិញ។",
    },
  };

  function locale() {
    var l = (global.EInviteI18N && typeof global.EInviteI18N.getLocale === "function")
      ? global.EInviteI18N.getLocale()
      : (document.documentElement.lang || "en");
    return (l || "en").toLowerCase().indexOf("km") === 0 ? "km" : "en";
  }

  function t(key) { return (STRINGS[locale()] || STRINGS.en)[key] || key; }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function fmtDuration(ms) {
    if (!ms || ms < 1000) return "0s";
    var s = Math.floor(ms / 1000);
    if (s < 60) return s + "s";
    var m = Math.floor(s / 60);
    if (m < 60) return m + "m " + (s % 60) + "s";
    var h = Math.floor(m / 60);
    return h + "h " + (m % 60) + "m";
  }

  function fmtDelta(d) {
    if (d === undefined || d === null) return "";
    var sign = d > 0 ? "+" : "";
    return sign + d + "%";
  }

  function deltaClass(d) {
    if (d === undefined || d === null) return "";
    return d > 0 ? "ei-delta-up" : (d < 0 ? "ei-delta-down" : "ei-delta-flat");
  }

  async function fetchJson(path, opts) {
    var r = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    if (r.status === 204) return null;
    var txt = await r.text();
    var data = txt ? JSON.parse(txt) : {};
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }

  function getInviteId() {
    if (global.EInviteContext && typeof global.EInviteContext.getInvitationId === "function") {
      return global.EInviteContext.getInvitationId();
    }
    var m = location.pathname.match(/invitation[s]?\/([^/]+)/);
    return m ? m[1] : null;
  }

  function renderStatCard(label, value, delta) {
    var deltaHtml = (delta !== undefined && delta !== null)
      ? '<small class="ei-delta ' + deltaClass(delta) + '">' + escapeHtml(fmtDelta(delta)) + " · " + escapeHtml(t("deltaVsPrev")) + '</small>'
      : "";
    return '<div class="ei-stat-card"><span class="ei-stat-label">' + escapeHtml(t(label) || label) + '</span>'
      + '<strong class="ei-stat-value">' + escapeHtml(value) + '</strong>'
      + deltaHtml + '</div>';
  }

  function renderFunnel(steps) {
    if (!steps || !steps.length) return '<p class="ei-empty">' + escapeHtml(t("loading")) + '</p>';
    var max = Math.max.apply(null, steps.map(function (s) { return s.count; })) || 1;
    var rows = steps.map(function (s) {
      var barW = (s.count / max) * 100;
      return '<div class="ei-funnel-row">'
        + '<div class="ei-funnel-label">' + escapeHtml(s.step) + '</div>'
        + '<div class="ei-funnel-bar"><span style="width:' + barW + '%"></span></div>'
        + '<div class="ei-funnel-count">' + escapeHtml(s.count) + ' <small>(' + s.pct + '%)</small></div>'
        + '</div>';
    }).join("");
    return '<div class="ei-funnel">' + rows + '</div>';
  }

  function renderReferrers(refs) {
    if (!refs || !refs.length) return '<p class="ei-empty">—</p>';
    return '<table class="ei-referrer-table"><thead><tr><th>' + escapeHtml(t("topReferrers"))
      + '</th><th>' + escapeHtml(t("count")) + '</th></tr></thead><tbody>'
      + refs.map(function (r) {
          return '<tr><td>' + escapeHtml(r.domain) + '</td><td>' + escapeHtml(r.count) + '</td></tr>';
        }).join("")
      + '</tbody></table>';
  }

  function renderScrollDepth(scroll) {
    if (!scroll) return '<p class="ei-empty">—</p>';
    var avg = scroll.average || 0;
    var buckets = scroll.buckets || [];
    var bars = buckets.map(function (b) {
      return '<div class="ei-scroll-bucket"><span>' + b.pct + '%</span>'
        + '<div class="ei-scroll-bar"><span style="height:' + (b.count > 0 ? 100 : 0) + '%"></span></div>'
        + '<small>' + b.count + '</small></div>';
    }).join("");
    return '<div class="ei-scroll">'
      + '<div class="ei-scroll-avg">' + escapeHtml(t("scrollDepth")) + ': <strong>' + avg + '%</strong></div>'
      + '<div class="ei-scroll-buckets">' + bars + '</div>'
      + '</div>';
  }

  function renderDeviceSplit(devices) {
    if (!devices || !devices.length) return '<p class="ei-empty">—</p>';
    return '<canvas data-chart="donut" data-chart-label="' + escapeHtml(t("deviceSplit")) + '" data-chart-data=\''
      + JSON.stringify(devices.map(function (d) { return { label: d.label, value: d.value, color: d.color }; }))
      + '\'></canvas>';
  }

  function renderCountrySplit(countries) {
    if (!countries || !countries.length) return '<p class="ei-empty">—</p>';
    return '<ul class="ei-country-list">' + countries.map(function (c) {
      return '<li><span class="ei-country-code">' + escapeHtml(c.code) + '</span>'
        + '<span class="ei-country-count">' + escapeHtml(c.count) + '</span></li>';
    }).join("") + '</ul>';
  }

  function renderCharts(analytics) {
    if (!analytics) return;
    var ts = analytics.timeseries || { days: [], views: [], rsvps: [] };
    var lineCanvas = document.getElementById("ei-views-chart");
    if (lineCanvas && global.EInviteCharts) {
      var lineData = ts.days.map(function (d, i) { return { x: d, y: ts.views[i] || 0 }; });
      var overlay = ts.days.map(function (d, i) { return { x: d, y: ts.rsvps[i] || 0 }; });
      global.EInviteCharts.redraw(lineCanvas, "line", {
        data: lineData, overlay: overlay,
        color: "var(--ei-chart-line)", overlayColor: "var(--ei-chart-overlay)",
        label: t("viewsLast30"),
      });
    }
    var devCanvas = document.getElementById("ei-device-chart");
    if (devCanvas && global.EInviteCharts && analytics.deviceSplit) {
      global.EInviteCharts.redraw(devCanvas, "donut", {
        data: analytics.deviceSplit,
        label: t("deviceSplit"),
      });
    }
  }

  async function loadLiveActivity(inviteId) {
    var box = document.getElementById("ei-live-box");
    if (!box) return;
    try {
      var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/live");
      box.innerHTML = '<strong>' + data.activeSessions + '</strong> ' + escapeHtml(t("activeSessions"))
        + ' · ' + escapeHtml(t("lastEvent")) + ': ' + (data.lastEventAt ? new Date(data.lastEventAt).toLocaleTimeString() : "—");
    } catch (e) {
      box.innerHTML = escapeHtml(t("liveDisabled"));
      box.classList.add("ei-live-disabled");
    }
  }

  function setupPrivacyControls(inviteId) {
    var disableBtn = document.getElementById("ei-analytics-disable");
    var purgeBtn = document.getElementById("ei-analytics-purge");
    var exportCsv = document.getElementById("ei-analytics-export-csv");
    var exportJson = document.getElementById("ei-analytics-export-json");
    if (disableBtn) disableBtn.onclick = async function () {
      var enabled = disableBtn.dataset.enabled !== "false";
      try {
        var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/disable", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: !enabled }),
        });
        disableBtn.dataset.enabled = data.analyticsEnabled ? "true" : "false";
        disableBtn.textContent = data.analyticsEnabled ? t("disableAnalytics") : t("enableAnalytics");
        if (global.EInviteToast) global.EInviteToast.show(data.analyticsEnabled ? t("enabledToast") : t("disabledToast"));
      } catch (e) {
        if (global.EInviteToast) global.EInviteToast.show(e.message, "error");
      }
    };
    if (purgeBtn) purgeBtn.onclick = async function () {
      if (!confirm(t("purgeConfirm"))) return;
      try {
        await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics", { method: "DELETE" });
        if (global.EInviteToast) global.EInviteToast.show(t("purged"));
        setTimeout(function () { location.reload(); }, 500);
      } catch (e) {
        if (global.EInviteToast) global.EInviteToast.show(e.message, "error");
      }
    };
    if (exportCsv) exportCsv.onclick = function () {
      location.href = "/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/export?format=csv";
    };
    if (exportJson) exportJson.onclick = function () {
      location.href = "/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/export?format=json";
    };
  }

  async function render(inviteId) {
    var root = document.getElementById("analyticsRoot");
    if (!root) return;
    try {
      var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics");
      var invite = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId));
      var me = await fetchJson("/api/auth/me");
      if (!me.user) { location.href = "dashboard.html"; return; }
      var account = document.getElementById("analyticsAccount");
      if (account) account.textContent = me.user.email;
      var title = document.getElementById("analyticsTitle");
      if (title) {
        var doc = invite.document || {};
        var names = (doc.fields && doc.fields.names) || (doc.meta && doc.meta.title) || "Invitation";
        title.textContent = names + " · " + location.origin + "/i/" + invite.slug;
      }
      var a = data.analytics || {};
      var stats = a.stats || {};
      var deltas = stats.deltas || {};
      var html = '<div class="ei-grid ei-stats-grid">'
        + renderStatCard("totalViews", stats.totalViews || data.totalViews || 0, deltas.totalViews)
        + renderStatCard("uniqueRecipients", stats.uniqueRecipients || 0, deltas.uniqueRecipients)
        + renderStatCard("avgTime", fmtDuration(stats.avgDurationMs || 0), deltas.avgDurationMs)
        + renderStatCard("rsvpConversion", (stats.rsvpConversion || 0) + "%", deltas.rsvpConversion)
        + '</div>'
        + '<section class="ei-card ei-chart-card"><h2>' + escapeHtml(t("viewsLast30")) + '</h2>'
        + '<canvas id="ei-views-chart" data-chart="line" data-chart-label="' + escapeHtml(t("viewsLast30")) + '"></canvas>'
        + '</section>'
        + '<section class="ei-card ei-funnel-card"><h2>' + escapeHtml(t("funnel")) + '</h2>'
        + renderFunnel(a.funnel)
        + '</section>'
        + '<section class="ei-card ei-referrer-card"><h2>' + escapeHtml(t("topReferrers")) + '</h2>'
        + renderReferrers(a.topReferrers)
        + '</section>'
        + '<section class="ei-card ei-scroll-card"><h2>' + escapeHtml(t("scrollDepth")) + '</h2>'
        + renderScrollDepth(a.scrollDepth)
        + '</section>'
        + '<section class="ei-card ei-device-card"><h2>' + escapeHtml(t("deviceSplit")) + '</h2>'
        + '<canvas id="ei-device-chart" data-chart="donut" data-chart-label="' + escapeHtml(t("deviceSplit")) + '"></canvas>'
        + '</section>'
        + '<section class="ei-card ei-country-card"><h2>' + escapeHtml(t("countrySplit")) + '</h2>'
        + renderCountrySplit(a.countrySplit)
        + '</section>'
        + '<section class="ei-card ei-live-card"><h2>' + escapeHtml(t("liveActivity")) + '</h2>'
        + '<div id="ei-live-box" class="ei-live-box">' + escapeHtml(t("loadingLive")) + '</div></section>'
        + '<section class="ei-card ei-privacy-card"><h2>' + escapeHtml(t("disableAnalytics")) + '</h2>'
        + '<div class="ei-privacy-controls">'
        + '<button id="ei-analytics-disable" class="ei-btn" data-enabled="true">' + escapeHtml(t("disableAnalytics")) + '</button>'
        + '<button id="ei-analytics-purge" class="ei-btn ei-btn-danger">' + escapeHtml(t("purgeData")) + '</button>'
        + '<button id="ei-analytics-export-csv" class="ei-btn">' + escapeHtml(t("exportCsv")) + '</button>'
        + '<button id="ei-analytics-export-json" class="ei-btn">' + escapeHtml(t("exportJson")) + '</button>'
        + '</div></section>';
      root.innerHTML = html;
      // Render charts after DOM is updated.
      setTimeout(function () {
        renderCharts(a);
        setupPrivacyControls(inviteId);
        loadLiveActivity(inviteId);
      }, 50);
    } catch (e) {
      root.innerHTML = '<div class="ei-empty"><h2>' + escapeHtml(t("unavailable")) + '</h2><p>' + escapeHtml(e.message) + '</p></div>';
    }
  }

  var api = {
    version: 680,
    render: render,
    strings: STRINGS,
  };
  global.EInviteAnalyticsDashboard = api;

  // Auto-mount if the page has #analyticsRoot + invitation context.
  if (typeof document !== "undefined") {
    var start = function () {
      var root = document.getElementById("analyticsRoot");
      if (!root) return;
      var inviteId = getInviteId();
      if (!inviteId) {
        if (global.EInviteBackend && global.EInviteBackend.message)
          global.EInviteBackend.message(root, "Open analytics from a specific invitation.");
        return;
      }
      if (global.EInviteBackend && global.EInviteBackend.ready) {
        global.EInviteBackend.ready.then(function () {
          if (global.EInviteBackend.isAvailable && !global.EInviteBackend.isAvailable()) {
            global.EInviteBackend.message(root, "Analytics requires the full application server.");
            return;
          }
          render(inviteId);
        });
      } else {
        render(inviteId);
      }
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }

  return api;
})(typeof window !== "undefined" ? window : this);
