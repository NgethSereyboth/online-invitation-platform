;/**
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
    const en = (STRINGS[key] && STRINGS[key].en) || key;
    const km = (STRINGS[key] && STRINGS[key].km) || en;
    if (mode === 'en') return `<span class="i18n i18n-en" lang="en">${esc(en)}</span>`;
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km)}</span>`;
    return `<span class="i18n i18n-en" lang="en">${esc(en)}</span> <span class="i18n i18n-km khmer-text" lang="km" lang="km">${esc(km)}</span>`;
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
          ? `<span class="khmer-text" lang="km" lang="km">${esc(msgKm)}</span>`
          : mode === 'both'
            ? `<span lang="en">${esc(msg)}</span> <span class="khmer-text" lang="km" lang="km">${esc(msgKm)}</span>`
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


/* Mounted here instead of in a page-level inline <script>: the server sends
   `script-src 'self'` with no nonce or hash list, so the edit history mount block was refused
   outright and logged a CSP violation on every dashboard load. This module is already part
   of bundle-dashboard.js, so moving the mount into it adds no request and no script tag.
   The block below is byte-for-byte the inline block it replaces. */
// Mount edit-history view for the active invitation (V2-UX-3, ROADMAP-V2 §3.3).
// Placed AFTER the editor area (the dashboardView + create dialogs) and BEFORE
// the signup-sheets + polls panels inside <main>, so the host sees the diff
// history between the editor and the guest-feature panels. Shares the same
// invitation-id resolver chain as ux-1/ux-2 so all panels see the same active
// invitation. Wires window.EInviteEditHistory.mountHistoryView (which renders
// its own <section> with header + intro + resend button + diff list) plus
// mountBadge (which renders the "Edited after sending · <timestamp>" badge
// above the mount when the host has actually edited after sending). The
// editedAfterSendAt timestamp is fetched once from the edit-history endpoint
// (the same endpoint the history view itself uses) and surfaced via the
// badge + the #edit-history-meta line at the top of the panel.
(function () {
  function resolveInvitationId() {
    if (window.EINVITE_INVITATION_ID) return String(window.EINVITE_INVITATION_ID);
    try {
      var qp = new URLSearchParams(location.search).get('invitation');
      if (qp) return decodeURIComponent(qp);
    } catch (e) {}
    try {
      if (window.EInviteContext && typeof window.EInviteContext.getInvitationId === 'function') {
        return window.EInviteContext.getInvitationId() || '';
      }
    } catch (e) {}
    try { return localStorage.getItem('sovan-active-invite') || ''; } catch (e) { return ''; }
  }
  function detectMode() {
    if (window.EInviteLang) return window.EInviteLang;
    var htmlLang = String(document.documentElement.lang || '').toLowerCase();
    if (htmlLang === 'km' || htmlLang.indexOf('km-') === 0) return 'km';
    return 'both';
  }
  function formatTs(ts) {
    if (!ts) return '';
    try { var d = new Date(Number(ts)); if (isNaN(d.getTime())) return ''; return d.toLocaleString(); }
    catch (e) { return ''; }
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function setMeta(metaEl, mode, sentAt, editedAfterSendAt) {
    if (!metaEl) return;
    if (!sentAt && !editedAfterSendAt) { metaEl.innerHTML = ''; return; }
    var sentEn = sentAt ? 'Sent ' + formatTs(sentAt) : '';
    var sentKm = sentAt ? 'បានផ្ញើ ' + formatTs(sentAt) : '';
    var editedEn = editedAfterSendAt ? 'Edited after sending ' + formatTs(editedAfterSendAt) : '';
    var editedKm = editedAfterSendAt ? 'បានកែប្រែបន្ទាប់ពីផ្ញើ ' + formatTs(editedAfterSendAt) : '';
    var partsEn = [sentEn, editedEn].filter(Boolean).join(' · ');
    var partsKm = [sentKm, editedKm].filter(Boolean).join(' · ');
    if (mode === 'km') {
      metaEl.innerHTML = '<span lang="km" class="khmer-text">' + esc(partsKm) + '</span>';
    } else if (mode === 'en') {
      metaEl.innerHTML = '<span>' + esc(partsEn) + '</span>';
    } else {
      metaEl.innerHTML = '<span>' + esc(partsEn) + '</span> <span lang="km" class="khmer-text">' + esc(partsKm) + '</span>';
    }
  }
  function mountPanel() {
    var panel = document.getElementById('edit-history-panel');
    if (!panel) return;
    var mountEl = document.getElementById('edit-history-mount');
    var badgeEl = document.getElementById('edited-after-send-badge');
    var metaEl = document.getElementById('edit-history-meta');
    if (!mountEl || !badgeEl) return;
    // Static mode (no application server): both the history view and the badge
    // read /api/invitations/{id}/edit-history, so skip both fetches.
    if (window.EInviteBackend && !window.EInviteBackend.isAvailable()) { panel.hidden = true; return; }
    if (!window.EInviteEditHistory || typeof window.EInviteEditHistory.mountHistoryView !== 'function') {
      console.warn('EInviteEditHistory not available — edit-history panel will not mount.');
      return;
    }
    var invitationId = resolveInvitationId();
    if (!invitationId) {
      mountEl.innerHTML = '<p class="muted"><span class="i18n i18n-en">Select an invitation first to view its edit history.</span><span class="i18n i18n-km khmer-text" lang="km">Select an invitation first to view its edit history.</span></p>';
      panel.hidden = false;
      return;
    }
    panel.hidden = false;
    var mode = detectMode();
    // (1) Mount the history view — it renders its own <section> with header +
    // intro + resend-notification button + diff list inside #edit-history-mount.
    try {
      window.EInviteEditHistory.mountHistoryView(mountEl, { invitationId: invitationId, mode: mode });
    } catch (e) { console.warn('edit-history mount failed', e); }
    // (2) Fetch the same endpoint to get sentAt + editedAfterSendAt so we can
    // render the badge + the meta line at the top of the panel. The history
    // view does its own fetch for the diff list; this one is for the badge.
    try {
      fetch('/api/invitations/' + encodeURIComponent(invitationId) + '/edit-history', {
        headers: { Accept: 'application/json' }
      }).then(function (r) { return r.ok ? r.json() : null; }).then(function (data) {
        if (!data) return;
        var sentAt = data.sentAt || null;
        var editedAfterSendAt = data.editedAfterSendAt || null;
        setMeta(metaEl, mode, sentAt, editedAfterSendAt);
        if (!editedAfterSendAt) return; // No post-send edits → no badge.
        try {
          window.EInviteEditHistory.mountBadge(badgeEl, {
            invitationId: invitationId,
            editedAfterSendAt: editedAfterSendAt,
            sentAt: sentAt,
            mode: mode
          });
        } catch (e) { console.warn('edit-history badge mount failed', e); }
      }).catch(function () { /* Badge is best-effort; ignore fetch errors. */ });
    } catch (e) { /* Badge fetch is best-effort. */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountPanel, { once: true });
  } else { mountPanel(); }
})();