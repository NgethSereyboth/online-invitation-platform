/**
 * ui-layout.js — Editor layout chrome (v54 refactor).
 *
 * Consolidates the former `windows-ui-v16.js` into a documented, stable
 * module responsible for the studio editor's surrounding layout:
 *
 *   • Stage column ordering (toolbar → context row → viewport → page dock).
 *   • The toolbar "More" overflow menu (secondary canvas/studio controls).
 *   • Keeping the active page chip and active tool visible (scroll-into-view).
 *
 * BUG FIXES vs. the old v16 module:
 *
 *   3. Stable toolbar — the old module ran `moveSecondaryControls()` and
 *      `layoutContextToolbar()` on EVERY DOM mutation (via a MutationObserver
 *      on `childList` + `class` + `aria-pressed`), which physically moved
 *      toolbar buttons into/out of the "More" panel and toggled the context
 *      row between `display:block` and `display:none`. That is what made the
 *      shortcut-bar icons "jump". This module instead:
 *        - Populates the "More" panel ONCE on install, then only re-checks on
 *          viewport resize (debounced). Buttons keep their DOM position.
 *        - Gives the context row a stable, reserved height so showing/hiding
 *          it never shifts surrounding chrome.
 *   4. Full sidebar labels — adds a "collapse to icons" toggle so long
 *      category titles (Elements, Uploads, …) can be shown in full, with an
 *      icon-only mode available when space is tight.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';

  // Idempotency guard.
  if (window.EInviteUiLayout?.version >= 54) return;
  window.EInviteUiLayout = { version: 54 };

  // Claim the legacy v16 namespace too, so any stray late-loading copy of the
  // old `windows-ui-v16.js` (guarded by `window.__einviteWindowsUiV16`) will
  // no-op rather than double-process the toolbar chrome.
  window.__einviteWindowsUiV16 = true;

  /** @type {(selector:string, root?:ParentNode)=>Element|null} */
  const $ = (selector, root = document) => root.querySelector(selector);
  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  const body = document.body;
  // Bail when the editor stage is not present (non-editor routes).
  if (!body || !$('#stage')) return;

  body.classList.add('windows-ui-v54');

  // --- Module state ----------------------------------------------------------
  /** The lazily-built "More" details element + its panel. */
  let toolbarMore = null;
  let morePanel = null;
  /** Set of controls already moved into the More panel (avoids double-move). */
  const moved = new Set();
  /** Debounce handle for resize-driven re-checks. */
  let resizeRaf = 0;

  /**
   * Selectors for secondary controls that belong in the toolbar "More" menu.
   * These are the long-tail of canvas/studio toggles that would otherwise
   * crowd the primary toolbar.
   */
  const secondarySelectors = [
    '#gridToggle', '#rulersToggle', '#safeMarginToggle', '#copyObjects', '#pasteObjects',
    '#workflowV5Focus', '#workflowV6FlowBtn', '#eiFocusToggle', '.ei-experience-launch', '#eiTimelineLaunch', '#v13OperationsBtn'
  ];

  /**
   * Resolve the primary canvas toolbar element.
   * @returns {Element|null}
   */
  function toolbar() {
    return $('.stage-wrap > .studio-canvas-toolbar, .stage-wrap > .toolbar');
  }

  /**
   * Lazily build the "More" details menu inside the toolbar and wire its
   * outside-click / Escape dismissal. The menu is appended near the active
   * canvas label so it sits at the end of the primary toolbar group.
   * @returns {HTMLDetailsElement|null}
   */
  function ensureToolbarMore() {
    const bar = toolbar();
    if (!bar) return null;
    if (!toolbarMore) {
      toolbarMore = document.createElement('details');
      toolbarMore.id = 'v54ToolbarMore';
      toolbarMore.className = 'v54-toolbar-more';
      toolbarMore.innerHTML =
        '<summary aria-label="More canvas and studio tools">More <span aria-hidden="true">⌄</span></summary>' +
        '<div class="v54-toolbar-more-panel" role="group" aria-label="More canvas and studio tools"></div>';
      morePanel = $('.v54-toolbar-more-panel', toolbarMore);
      const label = $('#activeCanvasLabel', bar);
      if (label) bar.insertBefore(toolbarMore, label);
      else bar.append(toolbarMore);

      // Reflect open state onto aria-expanded for assistive tech.
      toolbarMore.addEventListener('toggle', () => {
        toolbarMore.querySelector('summary')?.setAttribute('aria-expanded', String(toolbarMore.open));
      });
      // Close on outside pointerdown.
      document.addEventListener('pointerdown', event => {
        if (toolbarMore?.open && !event.target.closest('#v54ToolbarMore')) toolbarMore.open = false;
      }, true);
      // Close on Escape and return focus to the summary.
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && toolbarMore?.open) {
          event.preventDefault();
          toolbarMore.open = false;
          toolbarMore.querySelector('summary')?.focus({ preventScroll: true });
        }
      }, true);
    }
    return toolbarMore;
  }

  /**
   * Move each secondary control into the "More" panel. Runs ONCE on install
   * (and again only if new controls appear after a resize), so the toolbar
   * layout is stable and icons do not jump on every selection/mutation.
   */
  function populateToolbarMore() {
    ensureToolbarMore();
    if (!morePanel) return;
    secondarySelectors.forEach(selector => {
      const element = $(selector);
      if (!element || moved.has(element) || element.closest('#v54ToolbarMore')) return;
      moved.add(element);
      element.classList.add('v54-toolbar-secondary');
      // Clear any inline positioning that the old module left behind so the
      // control lays out naturally inside the panel.
      ['left', 'right', 'top', 'bottom', 'transform'].forEach(prop => element.style.removeProperty(prop));
      morePanel.append(element);
    });
  }

  /**
   * Close the "More" menu after a panel button is activated.
   * @param {Event} event
   */
  function closeMoreAfterAction(event) {
    if (!toolbarMore?.open || !event.target.closest('.v54-toolbar-more-panel button')) return;
    requestAnimationFrame(() => { if (toolbarMore) toolbarMore.open = false; });
  }

  /**
   * Scroll the active page chip into view within the page dock track. Called
   * after navigation clicks and on resize.
   */
  function keepActivePageVisible() {
    const track = $('.workflow-page-dock-track');
    const active = $('.workflow-page-chip.active', track || document);
    if (!track || !active) return;
    const target = Math.max(0, active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2);
    if (Math.abs(track.scrollLeft - target) > 1) track.scrollTo({ left: target, behavior: 'auto' });
  }

  /**
   * Scroll the active tool button into view within its tool rail.
   * @param {ParentNode} [root=document]
   */
  function keepActiveToolVisible(root = document) {
    $$('.ei-tool-rail', root).forEach(rail => {
      const active = $('.active,[aria-pressed="true"]', rail);
      if (!active) return;
      const left = active.offsetLeft;
      const right = left + active.offsetWidth;
      const visibleLeft = rail.scrollLeft;
      const visibleRight = visibleLeft + rail.clientWidth;
      if (left < visibleLeft) rail.scrollTo({ left: Math.max(0, left - 8), behavior: 'auto' });
      else if (right > visibleRight) rail.scrollTo({ left: Math.max(0, right - rail.clientWidth + 8), behavior: 'auto' });
    });
  }

  /**
   * Promote the context toolbar to a stable, reserved row above the viewport.
   *
   * Unlike the old module, this NEVER toggles `display:none` (which caused
   * layout shift). Instead it reserves a stable min-height row and only
   * flips a `visible` class so the surrounding chrome never moves.
   */
  function ensureContextRow() {
    const wrap = $('.stage-wrap');
    const context = $('.ei-context-toolbar');
    if (!wrap || !context) return;

    if (!context.classList.contains('v54-context-row')) {
      context.classList.add('v54-context-row');
      const viewportEl = $('#canvasViewport', wrap);
      if (viewportEl) wrap.insertBefore(context, viewportEl);
      else wrap.append(context);
    }

    // Decide whether the context row has content worth showing. We check
    // children length and an explicit hide flag, but we never set
    // display:none — the reserved row keeps surrounding layout stable.
    const hasContent = context.children.length > 0 && context.style.display !== 'none';
    context.classList.toggle('visible', hasContent);
  }

  /**
   * Mark the page dock row as reserved so it keeps its slot in the column.
   */
  function ensureDockOrder() {
    const wrap = $('.stage-wrap');
    const dock = $('#workflowPageDock');
    if (wrap && dock && dock.parentElement === wrap) {
      dock.dataset.v54ReservedRow = 'true';
      requestAnimationFrame(keepActivePageVisible);
    }
  }

  /**
   * Debounced resize re-check: re-populate the More panel (in case new
   * controls appeared) and re-run the stability passes. Toolbar buttons keep
   * their positions; only overflow discovery runs.
   */
  function onResize() {
    if (resizeRaf) return;
    resizeRaf = requestAnimationFrame(() => {
      resizeRaf = 0;
      populateToolbarMore();
      ensureContextRow();
      ensureDockOrder();
      keepActivePageVisible();
      keepActiveToolVisible();
    });
  }

  // =========================================================================
  // Sidebar labels — full text + collapse-to-icons toggle (bug #4)
  // =========================================================================
  /** localStorage key for the sidebar collapse preference. */
  const SIDEBAR_KEY = 'einvite-v54-sidebar-collapsed';

  /**
   * Read the persisted sidebar collapse preference.
   * @returns {boolean}
   */
  function sidebarCollapsed() {
    try { return localStorage.getItem(SIDEBAR_KEY) === '1'; } catch { return false; }
  }

  /**
   * Apply (or clear) the sidebar collapsed state. Collapsed shows icons only;
   * expanded shows full category labels so "Elements"/"Uploads" are readable.
   * @param {boolean} collapsed
   */
  function setSidebarCollapsed(collapsed) {
    body.classList.toggle('sidebar-collapsed', collapsed);
    try { localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0'); } catch { /* ignore */ }
    const toggle = $('#v54SidebarCollapse');
    if (toggle) {
      toggle.setAttribute('aria-pressed', String(collapsed));
      toggle.title = collapsed ? 'Show labels' : 'Show icons only';
      const label = toggle.querySelector('.v54-collapse-label');
      if (label) label.textContent = collapsed ? '›' : '‹';
    }
  }

  /**
   * Inject a collapse toggle button into the tool rail header so the user can
   * switch between "full labels" and "icon-only" modes. Idempotent.
   */
  function ensureSidebarCollapseButton() {
    if ($('#v54SidebarCollapse')) return;
    const rail = $('.studio-tool-rail');
    if (!rail) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'v54SidebarCollapse';
    button.className = 'v54-sidebar-collapse';
    button.setAttribute('aria-pressed', String(sidebarCollapsed()));
    button.title = sidebarCollapsed() ? 'Show labels' : 'Show icons only';
    button.innerHTML = '<span class="v54-collapse-label" aria-hidden="true">‹</span><span class="sr-only">Toggle sidebar labels</span>';
    button.addEventListener('click', () => setSidebarCollapsed(!body.classList.contains('sidebar-collapsed')));
    // Place at the top of the rail so it is always reachable.
    rail.prepend(button);
  }

  // =========================================================================
  // Wiring
  // =========================================================================
  /**
   * One-shot install: build chrome once, then attach only lightweight
   * scroll-into-view listeners. Crucially, we do NOT observe every DOM
   * mutation — that was the source of the "jumping" toolbar.
   */
  function install() {
    populateToolbarMore();
    ensureContextRow();
    ensureDockOrder();
    ensureSidebarCollapseButton();
    setSidebarCollapsed(sidebarCollapsed());
    keepActivePageVisible();
    keepActiveToolVisible();

    document.addEventListener('click', closeMoreAfterAction, true);
    // Keep the active page/tool scrolled into view after navigation clicks —
    // this is cheap and does not move toolbar chrome.
    document.addEventListener('click', event => {
      if (event.target.closest('.workflow-page-chip,.workflow-page-add,#workflowV7DockFlow')) requestAnimationFrame(keepActivePageVisible);
      if (event.target.closest('.ei-tool-rail button')) requestAnimationFrame(keepActiveToolVisible);
    }, true);

    // Re-check overflow only on resize, not on every state change.
    window.addEventListener('resize', onResize, { passive: true });

    // Re-run the stability passes once the editor is ready / state applied —
    // but throttled and NOT on every selection (which would re-introduce
    // jumping). The context-row class is cheap to re-assert.
    window.addEventListener('einvite:state-applied', () => setTimeout(() => { ensureContextRow(); keepActivePageVisible(); }, 80));
    document.addEventListener('einvite:editor-ready', () => setTimeout(() => { ensureContextRow(); ensureDockOrder(); }, 80));

    // Expose API for other modules / debugging.
    window.EInviteUiLayout = Object.freeze({
      version: 54,
      refresh: () => { populateToolbarMore(); ensureContextRow(); ensureDockOrder(); keepActivePageVisible(); keepActiveToolVisible(); },
      setSidebarCollapsed,
      sidebarCollapsed
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
