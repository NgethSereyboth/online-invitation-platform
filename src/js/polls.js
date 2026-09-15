/**
 * Phase 2a (V54.1) — Polls guest UI.
 *
 * Loaded on the public invitation page. Renders each poll with vote buttons
 * (or live results when visibility=live). Vanilla JS, bilingual EN+KH.
 *
 * Surface contract:
 *   window.EInvitePolls.enhance(root, { invitationId, mode, guestToken, accessToken })
 */
(function () {
  'use strict';

  const STRINGS = {
    sectionTitle: { en: 'Polls', km: 'ការស្ទង់មតិ' },
    sectionIntro: { en: 'Help your host decide by answering these polls.', km: 'ជួយម្ចាស់កម្មវិធីជ្រើសរើសដោយឆ្លើយតបការស្ទង់មតិទាំងនេះ។' },
    vote: { en: 'Vote', km: 'បោះឆ្នោត' },
    voted: { en: 'Voted', km: 'បានបោះឆ្នោត' },
    closed: { en: 'Closed', km: 'បិទហើយ' },
    votes: { en: 'votes', km: 'សន្លឹកឆ្នោត' },
    resultsHidden: { en: 'Results will be revealed when the poll closes.', km: 'លទ្ធផលនឹងបង្ហាញពេលការស្ទង់មតិបិទ។' },
    submit: { en: 'Submit vote', km: 'បញ្ជូនការបោះឆ្នោត' },
    name: { en: 'Your name', km: 'ឈ្មោះរបស់អ្នក' },
    email: { en: 'Email (optional)', km: 'អ៊ីមែល (ស្រេចចិត្ត)' },
    loading: { en: 'Loading polls…', km: 'កំពុងផ្ទុកការស្ទង់មតិ…' },
    empty: { en: 'No polls are open for this invitation yet.', km: 'មិនទាន់មានការស្ទង់មតិសម្រាប់ការអញ្ជើញនេះនៅឡើយ។' },
    error: { en: 'We could not save your vote. Please try again.', km: 'មិនអាចរក្សាទុកការបោះឆ្នោតបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
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
    section.className = 'guest-feature polls';
    section.setAttribute('aria-label', STRINGS.sectionTitle.en);
    section.innerHTML = `<h2>${langText('sectionTitle', mode)}</h2><p class="muted">${langText('sectionIntro', mode)}</p><p class="state">${langText('loading', mode)}</p>`;
    root.appendChild(section);

    refresh();

    async function refresh() {
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const polls = await res.json();
        render(polls);
      } catch (err) {
        section.querySelector('.state').textContent = err.message || 'error';
      }
    }

    function render(polls) {
      if (!polls || !polls.length) {
        section.querySelector('.state').innerHTML = `<p class="muted">${langText('empty', mode)}</p>`;
        return;
      }
      section.querySelector('.state').innerHTML = polls.map(renderPoll).join('');
      section.querySelectorAll('form[data-poll]').forEach((form) => {
        form.addEventListener('submit', onSubmitVote);
      });
    }

    function renderPoll(poll) {
      const closed = poll.closed;
      const showResults = poll.options && poll.options.some((o) => typeof o.votes === 'number');
      const total = poll.totalVotes || 0;
      const options = (poll.options || []).map((opt) => {
        const votes = (typeof opt.votes === 'number') ? opt.votes : 0;
        const pct = total > 0 ? Math.round((votes / total) * 100) : 0;
        const checked = (poll.myVotes || []).includes(opt.id) ? 'checked' : '';
        const input = closed ? '' : `<input type="${poll.multiSelect ? 'checkbox' : 'radio'}" name="option" value="${esc(opt.id)}" ${checked}>`;
        const bar = showResults ? `<div class="bar" style="width:${pct}%"></div><span class="vote-count">${votes} ${langText('votes', mode)}</span>` : '';
        return `<li class="option">${input}<span class="label">${esc(opt.label)}</span>${bar}</li>`;
      }).join('');
      return `
        <article class="poll" data-poll-id="${esc(poll.id)}">
          <h3>${esc(poll.question)}</h3>
          ${poll.deadlineTs ? `<p class="muted">${formatDate(poll.deadlineTs)}</p>` : ''}
          ${closed ? `<p class="badge badge-closed">${langText('closed', mode)}</p>` : ''}
          ${showResults ? '' : `<p class="muted">${langText('resultsHidden', mode)}</p>`}
          ${closed ? `<ul class="poll-options">${options}</ul>` : `
            <form data-poll="${esc(poll.id)}">
              <ul class="poll-options">${options}</ul>
              <label>${langText('name', mode)}<input type="text" name="name" required maxlength="120"></label>
              <label>${langText('email', mode)}<input type="email" name="email" maxlength="254"></label>
              <button type="submit">${langText('submit', mode)}</button>
            </form>
          `}
        </article>`;
    }

    async function onSubmitVote(event) {
      event.preventDefault();
      const form = event.currentTarget;
      const pollId = form.getAttribute('data-poll');
      const button = form.querySelector('button[type=submit]');
      const checked = Array.from(form.querySelectorAll('input[name=option]:checked')).map((i) => i.value);
      const name = form.querySelector('input[name=name]').value;
      const email = form.querySelector('input[name=email]').value;
      if (!checked.length) { alert('Select an option'); return; }
      if (button) button.disabled = true;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/polls/${encodeURIComponent(pollId)}/vote`, {
          method: 'POST', headers, body: JSON.stringify({ optionIds: checked, name, email }),
        });
        const result = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(result.error || 'HTTP ' + res.status);
        await refresh();
      } catch (err) {
        alert(err.message);
        if (button) button.disabled = false;
      }
    }
  }

  window.EInvitePolls = { enhance };
})();
