import { expect, states, test, waitForAppReady } from '../support/fixtures';

/**
 * @visual — screenshots are only meaningful on deterministic screen states.
 * Routes whose content is user-generated (dashboard, guests, responses) get
 * either a mask over the changing region or no full-page baseline at all.
 */
const FREEZE = `*,*::before,*::after{animation:none !important;transition:none !important;caret-color:transparent !important}`;

function nonceOf(response: import('@playwright/test').Response | null): string {
  // The nonce is issued per HTML response, so it must come from this
  // navigation's CSP header. Dashboard pages have no inline <script nonce>
  // to copy, and a second request would receive a different nonce.
  const csp = response?.headers()['content-security-policy'] || '';
  return /'nonce-([^']+)'/.exec(csp)?.[1] || '';
}

async function settle(page: import('@playwright/test').Page, nonce: string, extraCss = '') {
  await waitForAppReady(page);
  await page.evaluate(({ freeze, extra, nonce }) => {
    // The app ships a nonce-based style-src CSP; page.addStyleTag() injects an
    // un-nonced <style> and is blocked. Reuse the navigation response nonce.
    const style = document.createElement('style');
    if (nonce) style.setAttribute('nonce', nonce);
    style.textContent = freeze + extra;
    document.head.append(style);
  }, { freeze: FREEZE, extra: extraCss, nonce });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
}

test.describe('@visual static screens', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'baselines are captured on chromium');

  const screens: { name: string; path: string }[] = [
    { name: 'privacy', path: '/privacy.html' },
    { name: 'reset', path: '/reset.html' },
    { name: 'verify', path: '/verify.html' },
    { name: 'templates', path: '/templates.html' },
    { name: 'guests-empty', path: '/guests.html' },
    { name: 'responses-empty', path: '/responses.html' },
    { name: 'account-signed-out', path: '/account.html' },
  ];

  for (const screen of screens) {
    test(`${screen.name} matches its baseline`, async ({ page }) => {
      const response = await page.goto(screen.path, { waitUntil: 'domcontentloaded' });
      await settle(page, nonceOf(response));
      await expect(page).toHaveScreenshot(`${screen.name}.png`, {
        fullPage: true,
        mask: [page.locator('.guest-demo-badge'), page.locator('#accountEmail')],
      });
    });
  }

  test('dashboard matches its baseline signed out', async ({ page }) => {
    const response = await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await settle(page, nonceOf(response));
    // Signed out: the auth card is deterministic.
    await expect(page.locator('#loginView')).toBeVisible();
    await expect(page).toHaveScreenshot('dashboard-signed-out.png', { fullPage: true });
  });

  test('published guest invitation matches its baseline', async ({ page, seed }) => {
    const response = await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    await settle(page, nonceOf(response));
    await expect(page).toHaveScreenshot('guest-published.png', {
      fullPage: true,
      mask: [page.locator('.guest-demo-badge')],
    });
  });
});

test.describe('@visual independently changing components', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'baselines are captured on chromium');
  test.use({ storageState: states.owner() });

  test('dashboard shell is stable when invitation cards are masked', async ({ page }) => {
    const response = await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('.invite-card').first().waitFor({ state: 'visible' });
    // The grid grows with the seed and with every suite run. Capture only the
    // stable shell header/toolbar strip; the variable card area is intentionally
    // covered by separate component tests.
    await page.setViewportSize({ width: 1440, height: 240 });
    // The i18n and theme bootstraps inject the account/language/appearance
    // cluster after first paint, and its position depends on which account and
    // role the seed produced. Hide it (visibility keeps the layout box) so the
    // shell baseline covers only deterministic chrome.
    await settle(page, nonceOf(response), 'header .language-switch,header .ui-theme,#accountName,#logoutBtn,#adminBtn,#designerBtn{visibility:hidden !important}');
    // Viewport-only: the grid grows as the suite creates invitations, so a
    // full-page capture is not a stable baseline across runs.
    await expect(page).toHaveScreenshot('dashboard-shell.png', {
      mask: [page.locator('#inviteGrid')],
    });
  });

  test('create-invitation dialog matches its baseline', async ({ page }) => {
    const response = await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    await page.locator('#newBtn').click();
    await expect(page.locator('#createDialog')).toHaveJSProperty('open', true);
    await settle(page, nonceOf(response));
    await expect(page.locator('#createDialog')).toHaveScreenshot('create-dialog.png', {
      animations: 'disabled',
      mask: [page.locator('#templateChoices')],
    });
  });
});
