/**
 * Shared material upload client.
 *
 * Production flow:
 *   1. Ask the application server for a short-lived signed object-storage URL.
 *   2. Upload the binary directly to S3/R2 when configured.
 *   3. Ask the server to verify and register the uploaded object.
 *
 * Local/review flow:
 *   - If direct object-storage upload is not configured (HTTP 409), fall back to
 *     the existing authenticated raw upload endpoint.
 *
 * A failed direct PUT is deliberately not retried through the raw endpoint: a
 * successful-but-unobservable cross-origin PUT could otherwise leave duplicate
 * orphan objects. Instead the error explains that bucket CORS/provider settings
 * need review.
 */
(() => {
  'use strict';

  const authHeader = (token) => token ? { Authorization: `Bearer ${token}` } : {};

  async function readJson(response) {
    return response.json().catch(() => ({}));
  }

  async function rawUpload(invitationId, file, { token, name } = {}) {
    const response = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/raw`, {
      method: 'POST',
      headers: {
        ...authHeader(token),
        'Content-Type': file.type || 'application/octet-stream',
        'X-File-Name': encodeURIComponent(name || file.name || 'upload'),
      },
      body: file,
    });
    const payload = await readJson(response);
    if (!response.ok) throw new Error(payload.error || `Upload failed for ${name || file.name || 'material'}`);
    return { ...payload, uploadMode: 'server' };
  }

  async function directUpload(invitationId, file, { token, name } = {}) {
    const presign = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/presign`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader(token),
      },
      body: JSON.stringify({
        name: name || file.name || 'upload',
        mime: file.type || 'application/octet-stream',
        size: file.size,
      }),
    });

    // Local storage and development deployments intentionally use the normal
    // application upload endpoint.
    if (presign.status === 409) return null;

    const signed = await readJson(presign);
    if (!presign.ok) throw new Error(signed.error || 'Could not prepare direct material upload');
    if (!signed.directUpload || !signed.uploadUrl || !signed.claim) return null;

    let putResponse;
    try {
      putResponse = await fetch(signed.uploadUrl, {
        method: 'PUT',
        headers: signed.headers || { 'Content-Type': file.type || 'application/octet-stream' },
        body: file,
      });
    } catch (error) {
      throw new Error(`Direct storage upload could not reach the storage provider. Check the R2/S3 bucket CORS policy and public network access. ${error?.message || ''}`.trim());
    }
    if (!putResponse.ok) {
      throw new Error(`Direct storage upload failed with HTTP ${putResponse.status}. Check the object-storage CORS policy and signed-upload credentials.`);
    }

    const complete = await fetch(`/api/invitations/${encodeURIComponent(invitationId)}/assets/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeader(token),
      },
      body: JSON.stringify({ name: name || file.name || 'upload', claim: signed.claim }),
    });
    const payload = await readJson(complete);
    if (!complete.ok) throw new Error(payload.error || 'The uploaded material could not be verified and registered');
    return { ...payload, uploadMode: 'direct' };
  }

  async function upload(invitationId, file, options = {}) {
    if (!invitationId) throw new Error('Choose an invitation before uploading a material.');
    if (!file) throw new Error('Choose a file to upload.');

    const direct = await directUpload(invitationId, file, options);
    if (direct) return direct;
    return rawUpload(invitationId, file, options);
  }

  window.EInviteUpload = Object.freeze({ upload, rawUpload });
})();
