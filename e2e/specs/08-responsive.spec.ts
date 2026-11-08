import path from 'node:path';
import { expect, horizontalOverflow, states, test, waitForAppReady } from '../support/fixtures';

const SCREENS = path.resolve(__dirname, '../../artifacts/playwright-e2e/screenshots/responsive');

const WIDTHS = [
  { width: 320, height: 568, label: '320-mobile-min' },
  { width: 375, height: 667, label: '375-mobile' },
  { width: 390, height: 844, label: '390-mobile' },
  { width: 768, height: 1024, label: '768-tablet' },
  { width: 1024, height: 768, label: '1024-tablet-landscape' },
  { width: 1440, height: 900, label: '1440-desktop' },
  { width: 844, height: 390, label: '844-mobile-landscape' },
];

/**
 * @responsive — every width must keep the document inside the viewport. A
 * horizontal document scrollbar is a hard layout failure, not a cosmetic one:
 * it hides content off-screen and breaks the 320 px baseline.
 */
test.describe('@responsive viewport sweep', () => {
  for (const screen of [
    { name: 'dashboard', path: '/dashboard.html', auth: true },
    { name: 'guests', path: '/guests.html', auth: true },
    { name: 'checkin', path: '/checkin.html', auth: true },
    { name: 'templates', path: '/templates.html', auth: false },
    { name: 'privacy', path: '/privacy.html', auth: false },
  ]) {
    test(`${screen.name} stays inside every viewport`, async ({ page }) => {
      for (const viewport of WIDTHS) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto(screen.path, { waitUntil: 'domcontentloaded' });
        await waitForAppReady(page);

        const overflow = await horizontalOverflow(page);
        await page.screenshot({
          path: path.join(SCREENS, `${screen.name}-${viewport.label}.png`),
          fullPage: false,
        });
        expect(
          overflow,
          `${screen.path} overflows horizontally by ${overflow}px at ${viewport.width}px`,
        ).toBeLessThanOrEqual(1);
      }
    });
  }

  test('guest invitation stays inside every viewport', async ({ page, seed }) => {
    for (const viewport of WIDTHS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
      await page.locator('#rsvp').waitFor({ state: 'visible' });

      const overflow = await horizontalOverflow(page);
      await page.screenshot({
        path: path.join(SCREENS, `guest-${viewport.label}.png`),
        fullPage: false,
      });
      expect(
        overflow,
        `guest page overflows horizontally by ${overflow}px at ${viewport.width}px`,
      ).toBeLessThanOrEqual(1);
    }
  });
});

test.describe('@responsive editor at narrow widths', () => {
  test.use({ storageState: states.owner() });

  for (const width of [320, 390, 768, 1440]) {
    test(`editor remains usable at ${width}px`, async ({ page, seed }) => {
      // A fresh page per width: the editor's canvas is heavy and the project
      // history records a headless GPU crash when resizing a heavy canvas page.
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`/index.html?invitation=${seed.invitation.id}`, { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
        timeout: 20_000,
      });

      const overflow = await horizontalOverflow(page);
      await page.screenshot({
        path: path.join(SCREENS, `editor-${width}.png`),
        fullPage: false,
      });
      expect(overflow, `editor overflows horizontally by ${overflow}px at ${width}px`).toBeLessThanOrEqual(1);
      await expect(page.locator('#documentTitle')).toContainText(seed.invitation.title);
    });
  }
});
