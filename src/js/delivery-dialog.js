/**
 * Phase 2a (V54.1) — Multi-channel delivery host dialog.
 *
 * Loaded on the dashboard / host pages. Lets the host pick channels (email
 * default, SMS / WhatsApp / Telegram when env-configured), select recipients
 * from the guest list, and dispatch the invitation. Vanilla JS, bilingual
 * EN + KH.
 *
 * Surface contract:
 *   window.EInviteDeliveryDialog.open({ invitationId, document })
 */
(function () {
  'use strict';

  const STRINGS = {
    title: { en: 'Send invitation', km: 'ផ្ញើការអញ្ជើញ' },
    intro: {
      en: 'Pick channels and recipients. Email is always available; SMS / WhatsApp / Telegram require configuration.',
      km: 'ជ្រើសឆានែល និងអ្នកទទួល។ អ៊ីមែលអាចប្រើបានជានិច្ច; SMS / WhatsApp / Telegram ត្រូវការការកំណត់រចនាសម្ព័ន្ធ។',
    },
    channels: { en: 'Channels', km: 'ឆានែល' },
    recipients: { en: 'Recipients', km: 'អ្នកទទួល' },
    message: { en: 'Message (optional)', km: 'សារ (ស្រេចចិត្ត)' },
    subject: { en: 'Subject', km: 'ប្រធានបទ' },
    selectAll: { en: 'Select all', km: 'ជ្រើសទាំងអស់' },
    send: { en: 'Send', km: 'ផ្ញើ' },
    cancel: { en: 'Cancel', km: 'បោះបង់' },
    sent: { en: 'sent', km: 'បានផ្ញើ' },
    skipped: { en: 'skipped', km: 'រំលង' },
    failed: { en: 'failed', km: 'បរាជ័យ' },
    notConfigured: { en: 'Not configured', km: 'មិនបានកំណត់រចនាសម្ព័ន្ធ' },
    close: { en: 'Close', km: 'បិទ' },
  };

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const langText = (key, mode) => {
    const en = STRINGS[key] ? STRINGS[key].en : key;
    const km = STRINGS[key] ? STRINGS[key].km : key;
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    if (mode === 'both') return `<span class="i18n i18n-en">${esc(en)}</span> <span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    return `<span class="i18n i18n-en">${esc(en)}</span>`;
  };
  const detectLang = () => (document.documentElement.lang === 'km' ? 'km' : 'en');

  function open(opts) {
    if (!opts || !opts.invitationId) return;
    const invitationId = opts.invitationId;
    const lang = detectLang();
    const overlay = document.createElement('div');
    overlay.className = 'delivery-dialog-overlay';
    overlay.innerHTML = `
      <div class="delivery-dialog" role="dialog" aria-modal="true" aria-label="${esc(STRINGS.title.en)}">
        <header><h2>${langText('title', lang)}</h2><button type="button" data-close>&times;</button></header>
        <p class="muted">${langText('intro', lang)}</p>
        <form>
          <fieldset>
            <legend>${langText('channels', lang)}</legend>
            <div class="channel-list state">…</div>
          </fieldset>
          <fieldset>
            <legend>${langText('recipients', lang)}</legend>
            <label><input type="checkbox" data-select-all> ${langText('selectAll', lang)}</label>
            <div class="recipient-list state">…</div>
          </fieldset>
          <label>${langText('subject', lang)}<input type="text" name="subject" maxlength="200"></label>
          <label>${langText('message', lang)}<textarea name="message" rows="3" maxlength="5000"></textarea></label>
          <footer>
            <button type="button" data-close>${langText('cancel', lang)}</button>
            <button type="submit">${langText('send', lang)}</button>
          </footer>
        </form>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('[data-close]').addEventListener('click', () => overlay.remove());
    overlay.querySelector('.delivery-dialog').addEventListener('click', (ev) => ev.stopPropagation());
    overlay.addEventListener('click', () => overlay.remove());

    const channelList = overlay.querySelector('.channel-list');
    const recipientList = overlay.querySelector('.recipient-list');
    const selectAll = overlay.querySelector('[data-select-all]');
    const form = overlay.querySelector('form');

    // Load channels + recipients in parallel.
    Promise.all([
      fetch(`/api/invitations/${encodeURIComponent(invitationId)}/delivery-channels`).then((r) => r.json()),
      fetch(`/api/invitations/${encodeURIComponent(invitationId)}/guests`).then((r) => r.json()),
    ]).then(([channelData, guests]) => {
      renderChannels(channelData.channels || []);
      renderRecipients(guests || []);
    }).catch((err) => {
      channelList.innerHTML = `<p class="error">${esc(err.message)}</p>`;
    });

    selectAll.addEventListener('change', () => {
      recipientList.querySelectorAll('input[type=checkbox]').forEach((cb) => { cb.checked = selectAll.checked; });
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = form.querySelector('button[type=submit]');
      submit.disabled = true;
      const channels = Array.from(channelList.querySelectorAll('input[type=checkbox]:checked')).map((cb) => cb.value);
      const recipients = Array.from(recipientList.querySelectorAll('input[type=checkbox]:checked')).map((cb) => JSON.parse(cb.value));
      const data = Object.fromEntries(new FormData(form));
      if (!channels.length || !recipients.length) {
        alert('Select at least one channel and one recipient');
        submit.disabled = false;
        return;
      }
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/deliver`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channels,
            recipients,
            message: data.message || '',
            subject: data.subject || '',
          }),
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
        const results = result.results || [];
        const sent = results.filter((r) => r.status === 'sent').length;
        const skipped = results.filter((r) => r.status === 'skipped').length;
        const failed = results.filter((r) => r.status === 'failed').length;
        alert(`${sent} ${STRINGS.sent.en}, ${skipped} ${STRINGS.skipped.en}, ${failed} ${STRINGS.failed.en}`);
        overlay.remove();
      } catch (err) {
        alert(err.message);
        submit.disabled = false;
      }
    });

    function renderChannels(channels) {
      channelList.innerHTML = channels.map((c) => `
        <label>
          <input type="checkbox" value="${esc(c.name)}" ${c.name === 'email' ? 'checked' : ''} ${c.available ? '' : 'disabled'}>
          ${esc(c.label_en || c.name)}
          ${c.available ? '' : `<span class="muted">(${langText('notConfigured', lang)})</span>`}
        </label>`).join('');
    }

    function renderRecipients(guests) {
      if (!guests.length) {
        recipientList.innerHTML = `<p class="muted">No guests added yet.</p>`;
        return;
      }
      recipientList.innerHTML = guests.map((g) => `
        <label>
          <input type="checkbox" value='${esc(JSON.stringify({ guestId: g.id, name: g.name, email: g.email || '', phone: g.phone || '' }))}'>
          ${esc(g.name)} ${g.email ? `&lt;${esc(g.email)}&gt;` : ''} ${g.phone ? `(${esc(g.phone)})` : ''}
        </label>`).join('');
    }
  }

  window.EInviteDeliveryDialog = { open };
})();
