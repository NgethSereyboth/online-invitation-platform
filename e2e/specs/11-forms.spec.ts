import { accounts, expect, states, test } from '../support/fixtures';
import { uniqueSlug } from '../support/seed';

/**
 * @forms — boundary values, empty submits, max length, unicode and double
 * submission on the three forms a user actually types into.
 */
test.describe('@forms sign-in boundaries', () => {
  test('a 7-character password is rejected client-side', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(accounts.owner.email);
    await page.locator('#password').fill('short12');
    await page.locator('#loginBtn').click();
    await expect(page.locator('#authStatus')).toContainText(/8 characters/i);
  });

  test('a 200+ character password is rejected without signing in', async ({ page, seed }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(seed.victim.email);
    await page.locator('#password').fill('a'.repeat(240));
    await page.locator('#loginBtn').click();
    await expect(page.locator('#authStatus')).not.toBeEmpty();
    await expect(page.locator('#loginView')).toBeVisible();
  });

  test('unicode email is handled as data, not as markup', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill('ភ្ញៀវ@example.com');
    await page.locator('#password').fill('Qa-Passw0rd-2026');
    await page.locator('#loginBtn').click();
    // The browser may reject the address natively or the server may refuse it;
    // either way the user must stay signed out with the form intact.
    await expect(page.locator('#loginView')).toBeVisible();
    await expect(page.locator('#dashboardView')).toBeHidden();
    await expect(page.locator('#email')).toHaveValue('ភ្ញៀវ@example.com');
  });
});

test.describe('@forms create-invitation dialog', () => {
  test.use({ storageState: states.owner() });

  test('empty name is blocked by required validation', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('#newBtn').click();
    const dialog = page.locator('#createDialog');
    await expect(dialog).toHaveJSProperty('open', true);

    await page.locator('#newTitle').fill('');
    const valid = await page.locator('#createForm').evaluate((form) => (form as HTMLFormElement).checkValidity());
    expect(valid).toBe(false);
  });

  test('unicode title is accepted and appears on the dashboard', async ({ page, api }) => {
    const title = `ពិធីមង្គលការ QA ${uniqueSlug('uni')}`;
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('#newBtn').click();
    await page.locator('#newTitle').fill(title);
    await page.locator('#confirmCreate').click();

    await expect(page.locator('#createDialog')).toBeHidden({ timeout: 20_000 });

    const rows = (await (await api.get('/api/invitations')).json()) as { title: string }[];
    expect(rows.some((row) => row.title === title), 'server must store the unicode title verbatim').toBe(true);

    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible', timeout: 30_000 });
    await expect(page.locator('#inviteGrid').getByText(title, { exact: false })).toBeVisible({ timeout: 15_000 });
  });

  test('title input enforces its 120-character limit', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('#newBtn').click();
    await expect(page.locator('#newTitle')).toHaveAttribute('maxlength', '120');
    await expect(page.locator('#newTitle')).toHaveAttribute('required', '');
  });
});
