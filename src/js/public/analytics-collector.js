/* src/js/components/analytics-collector.js — v0.67.1 (ROADMAP-v0.54-to-v1.0 §6.2)
 *
 * Client-side analytics SDK. Batches events from the public invitation
 * page and posts them to /api/analytics/events.
 *
 *   - Max 20 events per batch.
 *   - Flush every 10 seconds.
 *   - Flush on visibilitychange to 'hidden'.
 *   - Use navigator.sendBeacon() on unload.
 *   - Use fetch(..., {keepalive: true}) as a fallback.
 *
 * Privacy:
 *   - Session id is a 128-bit hex stored in sessionStorage (resets on
 *     tab close).
 *   - Recipient id is read from the ?g= query param (the opaque guest
 *     id from a personalized invitation link).
 *   - IP is used server-side only to derive country_code + device_type,
 *     then discarded.
 *
 * Honours window.EInviteContext.analyticsEnabled — the public page sets
 * this to false when the host has opted out, and the collector no-ops.
 */
(function (global) {
  "use strict";
  if (global.EInviteAnalyticsCollector && global.EInviteAnalyticsCollector.version >= 671) {
    return global.EInviteAnalyticsCollector;
  }

  var MAX_EVENTS_PER_BATCH = 20;
  var FLUSH_INTERVAL_MS = 10_000; // 10 seconds
  var MAX_PAYLOAD_BYTES = 1024;   // 1 KB cap per event payload (mirrors server)
  var ENDPOINT = "/api/analytics/events";

  function getSessionId() {
    try {
      var sid = sessionStorage.getItem("ei-analytics-session-id");
      if (sid && /^[A-Fa-f0-9]{32,}$/.test(sid)) return sid;
      // Generate a fresh 128-bit hex session id.
      var bytes = new Uint8Array(16);
      (global.crypto && global.crypto.getRandomValues)
        ? global.crypto.getRandomValues(bytes)
        : Array.prototype.forEach.call(bytes, function (_, i) { bytes[i] = Math.floor(Math.random() * 256); });
      sid = Array.prototype.map.call(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
      sessionStorage.setItem("ei-analytics-session-id", sid);
      return sid;
    } catch (e) {
      // sessionStorage may be unavailable (private mode); generate an
      // ephemeral id and continue. We lose session continuity across
      // reloads, but we still fire events.
      return "00000000000000000000000000000000";
    }
  }

  function getInvitationId() {
    if (global.EInviteContext && typeof global.EInviteContext.getInvitationId === "function") {
      var id = global.EInviteContext.getInvitationId();
      if (id) return id;
    }
    // Fall back to the path: /i/{slug} or /api/public/{slug}/...
    var m = location.pathname.match(/\/(?:i|invitations?|api\/public)\/([^/?#]+)/);
    return m ? m[1] : null;
  }

  function getRecipientId() {
    // The guest-link query param is ?g=<opaque id>. We never collect email.
    var m = location.search.match(/[?&]g=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function isAnalyticsEnabled() {
    if (global.EInviteContext && typeof global.EInviteContext.isAnalyticsEnabled === "function") {
      try { return !!global.EInviteContext.isAnalyticsEnabled(); } catch (e) {}
    }
    if (global.EInviteContext && typeof global.EInviteContext.analyticsEnabled === "boolean") {
      return global.EInviteContext.analyticsEnabled;
    }
    // Default to enabled; the server enforces the per-invitation opt-out
    // independently, so even if the client sends events the server
    // will silently drop them.
    return true;
  }

  function truncatePayload(payload) {
    try {
      var s = JSON.stringify(payload || {});
      if (s.length <= MAX_PAYLOAD_BYTES) return JSON.parse(s);
      return { _truncated: s.slice(0, MAX_PAYLOAD_BYTES - 16) + "..." };
    } catch (e) {
      return { _error: "payload_not_serializable" };
    }
  }

  var queue = [];
  var flushTimer = null;
  var unloaded = false;

  function enqueue(eventType, payload) {
    if (!isAnalyticsEnabled()) return;
    var invitationId = getInvitationId();
    if (!invitationId) return;
    if (queue.length >= MAX_EVENTS_PER_BATCH) {
      // Drop the oldest to make room — we never want to back up
      // unbounded memory if the network is unavailable.
      queue.shift();
    }
    queue.push({
      type: eventType,
      ts: Date.now(),
      payload: truncatePayload(payload || {}),
    });
    scheduleFlush();
  }

  function scheduleFlush() {
    if (flushTimer) return;
    flushTimer = setTimeout(function () {
      flushTimer = null;
      flush();
    }, FLUSH_INTERVAL_MS);
  }

  function buildBody() {
    return {
      sessionId: getSessionId(),
      invitationId: getInvitationId(),
      recipientId: getRecipientId(),
      events: queue.slice(0, MAX_EVENTS_PER_BATCH),
    };
  }

  async function flush() {
    if (!queue.length) return;
    if (!isAnalyticsEnabled()) { queue.length = 0; return; }
    var batch = queue.slice(0, MAX_EVENTS_PER_BATCH);
    queue = queue.slice(batch.length);
    var body = JSON.stringify({
      sessionId: getSessionId(),
      invitationId: getInvitationId(),
      recipientId: getRecipientId(),
      events: batch,
    });
    try {
      // Prefer sendBeacon for unload safety; it doesn't get cancelled
      // by tab close. Fall back to fetch with keepalive:true.
      if (unloaded && global.navigator && typeof global.navigator.sendBeacon === "function") {
        var blob = new Blob([body], { type: "application/json" });
        if (global.navigator.sendBeacon(ENDPOINT, blob)) return;
      }
      await fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
        credentials: "same-origin",
        keepalive: true,
      });
    } catch (e) {
      // Network failed; re-queue the events so they get retried on
      // the next flush. Cap to MAX_EVENTS_PER_BATCH * 2 to avoid
      // unbounded growth.
      queue = batch.concat(queue).slice(0, MAX_EVENTS_PER_BATCH * 2);
    }
  }

  // Auto-flush on tab hide / page unload.
  function onVisibilityChange() {
    if (document.visibilityState === "hidden") {
      // Force a flush — the user is leaving or switching tabs.
      flush();
    }
  }
  function onBeforeUnload() {
    unloaded = true;
    flush();
  }
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", onVisibilityChange);
  }
  if (typeof window !== "undefined") {
    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("pagehide", onBeforeUnload);
  }

  var api = {
    version: 671,
    track: enqueue,
    flush: flush,
    getSessionId: getSessionId,
    ENDPOINT: ENDPOINT,
    EVENT_TYPES: [
      "invitation.view",
      "invitation.view.end",
      "invitation.gallery.open",
      "invitation.rsvp.open",
      "invitation.rsvp.submit",
      "invitation.rsvp.abandon",
      "invitation.link.click",
      "invitation.signup.claim",
      "invitation.poll.vote",
      "invitation.album.upload",
      "invitation.gift.claim",
    ],
  };
  global.EInviteAnalyticsCollector = api;

  // Auto-fire invitation.view on script load if we're on a public page.
  if (typeof document !== "undefined") {
    var autoStart = function () {
      if (!isAnalyticsEnabled()) return;
      if (!getInvitationId()) return;
      // Skip if we're on a host-owned dashboard page.
      if (/^\/(dashboard|account|admin|billing|materials|guests|responses|templates|designer|verify|reset|analytics)\.html/.test(location.pathname)) return;
      enqueue("invitation.view", {
        referrer: document.referrer || "",
        viewport: (window.matchMedia && window.matchMedia("(max-width: 768px)").matches) ? "mobile" : "desktop",
      });
      // Track scroll depth + fire invitation.view.end on unload.
      var maxScroll = 0;
      window.addEventListener("scroll", function () {
        var h = document.documentElement;
        var pct = Math.min(100, Math.round((window.scrollY || 0) / Math.max(1, h.scrollHeight - h.clientHeight) * 100));
        if (pct > maxScroll) maxScroll = pct;
      }, { passive: true });
      var sendEnd = function () {
        enqueue("invitation.view.end", {
          duration_ms: 0, // computed server-side from started_at
          scroll_depth_pct: maxScroll,
          max_scroll_pct: maxScroll,
        });
        flush();
      };
      window.addEventListener("pagehide", sendEnd);
      window.addEventListener("beforeunload", sendEnd);
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", autoStart);
    else autoStart();
  }

  return api;
})(typeof window !== "undefined" ? window : this);
