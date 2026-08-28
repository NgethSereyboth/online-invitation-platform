(() => {
  'use strict';
  if (window.__einviteWindowsUiV16) return;
  window.__einviteWindowsUiV16 = true;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const body = document.body;
  if (!body || !$('#stage')) return;
  body.classList.add('windows-ui-v16');
  let toolbarMore;
  let morePanel;
  const moved = new Set();
  const secondarySelectors = [
    '#gridToggle', '#rulersToggle', '#safeMarginToggle', '#copyObjects', '#pasteObjects',
    '#workflowV5Focus', '#workflowV6FlowBtn', '#eiFocusToggle', '.ei-experience-launch', '#eiTimelineLaunch', '#v13OperationsBtn'
  ];
  function toolbar() {
    return $('.stage-wrap > .studio-canvas-toolbar, .stage-wrap > .toolbar');
  }
  function ensureToolbarMore() {
    const bar = toolbar();
    if (!bar) return null;
    if (!toolbarMore) {
      toolbarMore = document.createElement('details');
      toolbarMore.id = 'v16ToolbarMore';
      toolbarMore.className = 'v16-toolbar-more';
      toolbarMore.innerHTML = '<summary aria-label="More canvas and studio tools">More <span aria-hidden="true">⌄</span></summary><div class="v16-toolbar-more-panel" role="group" aria-label="More canvas and studio tools"></div>';
      morePanel = $('.v16-toolbar-more-panel', toolbarMore);
      const label = $('#activeCanvasLabel', bar);
      if (label) bar.insertBefore(toolbarMore, label);
      else bar.append(toolbarMore);
      toolbarMore.addEventListener('toggle', () => {
        toolbarMore.querySelector('summary')?.setAttribute('aria-expanded', String(toolbarMore.open));
      });
      document.addEventListener('pointerdown', event => {
        if (toolbarMore?.open && !event.target.closest('#v16ToolbarMore')) toolbarMore.open = false;
      }, true);
      document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && toolbarMore?.open) {
          event.preventDefault();
          toolbarMore.open = false;
          toolbarMore.querySelector('summary')?.focus({preventScroll: true});
        }
      }, true);
    }
    return toolbarMore;
  }
  function moveSecondaryControls() {
    ensureToolbarMore();
    if (!morePanel) return;
    secondarySelectors.forEach(selector => {
      const element = $(selector);
      if (!element || moved.has(element) || element.closest('#v16ToolbarMore')) return;
      moved.add(element);
      element.classList.add('v16-toolbar-secondary');
      element.style.removeProperty('left');
      element.style.removeProperty('right');
      element.style.removeProperty('top');
      element.style.removeProperty('bottom');
      element.style.removeProperty('transform');
      morePanel.append(element);
    });
  }
  function closeMoreAfterAction(event) {
    if (!toolbarMore?.open || !event.target.closest('.v16-toolbar-more-panel button')) return;
    requestAnimationFrame(() => { if (toolbarMore) toolbarMore.open = false; });
  }
  document.addEventListener('click', closeMoreAfterAction, true);
  function keepActivePageVisible() {
    const track = $('.workflow-page-dock-track');
    const active = $('.workflow-page-chip.active', track || document);
    if (!track || !active) return;
    const target = Math.max(0, active.offsetLeft - (track.clientWidth - active.offsetWidth) / 2);
    if (Math.abs(track.scrollLeft - target) > 1) track.scrollTo({left: target, behavior: 'auto'});
  }
  function keepActiveToolVisible(root = document) {
    $$('.ei-tool-rail', root).forEach(rail => {
      const active = $('.active,[aria-pressed="true"]', rail);
      if (!active) return;
      const left = active.offsetLeft;
      const right = left + active.offsetWidth;
      const visibleLeft = rail.scrollLeft;
      const visibleRight = visibleLeft + rail.clientWidth;
      if (left < visibleLeft) {
        rail.scrollTo({left: Math.max(0, left - 8), behavior: 'auto'});
      } else if (right > visibleRight) {
        rail.scrollTo({left: Math.max(0, right - rail.clientWidth + 8), behavior: 'auto'});
      }
    });
  }
  function ensureContextRow() {
    const wrap = $('.stage-wrap');
    const context = $('.ei-context-toolbar');
    if (!wrap || !context) return;
    if (!context.classList.contains('v16-context-row')) {
      context.classList.add('v16-context-row');
      const viewport = $('#canvasViewport', wrap);
      if (viewport) wrap.insertBefore(context, viewport);
      else wrap.append(context);
    }
  }
  function ensureDockOrder() {
    const wrap = $('.stage-wrap');
    const dock = $('#workflowPageDock');
    if (wrap && dock && dock.parentElement === wrap) {
      dock.dataset.v16ReservedRow = 'true';
      requestAnimationFrame(keepActivePageVisible);
    }
  }
  function sync() {
    moveSecondaryControls();
    ensureContextRow();
    ensureDockOrder();
    keepActivePageVisible();
    keepActiveToolVisible();
  }
  document.addEventListener('click', event => {
    if (event.target.closest('.workflow-page-chip,.workflow-page-add,#workflowV7DockFlow')) requestAnimationFrame(keepActivePageVisible);
    if (event.target.closest('.ei-tool-rail button')) requestAnimationFrame(keepActiveToolVisible);
  }, true);
  window.addEventListener('einvite:state-applied', () => setTimeout(sync, 80));
  document.addEventListener('einvite:editor-ready', () => setTimeout(sync, 80));
  window.addEventListener('resize', () => requestAnimationFrame(sync), {passive: true});
  const observer = new MutationObserver(mutations => {
    const relevant = mutations.some(mutation => mutation.type === 'childList' || mutation.attributeName === 'class' || mutation.attributeName === 'aria-pressed');
    if (relevant) requestAnimationFrame(sync);
  });
  observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'aria-pressed']});
  requestAnimationFrame(sync);
})();
