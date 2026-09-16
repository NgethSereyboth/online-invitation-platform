/**
 * Phase 2a (V54.1) — Shared photo album guest UI.
 *
 * Loaded on the public invitation page. Lets guests upload photos (post-event)
 * and browse approved photos. Photos flow through the V54 malware scanner
 * before they are stored. Vanilla JS, bilingual EN + KH.
 *
 * V54.18 (ROADMAP-V2 §3.4): the upload path now uses XMLHttpRequest instead of
 * fetch so we can surface a live upload-progress bar, a "Processing…" state
 * while the server-side malware scan runs, an explicit Cancel button (calls
 * `xhr.abort()`), and a Retry button on failure. The MIME allow-list, the
 * FormData construction, the endpoint, and the success → reload-grid contract
 * are preserved exactly. The malware-scan 422 path surfaces a distinct
 * "Upload rejected: malware detected." message.
 *
 * Surface contract:
 *   window.EInviteAlbum.enhance(root, { invitationId, mode, guestToken, accessToken })
 */
(function () {
  'use strict';

  const STRINGS = {
    sectionTitle: { en: 'Shared photo album', km: 'អាល់ប៊ុមរូបថតរួម' },
    sectionIntro: {
      en: 'Share photos from the event. New uploads are reviewed by the host before they appear here.',
      km: 'ចែករំលែករូបថតពីការប្រគំតន្ត្រី។ រូបថតថ្មីៗត្រូវបានពិនិត្យដោយម្ចាស់កម្មវិធីមុននឹងបង្ហាញនៅទីនេះ។',
    },
    upload: { en: 'Upload photo', km: 'បញ្ចូលរូបថត' },
    caption: { en: 'Caption (optional)', km: 'ចំណងជើង (ស្រេចចិត្ត)' },
    choose: { en: 'Choose photo', km: 'ជ្រើសរូបថត' },
    submit: { en: 'Upload', km: 'បញ្ចូល' },
    pending: { en: 'Pending review', km: 'រង់ចាំពិនិត្យ' },
    approved: { en: 'Approved', km: 'បានអនុម័ត' },
    hidden: { en: 'Hidden', km: 'បានលាក់' },
    delete: { en: 'Delete', km: 'លុប' },
    loading: { en: 'Loading photos…', km: 'កំពុងផ្ទុករូបថត…' },
    empty: { en: 'No photos have been shared yet. Be the first!', km: 'មិនទាន់មានរូបថតត្រូវបានចែករំលែកនៅឡើយ។ ក្លាយជាមនុស្សដំបូង!' },
    error: { en: 'We could not upload the photo. Please try again.', km: 'មិនអាចបញ្ចូលរូបថតបានទេ។ សូមព្យាយាមម្ដងទៀត។' },
    success: { en: 'Photo uploaded! It will appear here after the host approves it.', km: 'រូបថតបានបញ្ចូល! វានឹងបង្ហាញនៅទីនេះបន្ទាប់ពីម្ចាស់កម្មវិធីអនុម័ត។' },
    approve: { en: 'Approve', km: 'អនុម័ត' },
    hide: { en: 'Hide', km: 'លាក់' },
    loadMore: { en: 'Load more', km: 'ផ្ទុកថែម' },
    // V54.18 (§3.4) — upload progress UI strings (bilingual EN + KH).
    uploading: { en: 'Uploading…', km: 'កំពុងផ្ទុកឡើង…' },
    processing: { en: 'Processing…', km: 'កំពុងដំណើរការ…' },
    uploadFailed: { en: 'Upload failed. Please try again.', km: 'ការផ្ទុកឡើងបរាជ័យ។ សូមព្យាយាមម្ដងទៀត។' },
    malwareDetected: { en: 'Upload rejected: malware detected.', km: 'ការផ្ទុកឡើងត្រូវបានបដិសេធ: បានរកឃើញម៉ាលវែរ។' },
    retry: { en: 'Retry', km: 'ព្យាយាមម្ដងទៀត' },
    cancel: { en: 'Cancel', km: 'បោះបង់' },
    cancelled: { en: 'Upload cancelled.', km: 'ការផ្ទុកឡើងត្រូវបានបោះបង់។' },
  };

  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const langText = (key, mode) => {
    const en = STRINGS[key] ? STRINGS[key].en : key;
    const km = STRINGS[key] ? STRINGS[key].km : key;
    if (mode === 'km') return `<span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    if (mode === 'both') return `<span class="i18n i18n-en">${esc(en)}</span> <span class="i18n i18n-km khmer-text">${esc(km)}</span>`;
    return `<span class="i18n i18n-en">${esc(en)}</span>`;
  };

  // V54.18 (§3.4) — Inject the upload-progress CSS once per document. The
  // task scope forbids editing any .css file, so the styles live in a
  // <style> element appended from JS. Idempotent: if the tag already exists
  // (e.g. the module is bundled into a page that loads album.js twice), the
  // second invocation is a no-op. The rules use the existing design tokens
  // (--brand / --brand-2 / --danger / --surface-2 / --border-1 / --text-2)
  // with hard-coded fallbacks so the bar is legible even on a page that has
  // not loaded tokens.css.
  const PROGRESS_STYLE_ID = 'einvite-album-progress-style-v54-18';
  if (!document.getElementById(PROGRESS_STYLE_ID)) {
    const styleEl = document.createElement('style');
    styleEl.id = PROGRESS_STYLE_ID;
    styleEl.textContent = [
      '.album-upload-progress{margin:8px 0 16px;padding:12px 14px;border:1px solid var(--border-1,#e2e3e8);border-radius:var(--radius-md,14px);background:var(--surface-2,#f8f8fb);}',
      '.album-upload-progress[hidden]{display:none!important;}',
      '.album-upload-progress-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;}',
      '.album-upload-progress-bar{flex:1 1 180px;min-width:180px;height:12px;background:var(--border-1,#e2e3e8);border-radius:6px;overflow:hidden;position:relative;}',
      '.album-upload-progress-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--brand,#8b465b),var(--brand-2,#9c6cff));transition:width .15s ease-out;border-radius:6px;}',
      '.album-upload-progress-text{margin:8px 0 0;font-size:13px;color:var(--text-2,#646773);min-height:1.2em;line-height:1.4;}',
      '.album-upload-progress-text.error{color:var(--danger,#c6404d);}',
      '.album-upload-progress-text.processing{color:var(--brand,#8b465b);font-style:italic;}',
      '.album-upload-progress-text.cancelled{color:var(--text-2,#646773);font-style:italic;}',
      '.album-upload-progress-text.success{color:var(--success,#2b9b68);}',
      '.album-upload-cancel,.album-upload-retry{flex:0 0 auto;padding:6px 14px;font-size:13px;border:1px solid var(--border-2,#d3d5dc);border-radius:var(--radius-sm,10px);background:var(--surface-1,#fff);color:var(--text-1,#1f2026);cursor:pointer;font-family:inherit;}',
      '.album-upload-cancel:hover,.album-upload-retry:hover{background:var(--surface-3,#eff0f4);}',
      '.album-upload-retry{background:var(--brand,#8b465b);color:#fff;border-color:var(--brand,#8b465b);}',
      '.album-upload-retry:hover{background:var(--brand-2,#9c6cff);border-color:var(--brand-2,#9c6cff);color:#fff;}',
      '.album-upload-cancel[hidden],.album-upload-retry[hidden]{display:none!important;}',
      '@media(max-width:540px){.album-upload-progress-bar{flex:1 1 100%;}}',
    ].join('\n');
    document.head.appendChild(styleEl);
  }

  function enhance(root, opts) {
    if (!root || !opts || !opts.invitationId) return;
    const invitationId = opts.invitationId;
    const guestToken = opts.guestToken || '';
    const accessToken = opts.accessToken || '';
    const mode = opts.mode || 'guest';
    const headers = {
      ...(guestToken ? { 'X-Invitation-Guest': guestToken } : {}),
      ...(accessToken ? { 'X-Invitation-Access': accessToken } : {}),
    };

    const section = document.createElement('section');
    section.className = 'guest-feature album';
    section.setAttribute('aria-label', STRINGS.sectionTitle.en);
    section.innerHTML = `
      <h2>${langText('sectionTitle', mode)}</h2>
      <p class="muted">${langText('sectionIntro', mode)}</p>
      <form class="album-upload">
        <label>${langText('choose', mode)}<input type="file" name="file" accept="image/jpeg,image/png,image/webp,image/gif" required></label>
        <label>${langText('caption', mode)}<input type="text" name="caption" maxlength="500"></label>
        <button type="submit">${langText('submit', mode)}</button>
      </form>
      <div class="album-upload-progress" hidden role="status" aria-live="polite" aria-atomic="true">
        <div class="album-upload-progress-row">
          <div class="album-upload-progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-label="${esc(STRINGS.uploading.en)}"><div class="album-upload-progress-fill"></div></div>
          <button type="button" class="album-upload-cancel">${langText('cancel', mode)}</button>
          <button type="button" class="album-upload-retry" hidden>${langText('retry', mode)}</button>
        </div>
        <p class="album-upload-progress-text"></p>
      </div>
      <div class="album-grid state">${langText('loading', mode)}</div>
      <button class="load-more" hidden>${langText('loadMore', mode)}</button>
    `;
    root.appendChild(section);

    let cursor = 0;
    const form = section.querySelector('.album-upload');
    const grid = section.querySelector('.album-grid');
    const loadMoreBtn = section.querySelector('.load-more');
    // V54.18 — upload-progress DOM handles. Cached once at mount so the
    // progress UI can be shown/hidden/reset without re-querying on every
    // upload attempt.
    const progressEl = section.querySelector('.album-upload-progress');
    const progressFill = progressEl.querySelector('.album-upload-progress-fill');
    const progressBar = progressEl.querySelector('.album-upload-progress-bar');
    const progressText = progressEl.querySelector('.album-upload-progress-text');
    const cancelBtn = progressEl.querySelector('.album-upload-cancel');
    const retryBtn = progressEl.querySelector('.album-upload-retry');

    form.addEventListener('submit', onUpload);
    loadMoreBtn.addEventListener('click', () => load(true));
    load(false);

    async function load(append) {
      try {
        const url = `/api/invitations/${encodeURIComponent(invitationId)}/album?limit=20` + (cursor ? `&before=${cursor}` : '');
        const res = await fetch(url, { headers });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        const html = (data.photos || []).map(renderPhoto).join('');
        if (append) grid.insertAdjacentHTML('beforeend', html);
        else grid.innerHTML = html || `<p class="muted">${langText('empty', mode)}</p>`;
        if (data.hasMore) {
          cursor = data.nextCursor;
          loadMoreBtn.hidden = false;
        } else {
          loadMoreBtn.hidden = true;
        }
        // Wire up delete/moderate buttons.
        grid.querySelectorAll('button[data-delete-photo]').forEach((b) => b.addEventListener('click', onDelete));
        grid.querySelectorAll('button[data-moderate-photo]').forEach((b) => b.addEventListener('click', onModerate));
      } catch (err) {
        grid.innerHTML = `<p class="error">${esc(err.message)}</p>`;
      }
    }

    function renderPhoto(p) {
      const isHost = mode === 'host';
      const statusBadge = isHost ? `<span class="badge badge-${esc(p.status)}">${p.status}</span>` : '';
      const moderation = isHost ? `
        ${p.status !== 'approved' ? `<button type="button" data-moderate-photo data-photo-id="${esc(p.id)}" data-status="approved">${langText('approve', mode)}</button>` : ''}
        ${p.status !== 'hidden' ? `<button type="button" data-moderate-photo data-photo-id="${esc(p.id)}" data-status="hidden">${langText('hide', mode)}</button>` : ''}
      ` : '';
      return `
        <figure class="album-photo">
          <img src="${esc(p.url)}" alt="${esc(p.caption || 'Photo')}" loading="lazy">
          ${p.caption ? `<figcaption>${esc(p.caption)}</figcaption>` : ''}
          ${statusBadge}
          ${moderation}
          <button type="button" data-delete-photo data-photo-id="${esc(p.id)}">${langText('delete', mode)}</button>
        </figure>`;
    }

    // V54.18 (§3.4) — form submit handler. Reads the current file + caption
    // from the form, then delegates to startUpload() which owns the XHR +
    // progress UI lifecycle. startUpload() is also the Retry entry point
    // (it re-reads the form so the user can swap the file between attempts).
    function onUpload(event) {
      event.preventDefault();
      startUpload();
    }

    // V54.18 (§3.4) — Replace fetch() with XMLHttpRequest for the album
    // upload path ONLY. The endpoint, FormData fields, MIME allow-list
    // (the accept="image/..." attribute on the input), and success →
    // reset + reload contract are unchanged. The XHR gives us:
    //   • xhr.upload 'progress' → live % bar.
    //   • xhr.upload 'load'     → switch to "Processing…" (malware scan).
    //   • xhr 'abort'           → Cancel button (calls xhr.abort()).
    //   • xhr 'error'           → network failure → Retry button.
    //   • xhr 'load'            → response: 2xx = success, 422+malware =
    //                             distinct malware message, else generic.
    function startUpload() {
      const file = form.querySelector('input[name=file]').files[0];
      const caption = form.querySelector('input[name=caption]').value;
      const button = form.querySelector('button[type=submit]');
      if (!file) return;

      // Reset the progress UI to the "Uploading…" state.
      progressEl.hidden = false;
      retryBtn.hidden = true;
      cancelBtn.hidden = false;
      progressText.classList.remove('error', 'processing', 'cancelled', 'success');
      progressText.innerHTML = langText('uploading', mode);
      progressFill.style.width = '0%';
      progressBar.setAttribute('aria-valuenow', '0');
      progressBar.setAttribute('aria-label', STRINGS.uploading.en);
      if (button) button.disabled = true;

      // FormData construction is identical to the previous fetch path —
      // same fields, same order, same multipart encoding.
      const fd = new FormData();
      fd.append('file', file);
      fd.append('caption', caption);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `/api/invitations/${encodeURIComponent(invitationId)}/album`);
      // Auth headers mirror the prior fetch() call. (Don't set
      // Content-Type — the browser sets multipart/form-data with the
      // correct boundary automatically.)
      if (guestToken) xhr.setRequestHeader('X-Invitation-Guest', guestToken);
      if (accessToken) xhr.setRequestHeader('X-Invitation-Access', accessToken);
      // Use responseType='text' + manual JSON.parse so we can still read
      // the body when the server returns a non-JSON error page (e.g. a
      // 502 from a reverse proxy). responseType='json' would null out
      // the body in that case.
      xhr.responseType = 'text';

      // Upload progress — fired periodically while the request body is
      // being sent. lengthComputable is false for chunked/unknown-length
      // streams; in that case we leave the bar at 0% and rely on the
      // upload 'load' event to jump to 100%.
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable && e.total > 0) {
          const pct = Math.min(100, Math.max(0, Math.round((e.loaded / e.total) * 100)));
          progressFill.style.width = pct + '%';
          progressBar.setAttribute('aria-valuenow', String(pct));
        }
      });

      // Upload body fully sent — the server is now running the malware
      // scan (ClamAV/Defender) which may take a few seconds. Switch the
      // text to "Processing…" and pin the bar at 100%. The bar stays
      // visible until the response arrives (xhr 'load') or the user
      // cancels (xhr 'abort').
      xhr.upload.addEventListener('load', () => {
        progressFill.style.width = '100%';
        progressBar.setAttribute('aria-valuenow', '100');
        progressText.classList.remove('error', 'cancelled', 'success');
        progressText.classList.add('processing');
        progressText.innerHTML = langText('processing', mode);
      });

      function resetProgressUI() {
        progressEl.hidden = true;
        progressText.classList.remove('error', 'processing', 'cancelled', 'success');
        progressText.innerHTML = '';
        progressFill.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-label', STRINGS.uploading.en);
        cancelBtn.hidden = false;
        retryBtn.hidden = true;
        if (button) button.disabled = false;
      }

      function showError(msgHtml) {
        progressText.classList.remove('processing', 'cancelled', 'success');
        progressText.classList.add('error');
        progressText.innerHTML = msgHtml;
        progressFill.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        // Hide Cancel (the xhr is done) and surface Retry so the user can
        // re-attempt with the same file (still in the input).
        cancelBtn.hidden = true;
        retryBtn.hidden = false;
        if (button) button.disabled = false;
      }

      // Cancel — the user clicked "Cancel" during upload or during the
      // server-side processing window. xhr.abort() fires the 'abort'
      // event synchronously (or in a microtask), which runs the cleanup
      // below. The file is NOT cleared from the input so the user can
      // hit Upload again if they change their mind.
      xhr.addEventListener('abort', () => {
        // Show the cancelled state briefly so the user gets feedback,
        // then hide the bar after ~2.5s. The submit button is re-enabled
        // immediately so the user can retry without waiting.
        progressText.classList.remove('processing', 'error', 'success');
        progressText.classList.add('cancelled');
        progressText.innerHTML = langText('cancelled', mode);
        progressFill.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        cancelBtn.hidden = true;
        retryBtn.hidden = true;
        if (button) button.disabled = false;
        // Auto-hide the progress bar after a short delay.
        window.setTimeout(() => {
          // Only hide if the user hasn't already started a new upload
          // (in which case progressText would no longer say "cancelled").
          if (progressText.classList.contains('cancelled')) {
            progressEl.hidden = true;
            progressText.classList.remove('cancelled');
            progressText.innerHTML = '';
          }
        }, 2500);
      });

      // Network-level error (no response reached the client). This fires
      // for CORS errors, DNS failures, dropped connections mid-upload,
      // and timeouts. Show the generic "Upload failed" message + Retry.
      xhr.addEventListener('error', () => {
        showError(langText('uploadFailed', mode));
      });

      // Response received — classify by status code. 2xx = success,
      // 422 + malware code = the distinct malware message, everything
      // else = the generic "Upload failed" message. Either way the bar
      // is hidden (success) or swapped to the error + Retry state.
      xhr.addEventListener('load', () => {
        const status = xhr.status || 0;
        let result = {};
        try {
          result = xhr.responseText ? JSON.parse(xhr.responseText) : {};
          if (!result || typeof result !== 'object') result = {};
        } catch (_) {
          result = {};
        }

        if (status >= 200 && status < 300) {
          // Success — hide the progress bar, reset the form (clears the
          // file input), reload the grid, and surface the same bilingual
          // success alert the previous fetch() path used.
          resetProgressUI();
          form.reset();
          alert(STRINGS.success.en);
          load(false);
          return;
        }

        if (status === 422 && (result.code === 'malware_detected' || /malware/i.test(result.error || ''))) {
          // V54.18 §3.4 — distinct malware-rejection message. The
          // server returns HTTP 422 with {"code": "malware_detected"}
          // (server.py L8314-8315, L8325-8326) when the ClamAV/Defender
          // scan rejects the bytes.
          showError(langText('malwareDetected', mode));
          return;
        }

        // Any other non-2xx status — generic upload-failed message.
        showError(langText('uploadFailed', mode));
      });

      // Cancel button — abort the in-flight xhr. The abort event
      // handler above does the UI cleanup, so this handler is a one-
      // liner. The try/catch guards against calling abort() on an
      // already-completed xhr (some browsers throw in that case).
      cancelBtn.onclick = () => {
        try { xhr.abort(); } catch (_) { /* already done */ }
      };

      // Retry button — re-enter startUpload() which re-reads the form.
      // The file remains in the input after a failed upload, so retry
      // re-attempts with the same file. If the user has swapped the
      // file in the meantime, the new file is used (startUpload reads
      // the input fresh on every call).
      retryBtn.onclick = () => {
        startUpload();
      };

      xhr.send(fd);
    }

    async function onDelete(event) {
      const btn = event.currentTarget;
      const photoId = btn.getAttribute('data-photo-id');
      if (!confirm('Delete this photo?')) return;
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/album/${encodeURIComponent(photoId)}`, {
          method: 'DELETE', headers,
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        load(false);
      } catch (err) {
        alert(err.message);
      }
    }

    async function onModerate(event) {
      const btn = event.currentTarget;
      const photoId = btn.getAttribute('data-photo-id');
      const status = btn.getAttribute('data-status');
      try {
        const res = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/album/${encodeURIComponent(photoId)}/moderate`, {
          method: 'POST', headers: { ...headers, 'Content-Type': 'application/json' },
          body: JSON.stringify({ status }),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        load(false);
      } catch (err) {
        alert(err.message);
      }
    }
  }

  window.EInviteAlbum = { enhance };
})();
