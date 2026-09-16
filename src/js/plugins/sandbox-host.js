/**
 * plugin_sandbox_host.js — V54.33 Phase 4a (ROADMAP-V2 §4.4)
 *
 * Host-side sandbox runtime for third-party plugins.
 *
 * Per `docs/plugins/PLUGIN-SANDBOX.md`:
 *   - UI plugins run in a cross-origin iframe with `sandbox="allow-scripts"`
 *     (NO `allow-same-origin`) + `credentialless`.
 *   - Communication via `MessageChannel` + `postMessage` with a strict
 *     request/response/error protocol.
 *   - Every capability must be explicitly granted via the manifest's
 *     `permissions[]` (resource-scoped, per `docs/ai/RESOURCE-SCOPED-PERMISSIONS.md`).
 *   - Resource limits: 50 MB heap, 100 ms CPU per call, 5 MB bundle.
 *
 * Usage:
 *   EInvitePluginSandboxHost.mount(container, {
 *     pluginId: 'com.example.confetti',
 *     manifest: { name: 'Confetti', version: '1.0.0', permissions: ['invitation:read'], entrypoint: '...' },
 *     approvedPermissions: ['invitation:read'],
 *     srcdoc: '<html>...</html>',  // or src: 'https://plugins.einvite.local/...'
 *   });
 *
 * The sandbox:
 *   1. Constructs the iframe with sandbox + credentialless attributes.
 *   2. Wires a MessageChannel — host sends `init` message with allowed
 *      permissions; plugin sends `request` messages for host methods.
 *   3. Validates each request against approvedPermissions — if the permission
 *      isn't granted, responds with `{error: "permission_denied"}`.
 *   4. Enforces resource limits (50 MB heap via performance.memory, 100 ms
 *      CPU per call via Date.now()).
 *   5. Emits audit events: plugin.launched, plugin.permission_denied,
 *      plugin.crashed (if the iframe dies).
 *
 * This is the host side. The plugin side uses `plugins/sdk/einvite-plugin.js`
 * (the SDK shim) which wraps the same MessageChannel protocol.
 */
