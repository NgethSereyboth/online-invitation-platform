/**
 * editor-core.js — Canvas core for the EInvite studio editor (v54 refactor).
 *
 * This module consolidates the former `workspace-experience-v24.js` into a
 * readable, fully-documented module. It is responsible for the canvas-level
 * interaction surface that surrounds the design document:
 *
 *   • Canvas zoom HUD (bottom-right cluster) + zoom preset popover.
 *   • A floating "selection card" that reports the active selection's size
 *     and rotation without stealing pointer focus.
 *   • Alt-drag duplication of objects (with live preview ghosts).
 *   • Middle-mouse / middle-pointer canvas panning.
 *   • A hover label that names the object under the pointer.
 *   • The "Essentials / All controls" inspector mode toggle, persisted to
 *     localStorage, so advanced chrome can be progressively disclosed.
 *   • Registration of canvas keyboard shortcuts into the command registry.
 *
 * BUG FIXES introduced here (vs. the old v24 module):
 *
 *   1. No auto-font-scaling on resize — while the user is dragging a resize or
 *      rotate handle the TypographyLayoutService auto-fit pass is suppressed
 *      so the configured font size is preserved (see `AutoFitGuard`).
 *   2. No auto-resize on click/selection — selecting an object no longer
 *      triggers a one-shot refit; auto-fit only runs on explicit user intent
 *      (the "Fit" button / a text change), never on a bare selection event.
 *
 * The module is designed to be loaded once, after the editor bridge, command
 * registry, and canvas view controller are available. It is idempotent: a
 * second load is a no-op (guarded by `window.EInviteEditorCore?.version`).
 */
