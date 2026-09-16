/**
 * ui-components.js — Editor workspace components (v54 refactor).
 *
 * A small, focused module that fixes text-overflow defects in the workspace
 * navigation chrome (bug #5: "Navigation Overflow — workspace navigation
 * cards/bubbles must expand or wrap text to fully contain long words").
 *
 * The root cause: many navigation surfaces use `white-space:nowrap` or omit an
 * `overflow-wrap` rule, so a single long word (a long invitation title, a
 * guest name, a venue, a template name) spills outside its card and overlaps
 * neighbours. CSS alone can fix the wrapping; this module additionally:
 *
 *   • Classifies workspace navigation surfaces so the CSS in
 *     `editor-styles.css` has stable hooks to target.
 *   • Provides a tiny progressive-enhancement that measures whether a card's
 *     text still overflows after wrapping and, if so, expands the card's
 *     min-height so the text is never clipped.
 *   • Adds a "long-word" guard to user-generated bubbles (page chips,
 *     layer rows, invite/material cards) so the layout stays predictable.
 *
 * Idempotent: a second load is a no-op.
 */
(() => {
  'use strict';
  if (window.EInviteUiComponents?.version >= 54) return;

  /** @type {(selector:string, root?:ParentNode)=>Element[]} */
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /**
   * CSS selectors for the workspace navigation surfaces whose text must never
   * spill. Shared between the tagging pass and the overflow-measurement pass.
   */
  const NAV_SURFACE_SELECTORS = [
    // Studio rail + pane cards
    '.studio-rail-button',
    '.studio-quick-grid button',
    '.studio-tip-card',
    '.page-nav-card',
    // Workflow chips/bubbles
    '.workflow-page-chip',
    '.workflow-page-chip strong',
    '.workflow-recent-grid button',
    '.workflow-search-results button',
    // Library / material / invite cards
    '.invite-card .invite-body h2',
    '.invite-card .actions button',
    '.material-card-page',
    '.studio-card',
    '.template-choice',
    '.template-live-thumb',
    // Layer rows + command palette rows
    '.layer-row',
    '.v23-command-row',
    // Dashboard overview + filter tabs
    '.dashboard-overview-cards article',
    '.dashboard-filter-tabs button',
    // Inspector headings / labels
    '.studio-inspector-heading strong',
    '.studio-pane-heading h1'
  ];

  /**
   * Tag every matching surface with a stable hook class so the CSS rules in
   * `editor-styles.css` can apply wrapping without fragile selector chains.
   * Idempotent (the class is only added once).
   */
  function tagNavSurfaces() {
    NAV_SURFACE_SELECTORS.forEach(selector => {
      $$(selector).forEach(node => {
        if (!node.classList.contains('v54-nav-text')) node.classList.add('v54-nav-text');
      });
    });
  }

  /**
   * Progressive enhancement: after the browser applies the CSS wrapping
   * rules, some cards may still be too short for their (now-wrapped) text and
   * would clip it. Measure scrollHeight vs. clientHeight and expand the
   * min-height so the full text is visible.
   *
   * This runs on a ResizeObserver of the stage + on editor events, throttled.
   */
  let expandRaf = 0;
  /**
   * Expand any nav card whose wrapped text is taller than its box.
   */
  function expandOverflowingCards() {
    if (expandRaf) return;
    expandRaf = requestAnimationFrame(() => {
      expandRaf = 0;
      $$('.v54-nav-text').forEach(node => {
        // Only measure leaf text containers (skip wrappers without their own
        // text height).
        if (node.scrollHeight - node.clientHeight > 2) {
          node.style.minHeight = `${Math.ceil(node.scrollHeight)}px`;
        }
      });
    });
  }

  /**
   * Observe the stage + panes for content changes that may introduce new nav
   * surfaces (e.g. switching tabs renders a new list of cards), then re-tag
   * and re-measure. Throttled via rAF so bursts are cheap.
   */
  function observeSurfaces() {
    const target = document.querySelector('#stage, .studio-pane-host, .studio-inspector-host');
    if (!target || typeof MutationObserver === 'undefined') return;
    const observer = new MutationObserver(() => {
      tagNavSurfaces();
      expandOverflowingCards();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    // Re-measure on resize as font metrics / widths change.
    window.addEventListener('resize', () => { tagNavSurfaces(); expandOverflowingCards(); }, { passive: true });
  }

  /**
   * Install the module.
   */
  function install() {
    tagNavSurfaces();
    expandOverflowingCards();
    observeSurfaces();
    // Defer a second pass so fonts have loaded and metrics are final.
    if (document.fonts?.ready?.then) {
      document.fonts.ready.then(() => { tagNavSurfaces(); expandOverflowingCards(); });
    }
    window.EInviteUiComponents = Object.freeze({
      version: 54,
      refresh: () => { tagNavSurfaces(); expandOverflowingCards(); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