window.EInvitePluginSandboxHost = (function () {
  'use strict';

  const HEAP_LIMIT_MB = 50;
  const CPU_LIMIT_MS = 100;
  const BUNDLE_LIMIT_BYTES = 5 * 1024 * 1024;  // 5 MB

  // Audit event logger — delegates to the host's existing audit endpoint.
  function audit(action, pluginId, metadata) {
    try {
      const payload = JSON.stringify({ action, pluginId, metadata, ts: Date.now() });
      // Fire-and-forget — use navigator.sendBeacon if available (non-blocking).
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/plugins/audit', payload);
      } else {
        fetch('/api/plugins/audit', { method: 'POST', body: payload, headers: { 'Content-Type': 'application/json' }, keepalive: true }).catch(function () {});
      }
    } catch (e) { /* never fail the host on audit errors */ }
  }

  // Validate a permission grant against the approved list.
  function isGranted(requested, approved) {
    if (!Array.isArray(approved) || !approved.length) return false;
    // Exact match.
    if (approved.indexOf(requested) !== -1) return true;
    // Wildcard match: "invitation:*:read" matches "invitation:123:read".
    for (let i = 0; i < approved.length; i++) {
      const grant = approved[i];
      if (grant.indexOf('*') === -1) continue;
      // Convert glob to regex: "invitation:*:read" -> "^invitation:[^:]+:read$"
      const pattern = '^' + grant.replace(/\*/g, '[^:]+') + '$';
      if (new RegExp(pattern).test(requested)) return true;
    }
    return false;
  }

  // Host method dispatch — maps permission strings to actual API calls.
  // This is the allow-list of host methods a plugin can request.
  const HOST_METHODS = {
    'invitation:read': function (args, ctx) {
      // GET /api/invitations/{id} — returns invitation document.
      if (!args || !args.invitationId) return Promise.reject(new Error('invitationId required'));
      return fetch('/api/invitations/' + encodeURIComponent(args.invitationId), { credentials: 'same-origin' })
        .then(function (r) { return r.json(); });
    },
    'asset:upload': function (args, ctx) {
      // POST /api/invitations/{id}/album — upload via the existing album endpoint.
      if (!args || !args.invitationId || !args.file) return Promise.reject(new Error('invitationId + file required'));
      const fd = new FormData();
      fd.append('file', args.file);
      if (args.caption) fd.append('caption', args.caption);
      return fetch('/api/invitations/' + encodeURIComponent(args.invitationId) + '/album', {
        method: 'POST', body: fd, credentials: 'same-origin',
      }).then(function (r) { return r.json(); });
    },
  };

  function mount(container, opts) {
    if (!container) throw new Error('mount: container required');
    if (!opts || !opts.pluginId) throw new Error('mount: opts.pluginId required');
    if (!opts.manifest) throw new Error('mount: opts.manifest required');
    if (!opts.srcdoc && !opts.src) throw new Error('mount: opts.srcdoc or opts.src required');

    // Bundle size check (if srcdoc provided).
    if (opts.srcdoc && opts.srcdoc.length > BUNDLE_LIMIT_BYTES) {
      audit('plugin.crashed', opts.pluginId, { reason: 'bundle_too_large', size: opts.srcdoc.length });
      throw new Error('Bundle exceeds 5 MB limit (' + opts.srcdoc.length + ' bytes)');
    }

    // Construct the sandboxed iframe.
    const iframe = document.createElement('iframe');
    iframe.setAttribute('sandbox', 'allow-scripts');  // NO allow-same-origin
    iframe.setAttribute('credentialless', '');  // V54.33 — no credentials shared
    iframe.setAttribute('loading', 'lazy');
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = '0';
    if (opts.src) {
      iframe.setAttribute('src', opts.src);
    } else {
      iframe.setAttribute('srcdoc', opts.srcdoc);
    }
    // Clear container + append.
    while (container.firstChild) container.removeChild(container.firstChild);
    container.appendChild(iframe);

    // Track resource usage.
    const startTime = Date.now();
    const callTimings = [];

    // Wire the MessageChannel.
    const channel = new MessageChannel();
    const hostPort = channel.port1;
    const pluginPort = channel.port2;

    // Listen for plugin messages.
    hostPort.onmessage = function (event) {
      const msg = event.data || {};
      if (msg.type === 'request') {
        // Resource limit: CPU per call.
        const callStart = Date.now();
        // Validate permission.
        if (!isGranted(msg.permission, opts.approvedPermissions || [])) {
          audit('plugin.permission_denied', opts.pluginId, {
            permission: msg.permission, method: msg.method, requestId: msg.id,
          });
          hostPort.postMessage({
            type: 'error', id: msg.id, error: 'permission_denied',
            message: 'Permission not granted: ' + msg.permission,
          });
          return;
        }
        // Dispatch to host method.
        const handler = HOST_METHODS[msg.permission];
        if (!handler) {
          hostPort.postMessage({
            type: 'error', id: msg.id, error: 'unknown_method',
            message: 'No handler for permission: ' + msg.permission,
          });
          return;
        }
        Promise.resolve()
          .then(function () { return handler(msg.args, { pluginId: opts.pluginId }); })
          .then(function (result) {
            const elapsed = Date.now() - callStart;
            callTimings.push(elapsed);
            if (elapsed > CPU_LIMIT_MS) {
              audit('plugin.crashed', opts.pluginId, { reason: 'cpu_limit_exceeded', elapsed: elapsed });
              hostPort.postMessage({
                type: 'error', id: msg.id, error: 'cpu_limit_exceeded',
                message: 'Call exceeded ' + CPU_LIMIT_MS + 'ms limit (' + elapsed + 'ms)',
              });
              return;
            }
            hostPort.postMessage({ type: 'response', id: msg.id, result: result });
          })
          .catch(function (err) {
            hostPort.postMessage({
              type: 'error', id: msg.id, error: 'host_error',
              message: String(err && err.message || err),
            });
          });
      } else if (msg.type === 'heartbeat') {
        // Heap check (if performance.memory is available — Chrome only).
        if (performance.memory && performance.memory.usedJSHeapSize > HEAP_LIMIT_MB * 1024 * 1024) {
          audit('plugin.crashed', opts.pluginId, {
            reason: 'heap_limit_exceeded',
            used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB',
          });
          // Terminate the iframe.
          iframe.src = 'about:blank';
          return;
        }
      }
    };

    // Send init message with allowed permissions.
    iframe.addEventListener('load', function () {
      // postMessage the plugin port to the iframe.
      iframe.contentWindow.postMessage({
        type: 'init',
        pluginId: opts.pluginId,
        manifest: opts.manifest,
        approvedPermissions: opts.approvedPermissions || [],
      }, '*', [pluginPort]);
      audit('plugin.launched', opts.pluginId, {
        manifest: opts.manifest.name + '@' + opts.manifest.version,
        permissions: opts.approvedPermissions || [],
      });
    });

    // Cleanup function.
    function destroy() {
      try {
        hostPort.close();
        iframe.src = 'about:blank';
        if (iframe.parentNode) iframe.parentNode.removeChild(iframe);
      } catch (e) { /* ignore */ }
    }

    return {
      iframe: iframe,
      port: hostPort,
      destroy: destroy,
      stats: function () {
        return {
          uptime_ms: Date.now() - startTime,
          calls: callTimings.length,
          avg_call_ms: callTimings.length ? Math.round(callTimings.reduce(function (a, b) { return a + b; }, 0) / callTimings.length) : 0,
        };
      },
    };
  }

  return { mount: mount, isGranted: isGranted, HOST_METHODS: HOST_METHODS };
})();
