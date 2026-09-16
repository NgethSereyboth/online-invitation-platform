/**
 * V2-UX-1 (ROADMAP-V2 §3.1) — Host-side management UI for sign-up sheets.
 *
 * Mounts on the dashboard as a per-invitation panel. The host can list,
 * create, edit, and delete sign-up sheets, expand "View claims" to see
 * every claim's name + email (host-only PII), and watch the loading /
 * empty / error states. Bilingual EN + Khmer per ROADMAP-V2 §3 ground
 * rule "every user-facing string must have an EN and KH variant".
 *
 * Reuses the design tokens (`tokens.css`, `modern-ui.css`) and the
 * existing Phase 2a-1 API contract that already powers the guest-side
 * `signup-sheets.js`. No new design system; no framework.
 *
 * API contract (Phase 2a-1, frozen):
 *   GET    /api/invitations/{id}/signup-sheets
 *          → 200 [{id, invitationId, title, type, slots[], deadlineTs, createdAt, archivedAt}]
 *          (host mode includes slot[].claims[] = {id, guestId, name, email, quantity, createdAt})
 *   POST   /api/invitations/{id}/signup-sheets        {title, type, slots[], deadlineTs?}
 *          → 201 {sheet}
 *   PUT    /api/invitations/{id}/signup-sheets/{sid}  {title?, type?, slots?, deadlineTs?}
 *          → 200 {sheet}
 *   DELETE /api/invitations/{id}/signup-sheets/{sid}
 *          → 200 {deleted:true}
 *
 * Surface contract:
 *   window.EInviteHostSignupSheets.mount(root, { invitationId, lang })
 *     - root: HTMLElement where the panel renders
 *     - invitationId: required; the active invitation
 *     - lang: optional 'en' | 'km' | 'both' (default 'both' for the host)
 */
