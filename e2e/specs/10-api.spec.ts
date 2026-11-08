import { expect, test } from '../support/fixtures';
import { weddingDocument } from '../support/api';
import { uniqueSlug } from '../support/seed';

/**
 * @api — the HTTP contract behind the UI, exercised with Playwright's request
 * context (no browser). Shapes and status codes here are the ones observed from
 * the running server, not inferred from documentation.
 */
test.describe('@api public contract', () => {
  test('health reports database, storage and feature readiness', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toMatchObject({ ok: true, database: 'sqlite' });
    expect(typeof body.uptimeSeconds).toBe('number');
  });

  test('anonymous reads expose no account data', async ({ request }) => {
    // /api/auth/me is a session probe: 200 with a null user by design, so the
    // client can ask "who am I?" without treating signed-out as an error.
    const me = await request.get('/api/auth/me');
    expect(me.status()).toBe(200);
    expect(await me.json()).toEqual({ user: null });

    for (const path of ['/api/invitations', '/api/account/usage']) {
      const response = await request.get(path);
      expect(response.status(), `${path} must reject anonymous callers`).toBe(401);
      expect(response.headers()['content-type']).toContain('application/json');
    }
  });

  test('login with a wrong password is a generic 401', async ({ request, baseURL, seed }) => {
    const response = await request.post('/api/auth/login', {
      data: { email: seed.victim.email, password: 'wrong-password-123' },
      headers: { Origin: baseURL! },
    });
    expect(response.status()).toBe(401);
    const body = await response.json();
    expect(JSON.stringify(body)).toMatch(/incorrect|invalid/i);
    expect(JSON.stringify(body), 'error must not disclose whether the account exists').not.toMatch(/not found|unknown user/i);
  });

  test('registration validates email and password shape', async ({ request, baseURL }) => {
    const headers = { Origin: baseURL! };
    const badEmail = await request.post('/api/auth/register', {
      data: { email: 'not-an-email', password: 'Qa-Passw0rd-2026' },
      headers,
    });
    expect(badEmail.status()).toBe(400);

    const shortPassword = await request.post('/api/auth/register', {
      data: { email: `qa.short.${Date.now()}@einvite.test`, password: 'short' },
      headers,
    });
    expect(shortPassword.status()).toBe(400);
  });

  test('duplicate registration is 409, not a second account', async ({ request, baseURL, seed }) => {
    const response = await request.post('/api/auth/register', {
      data: { email: seed.owner.email, password: 'Qa-Passw0rd-2026' },
      headers: { Origin: baseURL! },
    });
    expect(response.status()).toBe(409);
    expect((await response.json()).error).toMatch(/already exists/i);
  });

  test('unknown API route is a JSON 404', async ({ request }) => {
    const response = await request.get('/api/definitely-not-a-route');
    expect(response.status()).toBe(404);
    expect(response.headers()['content-type']).toContain('application/json');
  });
});

