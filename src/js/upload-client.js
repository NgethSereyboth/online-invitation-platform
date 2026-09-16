(() => {
  'use strict';
  const RESUMABLE_THRESHOLD = 8_000_000;
  const DEFAULT_CHUNK_SIZE = 5_000_000;
  async function readJson(response) {
    return response.json().catch(() => ({}));
  }
  function abortError() {
    try { return new DOMException('Upload cancelled', 'AbortError'); }
    catch { const error = new Error('Upload cancelled'); error.name = 'AbortError'; return error; }
  }
  function cookieValue(name) {
    const prefix = `${name}=`;
    const pair = String(document.cookie || '').split(';').map(value => value.trim()).find(value => value.startsWith(prefix));
    if (!pair) return '';
    try { return decodeURIComponent(pair.slice(prefix.length)); } catch { return pair.slice(prefix.length); }
  }
  function browserMutationHeaders(url, headers = {}) {
    const output = { ...headers };
    const sameOrigin = String(url || '').startsWith('/') || (() => {
      try { return new URL(url, location.href).origin === location.origin; } catch { return false; }
    })();
    if (sameOrigin && !Object.keys(output).some(key => key.toLowerCase() === 'x-csrf-token')) {
      const token = cookieValue('einvite_csrf');
      if (token) output['X-CSRF-Token'] = token;
    }
    return output;
  }
  function xhrRequest(url, { method = 'POST', headers = {}, body = null, signal, onProgress } = {}) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open(method, url, true);
      xhr.withCredentials = true;
      Object.entries(browserMutationHeaders(url, headers)).forEach(([key, value]) => xhr.setRequestHeader(key, value));
      if (xhr.upload && onProgress) xhr.upload.onprogress = event => {
        if (event.lengthComputable) onProgress(event.loaded, event.total);
      };
      xhr.onload = () => {
        let payload = {};
        try { payload = JSON.parse(xhr.responseText || '{}'); } catch {}
        if (xhr.status >= 200 && xhr.status < 300) resolve({ status: xhr.status, payload, xhr });
        else reject(Object.assign(new Error(payload.error || `Upload failed with HTTP ${xhr.status}`), { status: xhr.status, payload }));
      };
      xhr.onerror = () => reject(new Error('The upload connection was interrupted.'));
      xhr.onabort = () => reject(abortError());
      if (signal) {
        if (signal.aborted) return reject(abortError());
        signal.addEventListener('abort', () => xhr.abort(), { once: true });
      }
      xhr.send(body);
    });
  }
  function fontMime(file) {
    const name = String(file?.name || '').toLowerCase();
    if (name.endsWith('.ttf') || name.endsWith('.tff')) return 'font/ttf';
    if (name.endsWith('.otf')) return 'font/otf';
    if (name.endsWith('.woff2')) return 'font/woff2';
    return String(file?.type || 'application/octet-stream').toLowerCase();
  }
  async function uploadFont(invitationId, file, { name, signal, onProgress, licenseAcknowledged = false } = {}) {
    if (!invitationId) throw new Error('Choose an invitation before uploading a font.');
    if (!file) throw new Error('Choose a TTF, OTF, or WOFF2 font file.');
    const result = await xhrRequest(`/api/invitations/${encodeURIComponent(invitationId)}/fonts`, {
      method: 'POST', signal, body: file,
      headers: {
        'Content-Type': fontMime(file),
        'X-File-Name': encodeURIComponent(name || file.name || 'custom-font.ttf'),
        'X-Font-License-Acknowledged': licenseAcknowledged ? 'true' : 'false',
      },
      onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
    });
    onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
    return { ...result.payload, uploadMode: 'font-optimized' };
  }
  async function rawUpload(invitationId, file, { name, signal, onProgress, folder = '', importJobId = '' } = {}) {
    const result = await xhrRequest(`/api/invitations/${encodeURIComponent(invitationId)}/assets/raw`, {
      method: 'POST', signal, body: file,
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
        'X-File-Name': encodeURIComponent(name || file.name || 'upload'),
        'X-Material-Folder': encodeURIComponent(folder || ''),
        'X-Material-Import-Job': String(importJobId || ''),
      },
      onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
    });
    return { ...result.payload, uploadMode: 'server' };
  }
  async function directUpload(invitationId, file, { name, signal, onProgress, folder = '', importJobId = '' } = {}) {
    const presign = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/presign`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', mime: file.type || 'application/octet-stream', size: file.size, folder, importJobId }),
    });
    if (presign.status === 409) return null;
    const signed = await readJson(presign);
    if (!presign.ok) throw new Error(signed.error || 'Could not prepare direct material upload');
    if (!signed.directUpload || !signed.uploadUrl || !signed.claim) return null;
    try {
      await xhrRequest(signed.uploadUrl, {
        method: 'PUT', signal, body: file,
        headers: signed.headers || { 'Content-Type': file.type || 'application/octet-stream' },
        onProgress: (loaded, total) => onProgress?.({ loaded, total, percent: total ? Math.round(loaded / total * 100) : 0, phase: 'uploading' }),
      });
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      throw new Error(`Direct storage upload failed. Check the R2/S3 CORS policy and signed-upload credentials. ${error.message || ''}`.trim());
    }
    onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
    const complete = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/complete`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', claim: signed.claim }),
    });
    const payload = await readJson(complete);
    if (!complete.ok) throw new Error(payload.error || 'The uploaded material could not be verified and registered');
    return { ...payload, uploadMode: 'direct' };
  }
  async function resumableUpload(invitationId, file, { name, signal, onProgress, retries = 2, folder = '', importJobId = '' } = {}) {
    const start = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/uploads/start`, {
      method: 'POST', credentials: 'same-origin', signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || file.name || 'upload', mime: file.type || 'application/octet-stream', size: file.size, folder, importJobId }),
    });
    const session = await readJson(start);
    if (!start.ok) throw new Error(session.error || 'Could not start the resumable upload');
    const uploadId = session.uploadId;
    const chunkSize = Number(session.chunkSize || DEFAULT_CHUNK_SIZE);
    let offset = Number(session.received || 0);
    const cancelServerSession = () => fetch(`/api/uploads/${encodeURIComponent(uploadId)}`, { method: 'DELETE', credentials: 'same-origin' }).catch(() => {});
    try {
      while (offset < file.size) {
        if (signal?.aborted) throw abortError();
        const end = Math.min(file.size, offset + chunkSize);
        const chunk = file.slice(offset, end);
        let attempt = 0;
        while (true) {
          try {
            const result = await xhrRequest(`/api/uploads/${encodeURIComponent(uploadId)}`, {
              method: 'PUT', signal, body: chunk,
              headers: { 'Content-Type': 'application/octet-stream', 'X-Upload-Offset': String(offset) },
              onProgress: loaded => onProgress?.({ loaded: offset + loaded, total: file.size, percent: Math.round((offset + loaded) / file.size * 100), phase: 'uploading' }),
            });
            offset = Number(result.payload.received || end);
            break;
          } catch (error) {
            if (error.name === 'AbortError') throw error;
            if (++attempt > retries) throw error;
            const status = await fetch(`/api/uploads/${encodeURIComponent(uploadId)}`, { credentials: 'same-origin', signal }).then(readJson).catch(() => null);
            if (status && Number.isFinite(Number(status.received))) offset = Number(status.received);
            await new Promise(resolve => setTimeout(resolve, 350 * attempt));
          }
        }
      }
      onProgress?.({ loaded: file.size, total: file.size, percent: 100, phase: 'processing' });
      const complete = await fetch(`/api/uploads/${encodeURIComponent(uploadId)}/complete`, { method: 'POST', credentials: 'same-origin', signal, headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const payload = await readJson(complete);
      if (!complete.ok) throw new Error(payload.error || 'The resumable upload could not be finalized');
      return { ...payload, uploadMode: 'resumable' };
    } catch (error) {
      await cancelServerSession();
      throw error;
    }
  }
  async function upload(invitationId, file, options = {}) {
    if (!invitationId) throw new Error('Choose an invitation before uploading a material.');
    if (!file) throw new Error('Choose a file to upload.');
    if (options.signal?.aborted) throw abortError();
    const direct = options.forceServer ? null : await directUpload(invitationId, file, options);
    if (direct) return direct;
    if (file.size >= RESUMABLE_THRESHOLD) return resumableUpload(invitationId, file, options);
    return rawUpload(invitationId, file, options);
  }
  window.EInviteUpload = Object.freeze({ upload, uploadFont, rawUpload, resumableUpload, directUpload });
})();
