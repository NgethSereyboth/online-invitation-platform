import { expect, states, test, waitForAppReady } from '../support/fixtures';
import { ROUTES } from '../support/seed';

/**
 * @smoke — route inventory: every shipped page must load, keep a title, render a
 * landmark, and raise no uncaught exception. Signed out is the harder case for
 * several routes (the app used to emit 37 doomed /api requests on a signed-out
 * shell load), so console/network cleanliness is asserted on this pass.
 */
test.describe('@smoke route inventory (signed out)', () => {
  for (const route of ROUTES) {
    test(`${route.path} loads cleanly signed out`, async ({ page, diag }) => {
      const response = await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      await waitForAppReady(page);

      expect(response, `no response for ${route.path}`).not.toBeNull();
      expect(response!.status(), `${route.path} HTTP status`).toBeLessThan(400);

      await expect(page).toHaveTitle(/\S/);
      const htmlLang = await page.locator('html').getAttribute('lang');
      expect(htmlLang, '<html lang> must be declared').toMatch(/^(en|km)/);

      const main = page.locator('main').first();
      await expect(main).toBeVisible();

      // A page with no heading at all is a hierarchy defect (WCAG 1.3.1/2.4.6).
      const headings = await page.locator('h1, h2, h3').count();
      expect(headings, `${route.path} heading count`).toBeGreaterThan(0);

      diag.assertClean({ console: true });
    });
  }

  test('unknown route returns the server 404, not the app shell', async ({ page }) => {
    const response = await page.goto('/this-route-does-not-exist', { waitUntil: 'domcontentloaded' });
    expect(response!.status()).toBe(404);
  });
});

test.describe('@smoke route inventory (signed in)', () => {
  test.use({ storageState: states.owner() });

  for (const route of ROUTES) {
    test(`${route.path} loads cleanly with a session`, async ({ page, diag }) => {
      const response = await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      await waitForAppReady(page);

      expect(response!.status()).toBeLessThan(400);
      await expect(page).toHaveTitle(/\S/);
      await expect(page.locator('main').first()).toBeVisible();
      diag.assertClean();
    });
  }
});
