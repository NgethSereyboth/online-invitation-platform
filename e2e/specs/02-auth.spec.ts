import { expect, accounts, states, test } from '../support/fixtures';

/**
 * @auth @smoke — session lifecycle through the real sign-in form, plus the
 * signed-out posture of a session-only page. Storage state is used everywhere
 * else, so these are the only tests that exercise the login form itself.
 *
 * Login-failure tests use the per-run `victim` account: five failed attempts
 * lock an account for 15 minutes, and the owner account must stay usable.
 */
test.describe('@auth sign-in form', () => {
  test('empty submit reports a validation error', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#loginView')).toBeVisible();

    await page.locator('#loginBtn').click();
    await expect(page.locator('#authStatus')).toContainText(/valid email/i);
    await expect(page.locator('#loginView')).toBeVisible();
  });

  test('invalid email format is blocked by native validation', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#loginView')).toBeVisible();
    const requests: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/auth/login')) requests.push(request.url());
    });

    await page.locator('#email').fill('not-an-email');
    await page.locator('#password').fill('Qa-Passw0rd-2026');

    // type=email makes the field invalid before any script runs.
    const validity = await page.locator('#email').evaluate((input) => (input as HTMLInputElement).checkValidity());
    expect(validity, 'type=email must reject "not-an-email"').toBe(false);
    const message = await page
      .locator('#email')
      .evaluate((input) => (input as HTMLInputElement).validationMessage);
    expect(message.length, 'browser must explain the invalid address').toBeGreaterThan(0);

    await page.locator('#loginBtn').click();
    await expect(page.locator('#loginView')).toBeVisible();
    expect(requests, 'no login request should leave the browser for invalid input').toEqual([]);
  });

  test('wrong password shows a generic refusal and does not sign in', async ({ page, seed }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(seed.victim.email);
    await page.locator('#password').fill('definitely-the-wrong-password');
    await page.locator('#loginBtn').click();

    await expect(page.locator('#authStatus')).toContainText(/incorrect|invalid|failed/i, { timeout: 15_000 });
    await expect(page.locator('#loginView')).toBeVisible();
    await expect(page.locator('#dashboardView')).toBeHidden();
  });

  test('valid credentials open the dashboard', async ({ page, context }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(accounts.owner.email);
    await page.locator('#password').fill(accounts.owner.password);
    await page.locator('#loginBtn').click();

    await expect(page.locator('#dashboardView')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('#loginView')).toBeHidden();
    await expect(page.locator('#inviteGrid .invite-card').first()).toBeVisible();

    const session = (await context.cookies()).find((cookie) => cookie.name === 'einvite_session');
    expect(session, 'session cookie set by sign-in').toBeTruthy();
    expect(session!.httpOnly, 'session cookie must be HttpOnly').toBe(true);
    expect(session!.sameSite).toBe('Lax');
  });

  test('sign out returns to the sign-in card and clears the session', async ({ page, context }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(accounts.owner.email);
    await page.locator('#password').fill(accounts.owner.password);
    await page.locator('#loginBtn').click();
    await expect(page.locator('#dashboardView')).toBeVisible({ timeout: 20_000 });

    // The dashboard hides the header's direct sign-out button in favour of the
    // profile popover, so the journey is: avatar → Sign out.
    await page.locator('.fp-profile-button').first().click();
    await page.locator('[data-signout]').first().click();
    await expect(page.locator('#loginView')).toBeVisible();
    await expect(page.locator('#dashboardView')).toBeHidden();

    const session = (await context.cookies()).find((cookie) => cookie.name === 'einvite_session');
    expect(session, 'session cookie cleared on sign out').toBeFalsy();
  });
});

test.describe('@auth signed-out access', () => {
  test('session-only pages expose no account data without a session', async ({ page, context, seed }) => {
    await page.goto('/account.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.locator('#accountEmail')).not.toHaveText(seed.owner.email);
    const cookies = await context.cookies();
    expect(cookies.find((cookie) => cookie.name === 'einvite_session')).toBeFalsy();
  });

  test('admin console denies a signed-out visitor', async ({ page }) => {
    await page.goto('/admin.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const body = await page.locator('main').innerText();
    expect(body).not.toMatch(/Users\s*\d+/i);
    expect(body.trim().length).toBeGreaterThan(0);
  });
});

test.describe('@auth storage state reuse', () => {
  test.use({ storageState: states.owner() });

  test('a stored session opens the dashboard without signing in', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();
    await expect(page.locator('#loginView')).toBeHidden();
  });
});
