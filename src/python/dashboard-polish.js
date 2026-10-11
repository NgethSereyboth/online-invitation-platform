/*
 * dashboard-polish.js — V55 (dispatch Group 2): the dashboard's filter row and
 * its async states.
 *
 * Before: this module injected a marketing intro ("Create beautiful moments,
 * manage every guest."), four metric cards and a second filter bar, all with
 * English-only copy, and final-polish.css hid the real .dash-head. It is now the
 * single owner of the dashboard toolbar:
 *
 *   1. Filter row   — search (240px) + segmented control (All / Published / Archive).
 *   2. Loading      — skeleton cards that mirror the real card (same height, same
 *                     16:9 cover, same two-line body). Replaced as soon as the real
 *                     cards or the empty state land.
 *   3. Error        — when the invitations endpoint fails and there is nothing in
 *                     local storage: icon, plain-English reason, Retry.
 *   4. Card polish  — status badge (state only, never decoration), hover
 *                     quick-actions row, uniform card height.
 *
 * Bilingual: EN + KM spans through the platform `[lang] .i18n-km` mechanism.
 * Strings without a trusted Khmer source reuse the English text ("fallback" in
 * docs/i18n/TRANSLATIONS.csv) and are listed as KH_PENDING in
 * docs/reviews/redesign-report.md. Khmer is never invented here.
 */
