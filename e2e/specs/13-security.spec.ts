import { expect, test, uniqueSlug } from '../support/fixtures';
import { weddingDocument } from '../support/api';

/**
 * @security — non-destructive checks only: response headers, cookie flags,
 * CSRF enforcement, tenant isolation, escaped user content and secrets in the
 * client bundle. No scanner, no exploitation of third-party systems.
 */
test.describe('@security headers and cookies', () => {
  test('HTML routes ship a restrictive CSP and the standard headers', async ({ request }) => {
    for (const route of ['/index.html', '/dashboard.html', '/admin.html']) {
      const response = await request.get(route);
      const headers = response.headers();
      expect(headers['content-security-policy'], `${route} CSP`).toBeTruthy();
      expect(headers['content-security-policy']).toContain("default-src 'self'");
      expect(headers['content-security-policy'], 'CSP must not allow eval').not.toContain("'unsafe-eval'");
      expect(headers['content-security-policy']).toContain("frame-ancestors 'self'");
      expect(headers['x-content-type-options']).toBe('nosniff');
      expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin');
    }
  });

  test('session cookie is HttpOnly and SameSite=Lax', async ({ api, playwright, baseURL }) => {
    const context = await playwright.request.newContext({ baseURL });
    const response = await context.post('/api/auth/login', {
      data: { email: 'qa.owner@einvite.test', password: 'Qa-Passw0rd-2026' },
      headers: { Origin: baseURL! },
    });
    expect(response.ok()).toBe(true);
    const cookies = await context.storageState();
    const session = cookies.cookies.find((cookie) => cookie.name === 'einvite_session');
    expect(session, 'session cookie must be set').toBeTruthy();
    expect(session!.httpOnly).toBe(true);
    expect(session!.sameSite).toBe('Lax');
    await context.dispose();
    void api;
  });
});

test.describe('@security authorisation', () => {
  test('anonymous mutation is rejected with 401', async ({ request, baseURL }) => {
    const response = await request.post('/api/invitations', {
      data: { slug: uniqueSlug('qa-anon'), document: weddingDocument('Anonymous') },
      headers: { Origin: baseURL! },
    });
    expect(response.status()).toBe(401);
  });

  test('cross-tenant invitation read is a 404, not a 403 that confirms existence', async ({ api, seed }) => {
    const response = await api.get(`/api/invitations/${seed.otherInvitation.id}`);
    expect(response.status()).toBe(404);
  });

  test('unpublished invitations are not readable through the public API', async ({ request, seed }) => {
    const response = await request.get(`/api/public/${seed.emptyInvitation.slug}`);
    expect(response.status()).toBe(404);
  });
});

test.describe('@security injected content', () => {
  test('the check-in event name renders an HTML payload as text', async ({ browser, baseURL, seed }) => {
    const payload = `<img src=x onerror="window.__checkinXss=1"> QA Check-in ${uniqueSlug('xss')}`;
    const context = await browser.newContext({
      baseURL,
      storageState: seed.owner.storageState,
    });
    const page = await context.newPage();
    await page.addInitScript(() => {
      (window as unknown as { __checkinXss?: number }).__checkinXss = undefined;
    });
    let dialogFired = false;
    page.on('dialog', async (dialog) => {
      dialogFired = true;
      await dialog.dismiss();
    });
    await page.route(`**/api/invitations/${seed.invitation.id}`, async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.document.fields.names = payload;
      await route.fulfill({ response, json: body });
    });

    await page.goto(`/invitations/${seed.invitation.id}/checkin`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#eventName')).toContainText(payload);
    await expect(page.locator('#eventName img')).toHaveCount(0);
    const executed = await page.evaluate(() => (window as unknown as { __checkinXss?: number }).__checkinXss);
    expect(executed, 'check-in payload must not execute').toBeUndefined();
    expect(dialogFired).toBe(false);
    await context.close();
  });

  test('a script payload in the invitation title is rendered as text', async ({ page, api, request }) => {
    const payload = `<img src=x onerror="window.__xss=1"> QA XSS ${uniqueSlug('xss')}`;
    const created = await api.createInvitation(payload, uniqueSlug('qa-xss'));
    const detail = await api.get(`/api/invitations/${created.id}`);
    const body = await detail.json();
    await api.publish(created.id, body.document, body.updatedAt);

    let dialogFired = false;
    page.on('dialog', async (dialog) => {
      dialogFired = true;
      await dialog.dismiss();
    });

    const response = await request.get(`/i/${created.slug}`);
    const html = await response.text();
    expect(html).toContain('&lt;img');
    expect(html, 'raw payload must never be written into the document').not.toContain('<img src=x onerror=');

    await page.goto(`/i/${created.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#publicRoot').waitFor({ state: 'visible' });
    const executed = await page.evaluate(() => (window as unknown as { __xss?: number }).__xss);
    expect(executed, 'injected handler must not execute').toBeUndefined();
    expect(dialogFired).toBe(false);
  });

  test('the editor bundle ships no server secrets or API keys', async ({ request }) => {
    const bundle = await (await request.get('/bundle-index.js')).text();
    for (const pattern of [/sk-[A-Za-z0-9]{20,}/, /BEGIN (RSA |EC )?PRIVATE KEY/, /EINVITE_FIELD_ENCRYPTION_KEY/, /OPENAI_API_KEY\s*=/]) {
      expect(pattern.test(bundle), `bundle leaks ${pattern}`).toBe(false);
    }
  });
});