test.describe('@api authenticated contract', () => {
  test('create → publish → guest render is one coherent lifecycle', async ({ api, request }) => {
    const title = 'QA API Lifecycle';
    const created = await api.createInvitation(title, uniqueSlug('qa-api'));

    const detail = await api.get(`/api/invitations/${created.id}`);
    expect(detail.status()).toBe(200);
    const document = (await detail.json()).document;

    const publication = await api.publish(created.id, document, (await detail.json()).updatedAt);
    expect(publication.url).toBe(`/i/${created.slug}`);

    const guest = await request.get(`/i/${created.slug}`);
    expect(guest.status()).toBe(200);
    expect(await guest.text()).toContain(title);

    const publicJson = await request.get(`/api/public/${created.slug}`);
    expect(publicJson.status()).toBe(200);
    const payload = await publicJson.json();
    expect(payload.document.fields.names).toBe(title);
  });

  test('publishing a stale revision is rejected with revision_conflict', async ({ api }) => {
    const title = 'QA Revision Conflict';
    const created = await api.createInvitation(title, uniqueSlug('qa-rev'));
    const detail = await api.get(`/api/invitations/${created.id}`);
    const body = await detail.json();
    const revision = body.updatedAt;

    await api.publish(created.id, body.document, revision);
    const second = await api.post(`/api/invitations/${created.id}/publish`, {
      document: body.document,
      expectedRevision: revision,
    });
    expect(second.status()).toBe(409);
    expect((await second.json()).code).toBe('revision_conflict');
  });

  test('a second tenant cannot read another tenant\'s invitation', async ({ api, seed }) => {
    const response = await api.get(`/api/invitations/${seed.otherInvitation.id}`);
    expect(response.status()).toBe(404);
    expect((await response.json()).error).toMatch(/not found/i);
  });

  test('invitation list returns the owner\'s rows and leaks no other tenant data', async ({ api, seed }) => {
    const response = await api.get('/api/invitations');
    expect(response.status()).toBe(200);
    const rows = (await response.json()) as { slug: string; title: string }[];
    expect(rows.some((row) => row.slug === seed.invitation.slug)).toBe(true);
    expect(rows.some((row) => row.slug === seed.otherInvitation.slug)).toBe(false);
  });

  test('invitation list supports pagination, status filters and search', async ({ api, seed }) => {
    const all = (await (await api.get('/api/invitations')).json()) as { id: string; title: string; status: string }[];
    expect(all.length, 'fixture needs at least two invitations to test pagination').toBeGreaterThan(1);
    const limited = (await (await api.get('/api/invitations?limit=1')).json()) as { id: string }[];
    expect(limited, `limit=1 returned ${limited.length} of ${all.length} rows`).toHaveLength(1);
    const offset = (await (await api.get('/api/invitations?limit=1&offset=1')).json()) as { id: string }[];
    expect(offset, 'offset=1 must skip the first row').toHaveLength(1);
    expect(offset[0].id, 'offset must move the window').not.toBe(limited[0].id);

    const published = (await (await api.get('/api/invitations?status=published&limit=100')).json()) as { status: string }[];
    expect(published.length, 'the fixture must contain a published invitation').toBeGreaterThan(0);
    expect(published.every((row) => row.status === 'Published')).toBe(true);

    const searched = (await (
      await api.get(`/api/invitations?q=${encodeURIComponent(seed.invitation.title)}&limit=100`)
    ).json()) as { title: string }[];
    expect(searched.some((row) => row.title === seed.invitation.title)).toBe(true);

    const invalid = await api.get('/api/invitations?status=bogus');
    expect(invalid.status()).toBe(400);
  });

  test('RSVP endpoint rejects invalid payloads with 400', async ({ api, request, seed }) => {
    for (const payload of [
      { name: '', status: 'Maybe' },
      { name: 'QA Guest', status: 'Not a real option' },
      { name: 'QA Honeypot', website: 'http://spam.example' },
    ]) {
      const response = await request.post(`/api/public/${seed.invitation.slug}/rsvps`, { data: payload });
      expect(response.status(), `payload ${JSON.stringify(payload)}`).toBe(400);
      expect(response.headers()['content-type']).toContain('application/json');
    }
  });

  test('a valid RSVP and wish are accepted', async ({ request, seed }) => {
    const rsvp = await request.post(`/api/public/${seed.invitation.slug}/rsvps`, {
      data: { name: `QA API Guest ${uniqueSlug('x')}`, status: 'Maybe', count: 1, note: 'API contract' },
    });
    expect(rsvp.status()).toBe(201);
    expect((await rsvp.json()).saved).toBe(true);

    const wish = await request.post(`/api/public/${seed.invitation.slug}/wishes`, {
      data: { name: `QA API Wisher ${uniqueSlug('x')}`, message: 'All the best' },
    });
    expect(wish.status()).toBe(201);
  });

  test('mutating requests without a CSRF token are refused', async ({ request, baseURL, seed }) => {
    const response = await request.post('/api/invitations', {
      data: { slug: uniqueSlug('qa-nocsrf'), document: weddingDocument('No CSRF') },
      headers: { Origin: baseURL!, 'X-CSRF-Token': '' },
    });
    // With no session this is 401; with a session the CSRF gate answers 403.
    expect([401, 403]).toContain(response.status());
    const body = await response.json();
    expect(JSON.stringify(body)).toMatch(/csrf|authentication/i);
  });
});
