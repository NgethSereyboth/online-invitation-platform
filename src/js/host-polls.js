/**
 * V2-UX-2 (ROADMAP-V2 §3.2) — Host-side management UI for polls.
 *
 * Mounts on the dashboard as a per-invitation panel placed immediately
 * after the §3.1 sign-up-sheets panel (see dashboard.html). The host can
 * list, create, edit, delete, and "close now" polls, and expand a per-poll
 * "View results" region that draws a CSS bar chart plus the host-only voter
 * email list. Bilingual EN + Khmer per ROADMAP-V2 §3 ground rule
 * "every user-facing string must have an EN and KH variant".
 *
 * Reuses the design tokens (`tokens.css`, `modern-ui.css`) and the existing
 * Phase 2a-1 API contract that already powers the guest-side `polls.js`.
 * No new design system; no framework. Mirrors `host-signup-sheets.js` (§3.1)
 * for IIFE shape, STRINGS pattern, modal pattern, and empty/loading/error
 * states so the two panels feel like siblings.
 *
 * API contract (Phase 2a-1, frozen):
 *   GET    /api/invitations/{id}/polls
 *          → 200 [{id, invitationId, question, options[{id,label,description,votes}],
 *                  visibility, multiSelect, deadlineTs, createdAt, archivedAt,
 *                  closed, totalVotes, votes[{id,optionId,guestId,name,email,createdAt}]}]
 *          (host mode includes options[].votes counts + votes[] voter PII)
 *   POST   /api/invitations/{id}/polls          {question, options[{label,description?,id?}],
 *                                                visibility, multiSelect, deadlineTs?}
 *          → 201 {poll}
 *   PUT    /api/invitations/{id}/polls/{pid}   {question?, options?, visibility?,
 *                                                multiSelect?, deadlineTs?}
 *          → 200 {poll}
 *   DELETE /api/invitations/{id}/polls/{pid}   → 200 {deleted:true}
 *   GET    /api/invitations/{id}/polls/{pid}/results → 200 {poll with show_results=true}
 *
 * "Close now" sets `deadlineTs = now - 1000` (just in the past) via PUT so
 * the server's `closed = deadline_ts < now` check flips true on the next
 * list refresh — the existing endpoint has no dedicated "close" verb.
 *
 * Surface contract:
 *   window.EInviteHostPolls.mount(root, { invitationId, lang })
 *     - root: HTMLElement where the panel renders
 *     - invitationId: required; the active invitation
 *     - lang: optional 'en' | 'km' | 'both' (default 'both' for the host)
 */
