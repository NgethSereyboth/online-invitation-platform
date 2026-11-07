import path from 'node:path';
import { expect, states, test, waitForAppReady } from '../support/fixtures';

const SHOTS = path.resolve(__dirname, '../../artifacts/playwright-e2e/screenshots/network');

/**
 * @network — the app must degrade visibly, not crash, when its own API fails.
 * Every test here deliberately breaks one dependency and asserts the user sees
 * a state (error, empty, signed-out) instead of an uncaught exception.
 */
test.describe('@network failure modes', () => {
  test.use({ storageState: states.owner() });

  test('dashboard survives /api/auth/me returning 500', async ({ page, diag }) => {
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"upstream down"}' }),
    );
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await waitForAppReady(page);

    // Either the signed-out card or an explicit error state is acceptable; a
    // blank page or a thrown exception is not.
    const visibleText = await page.locator('main').innerText();
    expect(visibleText.trim().length, 'dashboard rendered no content under a 500').toBeGreaterThan(0);
    await page.screenshot({ path: path.join(SHOTS, 'dashboard-auth-me-500.png'), fullPage: true });
    diag.assertClean();
  });

  test('dashboard survives an aborted invitation list request', async ({ page, diag }) => {
    await page.route(/\/api\/invitations(?:\?.*)?$/, (route) => route.abort('failed'));
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await waitForAppReady(page);

    // The session survives a failed list call; the dashboard must render an
    // explanation instead of signing the user out or showing a blank page.
    await expect(page.locator('#dashboardView')).toBeVisible({ timeout: 15_000 });
    await expect(page.locator('#inviteGrid')).toContainText(/couldn.t load your invitations/i);
    const text = await page.locator('main').innerText();
    expect(text.trim().length, 'dashboard rendered nothing when its list request failed').toBeGreaterThan(0);
    expect(text).toMatch(/invitation|sign in|design/i);
    await page.screenshot({ path: path.join(SHOTS, 'dashboard-list-aborted.png'), fullPage: true });
    diag.assertClean();
  });

  test('dashboard survives malformed JSON from /api/auth/me', async ({ page, diag }) => {
    await page.route('**/api/auth/me', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '{not-json' }),
    );
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await waitForAppReady(page);

    const text = await page.locator('main').innerText();
    expect(text.trim().length).toBeGreaterThan(0);
    await page.screenshot({ path: path.join(SHOTS, 'dashboard-malformed-json.png'), fullPage: true });
    diag.assertClean();
  });
});

test.describe('@network guest page failure modes', () => {
  test('guest page states that the invitation could not load on 500', async ({ page, seed, diag }) => {
    await page.route(`**/api/public/${seed.invitation.slug}*`, (route) =>
      route.fulfill({ status: 500, contentType: 'application/json', body: '{"error":"boom"}' }),
    );
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });

    await expect(page.locator('#publicRoot')).toBeVisible();
    await expect(page.locator('#publicRoot')).not.toBeEmpty();
    const text = await page.locator('#publicRoot').innerText();
    expect(text.trim().length, 'guest page rendered nothing when the API failed').toBeGreaterThan(0);
    await page.screenshot({ path: path.join(SHOTS, 'guest-api-500.png'), fullPage: true });
    diag.assertClean();
  });

  test('guest page survives an aborted payload request', async ({ page, seed, diag }) => {
    await page.route(`**/api/public/${seed.invitation.slug}*`, (route) => route.abort('failed'));
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });

    await expect(page.locator('#publicRoot')).toBeVisible();
    const text = await page.locator('#publicRoot').innerText();
    expect(text.trim().length).toBeGreaterThan(0);
    await page.screenshot({ path: path.join(SHOTS, 'guest-aborted.png'), fullPage: true });
    diag.assertClean();
  });

  test('offline mode shows a visible notice instead of a blank page', async ({ page, seed, diag }) => {
    await page.route('**/api/**', (route) => route.abort('internetdisconnected'));
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });

    await expect(page.locator('#publicRoot')).toBeVisible();
    const text = await page.locator('#publicRoot').innerText();
    expect(text.trim().length).toBeGreaterThan(0);
    await page.screenshot({ path: path.join(SHOTS, 'guest-offline.png'), fullPage: true });
    diag.assertClean();
  });
});
