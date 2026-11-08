import path from 'node:path';
import { expect, test, uniqueSlug } from '../support/fixtures';

const SHOTS = path.resolve(__dirname, '../../artifacts/playwright-e2e/screenshots/guest');

/**
 * @smoke guest journey — the published invitation as a guest experiences it:
 * sections render, the RSVP and wishes forms write through to the host's API,
 * validation blocks empty submissions, and a double click cannot double-submit.
 */
test.describe('@smoke guest invitation', () => {
  test('renders the published invitation with its real content', async ({ page, seed, diag }) => {
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.locator('#publicRoot').waitFor({ state: 'visible' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });

    await expect(page).toHaveTitle(seed.invitation.title);
    await expect(page.getByText(seed.invitation.title, { exact: false }).first()).toBeVisible();
    // The seeded document's event carries the venue rendered on the guest page;
    // the top-level fields.venue string is not shown (recorded in the report).
    await expect(page.getByText('Main Ceremony', { exact: false })).toBeVisible();
    await expect(page.getByText('Royal Hall', { exact: false })).toBeVisible();
    await expect(page.locator('#rsvp')).toBeVisible();
    await expect(page.locator('#guestWish')).toBeVisible();

    await page.screenshot({ path: path.join(SHOTS, 'guest-published-desktop.png'), fullPage: true });
    diag.assertClean({ console: true });
  });

  test('RSVP happy path writes exactly one response', async ({ page, seed, api }) => {
    const guestName = `QA Guest ${uniqueSlug('rsvp')}`;
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    const form = page.locator('#rsvp');
    await form.waitFor({ state: 'visible' });

    await form.locator('input[name="name"]').fill(guestName);
    await form.locator('select[name="status"]').selectOption({ label: 'Yes, joyfully' });
    await form.locator('input[name="count"]').fill('2');
    await form.locator('textarea[name="note"]').fill('Looking forward to celebrating with you.');
    await form.locator('button').click();

    await expect
      .poll(
        async () => {
          const response = await api.get(`/api/invitations/${seed.invitation.id}/rsvps`);
          const rows = (await response.json()) as { name?: string }[];
          return rows.filter((row) => row.name === guestName).length;
        },
        { timeout: 15_000, message: 'the RSVP should reach the host API exactly once' },
      )
      .toBe(1);

    await page.screenshot({ path: path.join(SHOTS, 'guest-rsvp-submitted.png'), fullPage: true });
  });

  test('empty RSVP is blocked by native validation and never reaches the API', async ({ page, seed, api }) => {
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    const form = page.locator('#rsvp');
    await form.waitFor({ state: 'visible' });

    const before = ((await (await api.get(`/api/invitations/${seed.invitation.id}/rsvps`)).json()) as unknown[]).length;
    await form.locator('input[name="name"]').fill('');
    const validity = await form.evaluate((element) => (element as HTMLFormElement).checkValidity());
    expect(validity, 'a form with a required empty name must be invalid').toBe(false);

    const message = await form
      .locator('input[name="name"]')
      .evaluate((element) => (element as HTMLInputElement).validationMessage);
    expect(message.length, 'browser must explain why the empty name is rejected').toBeGreaterThan(0);

    const after = ((await (await api.get(`/api/invitations/${seed.invitation.id}/rsvps`)).json()) as unknown[]).length;
    expect(after, 'invalid form must not submit').toBe(before);
  });

  test('double-clicking Send RSVP submits once', async ({ page, seed, api }) => {
    const guestName = `QA Double ${uniqueSlug('rsvp')}`;
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    const form = page.locator('#rsvp');
    await form.waitFor({ state: 'visible' });

    await form.locator('input[name="name"]').fill(guestName);
    await form.locator('textarea[name="note"]').fill('Double submit probe.');
    const button = form.locator('button');
    // Two clicks in the same task queue: the second must hit the disabled guard.
    await button.click({ clickCount: 2, delay: 10 });

    await expect
      .poll(
        async () => {
          const rows = (await (await api.get(`/api/invitations/${seed.invitation.id}/rsvps`)).json()) as { name?: string }[];
          return rows.filter((row) => row.name === guestName).length;
        },
        { timeout: 15_000 },
      )
      .toBe(1);
  });

  test('wishes form writes through and accepts unicode', async ({ page, seed, api }) => {
    const guestName = `ភ្ញៀវ QA ${uniqueSlug('wish')}`;
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    const form = page.locator('#guestWish');
    await form.waitFor({ state: 'visible' });

    await form.locator('input[name="name"]').fill(guestName);
    await form.locator('textarea[name="message"]').fill('សូមជូនពរ សុភមង្គល 🎉 — congratulations!');
    await form.locator('button').click();

    await expect
      .poll(
        async () => {
          const rows = (await (await api.get(`/api/invitations/${seed.invitation.id}/wishes`)).json()) as { name?: string }[];
          return rows.filter((row) => row.name === guestName).length;
        },
        { timeout: 15_000 },
      )
      .toBe(1);
  });

  test('unpublished invitation is a real 404, not a rendered shell', async ({ page, seed }) => {
    const response = await page.goto(`/i/${seed.emptyInvitation.slug}`, { waitUntil: 'domcontentloaded' });
    expect(response!.status()).toBe(404);
    await expect(page.locator('body')).not.toContainText(seed.invitation.title);
  });
});