(() => {
  'use strict';
  const view = document.querySelector('#dashboardView');
  const grid = document.querySelector('#inviteGrid');
  if (!view || !grid) return;

  const SEGMENTS = [
    { id: 'all', en: 'All', km: 'ទាំងអស់' },          /* docs/i18n/TRANSLATIONS.csv: translated */
    { id: 'published', en: 'Published', km: 'ផ្សាយ' },  /* translated */
    { id: 'archived', en: 'Archive', km: 'បង្ងា' }      /* translated */
  ];

  function i18nHtml(en, km) {
    const khmer = km == null ? en : km;
    const cls = km == null ? 'i18n i18n-km' : 'i18n i18n-km khmer-text';
    return `<span class="i18n i18n-en">${en}</span><span class="${cls}" lang="km">${khmer}</span>`;
  }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /* --- 1. Filter row ------------------------------------------------------ */
  let toolbar = null;
  let query = '';
  let segment = 'all';

  function buildToolbar() {
    if (document.querySelector('.dashboard-filterbar')) {
      toolbar = document.querySelector('.dashboard-filterbar');
      return;
    }
    toolbar = document.createElement('div');
    toolbar.className = 'dashboard-filterbar app-toolbar';
    toolbar.innerHTML =
      `<label class="app-search">` +
      `<span class="app-search__icon" aria-hidden="true">⌕</span>` +
      `<input id="dashboardSearch" type="search" autocomplete="off" ` +
      `placeholder="${esc('Search invitations…')}" ` +
      `data-en="${esc('Search invitations…')}" data-km="${esc('Search invitations…')}" ` +
      `aria-label="${esc('Search invitations…')}">` +
      `</label>` +
      `<div class="segmented" role="group" aria-label="${esc('Filter invitations')}">` +
      SEGMENTS.map(s => `<button type="button" data-dash-filter="${s.id}"` +
        `${s.id === 'all' ? ' class="active" aria-pressed="true"' : ' aria-pressed="false"'}>${i18nHtml(s.en, s.km)}</button>`).join('') +
      `</div>`;
    const head = view.querySelector('.dash-head');
    if (head) head.after(toolbar);
    else view.prepend(toolbar);

    const search = toolbar.querySelector('#dashboardSearch');
    search.addEventListener('input', () => { query = search.value.trim().toLowerCase(); applyFilters(); });
    toolbar.querySelectorAll('[data-dash-filter]').forEach(button => {
      button.addEventListener('click', () => {
        segment = button.dataset.dashFilter;
        toolbar.querySelectorAll('[data-dash-filter]').forEach(other => {
          const on = other === button;
          other.classList.toggle('active', on);
          other.setAttribute('aria-pressed', String(on));
        });
        applyFilters();
      });
    });
  }

  function statusOf(card) {
    const badge = card.querySelector('.app-badge');
    return badge ? badge.dataset.state : 'published';
  }

  function applyFilters() {
    const cards = grid.querySelectorAll('.invite-card');
    let visible = 0;
    cards.forEach(card => {
      const matchesQuery = !query || card.textContent.toLowerCase().includes(query);
      const matchesSegment = segment === 'all' || statusOf(card) === segment;
      const show = matchesQuery && matchesSegment;
      card.hidden = !show;
      if (show) visible++;
    });
    let note = grid.querySelector('.dashboard-no-results');
    if (!cards.length) { if (note) note.remove(); return; }
    if (visible) { if (note) note.remove(); return; }
    if (!note) {
      note = document.createElement('p');
      note.className = 'dashboard-no-results empty-state__message';
      note.innerHTML = i18nHtml('No invitations match this filter.', null);
      grid.append(note);
    }
  }

  /* --- 2. Loading skeletons ---------------------------------------------- */
  function showSkeletons() {
    if (grid.querySelector('.invite-card, .empty-state, .error-state')) return;
    if (grid.querySelector('.skeleton-card')) return;
    grid.innerHTML = Array.from({ length: 6 }, () =>
      `<article class="skeleton-card" aria-hidden="true">` +
      `<span class="skeleton-card__cover"></span>` +
      `<span class="skeleton-card__line"></span>` +
      `<span class="skeleton-card__line skeleton-card__line--short"></span>` +
      `</article>`).join('');
  }
  function clearSkeletons() {
    grid.querySelectorAll('.skeleton-card').forEach(node => node.remove());
  }

  /* --- 3. Error state ---------------------------------------------------- */
  function renderError(reason) {
    if (grid.querySelector('.error-state')) return;
    clearSkeletons();
    grid.innerHTML =
      `<section class="error-state empty-state">` +
      `<span class="empty-state__icon" aria-hidden="true">⚠</span>` +
      `<h2 class="empty-state__title">${i18nHtml("Couldn't load your invitations", null)}</h2>` +
      `<p class="empty-state__message">${i18nHtml(reason || 'The server did not answer. Your drafts are still saved on this device.')}</p>` +
      `<div class="empty-state__action"><button type="button" class="app-button--secondary" data-retry>${i18nHtml('Retry', 'ព្យាយាមម្ដងទៀត')}</button></div>` +
      `</section>`;
    const retry = grid.querySelector('[data-retry]');
    if (retry) retry.addEventListener('click', () => window.location.reload());
  }

  async function probeServer() {
    /* Static mode (no application server): the backend module already knows, so
       do not fire a request whose only possible answer is a 404 (G8). The local
       draft store stays authoritative. */
    if (window.EInviteBackend?.ready) { try { await window.EInviteBackend.ready; } catch (e) { /* ignore */ } }
    if (window.EInviteBackend && !window.EInviteBackend.isAvailable()) return;
    let localInvites = null;
    try { localInvites = JSON.parse(localStorage.getItem('sovan-multi-invites-v1') || 'null'); } catch (e) { localInvites = null; }
    /* Local-first: an array (empty or not) is authoritative enough. Only a device
       that has never seen this account needs the server, and only then can a failed
       request be reported as an error state. */
    if (Array.isArray(localInvites)) return;
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 7000) : null;
    fetch('/api/invitations', { headers: { Accept: 'application/json' }, credentials: 'same-origin', signal: controller ? controller.signal : undefined })
      .then(response => {
        if (timer) clearTimeout(timer);
        if (!response.ok) renderError(response.status === 401 ? 'Your session expired. Sign in again to load them.' : 'The server answered with an error. Your drafts are still saved on this device.');
      })
      .catch(() => {
        if (timer) clearTimeout(timer);
        renderError('The server is unreachable. Your drafts are still saved on this device.');
      });
  }

  /* --- 4. Card polish ---------------------------------------------------- */
  const BADGE = {
    published: { en: 'Published', km: 'ផ្សាយ', icon: '●' },
    draft: { en: 'Draft', km: null, icon: '◐' },
    archived: { en: 'Archived', km: 'បង្ងា', icon: '▤' }
  };

  function decorate() {
    grid.querySelectorAll('.invite-card').forEach(card => {
      /* Status badge: state only — never "New!" or "Recommended". */
      const pill = card.querySelector('.invite-status-pill');
      if (pill) {
        const raw = (pill.textContent || '').trim().toLowerCase();
        const state = raw.includes('draft') ? 'draft' : raw.includes('archiv') ? 'archived' : 'published';
        const meta = BADGE[state];
        pill.className = `app-badge app-badge--${state}`;
        pill.dataset.state = state;
        pill.innerHTML = `<span aria-hidden="true">${meta.icon}</span>${i18nHtml(meta.en, meta.km)}`;
      }
      /* Hover quick actions — visible affordance before the drag/click begins. */
      if (!card.querySelector('.invite-quick')) {
        const body = card.querySelector('.invite-body');
        if (body) {
          const quick = document.createElement('div');
          quick.className = 'invite-quick';
          quick.innerHTML =
            `<button type="button" class="app-iconbtn" data-quick="edit" title="${esc('Edit design')}">${i18nHtml('Edit', 'កែប្រែ')}</button>` +
            `<a class="app-iconbtn" href="guests.html" title="${esc('Guest list')}">${i18nHtml('Guests', 'បញ្ចូលភ្ញៀវ')}</a>` +
            `<a class="app-iconbtn" href="analytics.html" title="${esc('Analytics')}">${i18nHtml('Analytics', 'វិភានសម្តែង')}</a>`;
          body.append(quick);
          quick.querySelector('[data-quick="edit"]').addEventListener('click', () => {
            const edit = card.querySelector('[data-edit]');
            if (edit) edit.click();
          });
        }
      }
    });
    applyFilters();
  }

  function schedule() {
    if (view.hidden) return;
    clearSkeletons();
    decorate();
  }

  buildToolbar();
  if (!document.querySelector('.invite-card')) showSkeletons();
  new MutationObserver(() => { if (grid.querySelector('.invite-card')) schedule(); }).observe(grid, { childList: true });
  document.addEventListener('DOMContentLoaded', () => {
    if (view.hidden) showSkeletons();
    setTimeout(() => { clearSkeletons(); decorate(); probeServer(); }, 400);
  }, { once: true });
  if (document.readyState !== 'loading') setTimeout(() => { clearSkeletons(); decorate(); probeServer(); }, 400);

  window.EInviteDashboard = Object.freeze({ version: 55, decorate, applyFilters, renderError });
})();
