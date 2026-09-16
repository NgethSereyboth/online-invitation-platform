/**
 * src/js/editor/collab/presence.js — Live cursors with names (ROADMAP §3.5.1, v0.58.0).
 *
 * Extends the existing `collaboration-presence-v52.js` (which already wires
 * the heartbeat / WebSocket / poll fallback) with:
 *   • Y.js awareness protocol for cursor position + identity (when Y.js is
 *     loaded and an awareness instance is provided by the CRDT layer).
 *   • Stable cursor color derived from the user ID (hash → hue).
 *   • Label shows the user's display name, or "Guest" if anonymous.
 *   • Cursors fade after 5s of no movement (CSS opacity transition).
 *   • Throttled to 20Hz (50ms) — coarser than the 80ms v52 default, matching
 *     the ROADMAP requirement.
 *
 * Public API:
 *   EInviteCollabPresence.mount(stage, channel)  → render overlay on a stage
 *   EInviteCollabPresence.attach(channel)         → wire cursor events
 *   EInviteCollabPresence.render(channel)         → re-render remote cursors
 *   EInviteCollabPresence.shareYAwareness(aw)     → wire Y.js awareness (optional)
 *
 * Bilingual EN+KH strings for "Guest" / "editing" labels.
 */
(() => {
  'use strict';
  if (window.EInviteCollabPresence) return;

  const CURSOR_THROTTLE_MS = 50;     // 20 Hz
  const FADE_AFTER_MS = 5000;
  const REAP_INTERVAL_MS = 1000;

  const STRINGS = {
    en: { guest: 'Guest', you: 'You', editing: 'editing', viewing: 'viewing', idle: 'idle' },
    km: { guest: 'ភ្ញៀវ', you: 'អ្នក', editing: 'កំពុងកែសម្រួល', viewing: 'កំពុងមើល', idle: 'ទំនេរ' }
  };

  function locale() {
    const lang = window.EInviteI18N?.getLocale?.() || document.documentElement.lang || 'en';
    return String(lang).toLowerCase().startsWith('km') ? 'km' : 'en';
  }
  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  /** Stable hue (0-360) derived from the actor id. */
  function actorHue(actor) {
    let h = 0;
    for (const ch of String(actor || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return h % 360;
  }
  function actorColor(actor) {
    return `hsl(${actorHue(actor)},65%,55%)`;
  }

  /** Module state. */
  const state = {
    overlay: null,
    channel: null,
    throttleAt: 0,
    awareness: null,
    lastLocalCursor: null
  };

  /** Get-or-create the cursor overlay (#eiCollabCursors) inside #stage. */
  function overlay(stage) {
    if (state.overlay && state.overlay.isConnected) return state.overlay;
    const parent = stage || document.getElementById('stage') || document.body;
    const node = document.createElement('div');
    node.id = 'eiCollabCursors';
    node.className = 'ei-collab-cursors';
    node.setAttribute('aria-hidden', 'true');
    parent.appendChild(node);
    state.overlay = node;
    return node;
  }

  /** Build one remote-cursor DOM node. */
  function buildCursor(item) {
    const node = document.createElement('div');
    node.className = 'ei-collab-cursor';
    node.dataset.actor = String(item.actor || '');
    node.style.setProperty('--collab-color', item.color || actorColor(item.actor));
    const dot = document.createElement('div');
    dot.className = 'ei-collab-cursor__dot';
    const label = document.createElement('span');
    label.className = 'ei-collab-cursor__label';
    label.textContent = item.name || t('guest');
    node.append(dot, label);
    return node;
  }

  function positionCursor(node, item, stage) {
    const rect = stage?.getBoundingClientRect();
    if (!rect || !item.cursor) return;
    const x = Math.max(0, Math.min(1, Number(item.cursor.x) || 0));
    const y = Math.max(0, Math.min(1, Number(item.cursor.y) || 0));
    node.style.left = `${x * rect.width}px`;
    node.style.top = `${y * rect.height}px`;
    node.dataset.lastMove = String(Date.now());
    node.classList.remove('is-faded');
  }

  /** Re-render every remote cursor from the channel's snapshot. */
  function render(channel = state.channel) {
    const stage = document.getElementById('stage');
    const layer = overlay(stage);
    const items = (channel?.list?.() || []);
    const byActor = new Map(items.map((x) => [String(x.actor), x]));
    // Reconcile: add new, update existing, remove stale.
    const existing = new Map([...layer.children].map((n) => [n.dataset.actor, n]));
    for (const [actor, item] of byActor) {
      let node = existing.get(actor);
      if (!node) {
        node = buildCursor(item);
        layer.appendChild(node);
      } else {
        // Update label + color in case they changed.
        const label = node.querySelector('.ei-collab-cursor__label');
        if (label) label.textContent = item.name || t('guest');
        node.style.setProperty('--collab-color', item.color || actorColor(actor));
      }
      positionCursor(node, item, stage);
    }
    // Remove cursors whose actor has left.
    for (const [actor, node] of existing) {
      if (!byActor.has(actor)) node.remove();
    }
  }

  /** Throttled local cursor broadcast. */
  function sendLocalCursor() {
    const ch = state.channel;
    if (!ch) return;
    const now = Date.now();
    if (now - state.throttleAt < CURSOR_THROTTLE_MS) return;
    state.throttleAt = now;
    if (state.lastLocalCursor) ch.setCursor?.(state.lastLocalCursor);
  }

  /** Wire local pointer events to broadcast cursor position. */
  function attachLocalPointer() {
    const stage = document.getElementById('stage');
    if (!stage) return;
    const onMove = (event) => {
      const rect = stage.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width;
      const y = (event.clientY - rect.top) / rect.height;
      if (x < 0 || x > 1 || y < 0 || y > 1) return;
      state.lastLocalCursor = { x, y, pageId: state.channel?.pageId || 'hero' };
      sendLocalCursor();
    };
    document.addEventListener('pointermove', onMove, { passive: true });
  }

  /** Wire to a Y.js awareness instance (optional — only if Y is loaded and
   *  a CRDT channel is configured). The awareness protocol broadcasts small
   *  state updates that don't need to be persisted; we use it for cursor
   *  position + name + color. */
  function shareYAwareness(awareness) {
    if (!awareness || state.awareness === awareness) return;
    state.awareness = awareness;
    const localState = { cursor: state.lastLocalCursor, actor: state.channel?.actor,
      name: state.channel?.name, color: state.channel?.color };
    try { awareness.setLocalState(localState); } catch { /* not a Y.js awareness */ }
    awareness.on?.('change', () => {
      const ch = state.channel;
      if (!ch) return;
      const remote = [];
      awareness.getStates?.().forEach((s, clientID) => {
        if (!s || !s.cursor) return;
        if (s.actor === ch.actor) return; // skip self
        remote.push({ actor: s.actor || String(clientID), name: s.name || t('guest'),
          color: s.color || actorColor(s.actor || clientID), cursor: s.cursor,
          updatedAt: Date.now() });
      });
      if (ch._mergeRemote) ch._mergeRemote(remote);
      render();
    });
  }

  /** Attach to a PresenceChannel (existing V52 type). */
  function attach(channel) {
    if (!channel) return;
    state.channel = channel;
    // Hook the channel's existing events — they fire on cursor/join/leave.
    channel.on?.('cursor', () => render(channel));
    channel.on?.('join', () => render(channel));
    channel.on?.('leave', () => render(channel));
    channel.on?.('selection', () => render(channel));
    channel.on?.('mode', () => render(channel));
    attachLocalPointer();
    render(channel);
    // Reap faded cursors on a 1s tick.
    setInterval(reapFaded, REAP_INTERVAL_MS);
  }

  /** Mark cursors that haven't moved in FADE_AFTER_MS as faded. */
  function reapFaded() {
    const layer = state.overlay;
    if (!layer) return;
    const now = Date.now();
    for (const node of layer.children) {
      const last = Number(node.dataset.lastMove || 0);
      if (last && now - last > FADE_AFTER_MS) node.classList.add('is-faded');
    }
  }

  /** Convenience entry point: join a channel for an invitation id. */
  async function join(invitationId, options = {}) {
    const factory = window.EInviteCollaborationPresenceV52;
    const channel = factory?.join ? await factory.join(invitationId, {
      ...options, name: options.name || window.EInviteContext?.getUserName?.() || '',
      color: options.color || actorColor(window.EInviteCRDTV31?.actorId?.() || 'guest')
    }) : null;
    if (channel) attach(channel);
    return channel;
  }

  /** Mount the overlay on a specific stage element (used when multiple stages
   *  exist or the stage is created later). */
  function mount(stage, channel) {
    overlay(stage);
    if (channel) attach(channel);
    return state.overlay;
  }

  window.EInviteCollabPresence = Object.freeze({
    version: 58, STRINGS, CURSOR_THROTTLE_MS, FADE_AFTER_MS,
    mount, attach, render, shareYAwareness, join, actorColor, actorHue
  });
})();
