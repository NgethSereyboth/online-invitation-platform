/**
 * eInvite Plugin SDK — host bridge shim.
 *
 * Bilingual README: see plugins/sdk/README.md
 * ឯកសារភាសាខ្មែរ: សូមមើល plugins/sdk/README.md
 *
 * This module is imported by plugins running inside the eInvite sandbox
 * (cross-origin iframe for UI plugins; Web Worker for logic plugins). It
 * provides a small surface for:
 *   - Lifecycle hooks (init, context_changed, locale_changed, suspend, resume, uninstall)
 *   - Host bridge calls (request/response/error via MessageChannel)
 *   - Permission queries (the plugin can ask "do I have permission X?" before
 *     making a request that would otherwise fail with permission_denied)
 *   - Quota queries (remaining heap / cpu / storage)
 *   - Safe logging (rate-limited to 10/sec by the host bridge)
 *
 * This file is intentionally framework-free (no React, no Lodash, no
 * transpilation step). It runs as-is in any modern browser (Chrome 100+,
 * Firefox 100+, Safari 16+). It is documented bilingually per ROADMAP
 * ground rule 5.
 *
 * Companion docs:
 *   - docs/plugins/PLUGIN-SPEC.md      (manifest + permissions)
 *   - docs/plugins/PLUGIN-SIGNING.md   (Ed25519 double-signing)
 *   - docs/plugins/PLUGIN-SANDBOX.md   (sandboxed execution model)
 *   - docs/plugins/MODERATION-PIPELINE.md (moderation + Verified Vendor)
 *
 * Version: 1.0.0  (Phase 4a / V54.6)
 */

