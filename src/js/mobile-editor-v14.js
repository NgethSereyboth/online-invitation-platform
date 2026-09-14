(() => {
  'use strict';
  if (window.__einviteMobileEditorV14) return;
  window.__einviteMobileEditorV14 = true;
  const body = document.body;
  const stage = document.getElementById('stage');
  const left = document.querySelector('aside.left');
  const right = document.querySelector('aside.right');
  if (!body || !stage || !left || !right) return;
  body.classList.add('mobile-editor-v14');
  const mq = matchMedia('(max-width: 600px)');
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  let returnFocus = null;
  let fitTimer = 0;
  function fitMobileCanvas(delay = 80) {
    if (!mq.matches) return;
    clearTimeout(fitTimer);
    fitTimer = setTimeout(() => {
      const fit = document.getElementById('fitCanvas');
      if (fit && body.dataset.mobileEditorMode === 'canvas') fit.click();
    }, delay);
  }
  function setHiddenState(panel, hidden) {
    if (!panel) return;
    panel.setAttribute('aria-hidden', String(hidden));
    if ('inert' in panel) panel.inert = hidden;
  }
  function currentMode() {
    if (body.classList.contains('mobile-creation-open')) return 'tools';
    if (body.classList.contains('mobile-inspector-open')) return 'quick';
    return 'canvas';
  }
  function sync() {
    const mobile = mq.matches;
    const mode = mobile ? currentMode() : 'desktop';
    body.dataset.mobileEditorMode = mode;
    if (!mobile) {
      body.classList.remove('mobile-creation-open', 'mobile-inspector-open', 'mobile-advanced-open');
      setHiddenState(left, false); setHiddenState(right, false);
    } else {
      setHiddenState(left, mode !== 'tools');
      setHiddenState(right, mode !== 'quick');
    }
    $$('#mobileEditorV14Bar [data-mobile-mode]').forEach(button => {
      const active = button.dataset.mobileMode === mode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
      button.setAttribute('aria-expanded', String(active && mode !== 'canvas'));
    });
  }
  function openMode(mode, trigger) {
    if (!mq.matches) return;
    returnFocus = trigger || document.activeElement;
    body.classList.toggle('mobile-creation-open', mode === 'tools');
    body.classList.toggle('mobile-inspector-open', mode === 'quick');
    body.classList.remove('mobile-advanced-open');
    sync();
    if (mode === 'tools') $('.studio-pane.active input, .studio-pane.active button, .studio-pane.active select, .studio-pane.active textarea, .studio-rail-button')?.focus({preventScroll:true});
    if (mode === 'quick') $('.studio-inspector-pane.active input, .studio-inspector-pane.active button, .studio-inspector-tab')?.focus({preventScroll:true});
    if (mode === 'canvas') {
      stage.focus?.({preventScroll:true});
      fitMobileCanvas();
      if (returnFocus instanceof HTMLElement && returnFocus.id !== 'mobileCanvasMode') returnFocus = null;
    }
  }
  const bar = document.createElement('nav');
  bar.id = 'mobileEditorV14Bar';
  bar.className = 'mobile-editor-v14-bar';
  bar.setAttribute('aria-label', 'Mobile editor controls');
  bar.innerHTML = `
    <button type="button" id="mobileCanvasMode" data-mobile-mode="canvas" aria-pressed="true"><span aria-hidden="true">▣</span><small>Canvas</small></button>
    <button type="button" id="mobileToolsMode" data-a11y-managed="true" data-mobile-mode="tools" aria-controls="mobileCreationPanel" aria-expanded="false"><span aria-hidden="true">＋</span><small>Tools</small></button>
    <button type="button" id="mobileQuickMode" data-a11y-managed="true" data-mobile-mode="quick" aria-controls="mobileQuickInspector" aria-expanded="false"><span aria-hidden="true">✎</span><small>Quick Edit</small></button>
    <button type="button" id="mobilePreviewV14"><span aria-hidden="true">◉</span><small>Preview</small></button>
    <button type="button" id="mobilePublishV14"><span aria-hidden="true">↗</span><small>Publish</small></button>
    <button type="button" id="mobileAdvancedV14" aria-haspopup="dialog"><span aria-hidden="true">•••</span><small>Advanced</small></button>`;
  document.body.append(bar);
  left.id ||= 'mobileCreationPanel';
  right.id ||= 'mobileQuickInspector';
  bar.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.dataset.mobileMode) return openMode(button.dataset.mobileMode, button);
    if (button.id === 'mobilePreviewV14') return document.getElementById('previewBtn')?.click();
    if (button.id === 'mobilePublishV14') return document.getElementById('publishBtn')?.click();
    if (button.id === 'mobileAdvancedV14') openAdvanced(button);
  });
  const advanced = document.createElement('dialog');
  advanced.id = 'mobileAdvancedDialogV14';
  advanced.className = 'mobile-advanced-v14';
  advanced.setAttribute('aria-labelledby', 'mobileAdvancedTitleV14');
  advanced.innerHTML = `<div class="mobile-advanced-head"><div><small>Advanced tools</small><h2 id="mobileAdvancedTitleV14">More editor capabilities</h2></div><button type="button" data-close aria-label="Close advanced tools">×</button></div>
    <p>Advanced photo, animation and studio operations stay out of the mobile canvas until you need them.</p>
    <div class="mobile-advanced-grid">
      <button type="button" data-launch=".ei-experience-launch">Style &amp; experience</button>
      <button type="button" data-launch="#eiFocusToggle">Focus mode</button>
      <button type="button" data-launch="#eiTimelineLaunch">Animation timeline</button>
      <button type="button" data-launch="#v13OperationsBtn">Studio operations</button>
      <button type="button" data-launch="#photoEditorLaunch,#openPhotoEditor,[data-photo-editor-open]">Photo editor</button>
      <button type="button" data-launch="#canvasPlusAiTools,.ai-fab,[data-ai-open]">AI tools</button>
      <button type="button" data-inspector="layers">Layers</button>
      <button type="button" data-inspector="sections">Sections & order</button>
    </div>`;
  document.body.append(advanced);
  function openAdvanced(trigger) {
    returnFocus = trigger;
    body.classList.add('mobile-advanced-open');
    advanced.showModal();
    advanced.querySelector('[data-close]')?.focus();
  }
  function closeAdvanced() {
    if (advanced.open) advanced.close();
    body.classList.remove('mobile-advanced-open');
    returnFocus?.focus?.({preventScroll:true});
  }
  advanced.addEventListener('click', event => {
    if (event.target === advanced || event.target.closest('[data-close]')) return closeAdvanced();
    const launch = event.target.closest('[data-launch]');
    if (launch) {
      const target = launch.dataset.launch.split(',').map(x => $(x.trim())).find(Boolean);
      closeAdvanced();
      target?.click();
      return;
    }
    const inspector = event.target.closest('[data-inspector]');
    if (inspector) {
      closeAdvanced();
      openMode('quick', document.getElementById('mobileQuickMode'));
      right.querySelector(`[data-inspector-tab="${CSS.escape(inspector.dataset.inspector)}"]`)?.click();
    }
  });
  advanced.addEventListener('cancel', event => { event.preventDefault(); closeAdvanced(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && mq.matches && !advanced.open && currentMode() !== 'canvas') {
      event.preventDefault(); openMode('canvas', document.getElementById('mobileCanvasMode'));
    }
  }, true);
  stage.addEventListener('pointerdown', () => {
    if (mq.matches && currentMode() !== 'canvas') openMode('canvas', document.getElementById('mobileCanvasMode'));
  }, true);
  document.addEventListener('click', event => {
    if (!mq.matches) return;
    if (event.target.closest('[data-studio-tab]')) {
      body.classList.add('mobile-creation-open'); body.classList.remove('mobile-inspector-open'); sync();
    }
    if (event.target.closest('[data-inspector-tab]')) {
      body.classList.add('mobile-inspector-open'); body.classList.remove('mobile-creation-open'); sync();
    }
  }, true);
  mq.addEventListener?.('change', event => { sync(); if (event.matches) fitMobileCanvas(120); });
  addEventListener('resize', () => { sync(); if (mq.matches) fitMobileCanvas(140); }, {passive:true});
  document.addEventListener('einvite:server-connected', () => fitMobileCanvas(160));
  document.addEventListener('einvite:editor-ready', () => fitMobileCanvas(120));
  requestAnimationFrame(() => { if (mq.matches) openMode('canvas', document.getElementById('mobileCanvasMode')); else sync(); });
})();
