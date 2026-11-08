import path from 'node:path';
import { expect, states, test } from '../support/fixtures';

const SHOTS = path.resolve(__dirname, '../../artifacts/playwright-e2e/screenshots/i18n');

/**
 * @i18n — the product ships an English/Khmer UI. This suite covers the two
 * switchers that actually exist (shell switcher and guest invitation proxy),
 * persistence across reload, the Khmer date format, and text overflow.
 * Arabic/Hebrew RTL is NOT supported by the product, so no RTL case exists:
 * that is a scope statement, not a skipped test.
 */
test.describe('@i18n shell language', () => {
  test.use({ storageState: states.owner() });

  test('switching to Khmer sets html lang and renders Khmer copy', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });

    await page.locator('[data-lang="km"]:visible').first().click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'km');
    await expect(page.getByText('ការរចនា', { exact: false }).first()).toBeVisible();
    await expect(page.locator('[data-lang="km"]:visible').first()).toHaveAttribute('aria-pressed', 'true');

    await page.screenshot({ path: path.join(SHOTS, 'dashboard-km.png'), fullPage: true });

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, 'Khmer dashboard overflows horizontally').toBeLessThanOrEqual(1);
  });

  test('language choice survives a reload', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('[data-lang="km"]:visible').first().click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'km');

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await expect(page.locator('html')).toHaveAttribute('lang', 'km');
    const stored = await page.evaluate(() => localStorage.getItem('einvite-lang'));
    expect(stored, 'language preference persisted in localStorage').toBeTruthy();
  });

  test('switching back to English restores lang and copy', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('[data-lang="km"]:visible').first().click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'km');
    await page.locator('[data-lang="en"]:visible').first().click();
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
    await expect(page.getByText('Your designs', { exact: false }).first()).toBeVisible();
  });
});

test.describe('@i18n guest invitation', () => {
  test('guest topbar language switch changes copy, lang and Khmer date', async ({ page, seed }) => {
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });

    // The /i/<slug> guest page injects the switch into the topbar. The
    // renderer's in-page copy is deliberately hidden; the Python contract
    // test tests/lt_4_1_language_switch_test.py enforces that split.
    const switchKm = page.locator('header.guest-topbar .language-switch [data-lang="km"]');
    await expect(switchKm, 'guest language switch must be reachable by a guest').toBeVisible();
    await expect(switchKm).toHaveAttribute('aria-pressed', 'false');
    await switchKm.click();

    await expect(page.locator('#publicRoot')).toHaveAttribute('data-language', 'km');
    await expect(page.locator('html')).toHaveAttribute('lang', 'km');
    await expect(switchKm).toHaveAttribute('aria-pressed', 'true');

    const khmerText = await page.locator('#publicRoot').innerText();
    const khmerDigits = /[០-៩]/;
    expect(khmerDigits.test(khmerText), 'Khmer guest page renders no Khmer numerals/date').toBe(true);
    await page.screenshot({ path: path.join(SHOTS, 'guest-km.png'), fullPage: true });

    await page.locator('header.guest-topbar .language-switch [data-lang="en"]').click();
    await expect(page.locator('#publicRoot')).toHaveAttribute('data-language', 'en');
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  });

  test('guest page keeps its layout at 320px in Khmer', async ({ page, seed }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    await expect(page.locator('header.guest-topbar .language-switch [data-lang="km"]')).toBeVisible();
    await page.locator('header.guest-topbar .language-switch [data-lang="km"]').click();
    await expect(page.locator('#publicRoot')).toHaveAttribute('data-language', 'km');

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    await page.screenshot({ path: path.join(SHOTS, 'guest-km-320.png'), fullPage: false });
    expect(overflow, `Khmer guest page overflows by ${overflow}px at 320`).toBeLessThanOrEqual(1);
  });
});