(function (global) {
  'use strict';

  if (global.EInvitePlugin) return; // idempotent

  // ─── i18n ────────────────────────────────────────────────────────────
  // EN/KH string table for SDK-internal error messages.
  // Plugins ship their own strings; this is only for the SDK shim itself.
  var STRINGS = {
    not_initialised: {
      en: 'Plugin SDK not initialised. Wait for onReady() before calling host APIs.',
      km: 'Plugin SDK មិនទាន់ចាប់ផ្តើម។ សូមរង់ចាំ onReady() មុននឹងហៅ API របស់ host។'
    },
    channel_closed: {
      en: 'MessageChannel to host is closed. The plugin may have been uninstalled.',
      km: 'Channel ទៅ host ត្រូវបានបិទ។ Plugin ប្រហែលជាត្រូវបានលុប។'
    },
    permission_denied: {
      en: 'Permission denied: the host did not grant "{permission}".',
      km: 'មិនអនុញ្ញាត: host មិនបានផ្តល់ "{permission}"។'
    },
    rate_limited: {
      en: 'Rate limited: too many requests. Retry after {retry_after_ms} ms.',
      km: 'ល្បឿនមានកំណត់: សំណើច្រើនពេក។ សាកល្បងសារជាថ្មីបន្ទាប់ពី {retry_after_ms} ms។'
    },
    cpu_timeout: {
      en: 'CPU timeout: the request exceeded the per-call CPU budget.',
      km: 'CPU អស់ពេល: សំណើបានលើសពេលកំណត់។'
    },
    quota_exceeded: {
      en: 'Quota exceeded: {resource} is at its cap.',
      km: 'Quota លើសកំណត់: {resource} បានដល់កម្រិតអតិបរមា។'
    },
    invalid_args: {
      en: 'Invalid arguments: {detail}',
      km: 'អាគុមេន invalid: {detail}'
    },
    internal: {
      en: 'Internal host error: {detail}',
      km: 'កំហុសខាងក្នុង host: {detail}'
    }
  };

  function t(key, locale, vars) {
    var entry = STRINGS[key] || { en: key, km: key };
    var tmpl = entry[locale] || entry.en;
    if (!vars) return tmpl;
    return tmpl.replace(/\{(\w+)\}/g, function (_, name) {
      return Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : '{' + name + '}';
    });
  }

  // ─── State ───────────────────────────────────────────────────────────
  var state = {
    ready: false,
    port: null,           // MessagePort to the host
    pluginId: null,
    version: null,
    permissions: [],      // approved permissions (intersection of declared + marketplace-approved)
    locale: 'en',
    context: {},          // invitation context
    pending: new Map(),   // id → { resolve, reject, started_at }
    seq: 0,
    hooks: {
      onReady: [],
      onContextChanged: [],
      onLocaleChanged: [],
      onSuspend: [],
      onResume: [],
      onUninstall: []
    }
  };

  // ─── Helpers ─────────────────────────────────────────────────────────
  function genId() {
    // crypto.randomUUID is available in secure contexts (the sandbox origin
    // is https://plugins.einvite.local, which is a secure context).
    if (global.crypto && global.crypto.randomUUID) return global.crypto.randomUUID();
    // Fallback for older browsers.
    return 'p-' + Date.now().toString(36) + '-' + (state.seq++).toString(36) + '-' +
      Math.random().toString(36).slice(2, 8);
  }

  function fail(msg) {
    if (state.hooks.onUninstall && state.hooks.onUninstall.length) {
      try { state.hooks.onUninstall.forEach(function (fn) { try { fn({ reason: msg }); } catch (_) {} }); } catch (_) {}
    }
    // The sandbox cannot itself close the iframe; the host will tear it down
    // when the parent process sees the channel is closed. We just stop
    // accepting new requests.
    state.ready = false;
  }

  // ─── Host bridge ─────────────────────────────────────────────────────
  function callHost(method, args, permission) {
    return new Promise(function (resolve, reject) {
      if (!state.ready || !state.port) {
        reject(new Error(t('not_initialised', state.locale)));
        return;
      }
      var id = genId();
      var msg = {
        type: 'einvite.plugin.request',
        id: id,
        method: method,
        args: args || {},
        permission: permission || null
      };
      var watchdog = setTimeout(function () {
        if (state.pending.has(id)) {
          state.pending.delete(id);
          reject(new Error(t('cpu_timeout', state.locale)));
        }
      }, 5000); // 5s default; the host enforces a tighter per-call CPU budget (default 100ms)

      state.pending.set(id, {
        resolve: function (v) { clearTimeout(watchdog); resolve(v); },
        reject: function (e) { clearTimeout(watchdog); reject(e); },
        started_at: Date.now()
      });
      try {
        state.port.postMessage(msg);
      } catch (e) {
        clearTimeout(watchdog);
        state.pending.delete(id);
        reject(new Error(t('channel_closed', state.locale)));
      }
    });
  }

  function handleMessage(event) {
    var data = event.data;
    if (!data || typeof data !== 'object') return;
    if (data.type === 'einvite.plugin.init') {
      state.pluginId = data.plugin_id;
      state.version = data.version;
      state.permissions = data.permissions || [];
      state.locale = data.locale || 'en';
      state.context = data.invitation_context || {};
      state.port = event.target || event.source; // MessagePort from init event
      state.ready = true;
      // notify hooks
      state.hooks.onReady.forEach(function (fn) {
        try { fn({ pluginId: state.pluginId, version: state.version, locale: state.locale, context: state.context }); }
        catch (e) { console.error('[einvite-plugin] onReady hook failed:', e); }
      });
      return;
    }
    if (data.type === 'einvite.plugin.response') {
      var entry = state.pending.get(data.id);
      if (!entry) return;
      state.pending.delete(data.id);
      if (data.ok) entry.resolve(data.result);
      else entry.reject(new Error(mapHostError(data.error)));
      return;
    }
    if (data.type === 'einvite.plugin.error') {
      var e = state.pending.get(data.id);
      if (!e) return;
      state.pending.delete(data.id);
      e.reject(new Error(mapHostError(data.error)));
      return;
    }
    // Lifecycle notifications (fire-and-forget from the host)
    if (data.type === 'einvite.plugin.context_changed') {
      state.context = data.context || state.context;
      state.hooks.onContextChanged.forEach(function (fn) { try { fn(state.context); } catch (e) {} });
      return;
    }
    if (data.type === 'einvite.plugin.locale_changed') {
      state.locale = data.locale || state.locale;
      state.hooks.onLocaleChanged.forEach(function (fn) { try { fn(state.locale); } catch (e) {} });
      return;
    }
    if (data.type === 'einvite.plugin.suspend') {
      state.hooks.onSuspend.forEach(function (fn) { try { fn({}); } catch (e) {} });
      return;
    }
    if (data.type === 'einvite.plugin.resume') {
      state.hooks.onResume.forEach(function (fn) { try { fn({}); } catch (e) {} });
      return;
    }
    if (data.type === 'einvite.plugin.uninstall') {
      state.hooks.onUninstall.forEach(function (fn) { try { fn({}); } catch (e) {} });
      state.ready = false;
      state.port = null;
      return;
    }
  }

  function mapHostError(err) {
    if (!err) return 'unknown error';
    var code = err.code || 'internal';
    var vars = {};
    if (err.required_permission) vars.permission = err.required_permission;
    if (err.retry_after_ms) vars.retry_after_ms = err.retry_after_ms;
    if (err.resource) vars.resource = err.resource;
    if (err.detail) vars.detail = err.detail;
    if (err.message) vars.detail = err.message;
    return t(code, state.locale, vars);
  }

  // ─── Public API ──────────────────────────────────────────────────────
  var api = {
    version: '1.0.0',

    // ── Lifecycle ──
    onReady: function (fn) { state.hooks.onReady.push(fn); return this; },
    onContextChanged: function (fn) { state.hooks.onContextChanged.push(fn); return this; },
    onLocaleChanged: function (fn) { state.hooks.onLocaleChanged.push(fn); return this; },
    onSuspend: function (fn) { state.hooks.onSuspend.push(fn); return this; },
    onResume: function (fn) { state.hooks.onResume.push(fn); return this; },
    onUninstall: function (fn) { state.hooks.onUninstall.push(fn); return this; },

    // ── Queries ──
    getLocale: function () { return state.locale; },
    getContext: function () { return state.context; },
    hasPermission: function (perm) {
      return state.permissions.indexOf(perm) !== -1;
    },
    getPermissions: function () { return state.permissions.slice(); },

    // ── Host bridge ──
    invitationRead: function (fields) {
      return callHost('invitation.read', { fields: fields || null }, 'invitation:{current}:read');
    },
    invitationUpdate: function (patch) {
      return callHost('invitation.update', { patch: patch }, 'invitation:{current}:edit');
    },
    invitationPublish: function () {
      return callHost('invitation.publish', {}, 'invitation:{current}:publish');
    },
    guestList: function (opts) {
      return callHost('guest.list', opts || {}, 'invitation:{current}:guest:read');
    },
    guestUpdateRsvp: function (guestId, status) {
      return callHost('guest.update_rsvp', { guest_id: guestId, status: status }, 'invitation:{current}:rsvp:update');
    },
    messageSend: function (recipientGuestId, message) {
      return callHost('message.send', { guest_id: recipientGuestId, message: message }, 'invitation:{current}:message:send');
    },
    assetUpload: function (bytes, name, mime) {
      // bytes is a Uint8Array (the host re-encodes to base64 for transport).
      return callHost('asset.upload', { bytes_b64: base64(bytes), name: name, mime: mime }, 'asset:upload');
    },
    assetRead: function (assetId) {
      return callHost('asset.read', { asset_id: assetId }, 'invitation:{current}:materials:read');
    },
    eventRead: function () {
      return callHost('event.read', {}, 'event:{current}:read');
    },
    eventCreateAutomation: function (trigger, action) {
      return callHost('event.create_automation', { trigger: trigger, action: action }, 'event:{current}:automation:create');
    },
    templateInstall: function (templateId) {
      return callHost('template.install', { template_id: templateId }, 'template:install');
    },
    // Generic bridge for plugin-defined methods (rare).
    request: function (method, args, permission) { return callHost(method, args, permission); },

    // ── Implicit capabilities (always available) ──
    getQuota: function () { return callHost('quota.get', {}, null); },
    log: function (level, message, fields) {
      return callHost('log.write', { level: level, message: message, fields: fields || {} }, null);
    }
  };

  // ─── Wire up ─────────────────────────────────────────────────────────
  // In a UI plugin (iframe), messages arrive via window.message event with
  // a MessagePort transferred in the init message. In a logic plugin
  // (Worker), messages arrive via the Worker's onmessage event.
  //
  // We support both by listening on whatever channel is available.
  if (typeof global.addEventListener === 'function') {
    global.addEventListener('message', function (event) {
      // The init message arrives on window (UI plugin) — it transfers a port.
      if (event.data && event.data.type === 'einvite.plugin.init') {
        if (event.ports && event.ports[0]) {
          state.port = event.ports[0];
          state.port.onmessage = handleMessage;
          // re-dispatch the init through handleMessage now that the port is wired.
          handleMessage({ data: event.data, target: state.port });
        }
      } else {
        // For UI plugins: subsequent messages arrive via window.message
        // (host posts to the iframe directly for lifecycle notifications).
        handleMessage({ data: event.data, target: state.port });
      }
    });
  }
  if (typeof global.onmessage !== 'undefined' && typeof global.postMessage === 'function' && typeof self !== 'undefined' && self === global) {
    // Worker context: messages arrive on `self.onmessage`.
    global.onmessage = function (event) {
      if (event.data && event.data.type === 'einvite.plugin.init') {
        if (event.ports && event.ports[0]) {
          state.port = event.ports[0];
          state.port.onmessage = handleMessage;
        }
        handleMessage({ data: event.data, target: state.port });
      } else {
        handleMessage({ data: event.data, target: state.port });
      }
    };
  }

  // ─── Util: base64 ────────────────────────────────────────────────────
  function base64(bytes) {
    // btoa may not be available in Worker context on very old browsers;
    // fall back to a manual implementation.
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var out = '';
    for (var i = 0; i < bytes.length; i += 3) {
      var b0 = bytes[i] || 0, b1 = bytes[i + 1] || 0, b2 = bytes[i + 2] || 0;
      out += chars[b0 >> 2];
      out += chars[((b0 & 3) << 4) | (b1 >> 4)];
      out += (i + 1 < bytes.length) ? chars[((b1 & 15) << 2) | (b2 >> 6)] : '=';
      out += (i + 2 < bytes.length) ? chars[b2 & 63] : '=';
    }
    return out;
  }

  global.EInvitePlugin = Object.freeze(api);
})(typeof self !== 'undefined' ? self : typeof window !== 'undefined' ? window : this);
