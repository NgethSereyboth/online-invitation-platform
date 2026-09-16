/* EInvite sessions UI (ROADMAP-v0.54-to-v1.0 §4.4) — v0.61.3
 *
 * Mounts into the existing account.html page (rendered by
 * account-security-v13.js / bundle-account-v15.js). The container
 * ``#v13Sessions`` already exists; this module augments it with a
 * richer table that shows parsed user-agent + device type and a
 * "Sign out everywhere else" bulk-revoke button.
 *
 * Backend:
 *   GET    /api/account/sessions           → list (parsed UA included)
 *   DELETE /api/account/sessions/{id}      → revoke one (existing)
 *   DELETE /api/account/sessions           → revoke all except current (new)
 *   POST   /api/account/sessions/revoke-all → existing bulk endpoint
 *
 * All strings are bilingual EN+KH.
 */
(function () {
  "use strict";
  if (window.EInviteSessions && window.EInviteSessions.version >= 1) return;

  var STRINGS = {
    en: {
      title: "Active sessions",
      subtitle: "Devices currently signed into your account. Revoke any you don't recognize.",
      currentBadge: "Current",
      deviceColumn: "Device",
      ipColumn: "IP address",
      lastActiveColumn: "Last active",
      actionsColumn: "Actions",
      revoke: "Revoke",
      revokeAll: "Sign out everywhere else",
      revokeAllConfirm: "This will sign out every session except the one you're using now. Continue?",
      revoked: "Session revoked.",
      revokedAll: "{count} session(s) signed out.",
      revokeFailed: "Could not revoke that session.",
      empty: "No active sessions.",
      loading: "Loading…",
      unknownBrowser: "Unknown browser",
      unknownOs: "Unknown OS",
      browserOnOs: "{browser} on {os}",
      mobile: "Mobile",
      tablet: "Tablet",
      desktop: "Desktop",
      justNow: "just now",
      minutesAgo: "{n} min ago",
      hoursAgo: "{n} h ago",
      daysAgo: "{n} d ago",
    },
    km: {
      title: "សម័យការសកម្ម",
      subtitle: "ឧបករណ៍ដែលបានចូលគណនីរបស់អ្នក។ ដកសម័យការណាមួយដែលអ្នកមិនស្គាល់។",
      currentBadge: "បច្ចុប្បន្ន",
      deviceColumn: "ឧបករណ៍",
      ipColumn: "អាសយដ្ឋាន IP",
      lastActiveColumn: "សកម្មចុងក្រោយ",
      actionsColumn: "សកម្មភាព",
      revoke: "ដកសម័យការ",
      revokeAll: "ចាកចេញពីគ្រប់ទីតាំងផ្សេងទៀត",
      revokeAllConfirm: "រឿងនេះនឹងចាកចេញពីគ្រប់សម័យការ លើកលែងតែសម័យការដែលអ្នកកំពុងប្រើ។ បន្តទេ?",
      revoked: "សម័យការត្រូវបានដកចេញ។",
      revokedAll: "សម័យការ {count} ត្រូវបានចាកចេញ។",
      revokeFailed: "មិនអាចដកសម័យការនោះបានទេ។",
      empty: "មិនមានសម័យការសកម្មទេ។",
      loading: "កំពុងផ្ទុក…",
      unknownBrowser: "កម្មវិធីរុករកមិនស្គាល់",
      unknownOs: "ប្រព័ន្ធប្រតិបត្តិការមិនស្គាល់",
      browserOnOs: "{browser} នៅលើ {os}",
      mobile: "ទូរស័ព្ទ",
      tablet: "ថេប្លេត",
      desktop: "កុំព្យូទ័រ",
      justNow: "ឥឡូវនេះ",
      minutesAgo: "{n} នាទីមុន",
      hoursAgo: "{n} ម៉ោងមុន",
      daysAgo: "{n} ថ្ងៃមុន",
    },
  };

  function locale() {
    if (window.EInviteI18N && typeof window.EInviteI18N.getLocale === "function") {
      try { return window.EInviteI18N.getLocale() || "en"; } catch (e) {}
    }
    var lang = (document.documentElement.lang || "en").toLowerCase();
    return lang.indexOf("km") === 0 ? "km" : "en";
  }
  function t(key, vars) {
    var dict = STRINGS[locale()] || STRINGS.en;
    var s = dict[key] || STRINGS.en[key] || key;
    if (vars) for (var k in vars) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  }
  function fmtDevice(session) {
    var pua = session.parsedUserAgent || {};
    var browser = pua.browser && pua.browser !== "Unknown" ? pua.browser : t("unknownBrowser");
    var os = pua.os && pua.os !== "Unknown" ? pua.os : t("unknownOs");
    return t("browserOnOs", { browser: browser, os: os });
  }
  function fmtRelative(ms) {
    if (!ms) return "—";
    var delta = Math.max(0, Date.now() - ms);
    var min = Math.floor(delta / 60000);
    if (min < 1) return t("justNow");
    if (min < 60) return t("minutesAgo", { n: min });
    var hours = Math.floor(min / 60);
    if (hours < 24) return t("hoursAgo", { n: hours });
    return t("daysAgo", { n: Math.floor(hours / 24) });
  }
  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function api(path, opts) {
    opts = opts || {};
    opts.headers = opts.headers || {};
    opts.headers["Accept"] = "application/json";
    if (opts.body) opts.headers["Content-Type"] = "application/json";
    var csrf = (document.cookie.match(/einvite_csrf=([^;]+)/) || [])[1] || "";
    if (csrf && opts.method && opts.method !== "GET") {
      opts.headers["X-CSRF-Token"] = csrf;
    }
    return fetch(path, opts).then(function (r) {
      return r.text().then(function (txt) {
        var data = null;
        try { data = txt ? JSON.parse(txt) : null; } catch (e) {}
        return { status: r.status, data: data, text: txt };
      });
    });
  }

  function render(container, sessions, onRefresh) {
    var html = '<div class="ei-sessions-card">';
    html += '<div class="ei-sessions-header"><div>';
    html += '<h3>' + escapeHtml(t("title")) + '</h3>';
    html += '<p class="ei-sessions-subtitle">' + escapeHtml(t("subtitle")) + '</p>';
    html += '</div>';
    html += '<button type="button" class="ei-sessions-revoke-all">' + escapeHtml(t("revokeAll")) + '</button>';
    html += '</div>';
    if (!sessions || !sessions.length) {
      html += '<p class="ei-sessions-empty">' + escapeHtml(t("empty")) + '</p></div>';
      container.innerHTML = html;
      return;
    }
    html += '<table class="ei-sessions-table"><thead><tr>';
    html += '<th>' + escapeHtml(t("deviceColumn")) + '</th>';
    html += '<th>' + escapeHtml(t("ipColumn")) + '</th>';
    html += '<th>' + escapeHtml(t("lastActiveColumn")) + '</th>';
    html += '<th>' + escapeHtml(t("actionsColumn")) + '</th>';
    html += '</tr></thead><tbody>';
    sessions.forEach(function (s) {
      var isCurrent = !!s.current;
      html += '<tr data-session-id="' + escapeHtml(s.id) + '"' + (isCurrent ? ' class="is-current"' : '') + '>';
      html += '<td><strong>' + escapeHtml(fmtDevice(s)) + '</strong>';
      if (isCurrent) html += ' <span class="ei-session-current-badge">' + escapeHtml(t("currentBadge")) + '</span>';
      html += '</td>';
      html += '<td><code>' + escapeHtml(s.ipAddress || "—") + '</code></td>';
      html += '<td>' + escapeHtml(fmtRelative(s.lastSeenAt || s.createdAt)) + '</td>';
      html += '<td>';
      if (isCurrent) {
        html += '<span class="ei-session-current-note">—</span>';
      } else {
        html += '<button type="button" class="ei-session-revoke-btn">' + escapeHtml(t("revoke")) + '</button>';
      }
      html += '</td></tr>';
    });
    html += '</tbody></table></div>';
    container.innerHTML = html;

    container.querySelectorAll(".ei-session-revoke-btn").forEach(function (btn) {
      btn.onclick = function () {
        var tr = btn.closest("tr");
        var id = tr.getAttribute("data-session-id");
        btn.disabled = true;
        api("/api/account/sessions/" + encodeURIComponent(id), { method: "DELETE" })
          .then(function (res) {
            if (res.status === 200) { tr.remove(); if (onRefresh) onRefresh(); }
            else { btn.disabled = false; alert(t("revokeFailed")); }
          })
          .catch(function () { btn.disabled = false; alert(t("revokeFailed")); });
      };
    });

    var revokeAll = container.querySelector(".ei-sessions-revoke-all");
    if (revokeAll) {
      revokeAll.onclick = function () {
        if (!confirm(t("revokeAllConfirm"))) return;
        revokeAll.disabled = true;
        api("/api/account/sessions", { method: "DELETE" })
          .then(function (res) {
            if (res.status === 200) {
              var n = (res.data && res.data.revoked) || 0;
              alert(t("revokedAll", { count: n }));
              if (onRefresh) onRefresh();
            } else {
              revokeAll.disabled = false;
              alert(t("revokeFailed"));
            }
          })
          .catch(function () { revokeAll.disabled = false; alert(t("revokeFailed")); });
      };
    }
  }

  function mount(container, onRefresh) {
    if (!container) return;
    container.innerHTML = '<p class="ei-sessions-loading">' + escapeHtml(t("loading")) + '</p>';
    api("/api/account/sessions").then(function (res) {
      var sessions = (res.status === 200 && res.data) ? res.data : [];
      render(container, sessions, onRefresh);
    }).catch(function () {
      render(container, [], onRefresh);
    });
  }

  // Auto-mount into #v13Sessions if the account page is loaded.
  function autoMount() {
    var container = document.getElementById("v13Sessions");
    if (container) mount(container, function () { mount(container, null); });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoMount);
  } else {
    autoMount();
  }

  window.EInviteSessions = {
    version: 1,
    mount: mount,
    render: render,
    parseUserAgent: function (ua) {
      // Browser-side mirror of server.parse_user_agent (kept in sync).
      var browser = "Unknown", bv = "";
      var patterns = [
        ["Edge", /Edg(?:e|A|iOS)?\/([\d.]+)/],
        ["Chrome", /Chrome\/([\d.]+)/],
        ["Firefox", /Firefox\/([\d.]+)/],
        ["Safari", /Version\/([\d.]+).*Safari\//],
        ["Opera", /OPR\/([\d.]+)/],
      ];
      for (var i = 0; i < patterns.length; i++) {
        var m = patterns[i][1].exec(ua || "");
        if (m) { browser = patterns[i][0]; bv = (m[1] || "").split(".")[0]; break; }
      }
      var os = "Unknown", osv = "";
      var osPatterns = [
        ["Windows", /Windows NT ([\d.]+)/],
        ["macOS", /Mac OS X ([\d_]+)/],
        ["iOS", /(?:iPhone|iPad).*OS ([\d_]+)/],
        ["Android", /Android ([\d.]+)/],
        ["Chrome OS", /CrOS/],
        ["Linux", /Linux/],
      ];
      for (var j = 0; j < osPatterns.length; j++) {
        var mm = osPatterns[j][1].exec(ua || "");
        if (mm) { os = osPatterns[j][0]; osv = (mm[1] || "").replace(/_/g, "."); break; }
      }
      var dtype = "desktop";
      if (/iPad|Tablet/.test(ua || "")) dtype = "tablet";
      else if (/Mobile|iPhone|Android/.test(ua || "")) dtype = "mobile";
      return { browser: browser, browserVersion: bv, os: os, osVersion: osv, deviceType: dtype };
    },
  };
})();
