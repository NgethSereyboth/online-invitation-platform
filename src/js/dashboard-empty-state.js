/*
 * dashboard-empty-state.js — V55 (dispatch Group 2).
 *
 * One job: when the signed-in dashboard has no invitations, render the centred
 * empty state instead of an empty grid. It composes with the `ux-6` empty-state
 * system in modern-ui.css (`.empty-state`, `__icon`, `__title`, `__message`,
 * `__action`) rather than inventing another visual language.
 *
 * Shape follows the dispatch: line-art illustration in the single accent colour,
 * Title medium headline, Body medium explanation, one primary action.
 *
 * Bilingual: every string ships an EN span and a KM span through the platform's
 * `[lang] .i18n-km` mechanism. Strings with no trusted Khmer in
 * docs/i18n/TRANSLATIONS.csv ("fallback" status, as the CSV calls it) reuse the
 * English text and are listed as KH_PENDING in docs/reviews/redesign-report.md —
 * never machine-invented Khmer.
 */
(() => {
  'use strict';
  const grid = document.querySelector('#inviteGrid');
  if (!grid) return;

  const FALLBACK = true; /* see KH_PENDING list in the redesign report */

  function html(en, km) {
    const khmer = km == null ? en : km;
    const cls = FALLBACK && km == null ? 'i18n i18n-km' : 'i18n i18n-km khmer-text';
    return `<span class="i18n i18n-en">${en}</span><span class="${cls}" lang="km">${khmer}</span>`;
  }

  /* Line-art illustration: single accent colour, no gradient, no drop-shadow stack. */
  const ART = `<svg viewBox="0 0 96 72" role="img" aria-hidden="true" focusable="false">` +
    `<rect x="10" y="10" width="60" height="44" rx="4" fill="none" stroke="currentColor" stroke-width="2"/>` +
    `<rect x="26" y="20" width="60" height="44" rx="4" fill="var(--app-surface)" stroke="currentColor" stroke-width="2"/>` +
    `<path d="M38 34h36M38 42h24M38 50h30" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>` +
    `</svg>`;

  function render() {
    const hasCards = grid.querySelector('.invite-card, [data-invite-id], article, .skeleton-card');
    if (hasCards && hasCards.hasAttribute && hasCards.classList.contains('skeleton-card')) return;
    if (grid.children.length && grid.querySelector('.invite-card, [data-invite-id], article')) return;
    /* An error state outranks the empty state — do not overwrite it. */
    if (grid.querySelector('.error-state')) return;

    grid.innerHTML =
      `<section class="empty-state empty-state--invitations">` +
      `<span class="empty-state__icon" aria-hidden="true">${ART}</span>` +
      `<h2 class="empty-state__title">${html('No invitations yet')}</h2>` +
      `<p class="empty-state__message">${html(
        'Create your first invitation, add your event details, then publish and share it with your guests.'
      )}</p>` +
      `<div class="empty-state__action"><button type="button" class="primary" data-empty-create>${html(
        'Create your first invitation'
      )}</button></div>` +
      `</section>`;

    const button = grid.querySelector('[data-empty-create]');
    if (button) {
      button.addEventListener('click', () => {
        const create = document.querySelector('#newBtn');
        if (create) create.click();
        else window.location.href = 'templates.html';
      });
    }
  }

  function schedule() {
    const view = document.querySelector('#dashboardView');
    if (!view || view.hidden) return;
    setTimeout(render, 0);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      new MutationObserver(schedule).observe(grid, { childList: true });
      schedule();
    }, { once: true });
  } else {
    new MutationObserver(schedule).observe(grid, { childList: true });
    schedule();
  }

  window.EInviteDashboardEmptyState = Object.freeze({ version: 55, render });
})();
