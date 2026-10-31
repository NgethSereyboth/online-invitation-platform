/*
 * Inspector reorganisation (2026-10-30).
 *
 * The Edit pane had grown into ~5,600 px of stacked panels: a transform card,
 * six typography cards, duplicate alignment grids, motion tools, V13 panels,
 * and the orphaned Design pane. This module keeps the existing DOM nodes (and
 * therefore every id, listener and save path) but files them into a short
 * icon-led toolbar plus one accordion group per job:
 *
 *   Position · Text · Style · Arrange · Motion · Page · More
 *
 * Position opens by default so size/position stay immediate. Text, Style and
 * Arrange hold the essentials the owner asked to keep in the pane; the rest is
 * one click away. The old Design tab is retired here: its palette, template and
 * background controls move into the always-available Page group.
 */
(() => {
  'use strict';

  const pane = () => document.querySelector('[data-inspector-pane="object"]');
  const props = () => pane()?.querySelector('#properties');
  const tools = [
    ['position', 'Position & size', 'M12 3v18M3 12h18M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3'],
    ['text', 'Text', 'M5 6h14M12 6v13M8 19h8'],
    ['style', 'Appearance', 'M12 3a9 9 0 1 0 0 18zM12 3v18'],
    ['arrange', 'Arrange', 'M4 7h16M4 12h16M4 17h16'],
    ['motion', 'Motion', 'M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM10 9l6 3-6 3z'],
    ['page', 'Page & palette', 'M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5'],
    ['more', 'More tools', 'M6 12h.01M12 12h.01M18 12h.01']
  ];
  const meta = {
    position: ['⊹', 'Position', 'X, Y, size and rotation'],
    text: ['T', 'Text', 'Content, type and fit'],
    style: ['◐', 'Style', 'Fill, border, shadow and photo'],
    arrange: ['⇅', 'Arrange', 'Align, order, lock and delete'],
    motion: ['✦', 'Motion', 'Animation, effects and timing'],
    page: ['▤', 'Page', 'Palette, background and template'],
    more: ['⋯', 'More', 'Advanced and responsive tools']
  };
  const icon = (path) => `<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
  let built = false;
  let busy = false;
  let queued = 0;

  const hasSelection = () => document.body.classList.contains('v54-has-selection')
    || Boolean(document.querySelector('.object.selected, .object.multi-selected'));

  const make = (tag, cls, html) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html != null) node.innerHTML = html;
    return node;
  };

  function group(name) {
    const [iconText, label, hint] = meta[name];
    const details = make('details', 'ix-group');
    details.dataset.ixGroup = name;
    details.innerHTML = `<summary><span class="ix-group-icon" aria-hidden="true">${iconText}</span><span class="ix-group-name">${label}</span><small class="ix-group-hint">${hint}</small><span class="ix-chevron" aria-hidden="true">⌄</span></summary><div class="ix-body"></div>`;
    details.addEventListener('toggle', () => {
      if (details.open && !busy) closeOthers(details);
      syncTools();
    });
    return details;
  }

  function closeOthers(current) {
    const host = current.parentElement;
    if (!host) return;
    host.querySelectorAll(':scope > details.ix-group[open]').forEach((other) => {
      if (other !== current) other.open = false;
    });
  }

  function openGroup(name, scroll = true) {
    const target = pane()?.querySelector(`.ix-group[data-ix-group="${CSS.escape(name)}"]`);
    if (!target || target.hidden) return;
    target.open = true;
    closeOthers(target);
    if (scroll) target.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    syncTools();
  }

  function build() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps || hostPane.querySelector('.ix-toolbox')) return false;

    // Keep the shell that app.js hides/shows, but move its contents into the
    // groups. The summary stays at the top of the pane for quick selection info.
    const summary = hostProps.querySelector('.selection-summary');
    const toolbox = make('div', 'ix-toolbox');
    toolbox.setAttribute('role', 'toolbar');
    toolbox.setAttribute('aria-label', 'Edit tools');
    tools.forEach(([name, label, path]) => {
      const button = make('button', 'ix-tool');
      button.type = 'button';
      button.dataset.ixTool = name;
      button.setAttribute('aria-label', label);
      button.title = label;
      button.innerHTML = `${icon(path)}<em class="ix-tool-tip">${label}</em>`;
      toolbox.append(button);
    });

    const groups = make('div', 'ix-groups');
    Object.keys(meta).forEach((name) => groups.append(group(name)));

    hostPane.insertBefore(toolbox, hostPane.querySelector('#noSelection'));
    hostPane.append(groups);
    toolbox.addEventListener('click', (event) => {
      const button = event.target.closest('[data-ix-tool]');
      if (!button || button.disabled) return;
      const name = button.dataset.ixTool;
      const target = groups.querySelector(`[data-ix-group="${CSS.escape(name)}"]`);
      if (!target) return;
      if (target.open) target.open = false;
      else openGroup(name);
      syncTools();
    });
    return true;
  }

  function slot(name) {
    return pane()?.querySelector(`.ix-group[data-ix-group="${CSS.escape(name)}"] .ix-body`);
  }

  function move(node, name) {
    const target = slot(name);
    if (!node || !target || target.contains(node)) return false;
    target.append(node);
    return true;
  }

  function hide(node) {
    if (node) node.hidden = true;
  }

  function compactTypography() {
    const root = pane()?.querySelector('#typographyControls');
    if (!root) return;
    root.hidden = true;
    const textSlot = slot('text');
    if (!textSlot) return;
    root.querySelectorAll(':scope > .v20-typography-shell > .v20-inspector-group, :scope > .v20-inspector-group').forEach((section) => {
      if (section.closest('.ix-sub')) return;
      const title = (section.querySelector('h3')?.textContent || 'Text').trim();
      // The parent tool is already called Text; a child sub-panel with the
      // same label read as a second, redundant section.
      const label = /^text$/i.test(title) ? 'Style & type' : title;
      const sub = make('details', 'ix-sub');
      sub.dataset.title = title;
      sub.innerHTML = `<summary><span>${label}</span><span class="ix-chevron" aria-hidden="true">⌄</span></summary>`;
      const body = make('div', 'ix-sub-body');
      section.classList.add('ix-flat');
      body.append(section);
      sub.append(body);
      textSlot.append(sub);
    });
  }

  // Page and More collect several unrelated cards. Fold each card into a
  // compact sub-accordion so opening the tool never drops a 1,300–1,800px wall
  // of controls into the pane.
  function foldSections(name) {
    const body = slot(name);
    if (!body) return;
    // Only fold direct children that are still loose. Late modules (responsive
    // constraints, shared styles) append cards after the first pass, so an
    // all-or-nothing guard left them as an unfolded wall at the bottom.
    const children = [...body.children].filter((node) => !node.classList.contains('ix-sub-fold'));
    const headingOf = (node) => {
      if (node.matches('h2, h3')) return (node.textContent || '').trim();
      return (node.querySelector(':scope > h2, :scope > .final-panel-title h2, :scope > header h2')?.textContent || '').trim();
    };
    const units = [];
    let current = null;
    children.forEach((node) => {
      const heading = headingOf(node);
      if (node.matches('h2, h3') || (heading && !node.matches('label'))) {
        current = { title: heading || 'Section', nodes: [] };
        units.push(current);
      }
      if (current) current.nodes.push(node);
    });
    if (!units.length) return;
    units.forEach((unit) => {
      const sub = make('details', 'ix-sub ix-sub-fold');
      const summary = make('summary');
      const label = make('span');
      // More holds an advanced transform card whose heading matched the
      // Position tool exactly. Rename the duplicate so the two read as
      // different jobs.
      label.textContent = name === 'more' && /^position\s*&\s*size$/i.test(unit.title) ? 'Advanced transform' : unit.title;
      const chevron = make('span', 'ix-chevron', '⌄');
      chevron.setAttribute('aria-hidden', 'true');
      summary.append(label, chevron);
      const inner = make('div', 'ix-sub-body');
      unit.nodes.forEach((node) => {
        if (node.matches('h2, h3')) node.hidden = true;
        else node.querySelectorAll(':scope > h2, :scope > .final-panel-title h2').forEach((heading) => { heading.hidden = true; });
        inner.append(node);
      });
      sub.append(summary, inner);
      body.append(sub);
    });
  }

  function moveLabel(selector, name) {
    const node = pane()?.querySelector(selector);
    if (!node || node.closest('.ix-groups')) return;
    move(node.closest('label,.toggle-row'), name);
  }

  function moveSection(selector, name) {
    const node = pane()?.querySelector(selector);
    if (!node || node.closest('.ix-groups')) return;
    move(node, name);
  }

  function classify() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps || busy) return;
    busy = true;
    try {
      if (!built) built = build();
      if (!hostPane.querySelector('.ix-groups')) return;

      // Selection summary lives above the toolbar and is hidden with #properties.
      const summary = hostProps.querySelector('.selection-summary');
      if (summary) summary.hidden = false;

      // Position — keep the precise transform card open at rest.
      const position = hostPane.querySelector('#peTransformPanel');
      if (position && !position.closest('.ix-groups')) move(position, 'position');

      // Text — the text field plus the six typography cards, each collapsible.
      const textArea = hostProps.querySelector('#textContentLabel');
      if (textArea && !textArea.closest('.ix-groups')) move(textArea, 'text');
      compactTypography();
      const textBox = hostPane.querySelector('#canvasPlusTextBox');
      if (textBox && !textBox.closest('.ix-groups') && slot('text')) {
        // Vertical alignment / box padding are a second block inside Text.
        // Fold them so opening Text shows the content field and a short list of
        // headings, not a fully expanded form below it.
        const sub = make('details', 'ix-sub');
        sub.dataset.title = 'Text box';
        sub.innerHTML = `<summary><span>Text box</span><span class="ix-chevron" aria-hidden="true">⌄</span></summary>`;
        const body = make('div', 'ix-sub-body');
        body.append(textBox);
        sub.append(body);
        slot('text').append(sub);
      }

      // Style — object appearance and the photo tools. The typography V19 style
      // recipes stay nearby because they restyle the selected object.
      const style = slot('style');
      if (style) {
        hostPane.querySelectorAll('h2').forEach((heading) => {
          if (/^appearance$/i.test(heading.textContent.trim()) && !heading.closest('.ix-groups')) move(heading, 'style');
        });
        ['objectOpacity', 'borderWidth', 'borderColor', 'borderRadius', 'shadowBlur', 'shadowColor'].forEach((id) => moveLabel(`#${id}`, 'style'));
        const recipes = hostPane.querySelector('.studio-style-recipes, #studio-style-recipes');
        if (recipes && !recipes.closest('.ix-groups')) move(recipes, 'style');
        const image = hostPane.querySelector('#imageControls');
        if (image && !image.closest('.ix-groups')) move(image, 'style');
        const photo = hostPane.querySelector('#canvasPlusAiTools');
        if (photo && !photo.closest('.ix-groups')) move(photo, 'style');
      }

      // Arrange — one alignment grid only, order, grouping, lock and delete.
      const arrange = slot('arrange');
      if (arrange) {
        const headings = [...hostPane.querySelectorAll('h2')].filter((h) => !h.closest('.ix-groups'));
        // Both headings said the same thing above one grid. Keep the grid and
        // let the Arrange group summary provide the label.
        headings.filter((h) => /^(alignment|align selected)$/i.test(h.textContent.trim())).forEach(hide);
        const mainGrid = hostPane.querySelector('#alignment-grid');
        if (mainGrid && !mainGrid.closest('.ix-groups')) move(mainGrid, 'arrange');
        const grids = [...hostPane.querySelectorAll('.alignment-grid')].filter((g) => !g.closest('.ix-groups'));
        grids.forEach((grid, index) => {
          if (index === 0) move(grid, 'arrange');
          else hide(grid);
        });
        move(hostPane.querySelector('#bringForward')?.closest('div.actions'), 'arrange');
        move(hostPane.querySelector('#groupObjects')?.closest('div.actions'), 'arrange');
        moveLabel('#showInHero', 'arrange');
        moveLabel('#objectLocked', 'arrange');
        // Duplicate and Delete are in the always-visible canvas action bar;
        // repeating them at the bottom of this group made the same command
        // appear three times on one screen. Keep the legacy buttons in the DOM
        // (toolbar handlers still click them) but out of the visible stack.
        hide(hostPane.querySelector('#duplicate'));
        hide(hostPane.querySelector('#deleteBtn'));
      }

      // Motion — animation picker, effects card, precision tools and timeline.
      const motion = slot('motion');
      if (motion) {
        move(hostPane.querySelector('#animationControls'), 'motion');
        move(hostPane.querySelector('.motion-measurement-settings'), 'motion');
        hostPane.querySelectorAll('.final-advanced-inspector').forEach((section) => {
          if (section.closest('.ix-groups') || section.id) return;
          const text = (section.querySelector('h2')?.textContent || '').trim();
          if (/effect|motion/i.test(text)) move(section, 'motion');
        });
        hostPane.querySelectorAll('.final-timeline').forEach((node) => move(node, 'motion'));
      }

      // Page — the retired Design tab, now always reachable.
      const pagePane = document.querySelector('[data-inspector-pane="theme"]');
      if (pagePane) {
        if (pagePane.classList.contains('active')) document.querySelector('[data-inspector-tab="object"]')?.click();
        const page = slot('page');
        if (page) {
          [...pagePane.children].forEach((node) => {
            if (node.classList.contains('studio-inspector-heading')) return;
            if (!page.contains(node)) page.append(node);
          });
        }
        document.querySelector('[data-inspector-tab="theme"]')?.remove();
        pagePane.remove();
      }
      foldSections('page');

      // More — advanced duplicates, responsive constraints and fine nudging.
      const more = slot('more');
      if (more) {
        move(hostPane.querySelector('#canvasPlusTransform'), 'more');
        move(hostPane.querySelector('#canvasPlusTextPlacement'), 'more');
        move(hostPane.querySelector('#eiSharedStylesV13'), 'more');
        move(hostPane.querySelector('#eiConstraintPanel'), 'more');
        move(hostPane.querySelector('#shapeControls'), 'more');
        const fine = [...hostPane.querySelectorAll('h2')].find((h) => /^fine position$/i.test(h.textContent.trim()));
        if (fine && !fine.closest('.ix-groups')) move(fine, 'more');
        hostPane.querySelectorAll('.actions').forEach((actions) => {
          if (actions.closest('.ix-groups')) return;
          if (actions.querySelector('[data-nudge], [data-size]')) move(actions, 'more');
        });
      }

      // Any late standalone card that belongs to none of the above is safer in
      // More than left as a 5,000 px wall below the groups.
      hostPane.querySelectorAll(':scope > .final-advanced-inspector, :scope > section[id]').forEach((section) => {
        if (section.closest('.ix-groups') || !section.id) return;
        if (['canvasPlusTransform', 'canvasPlusTextBox', 'canvasPlusTextPlacement', 'canvasPlusAiTools'].includes(section.id)) return;
        move(section, 'more');
      });
      foldSections('more');

      hide(hostProps.querySelector(':scope > .final-timeline'));
      const legacyHeading = hostPane.querySelector(':scope > h2.studio-inspector-heading');
      if (legacyHeading) hide(legacyHeading);
      hostPane.querySelectorAll('.final-advanced-inspector.is-disabled').forEach((node) => node.classList.remove('is-disabled'));
      syncSelection();
      syncTools();
    } finally {
      busy = false;
    }
  }

  function syncSelection() {
    const hostPane = pane();
    const hostProps = props();
    if (!hostPane || !hostProps) return;
    const selected = hasSelection();
    hostPane.classList.toggle('ix-has-selection', selected);
    hostPane.classList.toggle('ix-no-selection', !selected);
    hostPane.querySelectorAll('.ix-tool').forEach((button) => {
      const objectTool = button.dataset.ixTool !== 'page';
      button.disabled = objectTool && !selected;
      button.setAttribute('aria-disabled', String(button.disabled));
      button.title = button.disabled ? 'Select an object on the canvas to use this tool' : button.getAttribute('aria-label');
    });
    hostPane.querySelectorAll('.ix-group').forEach((groupNode) => {
      const page = groupNode.dataset.ixGroup === 'page';
      groupNode.hidden = !page && !selected;
    });
    if (!selected) {
      const pageGroup = hostPane.querySelector('.ix-group[data-ix-group="page"]');
      if (pageGroup && !pageGroup.open) {
        busy = true;
        pageGroup.open = true;
        busy = false;
      }
    }
  }

  function syncTools() {
    const hostPane = pane();
    if (!hostPane) return;
    hostPane.querySelectorAll('.ix-tool').forEach((button) => {
      const target = hostPane.querySelector(`.ix-group[data-ix-group="${CSS.escape(button.dataset.ixTool)}"]`);
      const open = Boolean(target?.open);
      button.classList.toggle('active', open);
      button.setAttribute('aria-expanded', String(open));
    });
  }

  function installShare() {
    const publish = document.querySelector('[data-inspector-pane="publish"]');
    if (!publish || publish.dataset.shareModern === 'true') return;
    const slug = publish.querySelector('#publicSlug')?.closest('label');
    const access = publish.querySelector('#accessMode')?.closest('label');
    const password = publish.querySelector('#accessPassword')?.closest('label');
    const save = publish.querySelector('#savePublishingSettings');
    const state = publish.querySelector('#publishingSettingsState');
    const info = publish.querySelector('#publishInfo');
    const history = publish.querySelector('#historyBtn');
    const unpublish = publish.querySelector('#unpublishBtn');
    const rsvp = publish.querySelector('#rsvpBtn');
    const wishes = publish.querySelector('#wishesBtn');
    if (!info || !history) return;
    publish.dataset.shareModern = 'true';
    const shell = make('div', 'share-shell');
    shell.innerHTML = `
      <div class="share-hero">
        <div class="share-state"><span class="share-state-dot" aria-hidden="true"></span><div><strong data-share-state>Draft</strong><small data-share-hint>Publish to create a shareable link.</small></div></div>
        <div class="share-link"><input data-share-url type="text" readonly value="" aria-label="Public invitation link"><button type="button" data-share-copy>Copy</button></div>
        <div class="share-main-actions"><button type="button" class="primary" data-share-publish>Publish</button><button type="button" data-share-preview>Preview</button></div>
      </div>
      <details class="share-section" open>
        <summary><span>Link &amp; access</span><small>Set the public address and who can open it.</small></summary>
        <div class="share-section-body"></div>
      </details>
      <details class="share-section">
        <summary><span>Manage</span><small>Versions, responses and guest wishes.</small></summary>
        <div class="share-section-body share-manage"></div>
      </details>`;
    const accessBody = shell.querySelector('.share-section-body');
    [slug, access, password, save, state].filter(Boolean).forEach((node) => accessBody.append(node));
    const manage = shell.querySelector('.share-manage');
    [history, unpublish, rsvp, wishes].filter(Boolean).forEach((node) => manage.append(node));
    // The hero already states draft/published; the legacy #publishInfo line is
    // kept in the DOM (app.js still updates it) but not shown, so it cannot
    // contradict the state with a stale local-snapshot message.
    // Collaboration and other modules append their own cards to this pane.
    // Keep them instead of discarding their DOM (and their event bindings).
    const moved = new Set([slug, access, password, save, state, info, history, unpublish, rsvp, wishes].filter(Boolean));
    const extras = [...publish.children].filter((node) => !moved.has(node)
      && node.id !== 'publishingSettings'
      && !node.classList.contains('studio-inspector-heading')
      && !(node.tagName === 'H2' && /^publishing$/i.test(node.textContent.trim())));
    extras.forEach((node) => shell.append(node));
    // app.js still writes #publishInfo on every publish/refresh. It must stay in
    // the document (hidden) or refreshPublish() throws inside apply() and every
    // subsequent edit — font size included — is rolled back.
    if (info) {
      info.hidden = true;
      shell.append(info);
    }
    publish.replaceChildren(shell);
    const url = shell.querySelector('[data-share-url]');
    const copy = shell.querySelector('[data-share-copy]');
    const copyText = async () => {
      if (!url.value) return;
      try {
        await navigator.clipboard.writeText(url.value);
      } catch {
        url.select();
        document.execCommand?.('copy');
      }
      copy.textContent = 'Copied';
      setTimeout(() => { copy.textContent = 'Copy'; }, 1400);
    };
    copy.addEventListener('click', copyText);
    shell.querySelector('[data-share-publish]').addEventListener('click', () => document.querySelector('#publishBtn')?.click());
    shell.querySelector('[data-share-preview]').addEventListener('click', () => document.querySelector('#previewBtn')?.click());
    const sync = () => {
      const text = (info.textContent || '').replace(/\s+/g, ' ').trim();
      let serverPublished = null;
      try {
        const inviteId = window.EInviteContext?.getInvitationId?.({ allowRemembered: false });
        const cached = inviteId ? window.inviteStore?.read(`sovan-server-invite:${inviteId}`) : null;
        if (cached && typeof cached.published === 'boolean') serverPublished = cached.published;
      } catch { serverPublished = null; }
      const published = serverPublished ?? !/not published|no snapshot|draft|unpublished|offline/i.test(text);
      const slugValue = (publish.querySelector('#publicSlug')?.value || '').trim();
      let link = '';
      if (info.dataset.publicUrl) {
        try { link = new URL(info.dataset.publicUrl, location.origin).href; } catch { link = ''; }
      }
      if (!link && slugValue) link = `${location.origin}/i/${encodeURIComponent(slugValue)}`;
      if (url.value !== link) url.value = link;
      copy.disabled = !link;
      copy.setAttribute('aria-disabled', String(!link));
      shell.dataset.published = String(published);
      shell.querySelector('[data-share-state]').textContent = published ? 'Published' : 'Draft';
      shell.querySelector('[data-share-hint]').textContent = published ? 'Anyone with the link can open the invitation.' : 'Publish to create a shareable link.';
      shell.querySelector('[data-share-publish]').textContent = published ? 'Update snapshot' : 'Publish';
    };
    sync();
    new MutationObserver(sync).observe(info, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ['data-public-url'] });
    publish.addEventListener('input', sync);
    publish.addEventListener('change', sync);
  }

  function schedule() {
    if (queued) return;
    queued = requestAnimationFrame(() => {
      queued = 0;
      classify();
      syncSelection();
      installShare();
    });
  }

  function install() {
    if (!pane()) return;
    classify();
    installShare();
    const observer = new MutationObserver((records) => {
      if (busy) return;
      if (records.every((record) => record.target.closest?.('.ix-groups') && record.type === 'attributes')) return;
      schedule();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const hostProps = props();
    if (hostProps) {
      new MutationObserver(syncSelection).observe(hostProps, { attributes: true, attributeFilter: ['hidden'] });
    }
    document.addEventListener('einvite:selection-changed', () => {
      requestAnimationFrame(() => {
        syncSelection();
        if (!hasSelection()) openGroup('page', false);
        else {
          const active = pane()?.querySelector('.ix-group[open]');
          if (!active || active.dataset.ixGroup === 'page') {
            const textObject = document.querySelector('#textContentLabel:not([hidden])');
            openGroup(textObject ? 'text' : 'position', false);
          }
        }
      });
    });
    const selectedText = document.querySelector('#textContentLabel:not([hidden])');
    if (hasSelection()) openGroup(selectedText ? 'text' : 'position', false);
    else openGroup('page', false);
    syncSelection();
    syncTools();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => setTimeout(install, 90), { once: true });
  else setTimeout(install, 90);
})();
