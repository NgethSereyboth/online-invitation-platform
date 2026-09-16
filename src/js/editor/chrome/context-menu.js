/**
 * context-menu.js — Right-click context menu (ROADMAP §3.1.3, v0.56).
 *
 * Exposes `EInviteContextMenu` — a service that renders a `<div role="menu">`
 * floating panel at `event.clientX/clientY` when the user right-clicks on the
 * canvas or on a selected element. The menu contents are context-dependent:
 *
 *   • Empty canvas (no selection under cursor) →
 *       Paste, Select all, Zoom to fit.
 *   • Single element selected →
 *       Cut, Copy, Duplicate, Delete, Bring to front, Send to back,
 *       Lock/Unlock, Hide/Show, Add comment, Group (disabled).
 *   • Multiple elements selected →
 *       Group, Ungroup, Align left/center/right, Distribute,
 *       Duplicate, Delete.
 *
 * Keyboard navigation (per ROADMAP §3.1.3):
 *   • Arrow Up/Down moves focus between items.
 *   • Enter activates the focused item.
 *   • Escape closes the menu.
 *   • Click outside or window blur also closes.
 *
 * Bilingual: every item has EN + KH labels (see STRINGS).
 *
 * Idempotent: a second load is a no-op. Plays nicely with the existing
 * v23 context menu (it appends an `ei-context-menu-open` body class so the
 * existing menu's `outside-click` handler can detect overlap).
 */
