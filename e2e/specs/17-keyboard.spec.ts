import { expect, states, test, waitForAppReady } from '../support/fixtures';

/**
 * @a11y @keyboard — the manual-equivalent checks axe cannot do: skip link,
 * tab order, visible focus, label association and heading hierarchy.
 */
test.describe('@a11y keyboard traversal', () => {
  test('skip link is the first stop and jumps to main', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#loginView').waitFor({ state: 'visible' });
    await page.keyboard.press('Tab');

    const first = await page.evaluate(() => ({
      tag: document.activeElement?.tagName,
      href: (document.activeElement as HTMLAnchorElement)?.getAttribute('href'),
      text: (document.activeElement as HTMLElement)?.innerText?.trim(),
    }));
    expect(first.tag).toBe('A');
    expect(first.href).toBe('#main');
    expect(first.text).toMatch(/skip to content/i);

    await page.keyboard.press('Enter');
    const focused = await page.evaluate(() => document.activeElement?.id);
    expect(focused).toBe('main');
  });

  test('tab order moves forward and does not get stuck', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    const seen: string[] = [];
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press('Tab');
      seen.push(
        await page.evaluate(() => {
          const element = document.activeElement as HTMLElement | null;
          if (!element) return 'none';
          return `${element.tagName}#${element.id || ''}.${(element.className || '').toString().split(' ')[0]}`;
        }),
      );
    }
    const unique = new Set(seen);
    expect(unique.size, `focus cycled instead of advancing: ${seen.join(' → ')}`).toBeGreaterThan(6);
    expect(seen).not.toContain('BODY#.undefined');
  });

  test('every tab stop paints a visible focus indicator', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    const failures: string[] = [];
    for (let i = 0; i < 12; i += 1) {
      await page.keyboard.press('Tab');
      const info = await page.evaluate(() => {
        const element = document.activeElement as HTMLElement;
        const style = getComputedStyle(element);
        return {
          target: `${element.tagName}#${element.id || ''}`,
          outlineStyle: style.outlineStyle,
          outlineWidth: style.outlineWidth,
          boxShadow: style.boxShadow,
        };
      });
      // A tab press past the last control parks focus on <body>; that is the
      // browser's cycle reset, not a control missing its focus ring.
      if (info.target === 'BODY#' || info.target === 'HTML#') continue;
      const hasRing =
        (info.outlineStyle !== 'none' && parseFloat(info.outlineWidth) > 0) || info.boxShadow !== 'none';
      if (!hasRing) failures.push(JSON.stringify(info));
    }
    expect(failures, `tab stops without a visible focus ring: ${failures.join(', ')}`).toEqual([]);
  });
});

test.describe('@a11y form labels and heading order', () => {
  test('dashboard sign-in controls have accessible names', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    const unnamed = await page.evaluate(() => {
      const controls = [...document.querySelectorAll('input, select, textarea')].filter((element) => {
        const style = getComputedStyle(element);
        return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0;
      });
      return controls
        .filter((element) => {
          const labels = (element as HTMLInputElement).labels;
          return !(
            (labels && labels.length > 0) ||
            element.getAttribute('aria-label') ||
            element.getAttribute('aria-labelledby') ||
            element.getAttribute('title')
          );
        })
        .map((element) => `${element.tagName}#${element.id || ''}`);
    });
    expect(unnamed, `controls with no accessible name: ${unnamed.join(', ')}`).toEqual([]);
  });

  test('guest list inputs have accessible names (sr-only labels)', async ({ page }) => {
    await page.goto('/guests.html', { waitUntil: 'domcontentloaded' });
    const unnamed = await page.evaluate(() => {
      return [...document.querySelectorAll('#addForm input')]
        .filter((element) => {
          const labels = (element as HTMLInputElement).labels;
          return !(labels && labels.length > 0) && !element.getAttribute('aria-label');
        })
        .map((element) => `${element.tagName}#${element.id || ''}`);
    });
    expect(unnamed, `guest-list controls with no accessible name: ${unnamed.join(', ')}`).toEqual([]);
  });

  test('heading hierarchy never skips a level', async ({ page }) => {
    const routes = ['/dashboard.html', '/guests.html', '/responses.html', '/checkin.html', '/privacy.html'];
    for (const route of routes) {
      await page.goto(route, { waitUntil: 'domcontentloaded' });
      // The signed-out dashboard swaps views after the session probe; scanning
      // before that swap finds an empty shell.
      await waitForAppReady(page);
      await expect(page.locator('main')).toBeVisible();
      const levels = await page.evaluate(() =>
        [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')]
          .filter((element) => element.getClientRects().length > 0)
          .map((element) => Number(element.tagName.slice(1))),
      );
      expect(levels.length, `${route} has no headings`).toBeGreaterThan(0);
      const h1Count = levels.filter((level) => level === 1).length;
      expect(h1Count, `${route} exposes ${h1Count} h1 headings`).toBe(1);
      const skips: string[] = [];
      for (let i = 1; i < levels.length; i += 1) {
        if (levels[i] - levels[i - 1] > 1) skips.push(`${route}: h${levels[i - 1]} → h${levels[i]}`);
      }
      expect(skips, skips.join(', ')).toEqual([]);
    }
  });

  test('guest invitation exposes a top-level heading', async ({ page, seed }) => {
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    const h1Count = await page.locator('#publicRoot h1').count();
    expect(h1Count, 'a full-page invitation needs exactly one h1').toBe(1);
  });
});

test.describe('@a11y focus management', () => {
  test.use({ storageState: states.owner() });

  test('closing the create dialog returns focus to its trigger', async ({ page }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    const trigger = page.locator('#newBtn');
    await trigger.click();
    await expect(page.locator('#createDialog')).toHaveJSProperty('open', true);
    await page.keyboard.press('Escape');
    await expect(page.locator('#createDialog')).not.toHaveJSProperty('open', true);
    await expect(trigger).toBeFocused();
  });
});
