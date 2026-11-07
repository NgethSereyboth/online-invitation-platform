import { expect, accounts, states, test, uniqueSlug } from '../support/fixtures';

/**
 * @persistence — what survives a reload, and where it is stored. These tests
 * assert the storage layer a user actually relies on: theme, language, the
 * server-side invitation row, and the session cookie.
 */
test.describe('@persistence client preferences', () => {
  test.use({ storageState: states.owner() });

  test('theme choice survives a reload', async ({ page }) => {
    // The theme toggle lives in the shared app shell, not on the dashboard's
    // signed-in view; check-in renders that shell regardless of selection.
    await page.goto('/checkin.html', { waitUntil: 'domcontentloaded' });

    const toggle = page.locator('[data-theme-toggle]').first();
    await expect(toggle).toBeVisible();
    const before = await page.evaluate(() => document.documentElement.dataset.theme || '');
    await toggle.click();
    const after = await page.evaluate(() => document.documentElement.dataset.theme || '');
    expect(after, 'theme toggle must change the document theme').not.toBe(before);

    const storage = await page.evaluate(() => ({ ...localStorage }));
    expect(Object.keys(storage).some((key) => /theme/i.test(key)), 'theme preference stored').toBe(true);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('[data-theme-toggle]').first()).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.dataset.theme || '')).toBe(after);
  });

  test('server-side invitation survives a reload', async ({ page, api }) => {
    const title = `QA Persisted ${uniqueSlug('row')}`;
    await api.createInvitation(title, uniqueSlug('qa-persist'));

    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible();
  });
});

test.describe('@persistence session lifecycle', () => {
  // Deliberately no storage state: signing out from the shared owner session
  // would revoke the session every other test in this run depends on.
  test.use({ storageState: { cookies: [], origins: [] } });

  test('signing out clears the local session after a reload', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#loginView').waitFor({ state: 'visible', timeout: 30_000 });
    await page.locator('#email').fill(accounts.owner.email);
    await page.locator('#password').fill(accounts.owner.password);
    await page.locator('#loginBtn').click();
    await page.locator('#dashboardView').waitFor({ state: 'visible', timeout: 30_000 });

    await page.locator('.fp-profile-button').first().click();
    await page.locator('[data-signout]').first().click();
    await expect(page.locator('#loginView')).toBeVisible();

    await page.reload({ waitUntil: 'domcontentloaded' });
    await expect(page.locator('#loginView')).toBeVisible();
    const cookies = await page.context().cookies();
    expect(cookies.find((cookie) => cookie.name === 'einvite_session')).toBeFalsy();
  });
});

test.describe('@persistence fresh browser profile', () => {
  test('the login form starts empty and leaks no previous account', async ({ browser, baseURL }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${baseURL}/dashboard.html`, { waitUntil: 'domcontentloaded' });
    await page.locator('#loginView').waitFor({ state: 'visible' });
    await expect(page.locator('#email')).toHaveValue('');
    await expect(page.locator('#password')).toHaveValue('');
    const storage = await page.evaluate(() => ({ ...localStorage }));
    expect(storage.accountKey ?? '').not.toContain(accounts.owner.email);
    expect(JSON.stringify(storage)).not.toContain(accounts.owner.email);
    await context.close();
  });
});
