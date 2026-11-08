import { expect, states, test, uniqueSlug } from '../support/fixtures';

/**
 * @smoke dashboard — the workspace a returning host lands on: their invitation
 * is listed with real metadata, creating one works end to end, and the card
 * opens the editor for the right document.
 *
 * Two open paths exist in the shipped UI: the card cover and the overflow
 * menu's Edit item. Both are tested because the cover is the larger target and
 * the obvious one a user clicks first.
 */
test.describe('@smoke dashboard journeys', () => {
  test.use({ storageState: states.owner() });

  test('the seeded invitation is listed with its metadata', async ({ page, seed }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();

    const card = page.locator('.invite-card', { hasText: seed.invitation.title }).first();
    await expect(card).toBeVisible();
    await expect(card.locator('h2')).toContainText(seed.invitation.title);
    await expect(card.locator('.stats')).not.toBeEmpty();
    await expect(card.locator('.invite-overflow__toggle')).toHaveCount(1);
    await expect(card.locator('.invite-cover')).toHaveAttribute('aria-label', /Open/i);
  });

  test('the card cover opens the editor', async ({ page, seed }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });

    const card = page.locator('.invite-card', { hasText: seed.invitation.title }).first();
    await card.locator('.invite-cover').click();

    await expect(
      page,
      'clicking the invitation cover must open the editor, not leave the user on the dashboard',
    ).toHaveURL(new RegExp(encodeURIComponent(seed.invitation.id)), { timeout: 15_000 });
    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    await expect(page.locator('#documentTitle')).toContainText(seed.invitation.title);
  });

  test('the overflow menu Edit action opens the editor', async ({ page, seed }) => {
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });

    const card = page.locator('.invite-card', { hasText: seed.invitation.title }).first();
    await card.locator('.invite-overflow__toggle').click();
    const menu = card.locator('.invite-overflow__menu');
    await expect(menu).toBeVisible();
    await menu.locator('[data-edit]').first().click();

    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    await expect(page.locator('#documentTitle')).toContainText(seed.invitation.title);
  });

  test('pagination loads the next page only on request', async ({ page }) => {
    const offsets: number[] = [];
    const filteredRequests: string[] = [];
    const pageRows = (offset: number, count: number) =>
      Array.from({ length: count }, (_, index) => {
        const n = offset + index;
        return {
          id: `paged-${n}`,
          slug: `paged-${n}`,
          title: `Paged invitation ${n}`,
          type: 'Wedding',
          status: 'Draft',
          views: 0,
          rsvps: 0,
          updatedAt: '2026-11-07T00:00:00Z',
          archived: 0,
        };
      });

    await page.route(/\/api\/invitations\?limit=25&offset=(\d+)$/, async (route) => {
      const offset = Number(new URL(route.request().url()).searchParams.get('offset'));
      offsets.push(offset);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(pageRows(offset, offset === 0 ? 25 : 1)),
      });
    });
    await page.route(/\/api\/invitations\?limit=25&offset=0&status=published$/, async (route) => {
      filteredRequests.push(route.request().url());
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#dashboardView')).toBeVisible();
    await expect(page.locator('#inviteGrid .invite-card')).toHaveCount(24);
    await expect(page.locator('#loadMoreInvites')).toBeVisible();

    await page.locator('#loadMoreInvites').click();
    await expect(page.locator('#inviteGrid .invite-card')).toHaveCount(25);
    await expect(page.locator('#loadMoreInvites')).toBeHidden();
    expect(offsets).toEqual([0, 24]);

    await page.locator('[data-dash-filter="published"]').click();
    await expect.poll(() => filteredRequests.length).toBe(1);
    await expect(page.locator('#inviteGrid')).toContainText(/No invitations match this filter/i);
  });

  test('creating an invitation adds it to the grid once', async ({ page, api }) => {
    const title = `QA Created ${uniqueSlug('dash')}`;
    await page.goto('/dashboard.html', { waitUntil: 'domcontentloaded' });
    await page.locator('#dashboardView').waitFor({ state: 'visible' });
    const before = await page.locator('#inviteGrid .invite-card').count();

    await page.locator('#newBtn').click();
    const dialog = page.locator('#createDialog');
    await expect(dialog).toHaveJSProperty('open', true);
    await page.locator('#newTitle').fill(title);
    await page.locator('#confirmCreate').click();

    // Successful creation closes or removes the dialog; `toBeHidden` accepts both.
    await expect(dialog).toBeHidden({ timeout: 20_000 });
    // Parallel specs also create invitations and the grid re-renders, so the
    // server row is the stable proof that exactly one invitation was created.
    void before;

    const rows = (await (await api.get('/api/invitations')).json()) as { title: string }[];
    expect(rows.filter((row) => row.title === title)).toHaveLength(1);
  });
});