(() => {
  'use strict';

  // Idempotency guard — prevents double-initialisation if the bundle loads
  // this module more than once.
  if (window.EInviteEditorCore?.version >= 54) return;

  /** Editor-core API namespace exposed on `window`. */
  const api = { version: 54, destroy: null };

  // --- External dependencies -------------------------------------------------
  // These globals are provided by earlier bundle modules. We capture them once
  // so the rest of the module reads cleanly.
  const registry = window.EInviteCommandRegistry;
  const bridge = window.EInviteEditorBridge;
  const controller = window.EInviteCanvasViewController;
  const viewport = document.querySelector('#canvasViewport');
  const stage = document.querySelector('#stage');
  const wrap = document.querySelector('.stage-wrap');

  // Bail out silently when the editor chrome is not present on the page (e.g.
  // the module is bundled into a non-editor route). This keeps the bundle safe
  // to include globally.
  if (!registry || !bridge || !controller || !viewport || !stage || !wrap) return;

  // --- Tiny DOM helpers ------------------------------------------------------
  /**
   * Query a single element, scoped to `root` (document by default).
   * @param {string} selector CSS selector.
   * @param {ParentNode} [root=document] Search root.
   * @returns {Element|null}
   */
  const $ = (selector, root = document) => root.querySelector(selector);
  /**
   * Query all matching elements as an array, scoped to `root`.
   * @param {string} selector CSS selector.
   * @param {ParentNode} [root=document] Search root.
   * @returns {Element[]}
   */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /** Listener cleanup stack — every `on()` registration pushes a remover. */
  const cleanup = [];
  /**
   * Attach an event listener and remember how to remove it.
   * @param {EventTarget|null} target Target (null-safe).
   * @param {string} type Event name.
   * @param {EventListenerOrEventListenerObject} fn Handler.
   * @param {AddEventListenerOptions|boolean} [options] Listener options.
   */
  function on(target, type, fn, options) {
    target?.addEventListener?.(type, fn, options);
    cleanup.push(() => target?.removeEventListener?.(type, fn, options));
  }

  /** Module-level mutable state. Kept at the top so the lifecycle is obvious. */
  let hud = null;
  let popover = null;
  let selectionCard = null;
  let hoverBox = null;
  let inspectorToggle = null;
  let inspectorEmpty = null;
  let footerTools = null;
  let contextObserver = null;
  let selectionObserver = null;
  let headerObserver = null;
  let footerObserver = null;
  let resizeObserver = null;
  let raf = 0;
  let destroyed = false;

  /** Remembers the original DOM position of header buttons so they can be
   *  restored when the viewport grows wide enough to show them inline. */
  const headerHomes = new Map();

  // --- Small utilities -------------------------------------------------------
  /** Clamp `v` into `[min,max]`; non-finite values fall back to `min`. */
  const clamp = (v, min, max) => Math.min(max, Math.max(min, Number(v) || 0));

  /**
   * Escape a value for safe insertion into HTML text/attribute contexts.
   * @param {unknown} value
   * @returns {string}
   */
  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /** Deep-clone via the editor schema (falls back to JSON round-trip). */
  const clone = value => window.EInviteEditorSchema?.clone?.(value) ?? JSON.parse(JSON.stringify(value));

  /**
   * Generate a unique identifier with a readable prefix.
   * @param {string} prefix
   * @returns {string}
   */
  function uid(prefix) {
    return `${prefix}-${crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
  }

  /**
   * Resolve the object map for the currently active canvas.
   *
   * The editor supports a "hero" canvas plus numbered design pages. This
   * helper returns the correct `{id: object}` dictionary for whichever
   * canvas is active so command handlers operate on the right scope.
   *
   * @param {object} doc The editor document state.
   * @returns {Record<string, object>}
   */
  function activeMap(doc) {
    const canvas = bridge.getActiveCanvasId?.() || 'hero';
    if (canvas === 'hero') return doc.objects || (doc.objects = {});
    const pageId = String(canvas).replace(/^page:/, '');
    const page = (doc.designPages || []).find(item => String(item.id) === pageId);
    return page ? (page.objects || (page.objects = {})) : (doc.objects || (doc.objects = {}));
  }

  /**
   * Return the DOM elements currently marked as selected on the stage.
   * @returns {Element[]}
   */
  function selectedElements() {
    const ids = new Set(bridge.getSelectedIds?.() || []);
    return $$('.object', stage).filter(el => ids.has(el.dataset.id));
  }

  /**
   * Produce a human-readable type label for an object element, derived from
   * its `layerName` / `objectType` / `type` dataset attributes.
   * @param {Element} el
   * @returns {string}
   */
  function readableType(el) {
    const raw = el?.dataset.layerName || el?.dataset.objectType || el?.dataset.type || 'Object';
    return String(raw).replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  /**
   * Compute the current stage scale (CSS pixels per layout pixel).
   * Used to convert screen-space selection rects back into canvas units.
   * @returns {number}
   */
  function stageScale() {
    const rect = stage.getBoundingClientRect();
    return rect.width / Math.max(1, stage.offsetWidth);
  }

  /**
   * Measure the bounding box of the current selection in canvas units,
   * together with a short label and (for single selections) rotation.
   * @returns {{items:Element[],left:number,top:number,right:number,bottom:number,width:number,height:number,label:string,rotation:number}|null}
   */
  function selectionMetrics() {
    const items = selectedElements();
    if (!items.length) return null;
    const scale = Math.max(0.001, stageScale());
    const rects = items.map(el => el.getBoundingClientRect());
    const left = Math.min(...rects.map(r => r.left));
    const top = Math.min(...rects.map(r => r.top));
    const right = Math.max(...rects.map(r => r.right));
    const bottom = Math.max(...rects.map(r => r.bottom));
    return {
      items,
      left, top, right, bottom,
      width: (right - left) / scale,
      height: (bottom - top) / scale,
      label: items.length > 1 ? `${items.length} objects` : readableType(items[0]),
      rotation: items.length === 1 ? Number(items[0].dataset.rotation || 0) : 0
    };
  }

  // =========================================================================
  // AutoFitGuard — fixes "no auto-font-shrink on resize" & "no auto-resize on
  // click". The TypographyLayoutService refits text whenever it observes a
  // geometry change or a selection change. During an active resize drag and
  // for a single tick after a selection event we suppress that refit so the
  // user's configured font size is honoured.
  // =========================================================================
  const AutoFitGuard = (() => {
    /** When true, the patched scheduler must skip refit work. */
    let suppressed = false;
    /** Pending release timer (we keep suppression briefly after a drag ends
     *  so the final commit does not immediately re-trigger a refit). */
    let releaseTimer = 0;
    /** Original schedule/refit references, captured when we patch the service. */
    let originalSchedule = null;
    let originalRefit = null;
    let patched = false;

    /**
     * Toggle suppression and reflect it on the body so CSS can react.
     * @param {boolean} value
     * @param {string} [reason] Debug label.
     */
    function set(value, reason) {
      suppressed = !!value;
      document.body.classList.toggle('ei-suppress-autofit', suppressed);
      if (reason && window.__EINVITE_DEBUG_AUTOFIT) {
        // eslint-disable-next-line no-console
        console.debug('[AutoFitGuard]', reason, suppressed ? 'suppressed' : 'released');
      }
    }

    /**
     * Suppress for `ms` milliseconds, then auto-release.
     * @param {number} ms
     */
    function suppressFor(ms) {
      clearTimeout(releaseTimer);
      set(true);
      releaseTimer = setTimeout(() => set(false), ms);
    }

    /**
     * Patch the global TypographyLayoutService so its `schedule` and `refit`
     * methods become no-ops while suppression is active. Safe to call before
     * the service exists (it will retry on later selection events).
     */
    function patch() {
      const svc = window.TypographyLayoutService;
      if (!svc || patched) return;
      patched = true;
      // The responsive controller exposes `schedule`; the service exposes
      // `refit`. Patch both shapes defensively.
      if (typeof svc.schedule === 'function' && !svc.__v54Patched) {
        originalSchedule = svc.schedule.bind(svc);
        svc.schedule = function scheduled(items, ...rest) {
          if (suppressed) return; // honour the user's font size during resize/click
          return originalSchedule(items, ...rest);
        };
        svc.__v54Patched = true;
      }
      if (typeof svc.refit === 'function' && !svc.__v54RefitPatched) {
        originalRefit = svc.refit.bind(svc);
        svc.refit = function refit(node, ...rest) {
          if (suppressed) return null;
          return originalRefit(node, ...rest);
        };
        svc.__v54RefitPatched = true;
      }
    }

    return {
      /** Begin suppressing auto-fit (called on resize-handle pointerdown). */
      begin() { clearTimeout(releaseTimer); set(true, 'resize-begin'); },
      /** End suppression, holding it briefly so the commit settles first. */
      end(ms = 320) { suppressFor(ms); },
      /** Suppress for a single tick (called on selection-changed). */
      pulse(ms = 220) { suppressFor(ms); },
      /** Is suppression currently active? */
      get active() { return suppressed; },
      /** Try to patch the global service (idempotent). */
      patch
    };
  })();

  // =========================================================================
  // Canvas HUD (zoom cluster)
  // =========================================================================
  /**
   * Lazily build the bottom-right zoom HUD and wire its buttons.
   * @returns {HTMLDivElement}
   */
  function ensureHud() {
    if (hud) return hud;
    hud = document.createElement('div');
    hud.id = 'v54CanvasHud';
    hud.className = 'v54-canvas-hud';
    hud.setAttribute('aria-label', 'Canvas navigation');
    hud.innerHTML = (
      '<button type="button" data-v54-zoom="out" aria-label="Zoom out">−</button>' +
      '<button type="button" class="v54-zoom-value" data-v54-zoom="menu" aria-haspopup="menu">100%</button>' +
      '<button type="button" data-v54-zoom="in" aria-label="Zoom in">+</button>' +
      '<span></span>' +
      '<button type="button" data-v54-zoom="fit">Fit</button>' +
      '<button type="button" data-v54-zoom="selection">Selection</button>' +
      '<button type="button" data-command-id="workspace.hidePanels" title="Hide or show panels">Focus</button>'
    );
    wrap.append(hud);
    hud.addEventListener('click', event => {
      const action = event.target.closest('[data-v54-zoom]')?.dataset.v54Zoom;
      if (!action) return;
      if (action === 'out') controller.setZoom(controller.zoom - 0.1, { source: 'hud' });
      if (action === 'in') controller.setZoom(controller.zoom + 0.1, { source: 'hud' });
      if (action === 'fit') controller.fit();
      if (action === 'selection') controller.zoomToSelection();
      if (action === 'menu') toggleZoomMenu(event.target);
    });
    return hud;
  }

  /**
   * Lazily build the zoom-preset popover.
   * @returns {HTMLDivElement}
   */
  function ensureZoomMenu() {
    if (popover) return popover;
    popover = document.createElement('div');
    popover.id = 'v54ZoomMenu';
    popover.className = 'v54-zoom-menu';
    popover.hidden = true;
    popover.setAttribute('role', 'menu');
    popover.innerHTML = (
      [.5, .75, 1, 1.25, 1.5, 2]
        .map(value => `<button type="button" role="menuitem" data-v54-preset="${value}">${Math.round(value * 100)}%</button>`)
        .join('') +
      '<hr><button type="button" role="menuitem" data-v54-fit>Fit canvas</button>' +
      '<button type="button" role="menuitem" data-v54-selection>Zoom to selection</button>' +
      '<small>Ctrl/Cmd + wheel to zoom at pointer</small>'
    );
    document.body.append(popover);
    popover.addEventListener('click', event => {
      const preset = event.target.closest('[data-v54-preset]')?.dataset.v54Preset;
      if (preset) controller.setZoom(Number(preset), { source: 'menu' });
      else if (event.target.closest('[data-v54-fit]')) controller.fit();
      else if (event.target.closest('[data-v54-selection]')) controller.zoomToSelection();
      else return;
      closeZoomMenu();
    });
    return popover;
  }

  /**
   * Toggle the zoom popover open/closed, anchored to a button.
   * @param {Element} anchor
   */
  function toggleZoomMenu(anchor) {
    const menu = ensureZoomMenu();
    if (!menu.hidden) return closeZoomMenu();
    const rect = anchor.getBoundingClientRect();
    menu.hidden = false;
    menu.style.left = `${Math.min(innerWidth - menu.offsetWidth - 12, Math.max(12, rect.left - menu.offsetWidth / 2 + rect.width / 2))}px`;
    menu.style.top = `${Math.max(12, rect.top - menu.offsetHeight - 8)}px`;
    menu.querySelector('button')?.focus();
  }

  /** Hide the zoom popover. */
  function closeZoomMenu() { if (popover) popover.hidden = true; }

  // =========================================================================
  // Selection card (floating size/rotation read-out)
  // =========================================================================
  /**
   * Lazily build the selection card and prepend it to the viewport.
   * @returns {HTMLDivElement}
   */
  function ensureSelectionCard() {
    if (selectionCard) return selectionCard;
    selectionCard = document.createElement('div');
    selectionCard.id = 'v54SelectionCard';
    selectionCard.className = 'v54-selection-card';
    selectionCard.hidden = true;
    selectionCard.innerHTML = '<div><small data-v54-page></small><strong data-v54-label></strong></div><span data-v54-metrics></span>';
    viewport.prepend(selectionCard);
    return selectionCard;
  }

  /**
   * Refresh the selection card contents from the current selection. Hidden
   * when nothing is selected.
   */
  function updateSelectionCard() {
    if (destroyed) return;
    const card = ensureSelectionCard();
    const metrics = selectionMetrics();
    card.hidden = !metrics;
    if (!metrics) return;
    const canvasLabel = $('#activeCanvasLabel')?.textContent?.trim() || 'Canvas';
    $('[data-v54-page]', card).textContent = canvasLabel;
    $('[data-v54-label]', card).textContent = metrics.label;
    const rotation = Math.abs(metrics.rotation) > 0.05 ? ` · ${Math.round(metrics.rotation * 10) / 10}°` : '';
    $('[data-v54-metrics]', card).textContent = `${Math.round(metrics.width)} × ${Math.round(metrics.height)}${rotation}`;
    card.classList.toggle('is-multi', metrics.items.length > 1);
  }

  /**
   * Toggle body classes that drive inspector empty-state visibility and
   * update the empty-state copy.
   */
  function updateSelectionState() {
    const selected = selectedElements();
    const hasSelection = selected.length > 0;
    document.body.classList.toggle('v54-has-selection', hasSelection);
    if (inspectorEmpty) {
      inspectorEmpty.hidden = hasSelection;
      const label = inspectorEmpty.querySelector('[data-v54-empty-label]');
      if (label) label.textContent = hasSelection ? 'Selection ready' : 'Select an object to edit its position, style, image, text, and animation.';
    }
  }

  /**
   * Coalesce update work into a single macrotask so rapid selection/mutation
   * bursts do not thrash layout.
   */
  function scheduleUpdate() {
    if (raf) return;
    raf = setTimeout(() => {
      raf = 0;
      updateSelectionState();
      updateSelectionCard();
      updateZoomLabel();
      // NOTE: layoutContextToolbar / header / footer organisation deliberately
      // NOT called here — running them on every selection change is what made
      // the toolbar "jump". They run on install + resize only (see ui-layout).
    }, 0);
  }

  /** Sync the zoom HUD's numeric label + selection button disabled state. */
  function updateZoomLabel() {
    const value = $('.v54-zoom-value', ensureHud());
    if (value) value.textContent = `${Math.round(controller.zoom * 100)}%`;
    ensureHud().querySelector('[data-v54-zoom="selection"]').disabled = !(bridge.getSelectedIds?.() || []).length;
  }

  /**
   * Ctrl/Cmd + wheel zooms the canvas at the pointer location.
   * @param {WheelEvent} event
   */
  function wheelZoom(event) {
    if (!(event.ctrlKey || event.metaKey)) return;
    event.preventDefault();
    event.stopPropagation();
    const factor = Math.exp(-clamp(event.deltaY, -120, 120) * 0.0024);
    controller.setZoom(controller.zoom * factor, { clientX: event.clientX, clientY: event.clientY, source: 'wheel' });
    scheduleUpdate();
  }

  // =========================================================================
  // Alt-drag duplication (with live preview ghosts)
  // =========================================================================
  let duplicateDrag = null;
  let middlePan = null;

  /**
   * Begin an alt-drag duplication gesture. Only the primary button while Alt
   * is held (and no other modifiers) qualifies. Clicking on resize/rotate
   * handles, editable text, or form controls is ignored.
   * @param {PointerEvent} event
   */
  function beginDuplicateDrag(event) {
    if (event.button !== 0 || !event.altKey || event.shiftKey || event.ctrlKey || event.metaKey || duplicateDrag || middlePan) return;
    if (event.target.closest?.('[data-pe-handle],.pe-handle,.pe-rotate,.resize-handle,.rotate-handle,[contenteditable=true],button,input,select,textarea')) return;
    const object = event.target.closest?.('#stage .object');
    if (!object || object.dataset.locked === 'true') return;

    let ids = bridge.getSelectedIds?.() || [];
    if (!ids.includes(object.dataset.id)) { ids = [object.dataset.id]; bridge.select?.(ids); }

    const elements = $$('.object', stage).filter(el => ids.includes(el.dataset.id) && el.dataset.locked !== 'true');
    if (!elements.length) return;

    const sr = stage.getBoundingClientRect();
    const scale = Math.max(0.001, stageScale());
    // Capture each element's starting frame in canvas units once.
    const frames = elements.map(el => {
      const rect = el.getBoundingClientRect();
      return { id: el.dataset.id, x: (rect.left - sr.left) / scale, y: (rect.top - sr.top) / scale, w: rect.width / scale, h: rect.height / scale };
    });
    // Clone each element as a translucent preview ghost.
    const previews = elements.map((el, index) => {
      const preview = el.cloneNode(true);
      preview.dataset.v54DuplicatePreview = '1';
      preview.dataset.id = `preview-${index}`;
      preview.classList.remove('selected', 'multi-selected', 'marquee-hit');
      preview.setAttribute('aria-hidden', 'true');
      preview.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
      stage.append(preview);
      return preview;
    });

    duplicateDrag = { pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, ids, frames, previews, scale, active: false, dx: 0, dy: 0, target: event.target };
    event.target.setPointerCapture?.(event.pointerId);
    document.body.classList.add('v54-alt-duplicating');
    hideHover();
    event.preventDefault();
    event.stopImmediatePropagation();
  }

  /**
   * Move the duplicate-drag preview ghosts. A small dead-zone avoids
   * accidentally duplicating on a plain click.
   * @param {PointerEvent} event
   */
  function moveDuplicateDrag(event) {
    const drag = duplicateDrag;
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const screenDx = event.clientX - drag.startX;
    const screenDy = event.clientY - drag.startY;
    if (!drag.active && Math.hypot(screenDx, screenDy) < 4) return;
    drag.active = true;
    drag.dx = screenDx / drag.scale;
    drag.dy = screenDy / drag.scale;
    drag.previews.forEach(preview => { preview.style.translate = `${drag.dx}px ${drag.dy}px`; });
  }

  /**
   * Walk the group ancestry of each duplicated object so nested groups are
   * cloned alongside their members.
   * @param {object} doc Editor document.
   * @param {string[]} ids Object ids being duplicated.
   * @returns {{all:object,wanted:Set<string>}}
   */
  function sourceGroups(doc, ids) {
    const all = doc.sceneGraph?.groups || {};
    const wanted = new Set();
    ids.forEach(id => {
      let groupId = activeMap(doc)[id]?.groupId || '';
      let guard = 0;
      while (groupId && all[groupId] && guard++ < 50) {
        wanted.add(groupId);
        groupId = all[groupId].parentId || '';
      }
    });
    return { all, wanted };
  }

  /**
   * Commit the duplicate-drag gesture as a single transaction, re-clamping
   * positions to the stage and remapping group ids.
   * @param {object} drag The active duplicate-drag state.
   * @returns {string[]} The new object ids.
   */
  function commitDuplicateDrag(drag) {
    const newIds = [];
    const stageWidth = Math.max(1, stage.offsetWidth);
    const stageHeight = Math.max(1, stage.offsetHeight);
    const idMap = new Map(drag.ids.map(id => [id, uid('obj')]));
    idMap.forEach(id => newIds.push(id));

    bridge.transact?.('Alt-drag duplicate', doc => {
      const map = activeMap(doc);
      const { all, wanted } = sourceGroups(doc, drag.ids);
      const groupMap = new Map([...wanted].map(id => [id, uid('group')]));
      const maxZ = Math.max(0, ...Object.values(map).map(value => Number(value.zIndex) || 0));

      drag.ids.forEach((oldId, index) => {
        const source = map[oldId];
        if (!source) return;
        const next = clone(source);
        const frame = drag.frames[index];
        const newId = idMap.get(oldId);
        const x = clamp(frame.x + drag.dx, 0, Math.max(0, stageWidth - frame.w));
        const y = clamp(frame.y + drag.dy, 0, Math.max(0, stageHeight - frame.h));
        next.left = `${x / stageWidth * 100}%`;
        next.top = `${y / stageHeight * 100}%`;
        next.zIndex = maxZ + index + 1;
        next.legacyId = newId;
        next.groupId = groupMap.get(next.groupId) || '';
        next.parentGroupId = groupMap.get(next.parentGroupId) || '';
        delete next.id;
        map[newId] = next;
      });

      if (wanted.size) {
        doc.sceneGraph = doc.sceneGraph || {};
        doc.sceneGraph.groups = doc.sceneGraph.groups || {};
        [...wanted].forEach(oldId => {
          const group = all[oldId];
          const newId = groupMap.get(oldId);
          doc.sceneGraph.groups[newId] = {
            ...clone(group),
            id: newId,
            parentId: groupMap.get(group.parentId) || '',
            children: (group.children || []).map(child => groupMap.get(child) || idMap.get(child)).filter(Boolean)
          };
        });
      }
    });

    bridge.select?.(newIds);
    window.EInviteFeedback?.toast?.('Duplicated and moved');
    return newIds;
  }

  /**
   * End the duplicate-drag gesture, committing unless `cancel` is set.
   * @param {PointerEvent} event
   * @param {boolean} [cancel=false]
   */
  function endDuplicateDrag(event, cancel = false) {
    const drag = duplicateDrag;
    if (!drag || event.pointerId !== drag.pointerId) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    duplicateDrag = null;
    drag.previews.forEach(preview => preview.remove());
    document.body.classList.remove('v54-alt-duplicating');
    if (drag.active && !cancel) commitDuplicateDrag(drag);
    scheduleUpdate();
  }

  // =========================================================================
  // Middle-button panning
  // =========================================================================
  /**
   * Begin a middle-button canvas pan gesture.
   * @param {PointerEvent} event
   */
  function startMiddlePan(event) {
    if (event.button !== 1) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    middlePan = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, left: viewport.scrollLeft, top: viewport.scrollTop };
    viewport.classList.add('v54-middle-panning');
    viewport.setPointerCapture?.(event.pointerId);
  }

  /** Move the canvas viewport according to the active middle-pan gesture. */
  function moveMiddlePan(event) {
    if (!middlePan || event.pointerId !== middlePan.pointerId) return;
    event.preventDefault();
    viewport.scrollLeft = middlePan.left - (event.clientX - middlePan.x);
    viewport.scrollTop = middlePan.top - (event.clientY - middlePan.y);
  }

  /** Release the middle-pan gesture. */
  function endMiddlePan(event) {
    if (!middlePan || event.pointerId !== middlePan.pointerId) return;
    middlePan = null;
    viewport.classList.remove('v54-middle-panning');
  }

  // =========================================================================
  // Hover label
  // =========================================================================
  /**
   * Lazily build the hover label element.
   * @returns {HTMLDivElement}
   */
  function ensureHoverBox() {
    if (hoverBox) return hoverBox;
    hoverBox = document.createElement('div');
    hoverBox.className = 'v54-hover-box';
    hoverBox.hidden = true;
    hoverBox.innerHTML = '<span></span>';
    document.body.append(hoverBox);
    return hoverBox;
  }

  /**
   * Track the object under the pointer and show its type label. Skipped for
   * touch pointers, active pans, transforms, and already-selected/locked
   * objects.
   * @param {PointerEvent} event
   */
  function hoverMove(event) {
    if (event.pointerType === 'touch' || middlePan || document.body.classList.contains('v23-transform-active')) return hideHover();
    const object = event.target.closest?.('#stage .object');
    if (!object || object.classList.contains('selected') || object.classList.contains('multi-selected') || object.dataset.locked === 'true') return hideHover();
    const rect = object.getBoundingClientRect();
    const box = ensureHoverBox();
    box.hidden = false;
    Object.assign(box.style, { left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px`, transform: 'none' });
    box.querySelector('span').textContent = readableType(object);
  }

  /** Hide the hover label. */
  function hideHover() { if (hoverBox) hoverBox.hidden = true; }

  // =========================================================================
  // Inspector mode (Essentials / All controls)
  // =========================================================================
  /**
   * Build the inspector-mode toggle and tag advanced controls so they can be
   * hidden in "Essentials" mode. The choice is persisted to localStorage.
   */
  function ensureInspectorMode() {
    const right = $('.right');
    if (!right || inspectorToggle) return;

    inspectorToggle = document.createElement('div');
    inspectorToggle.className = 'v54-inspector-mode';
    inspectorToggle.innerHTML = '<span>Inspector</span><button type="button" data-v54-inspector-toggle></button>';
    right.insertBefore(inspectorToggle, right.children[1] || null);

    // Selectors for controls considered "advanced" — hidden in Essentials.
    const advanced = [
      '#advancedTextLayout', '#peLayoutAssistance', '#borderWidth', '#borderColor', '#borderRadius',
      '#shadowBlur', '#shadowColor', '#imagePositionX', '#imagePositionY', '#showInGallery', '#showInHero',
      '#objectLocked', '.alignment-grid'
    ];
    advanced.forEach(selector => $$(selector).forEach(node => (node.closest('label,details,section,div') || node).classList.add('v54-advanced-control')));

    const objectPane = $('[data-inspector-pane="object"]', right);
    if (objectPane) {
      $$('.final-timeline,#canvasPlusAiTools', objectPane).forEach(node => node.classList.add('v54-advanced-control'));
      $$('.final-advanced-inspector', objectPane).forEach(node => {
        if (!['canvasPlusTransform', 'canvasPlusTextBox', 'canvasPlusTextPlacement'].includes(node.id)) node.classList.add('v54-advanced-control');
      });
      // Empty state shown when nothing is selected — offers quick-add actions.
      inspectorEmpty = document.createElement('section');
      inspectorEmpty.className = 'v54-inspector-empty';
      inspectorEmpty.innerHTML = '<span aria-hidden="true">↖</span><strong>Choose something to edit</strong><p data-v54-empty-label>Select an object to edit its position, style, image, text, and animation.</p><div><button type="button" data-v54-open="text">Add text</button><button type="button" data-v54-open="elements">Browse elements</button><button type="button" data-v54-open="media">Add media</button></div>';
      const heading = $('.studio-inspector-heading', objectPane);
      if (heading && objectPane.firstElementChild !== heading) objectPane.prepend(heading);
      heading?.after(inspectorEmpty);
      inspectorEmpty.addEventListener('click', event => {
        const id = event.target.closest('[data-v54-open]')?.dataset.v54Open;
        if (!id) return;
        document.querySelector(`[data-studio-tab="${id}"]`)?.click();
      });
    }

    // Restore the user's last choice (default: essentials for a calmer UI).
    const saved = localStorage.getItem('einvite-v54-inspector-mode') || 'essential';
    setInspectorMode(saved === 'all' ? 'all' : 'essential');
    inspectorToggle.querySelector('button').onclick = () => setInspectorMode(document.body.classList.contains('v54-inspector-essential') ? 'all' : 'essential');
  }

  /**
   * Switch between "essential" (advanced controls hidden) and "all" modes.
   * @param {'essential'|'all'} mode
   */
  function setInspectorMode(mode) {
    const essential = mode !== 'all';
    document.body.classList.toggle('v54-inspector-essential', essential);
    try { localStorage.setItem('einvite-v54-inspector-mode', essential ? 'essential' : 'all'); } catch { /* ignore quota errors */ }
    if (inspectorToggle) {
      const button = inspectorToggle.querySelector('button');
      button.textContent = essential ? 'Essentials' : 'All controls';
      button.setAttribute('aria-pressed', String(!essential));
      button.title = essential ? 'Show all advanced controls' : 'Show essential controls only';
    }
  }

  // =========================================================================
  // Header & footer progressive disclosure (run on install + resize only)
  // =========================================================================
  /**
   * Remember the original DOM location of a header node via a comment marker
   * so it can be restored when the viewport is wide enough.
   * @param {Element} node
   */
  function rememberHeaderHome(node) {
    if (!node?.id || headerHomes.has(node.id)) return;
    const marker = document.createComment(`v54-home-${node.id}`);
    node.before(marker);
    headerHomes.set(node.id, marker);
  }

  /**
   * Move a header node back to its remembered home, if any.
   * @param {Element} node
   */
  function restoreHeaderNode(node) {
    const marker = headerHomes.get(node?.id);
    if (marker?.parentNode && marker.nextSibling !== node) marker.after(node);
  }

  /**
   * Reorganise the studio top bar into a compact "more" menu on narrow
   * viewports. Runs on install + resize only (NOT on every selection) so the
   * toolbar stays stable.
   */
  function organizeHeader() {
    const header = $('.studio-topbar');
    const more = $('.canvas-header-more');
    const menu = $('.canvas-header-more-menu', more);
    if (!header || !more || !menu) return;

    const ids = ['studioCommandBtn', 'studioCheckBtn', 'previewBtn', 'eiAiTopButton', 'eiAdvancedStudio', 'eiFuturePlatform'];
    ids.map(id => document.getElementById(id)).filter(Boolean).forEach(rememberHeaderHome);

    let project = $('.v54-header-menu-project', menu);
    let actions = $('.v54-header-menu-actions', menu);
    let advanced = $('.v54-header-menu-advanced', menu);
    if (!project) {
      project = document.createElement('div');
      project.className = 'v54-header-menu-section v54-header-menu-project';
      project.innerHTML = '<strong>Project</strong>';
      [$('#backupBtn'), $('#restoreBtn')].filter(Boolean).forEach(node => project.append(node));
      menu.replaceChildren(project);
    }
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'v54-header-menu-section v54-header-menu-actions';
      actions.innerHTML = '<strong>Editor</strong>';
      menu.append(actions);
    }
    if (!advanced) {
      advanced = document.createElement('div');
      advanced.className = 'v54-header-menu-section v54-header-menu-advanced';
      advanced.innerHTML = '<strong>Advanced tools</strong>';
      menu.append(advanced);
    }

    const compact = innerWidth <= 1180;
    const narrow = innerWidth <= 760;
    ['eiAdvancedStudio', 'eiFuturePlatform'].forEach(id => {
      const node = document.getElementById(id);
      if (node && node.parentElement !== advanced) advanced.append(node);
    });
    ['studioCommandBtn', 'studioCheckBtn', 'eiAiTopButton'].forEach(id => {
      const node = document.getElementById(id);
      if (!node) return;
      if (compact) { if (node.parentElement !== actions) actions.append(node); }
      else restoreHeaderNode(node);
    });
    const preview = $('#previewBtn');
    if (preview) {
      if (narrow) { if (preview.parentElement !== actions) actions.append(preview); }
      else restoreHeaderNode(preview);
    }
    menu.classList.toggle('v54-has-actions', actions.querySelector('button') != null);
    actions.hidden = !actions.querySelector('button');

    // Tag device buttons with a single-letter short label for compact toolbars.
    $$('.studio-canvas-toolbar [data-device]').forEach(button => {
      button.classList.add('v54-device-button');
      button.dataset.short = button.textContent.trim().slice(0, 1);
      button.setAttribute('aria-label', `${button.textContent.trim()} canvas`);
      button.title = `Preview ${button.textContent.trim().toLowerCase()} canvas`;
    });
  }

  /**
   * Build the footer "Tools" overflow trigger + menu.
   * @returns {HTMLDivElement|null}
   */
  function ensureFooterTools() {
    const footer = $('.studio-statusbar');
    const host = footer?.lastElementChild;
    if (!footer || !host) return null;
    if (footerTools?.isConnected) return footerTools;
    footerTools = document.createElement('div');
    footerTools.className = 'v54-footer-tools';
    footerTools.innerHTML = '<button type="button" class="v54-footer-tools-trigger" aria-expanded="false">Tools <span>⌃</span></button><div class="v54-footer-tools-menu" hidden><strong>Workspace tools</strong><div></div></div>';
    host.append(footerTools);
    const trigger = $('.v54-footer-tools-trigger', footerTools);
    const menu = $('.v54-footer-tools-menu', footerTools);
    trigger.onclick = event => {
      event.stopPropagation();
      menu.hidden = !menu.hidden;
      trigger.setAttribute('aria-expanded', String(!menu.hidden));
      if (!menu.hidden) menu.querySelector('button')?.focus();
    };
    menu.addEventListener('click', event => {
      if (event.target.closest('button')) {
        menu.hidden = true;
        trigger.setAttribute('aria-expanded', 'false');
      }
    });
    return footerTools;
  }

  /**
   * Move stray footer buttons into the footer Tools menu. Runs on install +
   * resize only.
   */
  function organizeFooter() {
    const tools = ensureFooterTools();
    const footer = $('.studio-statusbar');
    const host = footer?.lastElementChild;
    const menu = $('.v54-footer-tools-menu>div', tools);
    if (!tools || !host || !menu) return;
    [...host.children]
      .filter(node => node.tagName === 'BUTTON' && !node.classList.contains('v54-footer-tools-trigger'))
      .forEach(button => menu.append(button));
    tools.hidden = !menu.querySelector('button');
  }

  // =========================================================================
  // Command registration
  // =========================================================================
  /**
   * Register canvas-related keyboard shortcuts into the command registry.
   */
  function registerCommands() {
    registry.registerMany?.([
      {
        id: 'canvas.zoomSelection', title: 'Zoom to selection', category: 'Canvas',
        keywords: ['focus', 'selected object', 'fit'],
        bindings: { standard: ['Mod+2'], canva: ['Mod+2'], photoshop: ['Mod+2'] },
        enabled: () => !!(bridge.getSelectedIds?.() || []).length,
        run: () => controller.zoomToSelection()
      },
      {
        id: 'canvas.zoomPointerHelp', title: 'Show canvas navigation controls', category: 'Canvas',
        keywords: ['trackpad', 'wheel', 'pan', 'zoom'],
        bindings: { standard: [], canva: [], photoshop: [] },
        run: () => {
          ensureHud().animate?.(
            [{ transform: 'translateY(6px)', opacity: 0.6 }, { transform: 'translateY(0)', opacity: 1 }],
            { duration: 220 }
          );
          return true;
        }
      }
    ]);
  }

  // =========================================================================
  // Auto-fit suppression wiring (bugs #1 & #2)
  // =========================================================================
  /**
   * Detect the start of a resize/rotate drag via pointerdown on a handle and
   * engage AutoFitGuard so font size is locked for the duration of the drag.
   * @param {PointerEvent} event
   */
  function onHandlePointerDown(event) {
    const handle = event.target.closest?.(
      '.resize-handle,.rotate-handle,.pe-handle,.pe-rotate,[data-pe-handle],.object .handle'
    );
    if (!handle) return;
    AutoFitGuard.begin();
  }

  /** Release AutoFitGuard shortly after the drag ends. */
  function onHandlePointerUp() {
    if (AutoFitGuard.active) AutoFitGuard.end();
  }

  /**
   * Pulse AutoFitGuard for a single tick after a selection change so that
   * selecting an object does NOT trigger an automatic box refit (bug #2).
   */
  function onSelectionChanged() {
    AutoFitGuard.pulse();
    scheduleUpdate();
  }

  // =========================================================================
  // Install / destroy
  // =========================================================================
  /**
   * Install the module: build chrome, wire events, register commands, and
   * observe the DOM. Called once on DOMContentLoaded (or immediately if the
   * DOM is already ready).
   */
  function install() {
    document.body.classList.add('workspace-experience-v54');
    ensureHud();
    ensureSelectionCard();
    ensureHoverBox();
    ensureInspectorMode();
    organizeHeader();
    organizeFooter();
    registerCommands();
    updateZoomLabel();
    scheduleUpdate();

    // Fit the canvas on first paint for small screens (better first impression).
    if (matchMedia('(max-width:600px)').matches) {
      requestAnimationFrame(() => requestAnimationFrame(() => controller.fit()));
    }

    // Canvas input handlers.
    on(viewport, 'wheel', wheelZoom, { capture: true, passive: false });
    on(document, 'pointerdown', beginDuplicateDrag, true);
    on(window, 'pointermove', moveDuplicateDrag, true);
    on(window, 'pointerup', event => endDuplicateDrag(event, false), true);
    on(window, 'pointercancel', event => endDuplicateDrag(event, true), true);
    on(viewport, 'pointerdown', startMiddlePan, true);
    on(viewport, 'pointermove', moveMiddlePan, true);
    on(viewport, 'pointerup', endMiddlePan, true);
    on(viewport, 'pointercancel', endMiddlePan, true);
    on(stage, 'pointermove', hoverMove, { passive: true });
    on(stage, 'pointerleave', hideHover);

    // Auto-fit guard wiring — fixes "font shrinks on resize" & "box resizes on click".
    on(stage, 'pointerdown', onHandlePointerDown, true);
    on(window, 'pointerup', onHandlePointerUp, true);
    on(document, 'einvite:selection-changed', onSelectionChanged);
    // Also try to patch the typography service once it's available.
    on(window, 'einvite:editor-ready', () => { AutoFitGuard.patch(); organizeHeader(); organizeFooter(); });

    // Close popovers on outside interaction.
    on(document, 'pointerdown', event => {
      if (!event.target.closest?.('#v54ZoomMenu,.v54-zoom-value')) closeZoomMenu();
      if (!event.target.closest?.('.v54-footer-tools')) {
        const menu = $('.v54-footer-tools-menu');
        if (menu) {
          menu.hidden = true;
          $('.v54-footer-tools-trigger')?.setAttribute('aria-expanded', 'false');
        }
      }
    }, true);

    on(window, 'einvite:zoom-changed', scheduleUpdate);
    on(window, 'einvite:state-applied', scheduleUpdate);
    on(window, 'einvite:editor-state-replaced', scheduleUpdate);
    on(window, 'resize', () => { AutoFitGuard.patch(); organizeHeader(); organizeFooter(); scheduleUpdate(); });

    // Observe DOM mutations so the selection card / empty state stay in sync.
    // NOTE: we deliberately do NOT re-run organiseHeader/Footer here — doing
    // so on every mutation is what previously caused the toolbar to "jump".
    contextObserver = new MutationObserver(records => {
      if (records.some(record => {
        const target = record.target;
        if (target?.closest?.('.v54-context-menu')) return false;
        return target?.id === 'v23ContextToolbar' || target?.parentElement?.id === 'v23ContextToolbar' ||
          [...record.addedNodes].some(node => node.nodeType === 1 && (node.id === 'v23ContextToolbar' || node.querySelector?.('#v23ContextToolbar')));
      })) scheduleUpdate();
    });
    contextObserver.observe(document.body, { childList: true, subtree: true });

    selectionObserver = new MutationObserver(scheduleUpdate);
    selectionObserver.observe(stage, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });

    resizeObserver = new ResizeObserver(() => { organizeHeader(); organizeFooter(); scheduleUpdate(); });
    resizeObserver.observe(wrap);
    resizeObserver.observe(viewport);

    // Expose the public API under BOTH the new (EInviteEditorCore) and the
    // legacy (EInviteWorkspaceExperience) namespaces. Claiming the legacy
    // namespace means any late-loading copy of the old
    // `workspace-experience-v24.js` (which guards on
    // `window.EInviteWorkspaceExperience?.version >= 24`) will detect v>=24
    // and no-op, preventing duplicate canvas chrome. This lets us supersede
    // the old module safely even if a deferred loader still references it.
    window.EInviteWorkspaceExperience = Object.freeze({
      version: 24,
      refresh: scheduleUpdate,
      zoomToSelection: () => controller.zoomToSelection(),
      get hud() { return hud; }
    });
    window.EInviteEditorCore = Object.freeze({
      ...api,
      refresh: scheduleUpdate,
      zoomToSelection: () => controller.zoomToSelection(),
      AutoFitGuard,
      get hud() { return hud; }
    });
  }

  /**
   * Tear down everything: remove listeners, observers, and DOM. Used by the
   * editor lifecycle so the module can be safely re-initialised.
   */
  function destroy() {
    destroyed = true;
    if (raf) clearTimeout(raf);
    if (duplicateDrag) {
      duplicateDrag.previews.forEach(preview => preview.remove());
      duplicateDrag = null;
    }
    cleanup.splice(0).forEach(fn => { try { fn(); } catch { /* ignore */ } });
    contextObserver?.disconnect();
    selectionObserver?.disconnect();
    resizeObserver?.disconnect();
    hud?.remove();
    popover?.remove();
    selectionCard?.remove();
    hoverBox?.remove();
    inspectorToggle?.remove();
    inspectorEmpty?.remove();
    footerTools?.remove();
    headerHomes.forEach(marker => marker.remove());
    headerHomes.clear();
    document.body.classList.remove('workspace-experience-v54', 'v54-inspector-essential', 'v54-has-selection', 'ei-suppress-autofit');
    delete window.EInviteEditorCore;
  }
  api.destroy = destroy;

  // Register teardown with the editor lifecycle if present.
  window.EInviteLifecycle?.add?.(destroy);

  // Boot.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