(() => {
  'use strict';

  if (window.EInviteContextMenu?.version >= 56) return;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);
  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const bridge = () => window.EInviteEditorBridge;
  const pro = () => window.EInviteProfessionalEditor;
  const controller = () => window.EInviteCanvasViewController;
  const multi = () => window.EInviteMultiSelect;

  /**
   * Bilingual labels for every menu item. Each entry has `en` + `km`.
   * Items also have an optional `shortcut` (displayed on the right).
   */
  const STRINGS = Object.freeze({
    'menu.cut':         { en: 'Cut',            km: 'កាត់',            shortcut: 'Ctrl+X' },
    'menu.copy':        { en: 'Copy',           km: 'ចម្លង',           shortcut: 'Ctrl+C' },
    'menu.paste':       { en: 'Paste',          km: 'បិទភ្ជាប់',         shortcut: 'Ctrl+V' },
    'menu.duplicate':   { en: 'Duplicate',      km: 'ស្ទួន',           shortcut: 'Ctrl+D' },
    'menu.delete':      { en: 'Delete',         km: 'លុប',             shortcut: 'Del' },
    'menu.front':       { en: 'Bring to front', km: 'នាំមកមុខ',          shortcut: 'Ctrl+Shift+]' },
    'menu.back':        { en: 'Send to back',   km: 'ផ្ញើទៅក្រោយ',        shortcut: 'Ctrl+Shift+[' },
    'menu.forward':     { en: 'Bring forward',  km: 'នាំមកមុខបន្តិច',      shortcut: 'Ctrl+]' },
    'menu.backward':    { en: 'Send backward',  km: 'ផ្ញើទៅក្រោយបន្តិច',    shortcut: 'Ctrl+[' },
    'menu.group':       { en: 'Group',          km: 'ក្រុម',            shortcut: 'Ctrl+G' },
    'menu.ungroup':     { en: 'Ungroup',       km: 'ពុំក្រុម',           shortcut: 'Ctrl+Shift+G' },
    'menu.lock':        { en: 'Lock',           km: 'ចាក់សោ',            shortcut: '' },
    'menu.unlock':       { en: 'Unlock',         km: 'បើកសោ',            shortcut: '' },
    'menu.hide':        { en: 'Hide',           km: 'លាក់',             shortcut: '' },
    'menu.show':        { en: 'Show',           km: 'បង្ហាញ',           shortcut: '' },
    'menu.comment':     { en: 'Add comment',    km: 'បន្ថែមមតិយោបល់',      shortcut: '' },
    'menu.selectall':   { en: 'Select all',     km: 'ជ្រើរើសទាំងអស់',       shortcut: 'Ctrl+A' },
    'menu.zoomfit':     { en: 'Zoom to fit',    km: 'ពង្រីកឲ្យជាប់',       shortcut: '' },
    'menu.align.left':  { en: 'Align left',     km: 'តម្រឹមឆ្វេង',         shortcut: '' },
    'menu.align.center':{ en: 'Align center',   km: 'តម្រឹមកណ្តាល',        shortcut: '' },
    'menu.align.right': { en: 'Align right',    km: 'តម្រឹមស្តាំ',         shortcut: '' },
    'menu.distribute.h':{ en: 'Distribute horizontally', km: 'ចែកតំរឹមផ្តេក', shortcut: '' },
    'menu.distribute.v':{ en: 'Distribute vertically',   km: 'ចែកតំរឹមបញ្ឈរ', shortcut: '' }
  });

  /** @type {HTMLDivElement|null} */
  let menu = null;
  /** @type {(() => void)|null} Cleanup callback for the current menu's outside-click handler. */
  let teardownOutside = null;

  /**
   * Build a menu-item button element.
   * @param {keyof typeof STRINGS} key
   * @param {() => void} handler Called when the item is clicked or activated via Enter.
   * @param {{disabled?:boolean}} [options]
   * @returns {HTMLButtonElement}
   */
  function buildItem(key, handler, options = {}) {
    const labels = STRINGS[key] || { en: key, km: key, shortcut: '' };
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ei-menu-item';
    btn.setAttribute('role', 'menuitem');
    btn.tabIndex = -1;
    btn.innerHTML = `<span class="ei-menu-en"></span><span class="ei-menu-km"></span>${labels.shortcut ? `<span class="ei-menu-shortcut"></span>` : ''}`;
    btn.querySelector('.ei-menu-en').textContent = labels.en;
    btn.querySelector('.ei-menu-km').textContent = labels.km;
    if (labels.shortcut) btn.querySelector('.ei-menu-shortcut').textContent = labels.shortcut;
    btn.addEventListener('click', () => { handler(); close(); });
    btn.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        btn.click();
      }
    });
    if (options.disabled) {
      btn.setAttribute('aria-disabled', 'true');
      btn.disabled = true;
    }
    return btn;
  }

  /**
   * Build a separator `<hr>` element.
   * @returns {HTMLHRElement}
   */
  function buildSeparator() {
    const hr = document.createElement('hr');
    hr.className = 'ei-menu-separator';
    hr.setAttribute('role', 'separator');
    return hr;
  }

  /**
   * Build the list of menu items based on the current selection state.
   * @returns {HTMLButtonElement[]}
   */
  function buildItems() {
    const ids = (bridge()?.getSelectedIds?.() || []);
    const commands = pro()?.commands;
    /** @type {HTMLButtonElement[]} */
    const items = [];

    const push = (/** @type {keyof typeof STRINGS} */ key, /** @type {() => void} */ fn, opts) => {
      items.push(buildItem(key, fn, opts));
    };
    const sep = () => items.push(buildSeparator());

    if (ids.length === 0) {
      push('menu.paste',     () => commands?.pasteSelection?.());
      push('menu.selectall', () => multi()?.selectAll() ?? commands?.setSelection?.([], false));
      sep();
      push('menu.zoomfit',   () => controller()?.fit?.());
      return items;
    }

    if (ids.length === 1) {
      push('menu.cut',       () => commands?.cutSelection?.());
      push('menu.copy',      () => commands?.copySelection?.());
      push('menu.duplicate', () => multi()?.duplicate() ?? commands?.duplicateSelection?.());
      push('menu.delete',    () => multi()?.deleteSelection() ?? commands?.deleteSelection?.());
      sep();
      push('menu.front',     () => commands?.reorder?.(ids, 'front'));
      push('menu.forward',   () => commands?.reorder?.(ids, 'forward'));
      push('menu.backward',  () => commands?.reorder?.(ids, 'backward'));
      push('menu.back',      () => commands?.reorder?.(ids, 'back'));
      sep();
      push('menu.lock',      () => commands?.setObjectFlag?.(ids, 'locked', true));
      push('menu.hide',      () => commands?.setObjectFlag?.(ids, 'visible', false));
      push('menu.comment',   () => window.dispatchEvent(new CustomEvent('einvite:comment-add', { detail: { id: ids[0] } })));
      return items;
    }

    // Multiple selection.
    push('menu.group',      () => multi()?.group() ?? commands?.groupSelection?.());
    push('menu.ungroup',    () => multi()?.ungroup() ?? commands?.ungroupSelection?.(), { disabled: !commands?.ungroupSelection });
    sep();
    push('menu.align.left',   () => commands?.alignSelection?.('left'));
    push('menu.align.center', () => commands?.alignSelection?.('center'));
    push('menu.align.right',  () => commands?.alignSelection?.('right'));
    sep();
    push('menu.distribute.h', () => commands?.distributeSelection?.('horizontal'));
    push('menu.distribute.v', () => commands?.distributeSelection?.('vertical'));
    sep();
    push('menu.duplicate',  () => multi()?.duplicate() ?? commands?.duplicateSelection?.());
    push('menu.delete',     () => multi()?.deleteSelection() ?? commands?.deleteSelection?.());
    return items;
  }

  /**
   * Open the context menu at the given screen coordinates.
   * @param {number} clientX
   * @param {number} clientY
   */
  function open(clientX, clientY) {
    close();   // any existing menu first
    menu = document.createElement('div');
    menu.className = 'einvite-context-menu';
    menu.setAttribute('role', 'menu');
    menu.tabIndex = -1;
    menu.hidden = false;
    const items = buildItems();
    for (const item of items) menu.append(item);
    document.body.append(menu);
    // Position with edge clamping so the menu never overflows the viewport.
    const rect = menu.getBoundingClientRect();
    const w = rect.width || 220;
    const h = rect.height || 220;
    const left = Math.min(Math.max(4, clientX), window.innerWidth - w - 4);
    const top = Math.min(Math.max(4, clientY), window.innerHeight - h - 4);
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    // Focus the first enabled item.
    const first = menu.querySelector<HTMLButtonElement>('.ei-menu-item:not([aria-disabled="true"])');
    first?.focus();
    document.body.classList.add('ei-context-menu-open');
    // Wire outside-click + escape + blur handlers.
    const onOutside = (/** @type {PointerEvent} */ event) => {
      if (menu && !menu.contains(/** @type {Node} */ (/** @type {unknown} */ (event.target)))) close();
    };
    const onKey = (/** @type {KeyboardEvent} */ event) => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        const buttons = [...menu.querySelectorAll<HTMLButtonElement>('.ei-menu-item:not([aria-disabled="true"])')];
        if (!buttons.length) return;
        const focused = document.activeElement;
        const index = buttons.findIndex(b => b === focused);
        const next = buttons[(index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length];
        next?.focus();
      }
    };
    const onBlur = () => { if (!menu?.contains(document.activeElement)) close(); };
    document.addEventListener('pointerdown', onOutside, true);
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('blur', onBlur);
    teardownOutside = () => {
      document.removeEventListener('pointerdown', onOutside, true);
      document.removeEventListener('keydown', onKey, true);
      window.removeEventListener('blur', onBlur);
    };
  }

  /** Close the current menu (if any). */
  function close() {
    teardownOutside?.();
    teardownOutside = null;
    menu?.remove();
    menu = null;
    document.body.classList.remove('ei-context-menu-open');
  }

  /**
   * @param {MouseEvent} event
   */
  function onContextMenu(event) {
    // Allow native context menu on inputs/contenteditable.
    const target = event.target;
    if (target instanceof HTMLElement && (target.isContentEditable ||
        target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
    // Only show on the editor stage or one of its descendants.
    const stage = $('#stage');
    if (!stage) return;
    if (!stage.contains(/** @type {Node} */ (/** @type {unknown} */ (target))) && target !== stage) return;
    event.preventDefault();
    // If the user right-clicked an object that isn't already selected,
    // select it first (so the menu shows single-element actions).
    const obj = target instanceof Element ? target.closest('.object') : null;
    if (obj?.dataset.id) {
      const current = new Set((bridge()?.getSelectedIds?.() || []).map(String));
      if (!current.has(String(obj.dataset.id))) {
        bridge()?.select?.([String(obj.dataset.id)]);
      }
    }
    open(event.clientX, event.clientY);
  }

  // =========================================================================
  // Install / destroy
  // =========================================================================
  let installed = false;
  function install() {
    if (installed) return;
    const stage = $('#stage');
    if (!stage) return;
    document.addEventListener('contextmenu', onContextMenu, true);
    installed = true;
  }

  function destroy() {
    if (!installed) return;
    document.removeEventListener('contextmenu', onContextMenu, true);
    close();
    installed = false;
  }

  // Public API.
  window.EInviteContextMenu = Object.freeze({
    version: 56,
    STRINGS,
    open,
    close,
    install,
    destroy,
    get menu() { return menu; }
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();

  window.EInviteLifecycle?.add?.(destroy);
})();
