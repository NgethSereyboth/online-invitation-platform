/**
 * Phase 2a (V54.1) — Sign-up sheets guest UI.
 *
 * Loaded on the public invitation page (bundle-public-v15.js). Renders a
 * <section> per sheet showing slots, claim counts, and a claim form. Vanilla
 * JS — no chart library, no framework. Bilingual EN + KH strings per
 * ROADMAP ground rule 5.
 *
 * Surface contract (frozen for Phase 2a):
 *   window.EInviteSignupSheets.enhance(root, { invitationId, mode, guestToken, accessToken })
 *     mode is "host" or "guest" (passed by the host dashboard / public page).
 */
(function () {
  'use strict';

  const STRINGS = {
    sectionTitle: { en: 'Sign-up sheets', km: 'តារាងចុះឈ្មោះ' },
    sectionIntro: {
      en: 'Claim an item or slot to bring to the event.',
      km: 'ចុះឈ្មោះយកធាតុ ឬទីតាំងដែលត្រូវនាំយកទៅការប្រគំតន្ត្រី។',
    },
    claim: { en: 'Claim', km: 'ចុះឈ្មោះ' },
    cancel: { en: 'Cancel my spot', km: 'បោះបង់ទីតាំងរបស់ខ្ញុំ' },
    name: { en: 'Your name', km: 'ឈ្មោះរបស់អ្នក' },
    email: { en: 'Email (optional)', km: 'អ៊ីមែល (ស្រេចចិត្ត)' },
    quantity: { en: 'Quantity', km: 'ចំនួន' },
    remaining: { en: 'remaining', km: 'នៅសល់' },
    full: { en: 'Full', km: 'ពេញលេញ' },
    claimed: { en: 'You claimed this', km: 'អ្នកបានចុះឈ្មោះ' },
    closed: { en: 'Closed', km: 'បិទហើយ' },
    submit: { en: 'Save my spot', km: 'រក្សាទុកទីតាំងរបស់ខ្ញុំ' },
    loading: { en: 'Loading sign-up sheets…', km: 'កំពុងផ្ទុកតារាងចុះឈ្មោះ…' },
    empty: { en: 'No sign-up sheets are open for this invitation yet.', km: 'មិនទាន់មានតារាងចុះឈ្មោះសម្រាប់ការអញ្ជើញនេះនៅឡើយ។' },
    error: { en: 'We could not save your claim. Please try again.', km: 'មិនអាចរក្សាទុកការចុះឈ្មោះបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    cancelled: { en: 'Your spot was released.', km: 'ទីតាំងរបស់អ្នកត្រូវបានដកចេញ។' },
    success: { en: 'Saved! The host has been notified.', km: 'បានរក្សាទុក! ម្ចាស់កម្មវិធីបានទទួលដំណឹង។' },
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
  const formatDate = (ts) => (ts ? new Date(parseInt(ts, 10)).toLocaleString() : '');

  function enhance(root, opts) {
    if (!root || !opts || !opts.invitationId) return;
    const invitationId = opts.invitationId;
    const guestToken = opts.guestToken || '';
    const accessToken = opts.accessToken || '';
    const mode = opts.mode || 'guest';
    const headers = {
      'Content-Type': 'application/json',
      ...(guestToken ? { 'X-Invitation-Guest': guestToken } : {}),
      ...(accessToken ? { 'X-Invitation-Access': accessToken } : {}),
    };

    const section = document.createElement('section');
    section.className = 'guest-feature signup-sheets';
    section.setAttribute('aria-label', STRINGS.sectionTitle.en);
    section.innerHTML = `<h2>${langText('sectionTitle', mode)}</h2><p class="muted">${langText('sectionIntro', mode)}</p><p class="state">${langText('loading', mode)}</p>`;
    root.appendChild(section);

    refresh();

    async function refresh() {
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const sheets = await res.json();
        render(sheets);
      } catch (err) {
        section.querySelector('.state').textContent = err.message || 'error';
      }
    }

    function render(sheets) {
      if (!sheets || !sheets.length) {
        section.querySelector('.state').innerHTML = `<p class="muted">${langText('empty', mode)}</p>`;
        return;
      }
      const html = sheets.map(renderSheet).join('');
      section.querySelector('.state').innerHTML = html;
      section.querySelectorAll('form[data-sheet]').forEach((form) => {
        form.addEventListener('submit', onSubmitClaim);
      });
      section.querySelectorAll('button[data-cancel-claim]').forEach((btn) => {
        btn.addEventListener('click', onCancelClaim);
      });
    }

    function renderSheet(sheet) {
      const closed = sheet.deadlineTs && parseInt(sheet.deadlineTs, 10) < Date.now();
      const slots = (sheet.slots || []).map((slot) => renderSlot(slot, sheet, closed)).join('');
      return `
        <article class="signup-sheet" data-sheet-id="${esc(sheet.id)}">
          <h3>${esc(sheet.title)}</h3>
          ${sheet.deadlineTs ? `<p class="muted">${langText('closed', mode).includes('Closed') ? 'Deadline' : 'កាលបរិច្ឆេទកំណត់'}: ${formatDate(sheet.deadlineTs)}</p>` : ''}
          ${closed ? `<p class="badge badge-closed">${langText('closed', mode)}</p>` : ''}
          <ul class="slot-list">${slots}</ul>
        </article>`;
    }

    function renderSlot(slot, sheet, closed) {
      const capacity = parseInt(slot.capacity || 0, 10);
      const claimed = parseInt(slot.claimedQuantity || 0, 10);
      const remaining = capacity > 0 ? Math.max(0, capacity - claimed) : null;
      const mine = (slot.claims || []).some((c) => c.self);
      const full = capacity > 0 && remaining === 0;
      return `
        <li class="slot" data-slot-id="${esc(slot.id)}">
          <div class="slot-head">
            <strong>${esc(slot.label)}</strong>
            ${capacity > 0 ? `<span class="badge ${full ? 'badge-full' : ''}">${full ? langText('full', mode) : `${remaining} ${langText('remaining', mode)}`}</span>` : `<span class="badge">${claimed} ${langText('claimed', mode).toLowerCase()}</span>`}
            ${mine ? `<span class="badge badge-mine">${langText('claimed', mode)}</span>` : ''}
          </div>
          ${slot.description ? `<p class="muted">${esc(slot.description)}</p>` : ''}
          ${closed || full ? '' : `
            <form data-sheet="${esc(sheet.id)}" data-slot="${esc(slot.id)}">
              <label>${langText('name', mode)}<input type="text" name="name" required maxlength="120"></label>
              <label>${langText('email', mode)}<input type="email" name="email" maxlength="254"></label>
              <label>${langText('quantity', mode)}<input type="number" name="quantity" min="1" max="100" value="1"></label>
              <button type="submit">${langText('submit', mode)}</button>
            </form>
          `}
          ${mine ? `<button type="button" data-cancel-claim data-sheet="${esc(sheet.id)}" data-slot="${esc(slot.id)}">${langText('cancel', mode)}</button>` : ''}
        </li>`;
    }

    async function onSubmitClaim(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const sheetId = form.getAttribute('data-sheet');
      const slotId = form.getAttribute('data-slot');
      const button = form.querySelector('button[type=submit]');
      const data = Object.fromEntries(new FormData(form));
      const payload = { slotId, quantity: parseInt(data.quantity || 1, 10), name: data.name, email: data.email };
      if (button) button.disabled = true;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets/${encodeURIComponent(sheetId)}/claim`, {
          method: 'POST', headers, body: JSON.stringify(payload),
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
        await refresh();
      } catch (err) {
        alert(err.message);
        if (button) button.disabled = false;
      }
    }

    async function onCancelClaim(event) {
      const btn = event.currentTarget;
      const sheetId = btn.getAttribute('data-sheet');
      // Find the claim id for this slot — server returns it in the next refresh,
      // but for cancellation we look it up via the list response's claim.self.
      // Simpler: re-fetch and DELETE the matching claim.
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`, { headers });
        const sheets = await res.json();
        const sheet = sheets.find((s) => s.id === sheetId);
        if (!sheet) return;
        const slot = (sheet.slots || []).find((sl) => sl.id === btn.getAttribute('data-slot'));
        const mine = (slot && slot.claims || []).find((c) => c.self);
        if (!mine) return;
        const del = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets/${encodeURIComponent(sheetId)}/claims/${encodeURIComponent(mine.id)}`, {
          method: 'DELETE', headers,
        });
        if (!del.ok) throw new Error('HTTP ' + del.status);
        await refresh();
      } catch (err) {
        alert(err.message);
      }
    }
  }

  window.EInviteSignupSheets = { enhance };
})();
