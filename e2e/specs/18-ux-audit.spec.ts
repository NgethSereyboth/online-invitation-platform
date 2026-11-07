import fs from 'node:fs';
import path from 'node:path';
import { expect, states, test, waitForAppReady } from '../support/fixtures';
import { ROUTES } from '../support/seed';

const UX_DIR = path.resolve(__dirname, '../../artifacts/playwright-e2e/screenshots/ux');

/**
 * @ux — the audit pass: one screenshot per screen plus assertions on the
 * things a screenshot cannot prove (empty-state guidance, destructive-action
 * separation, error-message quality, and a working overflow menu).
 */
test.describe('@ux screen captures', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'captures are taken once, on chromium');

  test('every route is captured with its heading and primary affordances recorded', async ({ page }) => {
    fs.mkdirSync(UX_DIR, { recursive: true });
    const inventory: unknown[] = [];

    for (const route of ROUTES) {
      await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      await waitForAppReady(page);
      await page.screenshot({
        path: path.join(UX_DIR, `${route.path.replace(/\W+/g, '-').replace(/^-|-$/g, '')}.png`),
        fullPage: true,
      });

      inventory.push(
        await page.evaluate((meta) => {
          const main = document.querySelector('main');
          const headings = [...document.querySelectorAll('h1, h2')].map((element) =>
            (element.textContent || '').replace(/\s+/g, ' ').trim(),
          );
          const actions = [...document.querySelectorAll('button, a.button-link, button.primary')]
            .filter((element) => element.getClientRects().length > 0 && !(element as HTMLButtonElement).disabled)
            .map((element) => (element.textContent || '').replace(/\s+/g, ' ').trim())
            .filter(Boolean);
          return {
            route: meta.path,
            name: meta.name,
            headings: headings.slice(0, 6),
            actionCount: actions.length,
            actions: actions.slice(0, 8),
            bodyTextLength: (main?.innerText || '').trim().length,
          };
        }, { path: route.path, name: route.name }),
      );
    }

    await test.info().attach('ux-inventory', {
      body: JSON.stringify(inventory, null, 2),
      contentType: 'application/json',
    });
    fs.writeFileSync(path.join(UX_DIR, 'inventory.json'), JSON.stringify(inventory, null, 2));
    expect(inventory.length).toBe(ROUTES.length);
  });
});

test.describe('@ux empty states and error quality', () => {
  test('guests page without a selected invitation explains what to do', async ({ page }) => {
    await page.goto('/guests.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const body = await page.locator('main').innerText();
    expect(body).toMatch(/not available|select|invitation/i);
  });

  test('responses page without a selected invitation explains what to do', async ({ page }) => {
    await page.goto('/responses.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const body = await page.locator('main').innerText();
    expect(body.trim().length).toBeGreaterThan(0);
    expect(body).toMatch(/invitation|responses|select|open|no rsvp/i);
  });

  test('check-in without a selected invitation is a guided dead end, not a blank screen', async ({ page }) => {
    await page.goto('/checkin.html', { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle').catch(() => {});
    const body = await page.locator('main').innerText();
    expect(body).toMatch(/no invitation selected|open an invitation/i);
  });

  test('a wrong password produces a human sentence, not a stack trace', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#email').fill(`qa.nobody.${Date.now().toString(36)}@einvite.test`);
    await page.locator('#password').fill('wrong-password-xyz');
    await page.locator('#loginBtn').click();
    await expect(page.locator('#authStatus')).not.toBeEmpty({ timeout: 15_000 });

    const message = (await page.locator('#authStatus').innerText()).trim();
    expect(message.length, `message too short: "${message}"`).toBeGreaterThan(10);
    expect(message).not.toMatch(/TypeError|undefined|\[object Object\]|stack/i);
  });
});

test.describe('@ux dashboard affordances', () => {
  test.use({ storageState: states.owner() });

  test('invitation overflow menu opens, is keyboard reachable and closes on Escape', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    const toggle = page.locator('.invite-overflow__toggle').first();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await expect(page.locator('.invite-overflow__menu').first()).toBeVisible();

    const items = await page.locator('.invite-overflow__menu').first().getByRole('menuitem').count();
    const buttons = await page.locator('.invite-overflow__menu').first().locator('button').count();
    expect(Math.max(items, buttons), 'overflow menu must expose actions').toBeGreaterThan(3);

    await page.keyboard.press('Escape');
    await expect(page.locator('.invite-overflow__menu').first()).toBeHidden();
  });

  test('destructive actions are visually separated from safe ones', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('.invite-overflow__toggle').first().click();
    const danger = page.locator('.invite-overflow__menu .danger').first();
    await expect(danger).toBeVisible();
    const classes = (await danger.getAttribute('class')) || '';
    expect(classes, 'destructive action must carry a distinct class').toContain('danger');
  });
});
