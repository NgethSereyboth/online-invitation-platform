import { expect, states, test, uniqueSlug } from '../support/fixtures';
import { weddingDocument } from '../support/api';

/**
 * @smoke editor — the design studio is the product's centre of gravity. These
 * tests edit a real invitation document and publish it, then read the public
 * page back, so a broken bridge between editor state and server state fails.
 */
test.describe('@smoke editor', () => {
  test.use({ storageState: states.owner() });

  test('loads the requested document and edits a field', async ({ page, api }) => {
    // A private document: this test edits and autosaves, and mutating the
    // shared seed would race every other spec that reads it.
    const title = `QA Editor ${uniqueSlug('edit')}`;
    const created = await api.createInvitation(title, `qa-editor-${uniqueSlug('doc')}`);
    await page.goto(`/index.html?invitation=${encodeURIComponent(created.id)}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    // First visit opens a creation-studio tour; it is modal and would swallow
    // every later click, so dismiss it before interacting.
    await page.keyboard.press('Escape');

    await expect(page.locator('#documentTitle')).toContainText(title);
    await expect(page.locator('#canvasViewport, .canvas-viewport').first()).toBeVisible();

    // The content fields live in the Event pane of the left rail; the editor
    // opens on Pages.
    await page.locator('aside.left [data-studio-tab="event"]').click();
    const names = page.locator('#names');
    await expect(names).toBeVisible();
    await names.fill('QA Edited Names');
    await expect
      .poll(() => page.evaluate(() => (window as any).EInviteEditorBridge?.getState?.().fields?.names))
      .toBe('QA Edited Names');

    await page.locator('#undoBtn').click();
    await expect
      .poll(() => page.evaluate(() => (window as any).EInviteEditorBridge?.getState?.().fields?.names))
      .toBe(title);
  });

  test('shortcuts surface opens and closes with Escape', async ({ page, seed }) => {
    await page.goto(`/index.html?invitation=${encodeURIComponent(seed.invitation.id)}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    await page.keyboard.press('Escape');

    const trigger = page.locator('#studioCommandBtn');
    await expect(trigger).toBeVisible();
    await trigger.click();

    const surface = page.locator('[role="dialog"]:visible, dialog[open]').first();
    await expect(surface).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(surface).toBeHidden();
  });
});

test.describe('@smoke editor publish', () => {
  test.use({ storageState: states.owner() });
  // Publishing is a server mutation; keep it away from parallel workers that
  // read the same invitation list.
  test.describe.configure({ lock: '-exclusive-' });

  test('publishes a new invitation and the public page serves it', async ({ page, api, request }) => {
    const title = `QA Publish Flow ${uniqueSlug('pub')}`;
    const created = await api.createInvitation(title, `qa-publish-${uniqueSlug('flow')}`);

    await page.goto(`/index.html?invitation=${encodeURIComponent(created.id)}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true', null, {
      timeout: 25_000,
    });
    // Dismiss the first-run tour by its own control; Escape alone does not
    // always close it, and while open it intercepts every pointer event.
    const tourClose = page
      .locator('dialog.final-tour[open] .final-tour-close, dialog.final-tour[open] #finalTourDismiss')
      .first();
    if (await tourClose.count()) {
      await tourClose.click();
      await expect(page.locator('dialog.final-tour[open]')).toHaveCount(0);
    }

    // Publishing may confirm through window.confirm or a custom dialog.
    page.on('dialog', (dialog) => dialog.accept());
    await page.locator('#publishBtn').click();
    const confirm = page.locator('dialog[open] button.primary, dialog[open] [data-confirm]').first();
    if (await confirm.count()) await confirm.click().catch(() => {});

    await expect
      .poll(
        async () => {
          const guest = await request.get(`/i/${created.slug}`);
          return guest.status();
        },
        { timeout: 20_000, message: 'published invitation should resolve publicly' },
      )
      .toBe(200);

    const guest = await request.get(`/i/${created.slug}`);
    expect(await guest.text()).toContain(title);
    void weddingDocument;
  });
});
