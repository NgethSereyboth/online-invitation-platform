/**
 * Phase 2a (V54.4) — Post-send editing badge + edit-history view.
 *
 * Two surfaces:
 *
 *   1. Public "Edited after sending" badge — mounted on the public
 *      invitation page when the host has edited the invitation after
 *      delivering it. The badge shows the timestamp of the first
 *      post-send edit and is the wedge feature against Paperless Post
 *      and Evite, both of which lock the invitation after send.
 *
 *   2. Host edit-history view — mounted on the dashboard, shows the
 *      full diff history (added/changed/removed field paths) for every
 *      post-send edit, plus a "Resend update notification" button that
 *      triggers an "invitation updated" email to already-viewed guests.
 *
 * Bilingual EN + Khmer (KH) per ROADMAP ground rule 5.
 *
 * Surface contract:
 *   window.EInviteEditHistory.mountBadge(root, { invitationId, mode, sentAt, editedAfterSendAt })
 *   window.EInviteEditHistory.mountHistoryView(root, { invitationId, mode })
 */
(function () {
  'use strict';

  const STRINGS = {
    badgeLabel: { en: 'Edited after sending', km: 'បានកែប្រែបន្ទាប់ពីផ្ញើ' },
    badgeTitle: {
      en: 'The host updated this invitation after it was sent. Tap to view what changed.',
      km: 'ម្ចាស់កម្មវិធីបានកែប្រែការអញ្ជើញនេះបន្ទាប់ពីបានផ្ញើ។ ចុចដើម្បីមើលអ្វីដែលបានផ្លាស់ប្រែ។',
    },
    historyTitle: { en: 'Edit history', km: 'ប្រវត្តិកែប្រែ' },
    historyIntro: {
      en: 'Every change you made after the invitation was first sent is recorded here. Guests who already opened the invitation can be notified of the update.',
      km: 'ការផ្លាស់ប្រែណាមួយដែលអ្នកបានធ្វើបន្ទាប់ពីការអញ្ជើញត្រូវបានផ្ញើជាលើកដំបូងត្រូវបានកត់ត្រានៅទីនេះ។ ភ្ញៀវដែលបានបើកការអញ្ជើញរួចហើយអាចត្រូវបានជូនដំណឹងអំពីការផ្លាស់ប្រែ។',
    },
    empty: { en: 'No edits have been made after sending yet.', km: 'មិនទាន់មានការកែប្រែណាមួយបន្ទាប់ពីផ្ញើនៅឡើយទេ។' },
    resend: { en: 'Resend update notification', km: 'ផ្ញើការជូនដំណឹងបច្ចុប្បន្នភាពឡើងវិញ' },
    resendDone: {
      en: 'Notification sent to {sent} guest(s).',
      km: 'បានផ្ញើការជូនដំណឹងទៅ {sent} ភ្ញៀវ។',
    },
    resendFailed: { en: 'Could not resend the notification. Please try again.', km: 'មិនអាចផ្ញើការជូនដំណឹងឡើងវិញបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    diffAdded: { en: 'Added', km: 'បានបន្ថែម' },
    diffChanged: { en: 'Changed', km: 'បានផ្លាស់ប្រែ' },
    diffRemoved: { en: 'Removed', km: 'បានលុប' },
    reason: { en: 'Reason', km: 'មូលហេតុ' },
    versionLabel: { en: 'Version', km: 'កំណែ' },
    loading: { en: 'Loading edit history…', km: 'កំពុងផ្ទុកប្រវត្តិកែប្រែ…' },
    error: { en: 'Could not load edit history.', km: 'មិនអាចផ្ទុកប្រវត្តិកែប្រែបានទេ។' },
  };

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  // V2-UX-5 (P1-B, WCAG 3.1.2): emit lang="km" / lang="en" on every text fragment
  // so screen readers pick the correct pronunciation engine. The Khmer span keeps
  // the existing `khmer-text` class for CSS targeting via :lang(km) / [lang="km"].
  const langText = (key, mode) => {
    const en = STRINGS[key] ? STRINGS[key].en : key;
    const km = STRINGS[key] ? STRINGS[key].km : key;
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text" lang="km">${esc(km)}</span>`;
    if (mode === 'both') return `<span class="i18n i18n-en" lang="en">${esc(en)}</span> <span class="i18n i18n-km khmer-text" lang="km">${esc(km)}</span>`;
    return `<span class="i18n i18n-en" lang="en">${esc(en)}</span>`;
  };
  const formatTs = (ts) => {
    if (!ts) return '';
    try {
      const d = new Date(Number(ts));
      if (isNaN(d.getTime())) return '';
      return d.toLocaleString();
    } catch { return ''; }
  };

  /**
   * Mount the "Edited after sending" badge on the public invitation page.
   *
   * The badge is rendered above the main invitation content. Clicking it
   * scrolls to a small dialog explaining that the host updated the
   * invitation after sending it. The badge is only rendered when
   * ``editedAfterSendAt`` is set (i.e., the host has actually edited).
   */
  function mountBadge(root, opts) {
    if (!root || !opts || !opts.invitationId) return;
    if (!opts.editedAfterSendAt) return;  // No post-send edits → no badge.
    const mode = opts.mode || 'both';
    const badge = document.createElement('aside');
    badge.className = 'invitation-edit-badge reveal';
    badge.setAttribute('role', 'status');
    badge.setAttribute('aria-live', 'polite');
    badge.setAttribute('title', STRINGS.badgeTitle.en);
    const when = formatTs(opts.editedAfterSendAt);
    badge.innerHTML = `
      <span class="edit-badge-icon" aria-hidden="true">✎</span>
      <span class="edit-badge-text">${langText('badgeLabel', mode)}${when ? ` · ${esc(when)}` : ''}</span>
    `;
    // Insert as the first child of the root, above the cover/hero.
    root.insertBefore(badge, root.firstChild);
  }

  /**
   * Mount the host's full edit-history view (dashboard side).
   *
   * Fetches ``GET /api/invitations/{id}/edit-history`` and renders a
   * chronological list of edits with the diff (added/changed/removed
   * field paths) plus a "Resend update notification" button.
   */
  function mountHistoryView(root, opts) {
    if (!root || !opts || !opts.invitationId) return;
    const invitationId = opts.invitationId;
    const mode = opts.mode || 'both';
    const section = document.createElement('section');
    section.className = 'invitation-edit-history guest-feature';
    section.setAttribute('aria-label', STRINGS.historyTitle.en);
    section.innerHTML = `
      <h2>${langText('historyTitle', mode)}</h2>
      <p class="muted">${langText('historyIntro', mode)}</p>
      <button class="resend-notification primary" type="button" disabled>${langText('resend', mode)}</button>
      <p class="resend-status" role="status" aria-live="polite"></p>
      <ol class="edit-history-list">${langText('loading', mode)}</ol>
    `;
    root.appendChild(section);

    const list = section.querySelector('.edit-history-list');
    const resendBtn = section.querySelector('.resend-notification');
    const resendStatus = section.querySelector('.resend-status');

    fetch(`/api/invitations/${encodeURIComponent(invitationId)}/edit-history`, {
      headers: { Accept: 'application/json' },
    }).then((r) => r.json()).then((data) => {
      const entries = (data && data.history) || [];
      if (!entries.length) {
        list.innerHTML = `<li class="muted">${langText('empty', mode)}</li>`;
      } else {
        list.innerHTML = entries.map(renderEntry).join('');
      }
      // Enable the resend button only when there is at least one post-send edit.
      const canResend = !!(data && data.sentAt && entries.length);
      resendBtn.disabled = !canResend;
    }).catch(() => {
      list.innerHTML = `<li class="error">${langText('error', mode)}</li>`;
    });

    resendBtn.addEventListener('click', async () => {
      if (resendBtn.disabled) return;
      resendBtn.disabled = true;
      resendStatus.textContent = '';
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/resend-notification`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ onlyViewed: false }),
        });
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || 'HTTP ' + res.status);
        const sent = (payload && payload.sent) || 0;
        const msg = (STRINGS.resendDone.en).replace('{sent}', String(sent));
        const msgKm = (STRINGS.resendDone.km).replace('{sent}', String(sent));
        resendStatus.innerHTML = mode === 'km'
          ? `<span class="khmer-text" lang="km">${esc(msgKm)}</span>`
          : mode === 'both'
            ? `<span lang="en">${esc(msg)}</span> <span class="khmer-text" lang="km">${esc(msgKm)}</span>`
            : `<span lang="en">${esc(msg)}</span>`;
      } catch (err) {
        resendStatus.innerHTML = `<span class="error">${langText('resendFailed', mode)}</span>`;
      } finally {
        resendBtn.disabled = false;
      }
    });
  }

  function renderEntry(entry) {
    const when = formatTs(entry.editedAt);
    const reason = entry.reason || '';
    const diffItems = (entry.diff || []).map((d) => {
      const path = d.path || '?';
      const before = d.before;
      const after = d.after;
      const beforeStr = before === undefined || before === null ? `<em>${langText('diffRemoved', 'en')}</em>` : `<code>${esc(JSON.stringify(before))}</code>`;
      const afterStr = after === undefined || after === null ? `<em>${langText('diffRemoved', 'en')}</em>` : `<code>${esc(JSON.stringify(after))}</code>`;
      return `<li><span class="diff-path">${esc(path)}</span>: ${beforeStr} → ${afterStr}</li>`;
    }).join('');
    return `
      <li class="edit-history-entry">
        <header>
          <strong>${esc(when)}</strong>
          <span class="muted">v${esc(entry.documentVersion)}</span>
        </header>
        ${reason ? `<p class="edit-reason">${langText('reason', 'en')}: ${esc(reason)}</p>` : ''}
        ${diffItems ? `<ul class="edit-diff">${diffItems}</ul>` : ''}
      </li>`;
  }

  window.EInviteEditHistory = { mountBadge, mountHistoryView };
})();