(function () {
  'use strict';

  /** Bilingual strings — every label, button, and message. */
  const STRINGS = {
    panelTitle: { en: 'Sign-up sheets', km: 'តារាងចុះឈ្មោះ' },
    panelIntro: {
      en: 'Create sign-up sheets so guests can claim items or time slots. Guests see the same sheets on the live invitation page.',
      km: 'បង្កើតតារាងចុះឈ្មោះ ដូច្នេះភ្ញៀវអាចចុះឈ្មោះធាតុ ឬទីតាំងពេលវេលា។ ភ្ញៀវឃើញតារាងដដែលនៅលើទំព័រការអញ្ជើញផ្ទាល់។',
    },
    create: { en: 'Create sheet', km: 'បង្កើតតារាង' },
    edit: { en: 'Edit', km: 'កែប្រែ' },
    delete: { en: 'Delete', km: 'លុប' },
    cancel: { en: 'Cancel', km: 'បោះបង់' },
    save: { en: 'Save', km: 'រក្សាទុក' },
    viewClaims: { en: 'View claims', km: 'មើលការចុះឈ្មោះ' },
    hideClaims: { en: 'Hide claims', km: 'លាក់ការចុះឈ្មោះ' },
    loading: { en: 'Loading sign-up sheets…', km: 'កំពុងផ្ទុកតារាងចុះឈ្មោះ…' },
    empty: { en: 'No sign-up sheets yet. Create one to let guests claim items or slots.', km: 'មិនទាន់មានតារាងចុះឈ្មោះនៅឡើយ។ បង្កើតមួយដើម្បីឱ្យភ្ញៀវអាចចុះឈ្មោះធាតុ ឬទីតាំង។' },
    error: { en: 'Could not load sign-up sheets. Please try again.', km: 'មិនអាចផ្ទុកតារាងចុះឈ្មោះបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    noInvitation: { en: 'Select an invitation first to manage its sign-up sheets.', km: 'សូមជ្រើសការអញ្ជើញជាមុនសិនដើម្បីគ្រប់គ្រងតារាងចុះឈ្មោះរបស់វា។' },
    // ux-6 structured empty / loading / error states (separate title + message + action)
    emptyTitle: { en: 'No sign-up sheets yet', km: 'មិនទាន់មានសន្លឹកចុះឈ្មោះទេ' },
    emptyMessage: { en: 'Create a sheet to let guests claim items or slots.', km: 'បង្កើតសន្លឹកដើម្បីឱ្យភ្ញៀវចុះឈ្មោះធាតុ ឬឈរ។' },
    emptyAction: { en: 'Create sheet', km: 'បង្កើតសន្លឹក' },
    errorTitle: { en: "Couldn't load sign-up sheets", km: 'មិនអាចផ្ទុកសន្លឹកចុះឈ្មោះបានទេ' },
    errorMessage: { en: 'Something went wrong while loading. Please try again.', km: 'មានបញ្ហាកើតឡើងពេលផ្ទុក។ សូមព្យាយាមម្ដងទៀត។' },
    errorNetwork: { en: 'Network error. Please check your connection.', km: 'កំហុសបណ្ដាញ។ សូមពិនិត្យការតភ្ជាប់របស់អ្នក។' },
    retry: { en: 'Try again', km: 'ព្យាយាមម្ដងទៀត' },
    skeletonAriaLabel: { en: 'Loading sign-up sheets', km: 'កំពុងផ្ទុកសន្លឹកចុះឈ្មោះ' },
    // Modal labels
    modalTitleCreate: { en: 'Create sign-up sheet', km: 'បង្កើតតារាងចុះឈ្មោះ' },
    modalTitleEdit: { en: 'Edit sign-up sheet', km: 'កែប្រែតារាងចុះឈ្មោះ' },
    titleLabel: { en: 'Title', km: 'ចំណងជើង' },
    titlePlaceholder: { en: 'e.g. Potluck dishes, Bring-a-drink, Setup helpers', km: 'ឧ. ម្ហូបឆ្អិនរួមគ្នា, នាំយកភេសជ្ជៈ, ជួយរៀបចំ' },
    descriptionLabel: { en: 'Description (optional)', km: 'ការពិពណ៌នា (ស្រេចចិត្ត)' },
    descriptionPlaceholder: { en: 'Shown to guests above the slot list', km: 'បង្ហាញដល់ភ្ញៀវពីលើបញ្ជីទីតាំង' },
    typeLabel: { en: 'Sheet type', km: 'ប្រភេទតារាង' },
    typeItems: { en: 'Items (guests claim one of N items)', km: 'ធាតុ (ភ្ញៀវចុះឈ្មោះធាតុមួយក្នុងចំណោម N ធាតុ)' },
    typeSlots: { en: 'Slots (guests claim a time/role slot)', km: 'ទីតាំង (ភ្ញៀវចុះឈ្មោះទីតាំងពេលវេលា/តួនាទី)' },
    slotsLabel: { en: 'Slots / items', km: 'ទីតាំង / ធាតុ' },
    slotLabel: { en: 'Label', km: 'ស្លាក' },
    slotLabelPlaceholder: { en: 'e.g. Appetizer, Drinks, Setup crew', km: 'ឧ. ប្រអប់អាហារ, ភេសជ្ជៈ, ក្រុមរៀបចំ' },
    slotCapacity: { en: 'Capacity', km: 'សមត្ថភាព' },
    slotCapacityHint: { en: '0 = unlimited', km: '0 = គ្មានដែនកំណត់' },
    slotDeadline: { en: 'Slot deadline (optional)', km: 'កាលបរិច្ឆេទកំណត់ទីតាំង (ស្រេចចិត្ត)' },
    addSlot: { en: '+ Add slot', km: '+ បន្ថែមទីតាំង' },
    removeSlot: { en: 'Remove', km: 'យកចេញ' },
    deadlineLabel: { en: 'Sheet-wide deadline (optional)', km: 'កាលបរិច្ឆេទកំណត់សរុប (ស្រេចចិត្ត)' },
    sheetDeadlineHint: { en: 'Closes all slots after this time', km: 'បិទទីតាំងទាំងអស់បន្ទាប់ពីពេលនេះ' },
    // Validation + result messages
    errTitleRequired: { en: 'Please enter a title.', km: 'សូមបញ្ចូលចំណងជើង។' },
    errSlotLabelRequired: { en: 'Every slot needs a label.', km: 'ទីតាំងនីមួយៗត្រូវការស្លាក។' },
    errSave: { en: 'Could not save the sheet. Please try again.', km: 'មិនអាចរក្សាទុកតារាងបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    errDelete: { en: 'Could not delete the sheet. Please try again.', km: 'មិនអាចលុបតារាងបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    errClaims: { en: 'Could not load claims for this sheet.', km: 'មិនអាចផ្ទុកការចុះឈ្មោះសម្រាប់តារាងនេះបានទេ។' },
    confirmDelete: { en: 'Delete this sign-up sheet? Existing claims will be hidden from guests.', km: 'លុបតារាងចុះឈ្មោះនេះ? ការចុះឈ្មោះដែលមានស្រាប់នឹងត្រូវលាក់ពីភ្ញៀវ។' },
    saved: { en: 'Saved.', km: 'បានរក្សាទុក។' },
    deleted: { en: 'Sheet deleted.', km: 'តារាងបានលុប។' },
    // List-view meta
    typeBadgeItems: { en: 'Items', km: 'ធាតុ' },
    typeBadgeSlots: { en: 'Slots', km: 'ទីតាំង' },
    slotsCount: { en: 'slots', km: 'ទីតាំង' },
    claimsCount: { en: 'claims', km: 'ការចុះឈ្មោះ' },
    deadlineLabel2: { en: 'Deadline', km: 'កាលបរិច្ឆេទកំណត់' },
    noDeadline: { en: 'No deadline', km: 'មិនមានកាលបរិច្ឆេទកំណត់' },
    noClaims: { en: 'No claims yet.', km: 'មិនទាន់មានការចុះឈ្មោះនៅឡើយ។' },
    claimName: { en: 'Name', km: 'ឈ្មោះ' },
    claimEmail: { en: 'Email', km: 'អ៊ីមែល' },
    claimQty: { en: 'Qty', km: 'ចំនួន' },
    claimWhen: { en: 'Claimed at', km: 'បានចុះឈ្មោះនៅ' },
  };

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const detectLang = () => {
    if (window.EInviteLang) return window.EInviteLang;
    const htmlLang = String(document.documentElement.lang || '').toLowerCase();
    if (htmlLang === 'km' || htmlLang.startsWith('km-')) return 'km';
    return 'both';
  };
  const langText = (key, mode) => {
    const en = STRINGS[key] ? STRINGS[key].en : key;
    const km = STRINGS[key] ? STRINGS[key].km : key;
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    if (mode === 'both') return `<span class="i18n i18n-en">${esc(en)}</span> <span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    return `<span class="i18n i18n-en">${esc(en)}</span>`;
  };
  const formatTs = (ts) => {
    if (!ts) return '';
    try {
      const d = new Date(Number(ts));
      if (isNaN(d.getTime())) return '';
      return d.toLocaleString();
    } catch { return ''; }
  };
  const toDatetimeLocalValue = (ts) => {
    if (!ts) return '';
    try {
      const d = new Date(Number(ts));
      if (isNaN(d.getTime())) return '';
      const pad = (n) => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    } catch { return ''; }
  };
  const fromDatetimeLocalValue = (val) => {
    if (!val) return null;
    const t = Date.parse(val);
    return isNaN(t) ? null : t;
  };

  function mount(root, opts) {
    if (!root) return;
    const invitationId = opts && opts.invitationId ? String(opts.invitationId) : '';
    const lang = (opts && opts.lang) || detectLang();

    const section = document.createElement('section');
    section.className = 'guest-feature host-signup-sheets event-section';
    section.setAttribute('data-event-section', 'signup-sheets');
    section.setAttribute('aria-label', STRINGS.panelTitle.en);
    section.innerHTML = `
      <h2>${langText('panelTitle', lang)}</h2>
      <p class="muted">${langText('panelIntro', lang)}</p>
      <div class="host-signup-sheets-toolbar">
        <button type="button" class="primary host-signup-create" hidden>${langText('create', lang)}</button>
      </div>
      <div class="host-signup-sheets-state" role="status" aria-live="polite">${langText('loading', lang)}</div>
    `;
    root.appendChild(section);

    const stateEl = section.querySelector('.host-signup-sheets-state');
    const createBtn = section.querySelector('.host-signup-create');

    if (!invitationId) {
      stateEl.innerHTML = `<p class="muted">${langText('noInvitation', lang)}</p>`;
      return;
    }
    createBtn.hidden = false;
    createBtn.addEventListener('click', () => openSheetModal(null));

    refresh();

    function renderLoading() {
      // 3 skeleton rows shaped like the real host-signup-sheet-row so the
      // user sees the actual layout (title bar + badge + slot count +
      // actions) instead of generic grey boxes.
      stateEl.setAttribute('aria-busy', 'true');
      const row = () => `
        <div class="skeleton skeleton--row" aria-hidden="true">
          <div class="skeleton skeleton--row-head">
            <span class="skeleton skeleton--title"></span>
            <span class="skeleton skeleton--pill"></span>
            <span class="skeleton skeleton--text-short"></span>
          </div>
          <div class="skeleton skeleton--row-actions">
            <span class="skeleton skeleton--button"></span>
            <span class="skeleton skeleton--button"></span>
            <span class="skeleton skeleton--button"></span>
          </div>
        </div>`;
      stateEl.innerHTML = `<div class="host-signup-skeletons" role="status" aria-label="${esc(STRINGS.skeletonAriaLabel[lang === 'km' ? 'km' : 'en'])}">${row()}${row()}${row()}</div>`;
    }

    function renderEmpty() {
      stateEl.removeAttribute('aria-busy');
      stateEl.innerHTML = `
        <div class="empty-state" role="status">
          <div class="empty-state__icon" aria-hidden="true">📋</div>
          <div class="empty-state__title">${langText('emptyTitle', lang)}</div>
          <div class="empty-state__message">${langText('emptyMessage', lang)}</div>
          <div class="empty-state__action">
            <button type="button" class="primary" data-empty-create>${langText('emptyAction', lang)}</button>
          </div>
        </div>`;
      const btn = stateEl.querySelector('[data-empty-create]');
      if (btn) btn.addEventListener('click', () => openSheetModal(null));
    }

    function renderError(err) {
      stateEl.removeAttribute('aria-busy');
      const isNetwork = err && (err instanceof TypeError || /fetch|network/i.test(err.message || ''));
      const messageKey = isNetwork ? 'errorNetwork' : 'errorMessage';
      stateEl.innerHTML = `
        <div class="error-state" role="alert">
          <div class="error-state__icon" aria-hidden="true">⚠️</div>
          <div class="error-state__title">${langText('errorTitle', lang)}</div>
          <div class="error-state__message">${langText(messageKey, lang)}${err && err.message && !isNetwork ? ` <code>${esc(err.message)}</code>` : ''}</div>
          <div class="error-state__retry">
            <button type="button" data-retry>${langText('retry', lang)}</button>
          </div>
        </div>`;
      const btn = stateEl.querySelector('[data-retry]');
      if (btn) btn.addEventListener('click', () => refresh());
    }

    async function refresh() {
      renderLoading();
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const sheets = await res.json();
        render(sheets || []);
      } catch (err) {
        renderError(err);
      }
    }

    function render(sheets) {
      if (!sheets.length) {
        renderEmpty();
        return;
      }
      stateEl.removeAttribute('aria-busy');
      stateEl.innerHTML = `<ul class="host-signup-sheet-list">${sheets.map(renderRow).join('')}</ul>`;
      stateEl.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => onEdit(b.dataset.edit)));
      stateEl.querySelectorAll('[data-delete]').forEach((b) => b.addEventListener('click', () => onDelete(b.dataset.delete)));
      stateEl.querySelectorAll('[data-claims]').forEach((b) => b.addEventListener('click', () => onToggleClaims(b)));
    }

    function renderRow(sheet) {
      const slots = Array.isArray(sheet.slots) ? sheet.slots : [];
      const slotCount = slots.length;
      const claimCount = slots.reduce((acc, s) => acc + (s && Array.isArray(s.claims) ? s.claims.length : 0), 0);
      const typeBadge = sheet.type === 'slots' ? langText('typeBadgeSlots', lang) : langText('typeBadgeItems', lang);
      const deadline = sheet.deadlineTs ? `<span class="muted">${langText('deadlineLabel2', lang)}: ${esc(formatTs(sheet.deadlineTs))}</span>` : `<span class="muted">${langText('noDeadline', lang)}</span>`;
      return `
        <li class="host-signup-sheet-row" data-sheet-id="${esc(sheet.id)}">
          <div class="host-signup-sheet-row-head">
            <strong class="host-signup-sheet-title">${esc(sheet.title)}</strong>
            <span class="badge">${typeBadge}</span>
            <span class="muted">${slotCount} ${langText('slotsCount', lang)} · ${claimCount} ${langText('claimsCount', lang)}</span>
            ${deadline}
          </div>
          <div class="host-signup-sheet-row-actions">
            <button type="button" data-edit="${esc(sheet.id)}">${langText('edit', lang)}</button>
            <button type="button" data-delete="${esc(sheet.id)}" class="danger">${langText('delete', lang)}</button>
            <button type="button" data-claims="${esc(sheet.id)}" aria-expanded="false">${langText('viewClaims', lang)}</button>
          </div>
          <div class="host-signup-claims-region" data-claims-region="${esc(sheet.id)}" hidden></div>
        </li>`;
    }

    // --- Modal -------------------------------------------------------------

    function openSheetModal(existing) {
      const isEdit = !!existing;
      const overlay = document.createElement('div');
      overlay.className = 'delivery-dialog-overlay host-signup-modal-overlay';
      const initialSlots = isEdit && Array.isArray(existing.slots) && existing.slots.length
        ? existing.slots.map((s) => ({ id: s.id || '', label: s.label || '', capacity: String(s.capacity || 0), description: s.description || '' }))
        : [{ id: '', label: '', capacity: '0', description: '' }];
      overlay.innerHTML = `
        <div class="delivery-dialog host-signup-modal" role="dialog" aria-modal="true" aria-label="${esc(STRINGS.modalTitleCreate.en)}">
          <header><h2>${isEdit ? langText('modalTitleEdit', lang) : langText('modalTitleCreate', lang)}</h2><button type="button" data-close>&times;</button></header>
          <form>
            <label>${langText('titleLabel', lang)}<input type="text" name="title" required maxlength="200" placeholder="${esc(STRINGS.titlePlaceholder.en)}" value="${esc(existing ? existing.title || '' : '')}"></label>
            <label>${langText('descriptionLabel', lang)}<textarea name="description" rows="2" maxlength="1000" placeholder="${esc(STRINGS.descriptionPlaceholder.en)}">${esc(existing && existing.description ? existing.description : '')}</textarea></label>
            <fieldset>
              <legend>${langText('typeLabel', lang)}</legend>
              <label class="host-signup-type-radio"><input type="radio" name="type" value="items" ${(!existing || existing.type !== 'slots') ? 'checked' : ''}> ${langText('typeItems', lang)}</label>
              <label class="host-signup-type-radio"><input type="radio" name="type" value="slots" ${(existing && existing.type === 'slots') ? 'checked' : ''}> ${langText('typeSlots', lang)}</label>
            </fieldset>
            <fieldset>
              <legend>${langText('slotsLabel', lang)}</legend>
              <ol class="host-signup-slot-rows"></ol>
              <button type="button" class="host-signup-add-slot">${langText('addSlot', lang)}</button>
            </fieldset>
            <label>${langText('deadlineLabel', lang)}<input type="datetime-local" name="deadlineTs" value="${esc(toDatetimeLocalValue(existing ? existing.deadlineTs : null))}"></label>
            <p class="hint">${langText('sheetDeadlineHint', lang)}</p>
            <p class="host-signup-modal-status" role="status" aria-live="polite"></p>
            <footer>
              <button type="button" data-close>${langText('cancel', lang)}</button>
              <button type="submit" class="primary">${langText('save', lang)}</button>
            </footer>
          </form>
        </div>`;
      document.body.appendChild(overlay);

      const slotRows = overlay.querySelector('.host-signup-slot-rows');
      const addSlotBtn = overlay.querySelector('.host-signup-add-slot');
      const statusEl = overlay.querySelector('.host-signup-modal-status');
      const form = overlay.querySelector('form');

      function renderSlotRow(slot) {
        const li = document.createElement('li');
        li.className = 'host-signup-slot-row';
        li.innerHTML = `
          <label>${langText('slotLabel', lang)}<input type="text" name="slotLabel" required maxlength="200" placeholder="${esc(STRINGS.slotLabelPlaceholder.en)}" value="${esc(slot.label)}"></label>
          <label>${langText('slotCapacity', lang)}<input type="number" name="slotCapacity" min="0" max="100000" value="${esc(slot.capacity || '0')}"><small class="hint">${langText('slotCapacityHint', lang)}</small></label>
          <button type="button" class="host-signup-remove-slot danger" title="${esc(STRINGS.removeSlot.en)}">×</button>
        `;
        li.querySelector('.host-signup-remove-slot').addEventListener('click', () => {
          if (slotRows.children.length > 1) li.remove();
          else { li.querySelector('input[name=slotLabel]').value = ''; li.querySelector('input[name=slotCapacity]').value = '0'; }
        });
        return li;
      }
      initialSlots.forEach((s) => slotRows.appendChild(renderSlotRow(s)));
      addSlotBtn.addEventListener('click', () => slotRows.appendChild(renderSlotRow({ id: '', label: '', capacity: '0' })));

      function closeOverlay() { overlay.remove(); }
      overlay.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', closeOverlay));
      overlay.querySelector('.host-signup-modal').addEventListener('click', (ev) => ev.stopPropagation());
      overlay.addEventListener('click', closeOverlay);

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const fd = new FormData(form);
        const title = String(fd.get('title') || '').trim();
        if (!title) { statusEl.innerHTML = `<span class="error">${langText('errTitleRequired', lang)}</span>`; return; }
        const description = String(fd.get('description') || '').trim();
        const sheetType = String(fd.get('type') || 'items');
        const slots = Array.from(slotRows.children).map((li) => ({
          label: String(li.querySelector('input[name=slotLabel]').value || '').trim(),
          capacity: parseInt(li.querySelector('input[name=slotCapacity]').value || '0', 10) || 0,
          description: '',
        }));
        if (slots.some((s) => !s.label)) { statusEl.innerHTML = `<span class="error">${langText('errSlotLabelRequired', lang)}</span>`; return; }
        const deadlineTs = fromDatetimeLocalValue(String(fd.get('deadlineTs') || ''));
        const payload = { title, type: sheetType, slots, deadlineTs };
        const submit = form.querySelector('button[type=submit]');
        submit.disabled = true;
        try {
          const url = isEdit
            ? `/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets/${encodeURIComponent(existing.id)}`
            : `/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`;
          const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
          });
          const result = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
          closeOverlay();
          await refresh();
          // V2-UX-7 (§3.7): success toast for create/edit mutation.
          if (window.EInviteToast) {
            EInviteToast.show({
              type: 'success',
              message_en: STRINGS.saved.en,
              message_km: STRINGS.saved.km,
              duration: 4000
            });
          }
        } catch (err) {
          statusEl.innerHTML = `<span class="error">${langText('errSave', lang)} <code>${esc(err.message || '')}</code></span>`;
          submit.disabled = false;
          // V2-UX-7 (§3.7): also surface the failure as a toast so the host
          // gets feedback even after closing the modal (the inline status is
          // only visible while the modal is open).
          if (window.EInviteToast) {
            EInviteToast.show({
              type: 'error',
              message_en: STRINGS.errSave.en + (err && err.message ? ' (' + err.message + ')' : ''),
              message_km: STRINGS.errSave.km + (err && err.message ? ' (' + err.message + ')' : ''),
              duration: 6000
            });
          }
        }
      });
    }

    // --- Edit / Delete / Claims ------------------------------------------

    async function onEdit(sheetId) {
      // Re-fetch the list to get the latest sheet (claims included in host mode).
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        const sheets = await res.json();
        const sheet = (sheets || []).find((s) => s.id === sheetId);
        if (!sheet) return refresh();
        openSheetModal(sheet);
      } catch {
        openSheetModal({ id: sheetId });
      }
    }

    async function onDelete(sheetId) {
      if (!confirm(STRINGS.confirmDelete.en + '\n' + STRINGS.confirmDelete.km)) return;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets/${encodeURIComponent(sheetId)}`, {
          method: 'DELETE', headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
        await refresh();
        // V2-UX-7 (§3.7): success toast for delete mutation.
        if (window.EInviteToast) {
          EInviteToast.show({
            type: 'success',
            message_en: STRINGS.deleted.en,
            message_km: STRINGS.deleted.km,
            duration: 4000
          });
        }
      } catch (err) {
        // V2-UX-7 (§3.7): replace the previous alert() with a bilingual
        // error toast; auto-dismiss after 6s (longer than success).
        if (window.EInviteToast) {
          EInviteToast.show({
            type: 'error',
            message_en: err.message || STRINGS.errDelete.en,
            message_km: err.message || STRINGS.errDelete.km,
            duration: 6000
          });
        }
      }
    }

    async function onToggleClaims(btn) {
      const sheetId = btn.getAttribute('data-claims');
      const region = stateEl.querySelector(`[data-claims-region="${cssEsc(sheetId)}"]`);
      if (!region) return;
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        region.hidden = true;
        region.innerHTML = '';
        btn.setAttribute('aria-expanded', 'false');
        btn.textContent = STRINGS.viewClaims.en;
        return;
      }
      btn.setAttribute('aria-expanded', 'true');
      btn.textContent = STRINGS.hideClaims.en;
      region.hidden = false;
      region.innerHTML = `<p class="muted">${langText('loading', lang)}</p>`;
      // Claims are already returned as part of the host-mode list response
      // (see _signup_sheet_view include_claims=True). Re-fetch to be safe.
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/signup-sheets`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        const sheets = await res.json();
        const sheet = (sheets || []).find((s) => s.id === sheetId);
        renderClaims(region, sheet || { slots: [] });
      } catch (err) {
        region.innerHTML = `<p class="error">${langText('errClaims', lang)}</p>`;
      }
    }

    function renderClaims(region, sheet) {
      const slots = Array.isArray(sheet.slots) ? sheet.slots : [];
      if (!slots.length || !slots.some((s) => (s.claims || []).length)) {
        region.innerHTML = `<p class="muted">${langText('noClaims', lang)}</p>`;
        return;
      }
      const blocks = slots.map((slot) => {
        const claims = Array.isArray(slot.claims) ? slot.claims : [];
        if (!claims.length) return '';
        const rows = claims.map((c) => `
          <tr>
            <td>${esc(c.name || '')}</td>
            <td>${esc(c.email || '')}</td>
            <td>${esc(c.quantity || 1)}</td>
            <td>${esc(formatTs(c.createdAt))}</td>
          </tr>`).join('');
        return `
          <div class="host-signup-claims-slot">
            <strong>${esc(slot.label || '')}</strong>
            <table class="host-signup-claims-table">
              <thead><tr>
                <th>${langText('claimName', lang)}</th>
                <th>${langText('claimEmail', lang)}</th>
                <th>${langText('claimQty', lang)}</th>
                <th>${langText('claimWhen', lang)}</th>
              </tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>`;
      }).join('');
      region.innerHTML = blocks || `<p class="muted">${langText('noClaims', lang)}</p>`;
    }

    function cssEsc(id) {
      // Escape for querySelector — only [a-zA-Z0-9_-] are safe unquoted.
      return String(id || '').replace(/[^a-zA-Z0-9_-]/g, (c) => `\\${c}`);
    }
  }

  window.EInviteHostSignupSheets = { mount };
})();