(function () {
  'use strict';

  /** Bilingual strings — every label, button, and message. */
  const STRINGS = {
    panelTitle: { en: 'Polls', km: 'ការស្ទង់មតិ' },
    panelIntro: {
      en: 'Create polls so guests can vote. Guests see the same polls on the live invitation page.',
      km: 'បង្កើតការស្ទង់មតិ ដូច្នេះភ្ញៀវអាចបោះឆ្នោត។ ភ្ញៀវឃើញការស្ទង់មតិដដែលនៅលើទំព័រការអញ្ជើញផ្ទាល់។',
    },
    create: { en: 'Create poll', km: 'បង្កើតការស្ទង់មតិ' },
    edit: { en: 'Edit', km: 'កែប្រែ' },
    delete: { en: 'Delete', km: 'លុប' },
    cancel: { en: 'Cancel', km: 'បោះបង់' },
    save: { en: 'Save', km: 'រក្សាទុក' },
    closeNow: { en: 'Close now', km: 'បិទឥឡូវនេះ' },
    viewResults: { en: 'View results', km: 'មើលលទ្ធផល' },
    hideResults: { en: 'Hide results', km: 'លាក់លទ្ធផល' },
    loading: { en: 'Loading polls…', km: 'កំពុងផ្ទុកការស្ទង់មតិ…' },
    empty: { en: 'No polls yet. Create one to let guests vote.', km: 'មិនទាន់មានការស្ទង់មតិនៅឡើយ។ បង្កើតមួយដើម្បីឱ្យភ្ញៀវអាចបោះឆ្នោត។' },
    error: { en: 'Could not load polls. Please try again.', km: 'មិនអាចផ្ទុកការស្ទង់មតិបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    noInvitation: { en: 'Select an invitation first to manage its polls.', km: 'សូមជ្រើសការអញ្ជើញជាមុនសិនដើម្បីគ្រប់គ្រងការស្ទង់មតិរបស់វា។' },
    // ux-6 structured empty / loading / error states (separate title + message + action)
    emptyTitle: { en: 'No polls yet', km: 'មិនទាន់មានការស្ទង់មតិទេ' },
    emptyMessage: { en: 'Create a poll to gather guest preferences.', km: 'បង្កើតការស្ទង់មតិដើម្បីប្រមូលចំណូលចិត្តភ្ញៀវ។' },
    emptyAction: { en: 'Create poll', km: 'បង្កើតការស្ទង់មតិ' },
    errorTitle: { en: "Couldn't load polls", km: 'មិនអាចផ្ទុកការស្ទង់មតិបានទេ' },
    errorMessage: { en: 'Something went wrong while loading. Please try again.', km: 'មានបញ្ហាកើតឡើងពេលផ្ទុក។ សូមព្យាយាមម្ដងទៀត។' },
    errorNetwork: { en: 'Network error. Please check your connection.', km: 'កំហុសបណ្ដាញ។ សូមពិនិត្យការតភ្ជាប់របស់អ្នក។' },
    retry: { en: 'Try again', km: 'ព្យាយាមម្ដងទៀត' },
    skeletonAriaLabel: { en: 'Loading polls', km: 'កំពុងផ្ទុកការស្ទង់មតិ' },
    // Modal labels
    modalTitleCreate: { en: 'Create poll', km: 'បង្កើតការស្ទង់មតិ' },
    modalTitleEdit: { en: 'Edit poll', km: 'កែប្រែការស្ទង់មតិ' },
    questionLabel: { en: 'Question', km: 'សំណួរ' },
    questionPlaceholder: { en: 'e.g. Which date works best? Buffet or plated dinner?', km: 'ឧ. តើថ្ងៃណាសាកសម? បូហ្វេ ឬអាហារចាក់កែង?' },
    optionsLabel: { en: 'Options (2–20)', km: 'ជម្រើស (២–២០)' },
    optionLabel: { en: 'Option', km: 'ជម្រើស' },
    optionPlaceholder: { en: 'e.g. Saturday, Sunday, Either is fine', km: 'ឧ. ថ្ងៃសៅរ៍, ថ្ងៃអាទិត្យ, ថ្ងៃណាក៏បាន' },
    addOption: { en: '+ Add option', km: '+ បន្ថែមជម្រើស' },
    removeOption: { en: 'Remove', km: 'យកចេញ' },
    settingsLabel: { en: 'Settings', km: 'ការកំណត់' },
    multiSelectLabel: { en: 'Allow multiple selections', km: 'អនុញ្ញាតឱ្យជ្រើសច្រើន' },
    multiSelectHint: { en: 'Guests can pick more than one option', km: 'ភ្ញៀវអាចជ្រើសច្រើនជាងមួយជម្រើស' },
    visibilityLabel: { en: 'Results visibility', km: 'ការមើលឃើញលទ្ធផល' },
    visibilityLive: { en: 'Live — show counts as votes come in', km: 'ផ្ទាល់ — បង្ហាញចំនួនពេលភ្ញៀវបោះឆ្នោត' },
    visibilityHidden: { en: 'Hidden — reveal only after the poll closes', km: 'លាក់ — បង្ហាញតែពេលការស្ទង់មតិបិទ' },
    deadlineLabel: { en: 'Deadline (optional)', km: 'កាលបរិច្ឆេទកំណត់ (ស្រេចចិត្ត)' },
    deadlineHint: { en: 'Closes the poll after this time', km: 'បិទការស្ទង់មតិបន្ទាប់ពីពេលនេះ' },
    // Validation + result messages
    errQuestionRequired: { en: 'Please enter a question.', km: 'សូមបញ្ចូលសំណួរ។' },
    errOptionsRange: { en: 'A poll needs 2 to 20 options.', km: 'ការស្ទង់មតិត្រូវការជម្រើស ២ ដល់ ២០។' },
    errOptionLabelRequired: { en: 'Every option needs a label.', km: 'ជម្រើសនីមួយៗត្រូវការស្លាក។' },
    errSave: { en: 'Could not save the poll. Please try again.', km: 'មិនអាចរក្សាទុកការស្ទង់មតិបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    errDelete: { en: 'Could not delete the poll. Please try again.', km: 'មិនអាចលុបការស្ទង់មតិបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    errClose: { en: 'Could not close the poll. Please try again.', km: 'មិនអាចបិទការស្ទង់មតិបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    errResults: { en: 'Could not load results for this poll.', km: 'មិនអាចផ្ទុកលទ្ធផលសម្រាប់ការស្ទង់មតិនេះបានទេ។' },
    confirmDelete: { en: 'Delete this poll? Existing votes will be hidden from guests.', km: 'លុបការស្ទង់មតិនេះ? ការបោះឆ្នោតដែលមានស្រាប់នឹងត្រូវលាក់ពីភ្ញៀវ។' },
    confirmClose: { en: 'Close this poll now? Guests will no longer be able to vote.', km: 'បិទការស្ទង់មតិនេះឥឡូវនេះ? ភ្ញៀវនឹងមិនអាចបោះឆ្នោតបានទៀតទេ។' },
    // V2-UX-7 (§3.7): success toasts.
    saved: { en: 'Poll saved.', km: 'បានរក្សាទុកការស្ទង់មតិ។' },
    deleted: { en: 'Poll deleted.', km: 'ការស្ទង់មតិបានលុប។' },
    closed: { en: 'Poll closed.', km: 'ការស្ទង់មតិបានបិទ។' },
    // List-view meta
    statusOpen: { en: 'Open', km: 'បើក' },
    statusClosed: { en: 'Closed', km: 'បិតហើយ' },
    visibilityBadgeLive: { en: 'Live', km: 'ផ្ទាល់' },
    visibilityBadgeHidden: { en: 'Hidden', km: 'លាក់' },
    multiBadge: { en: 'Multi', km: 'ច្រើន' },
    singleBadge: { en: 'Single', km: 'មួយ' },
    votesCount: { en: 'votes', km: 'សន្លឹកឆ្នោត' },
    optionsCount: { en: 'options', km: 'ជម្រើស' },
    deadlineLabel2: { en: 'Deadline', km: 'កាលបរិច្ឆេទកំណត់' },
    noDeadline: { en: 'No deadline', km: 'មិនមានកាលបរិច្ឆេទកំណត់' },
    closedHint: { en: 'Closed — voting disabled', km: 'បិទ — បិទការបោះឆ្នោត' },
    noVotes: { en: 'No votes yet.', km: 'មិនទាន់មានការបោះឆ្នោតនៅឡើយ។' },
    voterName: { en: 'Voter', km: 'អ្នកបោះឆ្នោត' },
    voterEmail: { en: 'Email', km: 'អ៊ីមែល' },
    voterChoice: { en: 'Voted for', km: 'បានបោះឆ្នោតឱ្យ' },
    voterWhen: { en: 'Voted at', km: 'បោះឆ្នោតនៅ' },
    voterAnonymous: { en: 'Anonymous', km: 'អនាមិក' },
    totalVotesLabel: { en: 'Total votes', km: 'សន្លឹកឆ្នោតសរុប' },
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
  const cssEsc = (id) => String(id || '').replace(/[^a-zA-Z0-9_-]/g, (c) => `\\${c}`);

  function mount(root, opts) {
    if (!root) return;
    const invitationId = opts && opts.invitationId ? String(opts.invitationId) : '';
    const lang = (opts && opts.lang) || detectLang();

    const section = document.createElement('section');
    section.className = 'guest-feature host-polls event-section';
    section.setAttribute('data-event-section', 'polls');
    section.setAttribute('aria-label', STRINGS.panelTitle.en);
    section.innerHTML = `
      <h2>${langText('panelTitle', lang)}</h2>
      <p class="muted">${langText('panelIntro', lang)}</p>
      <div class="host-polls-toolbar">
        <button type="button" class="primary host-polls-create" hidden>${langText('create', lang)}</button>
      </div>
      <div class="host-polls-state" role="status" aria-live="polite">${langText('loading', lang)}</div>
    `;
    root.appendChild(section);

    const stateEl = section.querySelector('.host-polls-state');
    const createBtn = section.querySelector('.host-polls-create');

    if (!invitationId) {
      stateEl.innerHTML = `<p class="muted">${langText('noInvitation', lang)}</p>`;
      return;
    }
    createBtn.hidden = false;
    createBtn.addEventListener('click', () => openPollModal(null));

    refresh();

    function renderLoading() {
      // 3 skeleton rows shaped like the real host-poll-row so the user
      // sees the actual layout (question + status badges + meta +
      // actions) instead of generic grey boxes.
      stateEl.setAttribute('aria-busy', 'true');
      const row = () => `
        <div class="skeleton skeleton--row" aria-hidden="true">
          <div class="skeleton skeleton--row-head">
            <span class="skeleton skeleton--title"></span>
            <span class="skeleton skeleton--pill"></span>
            <span class="skeleton skeleton--pill"></span>
            <span class="skeleton skeleton--text-short"></span>
          </div>
          <div class="skeleton skeleton--row-actions">
            <span class="skeleton skeleton--button"></span>
            <span class="skeleton skeleton--button"></span>
            <span class="skeleton skeleton--button"></span>
            <span class="skeleton skeleton--button"></span>
          </div>
        </div>`;
      stateEl.innerHTML = `<div class="host-polls-skeletons" role="status" aria-label="${esc(STRINGS.skeletonAriaLabel[lang === 'km' ? 'km' : 'en'])}">${row()}${row()}${row()}</div>`;
    }

    function renderEmpty() {
      stateEl.removeAttribute('aria-busy');
      stateEl.innerHTML = `
        <div class="empty-state" role="status">
          <div class="empty-state__icon" aria-hidden="true">📊</div>
          <div class="empty-state__title">${langText('emptyTitle', lang)}</div>
          <div class="empty-state__message">${langText('emptyMessage', lang)}</div>
          <div class="empty-state__action">
            <button type="button" class="primary" data-empty-create>${langText('emptyAction', lang)}</button>
          </div>
        </div>`;
      const btn = stateEl.querySelector('[data-empty-create]');
      if (btn) btn.addEventListener('click', () => openPollModal(null));
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
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const polls = await res.json();
        render(polls || []);
      } catch (err) {
        renderError(err);
      }
    }

    function render(polls) {
      if (!polls.length) {
        renderEmpty();
        return;
      }
      stateEl.removeAttribute('aria-busy');
      stateEl.innerHTML = `<ul class="host-poll-list">${polls.map(renderRow).join('')}</ul>`;
      stateEl.querySelectorAll('[data-edit]').forEach((b) => b.addEventListener('click', () => onEdit(b.dataset.edit)));
      stateEl.querySelectorAll('[data-delete]').forEach((b) => b.addEventListener('click', () => onDelete(b.dataset.delete)));
      stateEl.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', () => onCloseNow(b.dataset.close)));
      stateEl.querySelectorAll('[data-results]').forEach((b) => b.addEventListener('click', () => onToggleResults(b)));
    }

    function renderRow(poll) {
      const options = Array.isArray(poll.options) ? poll.options : [];
      const optionCount = options.length;
      const totalVotes = typeof poll.totalVotes === 'number' ? poll.totalVotes
        : options.reduce((acc, o) => acc + (typeof o.votes === 'number' ? o.votes : 0), 0);
      const closed = !!poll.closed;
      const statusBadge = closed
        ? `<span class="badge badge-closed">${langText('statusClosed', lang)}</span>`
        : `<span class="badge badge-open">${langText('statusOpen', lang)}</span>`;
      const visibilityBadge = poll.visibility === 'live'
        ? `<span class="badge badge-live">${langText('visibilityBadgeLive', lang)}</span>`
        : `<span class="badge badge-hidden">${langText('visibilityBadgeHidden', lang)}</span>`;
      const selectBadge = poll.multiSelect
        ? `<span class="badge badge-multi">${langText('multiBadge', lang)}</span>`
        : `<span class="badge badge-single">${langText('singleBadge', lang)}</span>`;
      const deadline = poll.deadlineTs
        ? `<span class="muted">${langText('deadlineLabel2', lang)}: ${esc(formatTs(poll.deadlineTs))}</span>`
        : `<span class="muted">${langText('noDeadline', lang)}</span>`;
      const closeBtn = closed
        ? '' // Already closed — no "Close now" button.
        : `<button type="button" data-close="${esc(poll.id)}" class="warning">${langText('closeNow', lang)}</button>`;
      return `
        <li class="host-poll-row" data-poll-id="${esc(poll.id)}">
          <div class="host-poll-row-head">
            <strong class="host-poll-question">${esc(poll.question)}</strong>
            ${statusBadge}
            ${visibilityBadge}
            ${selectBadge}
            <span class="muted">${optionCount} ${langText('optionsCount', lang)} · ${totalVotes} ${langText('votesCount', lang)}</span>
            ${deadline}
          </div>
          <div class="host-poll-row-actions">
            <button type="button" data-edit="${esc(poll.id)}">${langText('edit', lang)}</button>
            <button type="button" data-delete="${esc(poll.id)}" class="danger">${langText('delete', lang)}</button>
            ${closeBtn}
            <button type="button" data-results="${esc(poll.id)}" aria-expanded="false">${langText('viewResults', lang)}</button>
          </div>
          <div class="host-poll-results-region" data-results-region="${esc(poll.id)}" hidden></div>
        </li>`;
    }

    // --- Modal -------------------------------------------------------------

    function openPollModal(existing) {
      const isEdit = !!existing;
      const overlay = document.createElement('div');
      overlay.className = 'delivery-dialog-overlay host-polls-modal-overlay';
      const initialOptions = isEdit && Array.isArray(existing.options) && existing.options.length
        ? existing.options.map((o) => ({ id: o.id || '', label: o.label || '', description: o.description || '' }))
        : [{ id: '', label: '', description: '' }, { id: '', label: '', description: '' }];
      const visibility = existing ? (existing.visibility || 'hidden_until_close') : 'hidden_until_close';
      const multiSelect = existing ? !!existing.multiSelect : false;
      overlay.innerHTML = `
        <div class="delivery-dialog host-polls-modal" role="dialog" aria-modal="true" aria-label="${esc(STRINGS.modalTitleCreate.en)}">
          <header><h2>${isEdit ? langText('modalTitleEdit', lang) : langText('modalTitleCreate', lang)}</h2><button type="button" data-close>&times;</button></header>
          <form>
            <label>${langText('questionLabel', lang)}<input type="text" name="question" required maxlength="500" placeholder="${esc(STRINGS.questionPlaceholder.en)}" value="${esc(existing ? existing.question || '' : '')}"></label>
            <fieldset>
              <legend>${langText('optionsLabel', lang)}</legend>
              <ol class="host-polls-option-rows"></ol>
              <button type="button" class="host-polls-add-option">${langText('addOption', lang)}</button>
            </fieldset>
            <fieldset>
              <legend>${langText('settingsLabel', lang)}</legend>
              <label class="host-polls-multiselect">
                <input type="checkbox" name="multiSelect" ${multiSelect ? 'checked' : ''}>
                <span>${langText('multiSelectLabel', lang)}</span>
                <small class="hint">${langText('multiSelectHint', lang)}</small>
              </label>
              <div class="host-polls-visibility" role="radiogroup" aria-label="${esc(STRINGS.visibilityLabel.en)}">
                <label class="host-polls-visibility-radio">
                  <input type="radio" name="visibility" value="live" ${visibility === 'live' ? 'checked' : ''}>
                  ${langText('visibilityLive', lang)}
                </label>
                <label class="host-polls-visibility-radio">
                  <input type="radio" name="visibility" value="hidden_until_close" ${visibility !== 'live' ? 'checked' : ''}>
                  ${langText('visibilityHidden', lang)}
                </label>
              </div>
            </fieldset>
            <label>${langText('deadlineLabel', lang)}<input type="datetime-local" name="deadlineTs" value="${esc(toDatetimeLocalValue(existing ? existing.deadlineTs : null))}"></label>
            <p class="hint">${langText('deadlineHint', lang)}</p>
            <p class="host-polls-modal-status" role="status" aria-live="polite"></p>
            <footer>
              <button type="button" data-close>${langText('cancel', lang)}</button>
              <button type="submit" class="primary">${langText('save', lang)}</button>
            </footer>
          </form>
        </div>`;
      document.body.appendChild(overlay);

      const optionRows = overlay.querySelector('.host-polls-option-rows');
      const addOptionBtn = overlay.querySelector('.host-polls-add-option');
      const statusEl = overlay.querySelector('.host-polls-modal-status');
      const form = overlay.querySelector('form');

      function renderOptionRow(opt) {
        const li = document.createElement('li');
        li.className = 'host-polls-option-row';
        li.innerHTML = `
          <input type="text" name="optionLabel" required maxlength="200" placeholder="${esc(STRINGS.optionPlaceholder.en)}" value="${esc(opt.label)}">
          <button type="button" class="host-polls-remove-option danger" title="${esc(STRINGS.removeOption.en)}">×</button>
        `;
        li.querySelector('.host-polls-remove-option').addEventListener('click', () => {
          // Keep at least 2 option rows so the 2–20 constraint is always visible.
          if (optionRows.children.length > 2) li.remove();
          else { li.querySelector('input[name=optionLabel]').value = ''; }
        });
        return li;
      }
      initialOptions.forEach((o) => optionRows.appendChild(renderOptionRow(o)));
      addOptionBtn.addEventListener('click', () => {
        if (optionRows.children.length >= 20) {
          statusEl.innerHTML = `<span class="error">${langText('errOptionsRange', lang)}</span>`;
          return;
        }
        optionRows.appendChild(renderOptionRow({ id: '', label: '', description: '' }));
      });

      function closeOverlay() { overlay.remove(); }
      overlay.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', closeOverlay));
      overlay.querySelector('.host-polls-modal').addEventListener('click', (ev) => ev.stopPropagation());
      overlay.addEventListener('click', closeOverlay);

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const fd = new FormData(form);
        const question = String(fd.get('question') || '').trim();
        if (!question) { statusEl.innerHTML = `<span class="error">${langText('errQuestionRequired', lang)}</span>`; return; }
        const existingMap = {};
        if (isEdit && Array.isArray(existing.options)) {
          existing.options.forEach((o) => { existingMap[String(o.label || '').toLowerCase()] = o.id || ''; });
        }
        const rawLabels = Array.from(optionRows.children).map((li) => String(li.querySelector('input[name=optionLabel]').value || '').trim());
        const deduped = rawLabels.filter((l, i, arr) => l && arr.indexOf(l) === i);
        if (deduped.length < 2 || deduped.length > 20) {
          statusEl.innerHTML = `<span class="error">${langText('errOptionsRange', lang)}</span>`;
          return;
        }
        if (rawLabels.some((l) => !l)) {
          statusEl.innerHTML = `<span class="error">${langText('errOptionLabelRequired', lang)}</span>`;
          return;
        }
        const options = deduped.map((label) => ({
          id: existingMap[label.toLowerCase()] || '',
          label,
          description: '',
        }));
        const visibility = String(fd.get('visibility') || 'hidden_until_close');
        const multiSelect = !!fd.get('multiSelect');
        const deadlineTs = fromDatetimeLocalValue(String(fd.get('deadlineTs') || ''));
        const payload = { question, options, visibility, multiSelect, deadlineTs };
        const submit = form.querySelector('button[type=submit]');
        submit.disabled = true;
        try {
          const url = isEdit
            ? `/api/invitations/${encodeURIComponent(invitationId)}/polls/${encodeURIComponent(existing.id)}`
            : `/api/invitations/${encodeURIComponent(invitationId)}/polls`;
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
          // gets feedback even after closing the modal.
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

    // --- Edit / Delete / Close / Results --------------------------------

    async function onEdit(pollId) {
      // Re-fetch the list to get the latest poll (votes included in host mode).
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        const polls = await res.json();
        const poll = (polls || []).find((p) => p.id === pollId);
        if (!poll) return refresh();
        openPollModal(poll);
      } catch {
        openPollModal({ id: pollId });
      }
    }

    async function onDelete(pollId) {
      if (!confirm(STRINGS.confirmDelete.en + '\n' + STRINGS.confirmDelete.km)) return;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls/${encodeURIComponent(pollId)}`, {
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

    async function onCloseNow(pollId) {
      if (!confirm(STRINGS.confirmClose.en + '\n' + STRINGS.confirmClose.km)) return;
      try {
        // Set deadline to 1s in the past so the server's `deadline_ts < now`
        // check flips `closed=true` on the next list refresh.
        const past = Date.now() - 1000;
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls/${encodeURIComponent(pollId)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ deadlineTs: past }),
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
        await refresh();
        // V2-UX-7 (§3.7): success toast for close-now mutation.
        if (window.EInviteToast) {
          EInviteToast.show({
            type: 'success',
            message_en: STRINGS.closed.en,
            message_km: STRINGS.closed.km,
            duration: 4000
          });
        }
      } catch (err) {
        // V2-UX-7 (§3.7): replace the previous alert() with a bilingual
        // error toast; auto-dismiss after 6s (longer than success).
        if (window.EInviteToast) {
          EInviteToast.show({
            type: 'error',
            message_en: err.message || STRINGS.errClose.en,
            message_km: err.message || STRINGS.errClose.km,
            duration: 6000
          });
        }
      }
    }

    async function onToggleResults(btn) {
      const pollId = btn.getAttribute('data-results');
      const region = stateEl.querySelector(`[data-results-region="${cssEsc(pollId)}"]`);
      if (!region) return;
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      if (expanded) {
        region.hidden = true;
        region.innerHTML = '';
        btn.setAttribute('aria-expanded', 'false');
        // Match the host-signup-sheets sibling: restore the EN label on collapse.
        btn.textContent = STRINGS.viewResults.en;
        return;
      }
      btn.setAttribute('aria-expanded', 'true');
      btn.textContent = STRINGS.hideResults.en;
      region.hidden = false;
      region.innerHTML = `<p class="muted">${langText('loading', lang)}</p>`;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls/${encodeURIComponent(pollId)}/results`, {
          headers: { Accept: 'application/json' }, credentials: 'same-origin',
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        renderResults(region, data || {});
      } catch (err) {
        region.innerHTML = `<p class="error">${langText('errResults', lang)} <code>${esc(err.message || '')}</code></p>`;
      }
    }

    function renderResults(region, poll) {
      const options = Array.isArray(poll.options) ? poll.options : [];
      const totalVotes = typeof poll.totalVotes === 'number' ? poll.totalVotes
        : options.reduce((acc, o) => acc + (typeof o.votes === 'number' ? o.votes : 0), 0);
      if (!totalVotes) {
        region.innerHTML = `<p class="muted">${langText('noVotes', lang)}</p>`;
        return;
      }
      const maxVotes = options.reduce((m, o) => Math.max(m, typeof o.votes === 'number' ? o.votes : 0), 0) || 1;
      const barRows = options.map((opt) => {
        const votes = typeof opt.votes === 'number' ? opt.votes : 0;
        const pct = Math.round((votes / maxVotes) * 100);
        return `
          <li class="host-poll-result-bar-row">
            <span class="host-poll-result-label">${esc(opt.label || '')}</span>
            <div class="host-poll-result-bar-track"><div class="host-poll-result-bar-fill" style="width:${pct}%"></div></div>
            <span class="host-poll-result-count">${votes}</span>
          </li>`;
      }).join('');
      // Voter list — host-only PII (full emails per §3.2 acceptance).
      const voters = Array.isArray(poll.votes) ? poll.votes : [];
      const optionLabelMap = {};
      options.forEach((o) => { optionLabelMap[String(o.id)] = o.label || ''; });
      const voterRows = voters.map((v) => `
        <tr>
          <td>${esc(v.name || STRINGS.voterAnonymous.en)}</td>
          <td>${esc(v.email || '')}</td>
          <td>${esc(optionLabelMap[String(v.optionId)] || v.optionId || '')}</td>
          <td>${esc(formatTs(v.createdAt))}</td>
        </tr>`).join('');
      const voterBlock = voters.length
        ? `
          <div class="host-poll-voters">
            <table class="host-poll-voters-table">
              <thead><tr>
                <th>${langText('voterName', lang)}</th>
                <th>${langText('voterEmail', lang)}</th>
                <th>${langText('voterChoice', lang)}</th>
                <th>${langText('voterWhen', lang)}</th>
              </tr></thead>
              <tbody>${voterRows}</tbody>
            </table>
          </div>`
        : '';
      region.innerHTML = `
        <div class="host-poll-result-summary">
          <span class="muted">${langText('totalVotesLabel', lang)}: <strong>${totalVotes}</strong></span>
        </div>
        <ul class="host-poll-result-bars">${barRows}</ul>
        ${voterBlock}`;
    }
  }

  window.EInviteHostPolls = { mount };
})();
