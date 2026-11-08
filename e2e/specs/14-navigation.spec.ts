import { expect, states, test } from '../support/fixtures';

/**
 * @navigation — deep links, the closed page-alias map, history, refresh and
 * multi-tab behaviour. A direct URL is how most links arrive (chat, email,
 * QR code), so an alias that 404s is a release blocker.
 */
test.describe('@navigation page aliases', () => {
  for (const alias of ['/dashboard', '/templates', '/guests', '/designer', '/account']) {
    test(`${alias} resolves to its page`, async ({ page }) => {
      const response = await page.goto(alias, { waitUntil: 'domcontentloaded' });
      expect(response!.status(), `${alias} must be a direct 200`).toBe(200);
      expect(new URL(page.url()).pathname).toBe(alias);
      await expect(page).toHaveTitle(/\S/);
    });
  }

  test('an unknown page is a 404 and does not render the app shell', async ({ page }) => {
    const response = await page.goto('/no-such-page', { waitUntil: 'domcontentloaded' });
    expect(response!.status()).toBe(404);
    await expect(page.locator('body')).not.toContainText('Your designs');
  });
});

test.describe('@navigation history and refresh', () => {
  test.use({ storageState: states.owner() });

  test('back and forward restore the previous screen', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();

    await page.goto('/templates.html', { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveTitle(/Template Studio/i);

    await page.goBack({ waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/dashboard\.html/);

    await page.goForward({ waitUntil: 'domcontentloaded' });
    await expect(page).toHaveURL(/templates\.html/);
  });

  test('refresh keeps the session and the dashboard state', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();
    const cardsBefore = await page.locator('#inviteGrid .invite-card').count();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();
    await expect(page.locator('#inviteGrid .invite-card')).toHaveCount(cardsBefore);
  });

  test('two tabs share the session without breaking each other', async ({ context, seed }) => {
    const first = await context.newPage();
    await first.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(first.locator('#dashboardView')).toBeVisible();

    const second = await context.newPage();
    await second.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(second.locator('#dashboardView')).toBeVisible();

    await second.close();
    await expect(first.locator('#dashboardView')).toBeVisible();
    await expect(first.getByText(seed.invitation.title, { exact: false }).first()).toBeVisible();
  });

  test('deep link opens the editor for the requested invitation', async ({ page, seed }) => {
    await page.goto(`/index.html?invitation=${encodeURIComponent(seed.invitation.id)}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    await expect(page.locator('#documentTitle')).toContainText(seed.invitation.title);
    expect(await page.evaluate(() => localStorage.getItem('sovan-active-invite'))).toBe(seed.invitation.id);
  });
});
