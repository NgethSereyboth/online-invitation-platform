import AxeBuilder from '@axe-core/playwright';
import { expect, states, test, waitForAppReady } from '../support/fixtures';
import { ROUTES } from '../support/seed';

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

async function scan(page: import('@playwright/test').Page, label: string) {
  // Reveal animations fade content in; scanning mid-animation reports transient
  // contrast failures for text that is already accessible once settled.
  await page.evaluate(async () => {
    const finiteAnimations = document.getAnimations().filter((animation) => {
      const timing = animation.effect?.getComputedTiming();
      return timing != null && Number.isFinite(timing.endTime);
    });
    await Promise.all(finiteAnimations.map((animation) => animation.finished.catch(() => undefined)));
  });
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const summary = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    nodes: violation.nodes.map((node) => node.target.join(' ')).slice(0, 5),
  }));
  await test.info().attach(`axe-${label}`, {
    body: JSON.stringify({ violations: summary, passes: results.passes.length }, null, 2),
    contentType: 'application/json',
  });
  expect(summary, `axe violations on ${label}: ${JSON.stringify(summary, null, 2)}`).toEqual([]);
  return results;
}

/**
 * @a11y — WCAG 2.2 AA automated coverage. axe-core is not a substitute for the
 * keyboard/manual-equivalent pass in 17-keyboard.spec.ts; it catches the
 * machine-checkable rules and nothing more.
 */
test.describe('@a11y axe scans', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'axe runs once, on chromium');

  for (const route of ROUTES) {
    test(`${route.path} has no axe violations`, async ({ page }) => {
      await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      await waitForAppReady(page);
      await page.evaluate(() => document.fonts.ready);
      await scan(page, route.path.replace(/[^a-z0-9]+/gi, '-'));
    });
  }

  test('published guest invitation has no axe violations', async ({ page, seed }) => {
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#publicRoot').waitFor({ state: 'visible' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    await page.evaluate(() => document.fonts.ready);
    await scan(page, 'guest-published');
  });

  test('mobile guest invitation has no axe violations', async ({ page, seed }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#publicRoot').waitFor({ state: 'visible' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    await scan(page, 'guest-mobile');
  });
});

test.describe('@a11y dialog states', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'axe runs once, on chromium');
  test.use({ storageState: states.owner() });

  test('create-invitation dialog has no axe violations', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('#newBtn').click();
    await expect(page.locator('#createDialog')).toHaveJSProperty('open', true);
    await scan(page, 'dashboard-create-dialog');
  });

  test('create-invitation dialog traps focus and restores it', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });

    const trigger = page.locator('#newBtn');
    await trigger.click();
    const dialog = page.locator('#createDialog');
    await expect(dialog).toHaveJSProperty('open', true);

    const focusInside = await page.evaluate(() =>
      document.querySelector('#createDialog')!.contains(document.activeElement),
    );
    expect(focusInside, 'focus must move into the open modal').toBe(true);

    for (let i = 0; i < 12; i += 1) await page.keyboard.press('Tab');
    const stillInside = await page.evaluate(() =>
      document.querySelector('#createDialog')!.contains(document.activeElement),
    );
    expect(stillInside, 'focus escaped the modal while tabbing').toBe(true);

    await page.keyboard.press('Escape');
    await expect(dialog).not.toHaveJSProperty('open', true);
    await expect(trigger).toBeFocused();
  });
});
