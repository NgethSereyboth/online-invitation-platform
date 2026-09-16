/**
 * selection.js — Multi-select + group operations (ROADMAP §3.1.2, v0.56).
 *
 * Exposes `EInviteMultiSelect` — a service that extends the editor's
 * single-element selection model to support multiple elements:
 *
 *   • Selection is a `Set<elementId>`. Order matters for z-index reordering.
 *   • Shift-click to add/remove from the selection.
 *   • Marquee drag (empty-canvas pointerdown + drag) to select multiple.
 *   • Group bounds = union of member bounding boxes + 8px padding.
 *   • Group transforms: move (same delta), resize (proportional), delete,
 *     duplicate. Delegates to the existing `EInviteProfessionalEditor`
 *     commands (groupSelection, ungroupSelection, etc.) which already persist
 *     groups in the document model.
 *   • Keyboard: Ctrl+G group, Ctrl+Shift+G ungroup, Ctrl+A select all,
 *     Escape deselect. (These shortcuts already exist in the command
 *     registry; this module wires the handler too for resilience.)
 *
 * The service is purely additive — it does NOT replace the existing
 * `bridge.select()` flow; it layers marquee + shift-click on top, then
 * delegates the actual selection change to `bridge.select(ids)`.
 *
 * Bilingual strings: group/ungroup labels (EN + KH).
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';

  if (window.EInviteMultiSelect?.version >= 56) return;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);
  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /** Padding (px) around the union of selected rects → group bounds. */
  const GROUP_PADDING_PX = 8;
  /** Minimum drag distance (px) before a marquee is treated as a drag. */
  const MARQUEE_THRESHOLD_PX = 4;

  /** Bilingual labels for group operations. */
  const STRINGS = Object.freeze({
    'group.label':       { en: 'Group',  km: 'ក្រុម' },
    'ungroup.label':     { en: 'Ungroup', km: 'ពុំក្រុម' },
    'select.all':        { en: 'Select all', km: 'ជ្រើរើសទាំងអស់' },
    'select.none':       { en: 'Deselect', km: 'មិនជ្រើរើស' },
    'group.created':     { en: 'Group created', km: 'បានបង្កើតក្រុម' },
    'group.dissolved':   { en: 'Group dissolved', km: 'បានរំលាយក្រុម' }
  });

  // =========================================================================
  // Selection state — wraps the bridge's selection (which is an array of
  // ids stored in app.js) as a Set, with order preserved via insertion.
  // =========================================================================
  const bridge = () => window.EInviteEditorBridge;
  const pro = () => window.EInviteProfessionalEditor;
  const stage = () => $('#stage');

  /**
   * @returns {Set<string>} The current selection as a Set.
   */
  function getSelection() {
    return new Set((bridge()?.getSelectedIds?.() || []).map(String));
  }

  /**
   * Replace the current selection with the given ids (order preserved).
   * @param {Iterable<string>} ids
   */
  function setSelection(ids) {
    bridge()?.select?.([...ids]);
    window.dispatchEvent(new CustomEvent('einvite:multi-select-changed', {
      detail: { count: getSelection().size }
    }));
  }

  /**
   * Add a single id (shift-click semantics — toggle if already present).
   * @param {string} id
   * @param {boolean} [additive=true] If false, replaces the selection.
   */
  function toggle(id, additive = true) {
    const next = additive ? new Set(getSelection()) : new Set();
    if (additive && next.has(id)) next.delete(id);
    else next.add(id);
    setSelection(next);
  }

  /**
   * Add ids to the selection without removing existing ones.
   * @param {Iterable<string>} ids
   */
  function add(ids) {
    const next = new Set(getSelection());
    for (const id of ids) next.add(String(id));
    setSelection(next);
  }

  /** Remove ids from the selection. */
  function remove(ids) {
    const next = new Set(getSelection());
    for (const id of ids) next.delete(String(id));
    setSelection(next);
  }

  /** Clear the selection. */
  function clear() { setSelection([]); }

  /**
   * Select every visible, unlocked object on the active canvas.
   * @returns {number} The number of objects selected.
   */
  function selectAll() {
    const st = stage();
    if (!st) return 0;
    const ids = $$('.object', st)
      .filter(el => el.dataset.visible !== 'false' && el.dataset.locked !== 'true')
      .map(el => el.dataset.id)
      .filter(Boolean);
    setSelection(ids);
    return ids.length;
  }

  // =========================================================================
  // Group bounds — union of member bounding boxes + 8px padding.
  // =========================================================================

  /**
   * Compute the union bounding box of a set of element ids on the stage,
   * plus 8px padding on all sides (per ROADMAP §3.1.2).
   *
   * Returns null if no elements matched.
   *
   * @param {Iterable<string>} ids
   * @returns {{left:number,top:number,right:number,bottom:number,width:number,height:number}|null}
   *          In CSS pixels, relative to the stage (unaffected by stage scale).
   */
  function groupBounds(ids) {
    const st = stage();
    if (!st) return null;
    const wanted = new Set([...ids].map(String));
    const items = $$('.object', st).filter(el => wanted.has(el.dataset.id));
    if (!items.length) return null;
    const scale = (() => {
      const r = st.getBoundingClientRect();
      return r.width / Math.max(1, st.offsetWidth);
    })();
    const rects = items.map(el => el.getBoundingClientRect());
    const left = Math.min(...rects.map(r => r.left));
    const top = Math.min(...rects.map(r => r.top));
    const right = Math.max(...rects.map(r => r.right));
    const bottom = Math.max(...rects.map(r => r.bottom));
    return {
      left:   (left / scale)   - GROUP_PADDING_PX,
      top:    (top / scale)    - GROUP_PADDING_PX,
      right:  (right / scale)  + GROUP_PADDING_PX,
      bottom: (bottom / scale) + GROUP_PADDING_PX,
      width:  ((right - left) / scale) + 2 * GROUP_PADDING_PX,
      height: ((bottom - top) / scale) + 2 * GROUP_PADDING_PX
    };
  }

  // =========================================================================
  // Group transforms — delegate to the pro editor for the heavy lifting
  // (it already persists groups in the document model). This module exposes
  // a thin wrapper so context-menu / inspector can call them with a unified
  // API and get bilingual confirmation events back.
  // =========================================================================

  /** Group the current selection. */
  function group() {
    const commands = pro()?.commands;
    if (!commands?.groupSelection) return false;
    commands.groupSelection();
    window.dispatchEvent(new CustomEvent('einvite:group-changed', {
      detail: { action: 'group', label: STRINGS['group.created'] }
    }));
    return true;
  }

  /** Ungroup the current selection. */
  function ungroup() {
    const commands = pro()?.commands;
    if (!commands?.ungroupSelection) return false;
    commands.ungroupSelection();
    window.dispatchEvent(new CustomEvent('einvite:group-changed', {
      detail: { action: 'ungroup', label: STRINGS['group.dissolved'] }
    }));
    return true;
  }

  /** Duplicate the current selection (delegates to pro editor). */
  function duplicate() {
    return !!pro()?.commands?.duplicateSelection?.();
  }

  /** Delete the current selection. */
  function deleteSelection() {
    return !!pro()?.commands?.deleteSelection?.();
  }

  /**
   * Move every selected element by the same delta (dx, dy) in canvas pixels.
   * Delegates to the pro editor's `nudge` command (which handles commit +
   * history). When the pro editor is unavailable, falls back to a direct
   * `bridge.transact()` that walks the active canvas map.
   *
   * @param {number} dx
   * @param {number} dy
   */
  function moveBy(dx, dy) {
    const commands = pro()?.commands;
    if (commands?.nudge) {
      commands.nudge(dx, dy);
      return true;
    }
    const b = bridge();
    if (!b?.transact || !b?.getState) return false;
    const ids = [...getSelection()];
    if (!ids.length) return false;
    b.transact('Move selection', doc => {
      const canvasId = b.getActiveCanvasId?.() || 'hero';
      const map = canvasId === 'hero' ? (doc.objects || {})
        : ((doc.designPages || []).find(p => `page:${p.id}` === canvasId)?.objects || {});
      for (const id of ids) {
        const obj = map[id];
        if (!obj) continue;
        obj.left = (Number(obj.left) || 0) + dx;
        obj.top = (Number(obj.top) || 0) + dy;
      }
    });
    return true;
  }

  /**
   * Resize the group proportionally — every member's position and size is
   * scaled by the same factor from the group's top-left origin.
   *
   * @param {number} factorX Scale factor on the X axis (1 = no change).
   * @param {number} factorY Scale factor on the Y axis.
   * @returns {boolean} Whether the resize was applied.
   */
  function resize(factorX, factorY) {
    const b = bridge();
    if (!b?.transact || !b?.getState) return false;
    const ids = [...getSelection()];
    if (!ids.length) return false;
    const bounds = groupBounds(ids);
    if (!bounds) return false;
    b.transact('Resize group', doc => {
      const canvasId = b.getActiveCanvasId?.() || 'hero';
      const map = canvasId === 'hero' ? (doc.objects || {})
        : ((doc.designPages || []).find(p => `page:${p.id}` === canvasId)?.objects || {});
      const stageWidth = stage()?.offsetWidth || 1;
      const stageHeight = stage()?.offsetHeight || 1;
      for (const id of ids) {
        const obj = map[id];
        if (!obj) continue;
        const left = Number(obj.left) * stageWidth;
        const top = Number(obj.top) * stageHeight;
        const width = Number(obj.width) * stageWidth;
        const height = Number(obj.height) * stageHeight;
        const newLeft = bounds.left + (left - bounds.left) * factorX;
        const newTop = bounds.top + (top - bounds.top) * factorY;
        const newWidth = width * factorX;
        const newHeight = height * factorY;
        obj.left = newLeft / stageWidth;
        obj.top = newTop / stageHeight;
        obj.width = newWidth / stageWidth;
        obj.height = newHeight / stageHeight;
      }
    });
    return true;
  }

  // =========================================================================
  // Marquee selection — pointerdown on empty stage + drag.
  // =========================================================================

  /** @type {{pointerId:number,startX:number,startY:number,active:boolean,el:HTMLDivElement|null}|null} */
  let marquee = null;

  /**
   * Ensure the marquee box element exists (lazily created).
   * @returns {HTMLDivElement}
   */
  function ensureMarquee() {
    if (marquee?.el?.isConnected) return marquee.el;
    const el = document.createElement('div');
    el.className = 'einvite-marquee';
    el.hidden = true;
    const viewport = $('#canvasViewport') || document.body;
    viewport.append(el);
    marquee = marquee || { pointerId: 0, startX: 0, startY: 0, active: false, el };
    marquee.el = el;
    return el;
  }

  /**
   * @param {PointerEvent} event
   */
  function onPointerDown(event) {
    if (event.button !== 0) return;             // only left button
    if (event.shiftKey) return;                  // shift-click handled by toggle()
    const st = stage();
    if (!st) return;
    // Only start a marquee when the pointerdown is on the stage itself or on
    // its non-object children (the canvas background), NOT on an object.
    const target = event.target;
    if (target instanceof Element && target.closest('.object')) return;
    // Ignore pointerdowns on resize/rotate handles.
    if (target instanceof Element && target.closest('.resize-handle,.rotate-handle,.pe-handle,.pe-rotate,[data-pe-handle]')) return;
    marquee = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      active: false,
      el: ensureMarquee()
    };
    try { st.setPointerCapture?.(event.pointerId); } catch { /* ignore */ }
    document.body.classList.add('ei-canvas-dragging');
  }

  /**
   * @param {PointerEvent} event
   */
  function onPointerMove(event) {
    if (!marquee || event.pointerId !== marquee.pointerId) return;
    const dx = event.clientX - marquee.startX;
    const dy = event.clientY - marquee.startY;
    if (!marquee.active && Math.hypot(dx, dy) < MARQUEE_THRESHOLD_PX) return;
    marquee.active = true;
    const left = Math.min(marquee.startX, event.clientX);
    const top = Math.min(marquee.startY, event.clientY);
    marquee.el.hidden = false;
    marquee.el.style.left = `${left}px`;
    marquee.el.style.top = `${top}px`;
    marquee.el.style.width = `${Math.abs(dx)}px`;
    marquee.el.style.height = `${Math.abs(dy)}px`;
  }

  /**
   * @param {PointerEvent} event
   */
  function onPointerUp(event) {
    document.body.classList.remove('ei-canvas-dragging');
    if (!marquee || event.pointerId !== marquee.pointerId) return;
    const wasActive = marquee.active;
    const rect = marquee.el.getBoundingClientRect();
    marquee.el.hidden = true;
    marquee = null;
    if (!wasActive) return;   // treat as a click on empty canvas → deselect
    // Find objects whose bounding rects intersect the marquee.
    const st = stage();
    if (!st) return;
    const hits = $$('.object', st).filter(el => {
      if (el.dataset.visible === 'false' || el.dataset.locked === 'true') return false;
      const r = el.getBoundingClientRect();
      return !(r.right < rect.left || r.left > rect.right || r.bottom < rect.top || r.top > rect.bottom);
    }).map(el => el.dataset.id).filter(Boolean);
    setSelection(hits);
  }

  // =========================================================================
  // Shift-click handler — toggle an object's selection when shift-clicked.
  // =========================================================================

  /**
   * @param {PointerEvent} event
   */
  function onObjectClick(event) {
    if (!event.shiftKey) return;
    const obj = event.target instanceof Element ? event.target.closest('.object') : null;
    if (!obj?.dataset.id) return;
    event.preventDefault();
    event.stopPropagation();
    toggle(String(obj.dataset.id), true);
  }

  // =========================================================================
  // Keyboard shortcuts — Ctrl+A, Escape, Ctrl+G, Ctrl+Shift+G.
  // The command registry already registers these; this is a resilience layer
  // so multi-select works even when the pro editor's keyboard claim is
  // temporarily inactive (e.g. while typing in an inspector field).
  // =========================================================================

  /**
   * @param {KeyboardEvent} event
   */
  function onKeyDown(event) {
    // Don't hijack typing in inputs.
    const target = event.target;
    if (target instanceof HTMLElement && target.isContentEditable) return;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return;
    const mod = event.ctrlKey || event.metaKey;
    if (mod && !event.shiftKey && (event.key === 'a' || event.key === 'A')) {
      if (!stage()) return;
      event.preventDefault();
      selectAll();
      return;
    }
    if (event.key === 'Escape') {
      if (getSelection().size) {
        event.preventDefault();
        clear();
      }
      return;
    }
    if (mod && !event.shiftKey && (event.key === 'g' || event.key === 'G')) {
      if (getSelection().size > 1) {
        event.preventDefault();
        group();
      }
      return;
    }
    if (mod && event.shiftKey && (event.key === 'g' || event.key === 'G')) {
      if (getSelection().size) {
        event.preventDefault();
        ungroup();
      }
      return;
    }
  }

  // =========================================================================
  // Install / destroy
  // =========================================================================

  let installed = false;
  function install() {
    if (installed) return;
    const st = stage();
    if (!st) return;
    st.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('pointercancel', onPointerUp);
    st.addEventListener('click', onObjectClick, true);
    document.addEventListener('keydown', onKeyDown);
    installed = true;
  }

  function destroy() {
    if (!installed) return;
    const st = stage();
    st?.removeEventListener('pointerdown', onPointerDown);
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('pointercancel', onPointerUp);
    st?.removeEventListener('click', onObjectClick, true);
    document.removeEventListener('keydown', onKeyDown);
    marquee?.el?.remove();
    marquee = null;
    installed = false;
  }

  // Public API.
  window.EInviteMultiSelect = Object.freeze({
    version: 56,
    STRINGS,
    GROUP_PADDING_PX,
    // Pure helpers + state.
    getSelection,
    setSelection,
    toggle,
    add,
    remove,
    clear,
    selectAll,
    groupBounds,
    // Group transforms.
    group,
    ungroup,
    duplicate,
    deleteSelection,
    moveBy,
    resize,
    // Marquee + install.
    install,
    destroy,
    get marquee() { return marquee; }
  });

  // Boot when DOM is ready.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();

  window.EInviteLifecycle?.add?.(destroy);
})();
