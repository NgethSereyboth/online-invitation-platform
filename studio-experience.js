/*
 * E-invitation-website — Studio Experience Layer
 * ------------------------------------------------
 * A non-destructive UX enhancement layer loaded after app.js.
 * It reorganizes the existing editor controls into a modern creation studio
 * without changing the invitation document schema or existing event handlers.
 */
(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const body = document.body;
  if (!body || !$('#stage') || !$('.left') || !$('.right')) return;

  body.classList.add('studio-experience');

  const icon = {
    event: '◈', pages: '▤', media: '▧', blocks: '▦', elements: '✦',
    object: '◌', layers: '≡', sections: '▥', theme: '◐', publish: '↗'
  };

  function text(node) { return (node?.textContent || '').trim(); }
  function button(label, className = '') {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = label; if (className) b.className = className;
    return b;
  }

  // ---------------------------------------------------------------------------
  // Top application chrome
  // ---------------------------------------------------------------------------
  const header = $('body > header');
  if (header) {
    header.classList.add('studio-topbar');
    const brand = header.querySelector('strong');
    if (brand) {
      brand.innerHTML = '<span class="studio-brand-mark">E</span><span class="studio-brand-copy"><b>E-invitation</b><small>Design Studio</small></span>';
    }

    const titleWrap = document.createElement('div');
    titleWrap.className = 'studio-document-title';
    titleWrap.innerHTML = '<span class="studio-doc-label">Editing</span><strong id="studioDocName">Invitation</strong>';
    const saveState = $('#saveState');
    if (saveState) header.insertBefore(titleWrap, saveState);

    const commandButton = button('Quick actions', 'studio-command-trigger');
    commandButton.id = 'studioCommandBtn';
    commandButton.title = 'Quick actions (Ctrl/Cmd + K)';
    const checkButton = button('Design check', 'studio-check-trigger');
    checkButton.id = 'studioCheckBtn';
    checkButton.title = 'Review invitation readiness and accessibility';
    const preview = $('#previewBtn');
    if (preview) header.insertBefore(commandButton, preview);
    if (preview) header.insertBefore(checkButton, preview);

    const updateTitle = () => {
      const name = ($('#names')?.value || '').trim() || 'Untitled invitation';
      const target = $('#studioDocName');
      if (target) target.textContent = name;
    };
    $('#names')?.addEventListener('input', updateTitle);
    window.addEventListener('einvite:state-applied', updateTitle);
    updateTitle();
  }

  // ---------------------------------------------------------------------------
  // Left creation rail — Event / Pages / Media / Blocks / Elements
  // ---------------------------------------------------------------------------
  const left = $('.left');
  const leftGroupMap = {
    'Content': 'event',
    'Host contact': 'event',
    'Guest response': 'event',
    'Invitation sections': 'pages',
    'Visual page builder': 'pages',
    'Materials': 'media',
    'Gallery photos': 'media',
    'Custom sections': 'blocks',
    'Elements': 'elements',
    'Reusable element groups': 'elements'
  };

  function buildTabbedSide(container, config) {
    const original = [...container.children];
    const groups = new Map(config.tabs.map(tab => [tab.id, []]));
    let current = config.tabs[0].id;
    for (const node of original) {
      if (node.matches?.('h2') && config.map[text(node)]) current = config.map[text(node)];
      if (!groups.has(current)) groups.set(current, []);
      groups.get(current).push(node);
    }

    container.innerHTML = '';
    container.classList.add(config.className);
    const nav = document.createElement('nav'); nav.className = config.navClass;
    nav.setAttribute('aria-label', config.label);
    const host = document.createElement('div'); host.className = config.hostClass;

    const panes = new Map();
    config.tabs.forEach((tab, index) => {
      const navButton = button('', config.buttonClass);
      navButton.dataset.studioTab = tab.id;
      navButton.innerHTML = `<span class="studio-nav-icon">${tab.icon}</span><span>${tab.label}</span>`;
      navButton.title = tab.title || tab.label;
      nav.append(navButton);

      const pane = document.createElement('section');
      pane.className = `${config.paneClass}${index === 0 ? ' active' : ''}`;
      pane.dataset.studioPane = tab.id;
      const paneHead = document.createElement('div');
      paneHead.className = 'studio-pane-heading';
      paneHead.innerHTML = `<div><small>${config.eyebrow || 'Create'}</small><h1>${tab.label}</h1></div>`;
      pane.append(paneHead);
      (groups.get(tab.id) || []).forEach(node => pane.append(node));
      host.append(pane); panes.set(tab.id, pane);

      navButton.addEventListener('click', () => config.activate(tab.id));
    });
    container.append(nav, host);
    return { nav, host, panes };
  }

  let leftTabs;
  const activateLeft = id => {
    if (!leftTabs) return;
    $$('[data-studio-tab]', leftTabs.nav).forEach(b => b.classList.toggle('active', b.dataset.studioTab === id));
    $$('[data-studio-pane]', leftTabs.host).forEach(p => p.classList.toggle('active', p.dataset.studioPane === id));
    localStorage.setItem('einvite-editor-left-tab', id);
  };
  leftTabs = buildTabbedSide(left, {
    tabs: [
      { id: 'event', label: 'Event', icon: icon.event, title: 'Event information and guest settings' },
      { id: 'pages', label: 'Pages', icon: icon.pages, title: 'Invitation pages and structure' },
      { id: 'media', label: 'Uploads', icon: icon.media, title: 'Photos, video and music' },
      { id: 'blocks', label: 'Blocks', icon: icon.blocks, title: 'Reusable invitation content blocks' },
      { id: 'elements', label: 'Elements', icon: icon.elements, title: 'Text, shapes and decorations' }
    ],
    map: leftGroupMap,
    className: 'studio-left-panel', navClass: 'studio-tool-rail', hostClass: 'studio-pane-host',
    buttonClass: 'studio-rail-button', paneClass: 'studio-pane', label: 'Creation tools', eyebrow: 'Create', activate: activateLeft
  });
  activateLeft(localStorage.getItem('einvite-editor-left-tab') || 'event');

  // Search the currently open creation pane.
  const leftSearch = document.createElement('div');
  leftSearch.className = 'studio-panel-search';
  leftSearch.innerHTML = '<span>⌕</span><input type="search" placeholder="Search tools and settings…" aria-label="Search creation tools">';
  leftTabs.host.insertBefore(leftSearch, leftTabs.host.firstChild);
  const leftSearchInput = leftSearch.querySelector('input');
  leftSearchInput.addEventListener('input', () => {
    const q = leftSearchInput.value.trim().toLowerCase();
    const pane = $('.studio-pane.active', leftTabs.host);
    if (!pane) return;
    [...pane.children].forEach(node => {
      if (node.classList.contains('studio-pane-heading')) return;
      node.classList.toggle('studio-search-hidden', !!q && !text(node).toLowerCase().includes(q));
    });
  });
  $$('[data-studio-tab]', leftTabs.nav).forEach(b => b.addEventListener('click', () => {
    leftSearchInput.value = '';
    $$('.studio-search-hidden', leftTabs.host).forEach(x => x.classList.remove('studio-search-hidden'));
  }));

  // ---------------------------------------------------------------------------
  // Right inspector tabs — Object / Layers / Sections / Theme / Publish
  // ---------------------------------------------------------------------------
  const right = $('.right');
  const rightGroupMap = {
    'Style & motion': 'object',
    'Layers': 'layers',
    'Section motion': 'sections',
    'Section appearance': 'sections',
    'Template & palette': 'theme',
    'Reusable invitation template': 'theme',
    'Publishing': 'publish'
  };
  let rightTabs;
  const activateRight = id => {
    if (!rightTabs) return;
    $$('[data-inspector-tab]', rightTabs.nav).forEach(b => b.classList.toggle('active', b.dataset.inspectorTab === id));
    $$('[data-inspector-pane]', rightTabs.host).forEach(p => p.classList.toggle('active', p.dataset.inspectorPane === id));
    localStorage.setItem('einvite-editor-right-tab', id);
  };

  function buildInspector() {
    const original = [...right.children];
    const tabs = [
      { id: 'object', label: 'Edit', icon: icon.object },
      { id: 'layers', label: 'Layers', icon: icon.layers },
      { id: 'sections', label: 'Sections', icon: icon.sections },
      { id: 'theme', label: 'Design', icon: icon.theme },
      { id: 'publish', label: 'Share', icon: icon.publish }
    ];
    const groups = new Map(tabs.map(t => [t.id, []]));
    let current = 'object';
    original.forEach(node => {
      if (node.matches?.('h2') && rightGroupMap[text(node)]) current = rightGroupMap[text(node)];
      groups.get(current)?.push(node);
    });
    right.innerHTML = '';
    right.classList.add('studio-inspector');
    const nav = document.createElement('nav'); nav.className = 'studio-inspector-tabs';
    const host = document.createElement('div'); host.className = 'studio-inspector-host';
    tabs.forEach((tab, index) => {
      const b = button('', 'studio-inspector-tab');
      b.dataset.inspectorTab = tab.id;
      b.innerHTML = `<span>${tab.icon}</span><small>${tab.label}</small>`;
      b.onclick = () => activateRight(tab.id);
      nav.append(b);
      const pane = document.createElement('section');
      pane.dataset.inspectorPane = tab.id;
      pane.className = `studio-inspector-pane${index === 0 ? ' active' : ''}`;
      const head = document.createElement('div'); head.className = 'studio-inspector-heading';
      head.innerHTML = `<small>Inspector</small><strong>${tab.label}</strong>`;
      pane.append(head);
      (groups.get(tab.id) || []).forEach(node => pane.append(node));
      host.append(pane);
    });
    right.append(nav, host);
    return { nav, host };
  }
  rightTabs = buildInspector();
  activateRight(localStorage.getItem('einvite-editor-right-tab') || 'object');

  // Automatically expose object properties when an object is selected.
  $('#stage').addEventListener('pointerdown', event => {
    if (event.target.closest('.object')) setTimeout(() => activateRight('object'), 0);
  }, true);

  // ---------------------------------------------------------------------------
  // Quick insert / design recipes
  // ---------------------------------------------------------------------------
  const elementsPane = $('[data-studio-pane="elements"]', leftTabs.host);
  if (elementsPane) {
    const quick = document.createElement('section');
    quick.className = 'studio-quick-insert';
    quick.innerHTML = `
      <div class="studio-section-title"><div><small>Invitation essentials</small><strong>Quick insert</strong></div></div>
      <div class="studio-quick-grid">
        <button type="button" data-text-preset="heading"><span>Aa</span><strong>Heading</strong><small>Large editorial title</small></button>
        <button type="button" data-text-preset="subheading"><span>Ag</span><strong>Subheading</strong><small>Elegant supporting text</small></button>
        <button type="button" data-text-preset="body"><span>¶</span><strong>Body text</strong><small>Readable event copy</small></button>
        <button type="button" data-text-preset="khmer"><span>ក</span><strong>Khmer title</strong><small>Ceremonial Khmer style</small></button>
        <button type="button" data-smart-insert="monogram"><span>✦</span><strong>Monogram</strong><small>Couple initials</small></button>
        <button type="button" data-smart-insert="date"><span>◫</span><strong>Date badge</strong><small>Styled event date</small></button>
      </div>`;
    const heading = $('.studio-pane-heading', elementsPane);
    heading?.after(quick);
  }

  function fire(id, eventName = 'input') {
    const el = document.getElementById(id); if (!el) return;
    el.dispatchEvent(new Event(eventName, { bubbles: true }));
  }
  function setValue(id, value, eventName = 'input') {
    const el = document.getElementById(id); if (!el) return;
    el.value = value; fire(id, eventName);
  }
  function setTextPreset(kind, customText) {
    $('#addText')?.click();
    const presets = {
      heading: { text: customText || 'Your beautiful moment', font: 'Georgia,serif', size: 54, align: 'center', spacing: 0, line: 1.1 },
      subheading: { text: customText || 'Together with our families', font: 'Georgia,serif', size: 24, align: 'center', spacing: 0.5, line: 1.35 },
      body: { text: customText || 'Add your invitation message here.', font: 'Arial,sans-serif', size: 17, align: 'center', spacing: 0, line: 1.65 },
      khmer: { text: customText || 'សិរីមង្គលអាពាហ៍ពិពាហ៍', font: "'Khmer OS Muol Light','Noto Serif Khmer',serif", size: 38, align: 'center', spacing: 0, line: 1.65 }
    };
    const p = presets[kind] || presets.body;
    setValue('textContent', p.text, 'input');
    setValue('font', p.font, 'change');
    setValue('fontSize', p.size, 'input');
    setValue('textAlign', p.align, 'change');
    setValue('letterSpacing', p.spacing, 'input');
    setValue('lineHeight', p.line, 'input');
  }
  $$('[data-text-preset]').forEach(b => b.onclick = () => setTextPreset(b.dataset.textPreset));
  $$('[data-smart-insert]').forEach(b => b.onclick = () => {
    if (b.dataset.smartInsert === 'monogram') {
      const names = ($('#names')?.value || 'A & B').split(/&|and/i).map(x => x.trim()).filter(Boolean);
      const initials = names.slice(0, 2).map(x => x[0]?.toUpperCase() || '').join(' · ') || 'A · B';
      setTextPreset('heading', initials);
      setValue('fontSize', 72, 'input'); setValue('letterSpacing', 5, 'input');
      setValue('color', $('#accent')?.value || '#9d4555', 'input');
    } else if (b.dataset.smartInsert === 'date') {
      const raw = $('#date')?.value;
      let label = 'SAVE THE DATE';
      if (raw) {
        const d = new Date(`${raw}T00:00:00`);
        if (!Number.isNaN(d.getTime())) label = d.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' }).toUpperCase();
      }
      setTextPreset('subheading', label);
      setValue('fontSize', 19, 'input'); setValue('letterSpacing', 3, 'input');
    }
  });

  // Contextual style recipes in the object inspector.
  const objectPane = $('[data-inspector-pane="object"]', rightTabs.host);
  if (objectPane) {
    const recipes = document.createElement('div');
    recipes.className = 'studio-style-recipes';
    recipes.innerHTML = `
      <div class="studio-section-title"><div><small>One-click styling</small><strong>Design recipes</strong></div></div>
      <div class="studio-chip-row">
        <button type="button" data-recipe="editorial">Editorial</button>
        <button type="button" data-recipe="gold">Gold detail</button>
        <button type="button" data-recipe="glass">Glass card</button>
        <button type="button" data-recipe="soft">Soft depth</button>
        <button type="button" data-recipe="clean">Reset style</button>
      </div>`;
    $('.studio-inspector-heading', objectPane)?.after(recipes);
  }
  function applyRecipe(name) {
    const selectedCount = $$('.object.selected,.object.multi-selected').length;
    if (!selectedCount) return alert('Select one or more objects first.');
    const recipes = {
      editorial: { opacity: 100, borderWidth: 0, borderRadius: 0, shadowBlur: 0 },
      gold: { opacity: 100, borderWidth: 2, borderColor: '#c49a48', borderRadius: 14, shadowBlur: 10, shadowColor: '#704c1b' },
      glass: { opacity: 88, borderWidth: 1, borderColor: '#ffffff', borderRadius: 24, shadowBlur: 28, shadowColor: '#000000' },
      soft: { opacity: 100, borderWidth: 0, borderRadius: 18, shadowBlur: 24, shadowColor: '#000000' },
      clean: { opacity: 100, borderWidth: 0, borderRadius: 0, shadowBlur: 0, shadowColor: '#000000' }
    };
    const r = recipes[name]; if (!r) return;
    setValue('objectOpacity', r.opacity, 'input');
    setValue('borderWidth', r.borderWidth, 'input');
    if (r.borderColor) setValue('borderColor', r.borderColor, 'input');
    setValue('borderRadius', r.borderRadius, 'input');
    setValue('shadowBlur', r.shadowBlur, 'input');
    setValue('shadowColor', r.shadowColor, 'input');
  }
  $$('[data-recipe]').forEach(b => b.onclick = () => applyRecipe(b.dataset.recipe));

  // Rich image adjustments — persisted as normal object data.
  const imageControls = $('#imageControls');
  if (imageControls && !$('#studioImageAdjustments')) {
    const adjustments = document.createElement('div');
    adjustments.id = 'studioImageAdjustments';
    adjustments.className = 'studio-image-adjustments';
    adjustments.innerHTML = `
      <h3>Photo adjustments</h3>
      <div class="studio-photo-presets">
        <button type="button" data-photo-preset="original">Original</button>
        <button type="button" data-photo-preset="bw">B&amp;W</button>
        <button type="button" data-photo-preset="warm">Warm</button>
        <button type="button" data-photo-preset="soft">Soft</button>
        <button type="button" data-photo-preset="vivid">Vivid</button>
      </div>
      <label>Brightness <span data-filter-value="imageBrightness">100%</span><input data-image-filter="imageBrightness" type="range" min="20" max="200" step="1" value="100"></label>
      <label>Contrast <span data-filter-value="imageContrast">100%</span><input data-image-filter="imageContrast" type="range" min="20" max="200" step="1" value="100"></label>
      <label>Saturation <span data-filter-value="imageSaturation">100%</span><input data-image-filter="imageSaturation" type="range" min="0" max="250" step="1" value="100"></label>
      <label>Grayscale <span data-filter-value="imageGrayscale">0%</span><input data-image-filter="imageGrayscale" type="range" min="0" max="100" step="1" value="0"></label>
      <label>Warmth <span data-filter-value="imageSepia">0%</span><input data-image-filter="imageSepia" type="range" min="0" max="100" step="1" value="0"></label>
      <label>Blur <span data-filter-value="imageBlur">0px</span><input data-image-filter="imageBlur" type="range" min="0" max="20" step="0.5" value="0"></label>`;
    const crop = $('#cropPreview');
    imageControls.insertBefore(adjustments, crop || imageControls.firstChild);
  }
  const imageFilterDefaults = { imageBrightness:100, imageContrast:100, imageSaturation:100, imageGrayscale:0, imageSepia:0, imageBlur:0 };
  function selectedImageObjects(){ return $$('.object.selected,.object.multi-selected').filter(x=>x.dataset.objectType==='image'); }
  function imageFilterCss(data){
    const n=(key,min,max)=>Math.max(min,Math.min(max,Number(data[key] ?? imageFilterDefaults[key])));
    return `brightness(${n('imageBrightness',20,200)}%) contrast(${n('imageContrast',20,200)}%) saturate(${n('imageSaturation',0,250)}%) grayscale(${n('imageGrayscale',0,100)}%) sepia(${n('imageSepia',0,100)}%) blur(${n('imageBlur',0,20)}px)`;
  }
  function applyImageFiltersToSelection(){
    selectedImageObjects().forEach(item=>{const img=item.querySelector('img');if(img)img.style.filter=imageFilterCss(item.dataset);if(typeof applyObjectVisualStyle==='function')applyObjectVisualStyle(item)});
    if(typeof save==='function')save();
  }
  function refreshPhotoControls(){
    const item = selectedImageObjects().at(-1);
    $$('[data-image-filter]').forEach(input=>{
      const key=input.dataset.imageFilter,value=item?Number(item.dataset[key] ?? imageFilterDefaults[key]):imageFilterDefaults[key];
      input.value=String(value);input.disabled=!item;const label=$(`[data-filter-value="${key}"]`);if(label)label.textContent=key==='imageBlur'?`${value}px`:`${value}%`;
    });
  }
  $$('[data-image-filter]').forEach(input=>input.addEventListener('input',()=>{
    const key=input.dataset.imageFilter,value=input.value;selectedImageObjects().forEach(item=>item.dataset[key]=value);
    const label=$(`[data-filter-value="${key}"]`);if(label)label.textContent=key==='imageBlur'?`${value}px`:`${value}%`;
    applyImageFiltersToSelection();
  }));
  const photoPresets={
    original:{imageBrightness:100,imageContrast:100,imageSaturation:100,imageGrayscale:0,imageSepia:0,imageBlur:0},
    bw:{imageBrightness:102,imageContrast:112,imageSaturation:0,imageGrayscale:100,imageSepia:0,imageBlur:0},
    warm:{imageBrightness:104,imageContrast:102,imageSaturation:112,imageGrayscale:0,imageSepia:22,imageBlur:0},
    soft:{imageBrightness:108,imageContrast:88,imageSaturation:90,imageGrayscale:0,imageSepia:8,imageBlur:.3},
    vivid:{imageBrightness:103,imageContrast:118,imageSaturation:145,imageGrayscale:0,imageSepia:0,imageBlur:0}
  };
  $$('[data-photo-preset]').forEach(btn=>btn.onclick=()=>{
    const preset=photoPresets[btn.dataset.photoPreset];if(!preset||!selectedImageObjects().length)return;
    selectedImageObjects().forEach(item=>Object.entries(preset).forEach(([key,value])=>item.dataset[key]=String(value)));
    refreshPhotoControls();applyImageFiltersToSelection();
  });

  // ---------------------------------------------------------------------------
  // Canvas experience: grid, focus mode, contextual toolbar, status bar
  // ---------------------------------------------------------------------------
  const toolbar = $('.toolbar');
  if (toolbar) {
    toolbar.classList.add('studio-canvas-toolbar');
    const gridBtn = button('Grid', 'studio-toolbar-toggle'); gridBtn.id = 'gridToggle'; gridBtn.setAttribute('aria-pressed', 'false');
    const focusBtn = button('Focus', 'studio-toolbar-toggle'); focusBtn.id = 'focusModeBtn'; focusBtn.setAttribute('aria-pressed', 'false');
    const safe = $('#safeMarginToggle');
    safe?.after(gridBtn, focusBtn);
    gridBtn.onclick = () => {
      const active = !$('#stage').classList.contains('show-grid');
      $('#stage').classList.toggle('show-grid', active); gridBtn.setAttribute('aria-pressed', String(active));
    };
    focusBtn.onclick = () => {
      const active = !body.classList.contains('studio-focus-mode');
      body.classList.toggle('studio-focus-mode', active); focusBtn.setAttribute('aria-pressed', String(active));
    };
  }

  const viewport = $('#canvasViewport');
  if (viewport) {
    const emptyMessage = document.createElement('div');
    emptyMessage.className = 'studio-canvas-hint';
    emptyMessage.innerHTML = '<span>✦</span><strong>Design your invitation</strong><small>Drag to select · Space to pan · Ctrl/Cmd + K for quick actions</small>';
    viewport.prepend(emptyMessage);
  }

  const floating = document.createElement('div');
  floating.className = 'studio-selection-toolbar'; floating.hidden = true;
  floating.innerHTML = `
    <button type="button" data-float-action="duplicate" title="Duplicate (Ctrl/Cmd+D)">Duplicate</button>
    <button type="button" data-float-action="copyStyle" title="Copy appearance">Copy style</button>
    <button type="button" data-float-action="pasteStyle" title="Paste appearance">Paste style</button>
    <button type="button" data-float-action="forward" title="Bring forward">Forward</button>
    <button type="button" data-float-action="lock" title="Lock or unlock">Lock</button>
    <button type="button" data-float-action="group" title="Group selected">Group</button>
    <button type="button" data-float-action="tidy" title="Tidy selected objects">Tidy</button>
    <span></span>
    <button type="button" data-float-action="delete" class="danger" title="Delete">Delete</button>`;
  $('.stage-wrap')?.append(floating);
  const styleClipboardKey='einvite-object-style-clipboard-v1';
  const styleKeys=['font','color','fontSize','textAlign','fontWeight','fontStyle','letterSpacing','lineHeight','fillColor','shapeKind','opacity','borderWidth','borderColor','borderRadius','shadowBlur','shadowColor','animation','duration','imageFit','imageMask','imageFrame','imageBrightness','imageContrast','imageSaturation','imageGrayscale','imageSepia','imageBlur'];
  function primarySelected(){return $('.object.selected')||$('.object.multi-selected')}
  function copyObjectStyle(){const item=primarySelected();if(!item)return;const payload={};styleKeys.forEach(k=>payload[k]=item.dataset[k]);localStorage.setItem(styleClipboardKey,JSON.stringify(payload));const b=$('[data-float-action="pasteStyle"]',floating);if(b)b.disabled=false}
  function pasteObjectStyle(){let payload;try{payload=JSON.parse(localStorage.getItem(styleClipboardKey)||'null')}catch{}if(!payload)return alert('Copy an object style first.');const items=$$('.object.selected,.object.multi-selected');if(!items.length)return;items.forEach(item=>{styleKeys.forEach(k=>{if(payload[k]!=null)item.dataset[k]=payload[k]});if(typeof applyObjectVisualStyle==='function')applyObjectVisualStyle(item);const img=item.querySelector('img');if(img)img.style.filter=imageFilterCss(item.dataset)});if(typeof refreshSelectionUI==='function')refreshSelectionUI();refreshPhotoControls();if(typeof save==='function')save()}
  function tidySelected(){const items=$$('.object.selected,.object.multi-selected').filter(x=>x.dataset.locked!=='true');if(items.length<3)return alert('Select at least three unlocked objects to tidy.');const stage=$('#stage').getBoundingClientRect(),frames=items.map(item=>({item,rect:item.getBoundingClientRect()})),minL=Math.min(...frames.map(x=>x.rect.left)),maxR=Math.max(...frames.map(x=>x.rect.right)),minT=Math.min(...frames.map(x=>x.rect.top)),maxB=Math.max(...frames.map(x=>x.rect.bottom));const horizontal=(maxR-minL)>=(maxB-minT);frames.sort((a,b)=>horizontal?a.rect.left-b.rect.left:a.rect.top-b.rect.top);if(horizontal){const total=frames.reduce((s,x)=>s+x.rect.width,0),gap=Math.max(0,(maxR-minL-total)/(frames.length-1));let cursor=minL;frames.forEach(x=>{x.item.style.left=`${(cursor-stage.left)/stage.width*100}%`;cursor+=x.rect.width+gap})}else{const total=frames.reduce((s,x)=>s+x.rect.height,0),gap=Math.max(0,(maxB-minT-total)/(frames.length-1));let cursor=minT;frames.forEach(x=>{x.item.style.top=`${(cursor-stage.top)/stage.height*100}%`;cursor+=x.rect.height+gap})}if(typeof updateSelectionBounds==='function')updateSelectionBounds();if(typeof save==='function')save()}

  const floatAction = {
    duplicate: () => $('#duplicate')?.click(), forward: () => $('#bringForward')?.click(),
    copyStyle: copyObjectStyle, pasteStyle: pasteObjectStyle, tidy: tidySelected,
    group: () => $('#groupObjects')?.click(), delete: () => $('#deleteBtn')?.click(),
    lock: () => { const el = $('#objectLocked'); if (!el) return; el.checked = !el.checked; el.dispatchEvent(new Event('change', { bubbles: true })); }
  };
  $$('[data-float-action]', floating).forEach(b => b.onclick = () => floatAction[b.dataset.floatAction]?.());

  function refreshFloatingToolbar() {
    const items = $$('.object.selected,.object.multi-selected').filter(x => x.isConnected);
    floating.hidden = !items.length;
    if (items.length) {
      const locked = items.every(x => x.dataset.locked === 'true');
      const lock = $('[data-float-action="lock"]', floating); if (lock) lock.textContent = locked ? 'Unlock' : 'Lock';
      const group = $('[data-float-action="group"]', floating); if (group) group.disabled = items.length < 2;
    }
  }
  const selectionObserver = new MutationObserver(()=>{refreshFloatingToolbar();refreshPhotoControls()});
  selectionObserver.observe($('#stage'), { subtree: true, attributes: true, attributeFilter: ['class', 'data-locked'], childList: true });
  document.addEventListener('pointerup', () => setTimeout(refreshFloatingToolbar, 0), true);
  refreshFloatingToolbar();refreshPhotoControls();
  const pasteStyleButton=$('[data-float-action="pasteStyle"]',floating);if(pasteStyleButton)pasteStyleButton.disabled=!localStorage.getItem(styleClipboardKey);

  const statusbar = document.createElement('footer');
  statusbar.className = 'studio-statusbar';
  statusbar.innerHTML = `
    <div><span class="studio-status-dot"></span><strong id="studioStatusSave">Ready</strong><small id="studioStatusServer">Local workspace</small></div>
    <div class="studio-status-center"><span id="studioStatusCanvas">Main hero canvas</span><span>·</span><span id="studioSelectionStatus">No selection</span></div>
    <div><kbd>Ctrl K</kbd><span>Quick actions</span><kbd>Space</kbd><span>Pan</span></div>`;
  body.append(statusbar);

  function updateStatusbar() {
    const save = $('#saveState'); const server = $('#serverState'); const canvas = $('#activeCanvasLabel');
    if ($('#studioStatusSave')) $('#studioStatusSave').textContent = text(save) || 'Ready';
    if ($('#studioStatusServer')) $('#studioStatusServer').textContent = text(server) || 'Local workspace';
    if ($('#studioStatusCanvas')) $('#studioStatusCanvas').textContent = text(canvas) || 'Canvas';
    const count = $$('.object.selected,.object.multi-selected').length;
    if ($('#studioSelectionStatus')) $('#studioSelectionStatus').textContent = count ? `${count} object${count === 1 ? '' : 's'} selected` : 'No selection';
  }
  const statusObserver = new MutationObserver(updateStatusbar);
  [$('#saveState'), $('#serverState'), $('#activeCanvasLabel'), $('#stage')].filter(Boolean).forEach(node => statusObserver.observe(node, { subtree: true, childList: true, characterData: true, attributes: true }));
  document.addEventListener('pointerup', () => setTimeout(updateStatusbar, 0), true);
  updateStatusbar();

  // ---------------------------------------------------------------------------
  // Command palette
  // ---------------------------------------------------------------------------
  const palette = document.createElement('div');
  palette.className = 'studio-command-palette'; palette.hidden = true;
  palette.innerHTML = `
    <div class="studio-command-backdrop"></div>
    <section class="studio-command-dialog" role="dialog" aria-modal="true" aria-label="Quick actions">
      <div class="studio-command-search"><span>⌕</span><input type="search" placeholder="Search actions, pages, elements…" autocomplete="off"><kbd>Esc</kbd></div>
      <div class="studio-command-results"></div>
      <footer><span>↑↓ Navigate</span><span>Enter Run</span><span>Ctrl/Cmd + K Open</span></footer>
    </section>`;
  body.append(palette);
  const commandInput = $('input', palette), commandResults = $('.studio-command-results', palette);
  let activeCommandIndex = 0;

  const commands = [
    { label: 'Add heading text', group: 'Insert', keywords: 'text title heading', run: () => { activateLeft('elements'); setTextPreset('heading'); } },
    { label: 'Add Khmer ceremonial title', group: 'Insert', keywords: 'khmer text title', run: () => { activateLeft('elements'); setTextPreset('khmer'); } },
    { label: 'Add couple monogram', group: 'Invitation', keywords: 'couple initials monogram', run: () => $('[data-smart-insert="monogram"]')?.click() },
    { label: 'Add event date badge', group: 'Invitation', keywords: 'date save the date', run: () => $('[data-smart-insert="date"]')?.click() },
    { label: 'Add rectangle', group: 'Elements', keywords: 'shape rectangle box', run: () => $('[data-add-element="rectangle"]')?.click() },
    { label: 'Add circle', group: 'Elements', keywords: 'shape circle ellipse', run: () => $('[data-add-element="circle"]')?.click() },
    { label: 'Add flourish decoration', group: 'Elements', keywords: 'ornament decoration flourish wedding', run: () => $('[data-add-element="flourish"]')?.click() },
    { label: 'Add photo feature page', group: 'Pages', keywords: 'page photo image', run: () => { activateLeft('pages'); $('[data-add-page="photo"]')?.click(); } },
    { label: 'Add photo collage page', group: 'Pages', keywords: 'page collage photos', run: () => { activateLeft('pages'); $('[data-add-page="collage"]')?.click(); } },
    { label: 'Add ceremony page', group: 'Pages', keywords: 'page wedding ceremony', run: () => { activateLeft('pages'); $('[data-add-page="ceremony"]')?.click(); } },
    { label: 'Open event information', group: 'Navigate', keywords: 'content event names date venue rsvp', run: () => activateLeft('event') },
    { label: 'Open page builder', group: 'Navigate', keywords: 'pages sections builder', run: () => activateLeft('pages') },
    { label: 'Open uploads and media', group: 'Navigate', keywords: 'photos upload video music media', run: () => activateLeft('media') },
    { label: 'Open element library', group: 'Navigate', keywords: 'elements shapes text decorations', run: () => activateLeft('elements') },
    { label: 'Open design and palette', group: 'Navigate', keywords: 'theme design colors palette', run: () => activateRight('theme') },
    { label: 'Open publishing settings', group: 'Navigate', keywords: 'publish share url password', run: () => activateRight('publish') },
    { label: 'Run invitation design check', group: 'Invitation', keywords: 'check review accessibility readiness publish', run: () => openDesignCheck() },
    { label: 'Preview guest invitation', group: 'Actions', keywords: 'preview guest view', run: () => $('#previewBtn')?.click() },
    { label: 'Publish invitation snapshot', group: 'Actions', keywords: 'publish live share', run: () => $('#publishBtn')?.click() },
    { label: 'Fit canvas to workspace', group: 'Canvas', keywords: 'zoom fit canvas', run: () => $('#fitCanvas')?.click() },
    { label: 'Toggle safe margins', group: 'Canvas', keywords: 'safe margins guides', run: () => $('#safeMarginToggle')?.click() },
    { label: 'Toggle canvas grid', group: 'Canvas', keywords: 'grid guides', run: () => $('#gridToggle')?.click() },
    { label: 'Toggle focus mode', group: 'Canvas', keywords: 'focus hide panels workspace', run: () => $('#focusModeBtn')?.click() },
    { label: 'Copy selected object style', group: 'Edit', keywords: 'copy style appearance', run: copyObjectStyle },
    { label: 'Paste object style', group: 'Edit', keywords: 'paste style appearance', run: pasteObjectStyle },
    { label: 'Tidy selected objects', group: 'Edit', keywords: 'tidy distribute spacing objects', run: tidySelected },
    { label: 'Undo', group: 'Edit', keywords: 'undo history', run: () => $('#undoBtn')?.click() },
    { label: 'Redo', group: 'Edit', keywords: 'redo history', run: () => $('#redoBtn')?.click() }
  ];

  function filteredCommands() {
    const q = commandInput.value.trim().toLowerCase();
    return commands.filter(c => !q || `${c.label} ${c.group} ${c.keywords || ''}`.toLowerCase().includes(q));
  }
  function renderCommands() {
    const list = filteredCommands(); activeCommandIndex = Math.max(0, Math.min(activeCommandIndex, Math.max(0, list.length - 1)));
    commandResults.innerHTML = list.length ? '' : '<div class="studio-command-empty">No matching actions.</div>';
    let currentGroup = '';
    list.forEach((c, index) => {
      if (c.group !== currentGroup) {
        currentGroup = c.group;
        const heading = document.createElement('div'); heading.className = 'studio-command-group'; heading.textContent = currentGroup; commandResults.append(heading);
      }
      const row = button('', `studio-command-row${index === activeCommandIndex ? ' active' : ''}`);
      row.innerHTML = `<span class="studio-command-symbol">${index === activeCommandIndex ? '→' : '·'}</span><strong>${c.label}</strong><small>${c.group}</small>`;
      row.onmouseenter = () => { activeCommandIndex = index; $$('.studio-command-row', commandResults).forEach((x,i)=>x.classList.toggle('active',i===index)); };
      row.onclick = () => { closeCommandPalette(); c.run(); };
      commandResults.append(row);
    });
  }
  function openCommandPalette() { palette.hidden = false; activeCommandIndex = 0; commandInput.value = ''; renderCommands(); requestAnimationFrame(() => commandInput.focus()); }
  function closeCommandPalette() { palette.hidden = true; commandInput.blur(); }
  $('#studioCommandBtn')?.addEventListener('click', openCommandPalette);
  $('.studio-command-backdrop', palette)?.addEventListener('click', closeCommandPalette);
  commandInput.addEventListener('input', () => { activeCommandIndex = 0; renderCommands(); });
  commandInput.addEventListener('keydown', event => {
    const list = filteredCommands();
    if (event.key === 'ArrowDown') { event.preventDefault(); activeCommandIndex = Math.min(list.length - 1, activeCommandIndex + 1); renderCommands(); }
    if (event.key === 'ArrowUp') { event.preventDefault(); activeCommandIndex = Math.max(0, activeCommandIndex - 1); renderCommands(); }
    if (event.key === 'Enter' && list[activeCommandIndex]) { event.preventDefault(); closeCommandPalette(); list[activeCommandIndex].run(); }
    if (event.key === 'Escape') closeCommandPalette();
  });


  // ---------------------------------------------------------------------------
  // Invitation readiness / accessibility check
  // ---------------------------------------------------------------------------
  const designCheck = document.createElement('div');
  designCheck.className = 'studio-design-check'; designCheck.hidden = true;
  designCheck.innerHTML = `
    <div class="studio-command-backdrop"></div>
    <section class="studio-check-dialog" role="dialog" aria-modal="true" aria-label="Invitation design check">
      <header><div><small>Invitation quality</small><h2>Design check</h2></div><button type="button" data-close-check>×</button></header>
      <div class="studio-check-score"><div class="studio-score-ring"><strong id="studioCheckScore">0</strong><span>/ 100</span></div><div><strong id="studioCheckSummary">Reviewing your invitation…</strong><p>Checks content, guest experience, accessibility and publishing readiness.</p></div></div>
      <div class="studio-check-list" id="studioCheckList"></div>
      <footer><button type="button" data-close-check>Close</button><button type="button" class="primary" id="studioPreviewFromCheck">Preview as guest</button></footer>
    </section>`;
  body.append(designCheck);
  function closeDesignCheck(){ designCheck.hidden = true; }
  $$('[data-close-check]',designCheck).forEach(b=>b.onclick=closeDesignCheck);
  $('.studio-command-backdrop',designCheck).onclick=closeDesignCheck;
  $('#studioPreviewFromCheck').onclick=()=>{ closeDesignCheck(); $('#previewBtn')?.click(); };

  function hexRgb(hex){ const value=String(hex||'').replace('#',''); if(!/^[0-9a-f]{6}$/i.test(value))return null; return [0,2,4].map(i=>parseInt(value.slice(i,i+2),16)); }
  function luminance(hex){ const rgb=hexRgb(hex); if(!rgb)return null; const c=rgb.map(v=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4});return .2126*c[0]+.7152*c[1]+.0722*c[2]; }
  function contrast(a,b){ const la=luminance(a),lb=luminance(b);if(la==null||lb==null)return null;return (Math.max(la,lb)+.05)/(Math.min(la,lb)+.05); }
  function openDesignCheck(){
    const checks=[];
    const add=(ok,title,detail,action,weight=10)=>checks.push({ok,title,detail,action,weight});
    const names=($('#names')?.value||'').trim(),date=$('#date')?.value,venue=($('#venue')?.value||'').trim();
    add(!!names,'Event title or couple names',names?'Your invitation has a clear identity.':'Add the couple names or event title.',()=>{activateLeft('event');$('#names')?.focus()},12);
    add(!!date,'Event date',date?'A date is set for countdowns and guest information.':'Choose the event date.',()=>{activateLeft('event');$('#date')?.focus()},10);
    add(!!venue,'Primary venue',venue?'Your primary venue is included.':'Add the main venue so guests know where to go.',()=>{activateLeft('event');$('#venue')?.focus()},8);
    const venueOn=$('#venueEnabled')?.checked,map=($('#mapUrl')?.value||'').trim();
    add(!venueOn||!!map,'Map directions',!venueOn?'Venue section is disabled.':map?'Guests have a map link.':'Add a map link for easier navigation.',()=>{activateLeft('event');$('#mapUrl')?.focus()},8);
    const contactOn=$('#contactEnabled')?.checked,phone=($('#contactPhone')?.value||'').trim(),telegram=($('#contactTelegram')?.value||'').trim();
    add(!contactOn||!!phone||!!telegram,'Host contact',!contactOn?'Contact buttons are intentionally disabled.':phone||telegram?'Guests can contact a host.':'Add a phone number or Telegram contact, or disable the contact section.',()=>{activateLeft('event');$('#contactPhone')?.focus()},6);
    const images=$$('.object.image-object');
    add(images.length>0,'Visual storytelling',images.length?`${images.length} image object${images.length===1?'':'s'} in the design.`:'Add at least one meaningful image for a richer invitation.',()=>activateLeft('media'),9);
    const galleryImages=images.filter(x=>x.dataset.showInGallery!=='false');
    const missingAlt=galleryImages.filter(x=>!(x.dataset.alt||'').trim()).length;
    add(!galleryImages.length||missingAlt===0,'Image descriptions',!galleryImages.length?'No gallery images to review.':missingAlt?`${missingAlt} gallery image${missingAlt===1?'':'s'} missing accessible descriptions.`:'Gallery images have descriptions.',()=>activateLeft('media'),8);
    const tinyText=$$('.object.text-object').filter(x=>Number(x.dataset.fontSize||0)>0&&Number(x.dataset.fontSize)<12).length;
    add(tinyText===0,'Readable text size',tinyText?`${tinyText} text object${tinyText===1?' is':'s are'} smaller than 12px.`:'No unusually small canvas text found.',()=>activateRight('object'),6);
    const bg=$('#paletteBackground')?.value||'#ffffff',fg=$('#paletteText')?.value||'#222222',ratio=contrast(bg,fg);
    add(ratio==null||ratio>=4.5,'Color contrast',ratio==null?'Using template colors.':ratio>=4.5?`Text contrast is ${ratio.toFixed(1)}:1.`:`Text contrast is only ${ratio.toFixed(1)}:1; consider darker text or a lighter background.`,()=>activateRight('theme'),8);
    const opening=$('#openingEnabled')?.checked;
    add(!!opening,'Invitation opening experience',opening?'Tap-to-open experience is enabled.':'Consider enabling an opening experience for music and a more ceremonial reveal.',()=>activateLeft('media'),5);
    const slug=($('#publicSlug')?.value||'').trim();
    add(!!slug,'Shareable invitation link',slug?'A public link slug is configured.':'Set a memorable public link before publishing.',()=>{activateRight('publish');$('#publicSlug')?.focus()},10);
    const mode=$('#accessMode')?.value,password=($('#accessPassword')?.value||'').trim();
    add(mode!=='password'||password.length>=4,'Guest access settings',mode==='password'&&password.length<4?'Password protection is selected but the password is too short.':'Guest access settings look ready.',()=>activateRight('publish'),5);
    const total=checks.reduce((s,c)=>s+c.weight,0),earned=checks.reduce((s,c)=>s+(c.ok?c.weight:0),0),score=Math.round(earned/Math.max(1,total)*100);
    $('#studioCheckScore').textContent=score;
    $('#studioCheckSummary').textContent=score>=90?'Ready to impress your guests':score>=75?'Almost ready to publish':score>=55?'A few important details remain':'Keep building your invitation';
    const list=$('#studioCheckList');list.innerHTML='';
    checks.forEach(c=>{const row=document.createElement('article');row.className=`studio-check-item ${c.ok?'pass':'warn'}`;row.innerHTML=`<span>${c.ok?'✓':'!'}</span><div><strong>${c.title}</strong><p>${c.detail}</p></div>${c.ok?'':'<button type="button">Fix</button>'}`;const fix=row.querySelector('button');if(fix)fix.onclick=()=>{closeDesignCheck();c.action?.()};list.append(row)});
    designCheck.hidden=false;
  }
  $('#studioCheckBtn')?.addEventListener('click',openDesignCheck);

  // ---------------------------------------------------------------------------
  // Drag-to-canvas workflow for uploaded photos and design elements
  // ---------------------------------------------------------------------------
  function makeDraggableAssets(){
    $$('#assets img').forEach(img=>{if(img.dataset.studioDraggable)return;img.dataset.studioDraggable='true';img.draggable=true;img.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-asset',img.src);e.dataTransfer.effectAllowed='copy'})});
    $$('[data-add-element]').forEach(el=>{if(el.dataset.studioDraggable)return;el.dataset.studioDraggable='true';el.draggable=true;el.addEventListener('dragstart',e=>{e.dataTransfer.setData('application/x-einvite-element',el.dataset.addElement);e.dataTransfer.effectAllowed='copy'})});
  }
  const assetObserver=new MutationObserver(makeDraggableAssets);if($('#assets'))assetObserver.observe($('#assets'),{childList:true,subtree:true});makeDraggableAssets();
  $('#stage').addEventListener('dragover',e=>{if(e.dataTransfer.types.includes('application/x-einvite-asset')||e.dataTransfer.types.includes('application/x-einvite-element')){e.preventDefault();e.dataTransfer.dropEffect='copy';$('#stage').classList.add('studio-drop-target')}});
  $('#stage').addEventListener('dragleave',()=>$('#stage').classList.remove('studio-drop-target'));
  $('#stage').addEventListener('drop',e=>{
    const asset=e.dataTransfer.getData('application/x-einvite-asset'),kind=e.dataTransfer.getData('application/x-einvite-element');if(!asset&&!kind)return;
    e.preventDefault();$('#stage').classList.remove('studio-drop-target');
    if(asset){const img=$$('#assets img').find(x=>x.src===asset);img?.click()}else if(kind){$(`[data-add-element="${CSS.escape(kind)}"]`)?.click()}
    requestAnimationFrame(()=>{
      const target=$('.object.selected')||$('.object.multi-selected');if(!target)return;const rect=$('#stage').getBoundingClientRect();
      const x=Math.max(0,Math.min(92,(e.clientX-rect.left)/rect.width*100-8)),y=Math.max(0,Math.min(92,(e.clientY-rect.top)/rect.height*100-5));
      target.style.left=`${x}%`;target.style.top=`${y}%`;
      fire('rotation','input');
    })
  });

  // ---------------------------------------------------------------------------
  // Keyboard workflow enhancements
  // ---------------------------------------------------------------------------
  document.addEventListener('keydown', event => {
    const target = event.target;
    const editing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target?.isContentEditable;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault(); palette.hidden ? openCommandPalette() : closeCommandPalette(); return;
    }
    if (event.key === 'Escape' && !palette.hidden) { event.preventDefault(); closeCommandPalette(); return; }
    if (!editing && event.key.toLowerCase() === 'f' && !event.ctrlKey && !event.metaKey) {
      event.preventDefault(); $('#focusModeBtn')?.click();
    }
  });

  // ---------------------------------------------------------------------------
  // Small UX refinements and discoverability
  // ---------------------------------------------------------------------------
  const pagePane = $('[data-studio-pane="pages"]', leftTabs.host);
  if (pagePane) {
    const tip = document.createElement('div'); tip.className = 'studio-tip-card';
    tip.innerHTML = '<span>✦</span><div><strong>Build like a story, not a poster</strong><p>Mix artistic pages with live sections such as countdown, schedule, maps and RSVP.</p></div>';
    $('.studio-pane-heading', pagePane)?.after(tip);
  }
  const mediaPane = $('[data-studio-pane="media"]', leftTabs.host);
  if (mediaPane) {
    const tip = document.createElement('div'); tip.className = 'studio-tip-card compact';
    tip.innerHTML = '<span>▧</span><div><strong>Your material library</strong><p>Upload once, reuse photos, music and video across invitations.</p></div>';
    $('.studio-pane-heading', mediaPane)?.after(tip);
  }

  // Enhance native button labels without changing their IDs/actions.
  const labelMap = {
    previewBtn: 'Preview', publishBtn: 'Publish', backupBtn: 'Backup', restoreBtn: 'Restore',
    undoBtn: '↶', redoBtn: '↷', fitCanvas: 'Fit', panToggle: 'Hand', rulersToggle: 'Rulers', safeMarginToggle: 'Margins'
  };
  Object.entries(labelMap).forEach(([id, label]) => { const el = document.getElementById(id); if (el) el.textContent = label; });

  // Make all primary creation panel headings collapsible except the first in each pane.
  $$('.studio-pane h2').forEach(h => {
    h.classList.add('studio-subsection-heading');
  });

  // Initial sizing and state refresh.
  requestAnimationFrame(() => {
    refreshFloatingToolbar(); updateStatusbar();
    $('#fitCanvas')?.click();
  });
})();
