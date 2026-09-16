#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const assert = require('node:assert/strict');
let browser;

(async () => {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(20000);
  page.on('dialog', dialog => dialog.accept());

  await page.goto('http://127.0.0.1:4175/dashboard.html', { waitUntil: 'domcontentloaded' });
  await page.locator('#authRegisterTab').click();
  await page.locator('#email').fill(`move-overlay-${Date.now()}@example.com`);
  await page.locator('#password').fill('Move-overlay-123!');
  await page.locator('#registerConfirmPassword').fill('Move-overlay-123!');
  await page.locator('#loginBtn').click();
  await page.locator('#dashboardView:not([hidden])').waitFor();
  await page.locator('.dashboard-home-hero .create:visible,#emptyCreate:visible').first().click();
  await page.locator('#createDialog[open]').waitFor();
  await page.locator('#newTitle').fill('Move overlay tracking test');
  await page.locator('#confirmCreate').click();
  await page.waitForURL('**/invitations/*/editor');
  await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true');
  await page.waitForFunction(() => window.EInviteProfessionalEditor?.version >= 17);
  for (const selector of ['#studioOnboarding [data-onboarding-skip]', '#studioOnboarding .close', '[data-dismiss-onboarding]', '#finalTourDismiss']) {
    const button = page.locator(selector);
    if (await button.count() && await button.isVisible()) await button.click();
  }

  const target = page.locator('#stage .object[data-id="title"]');
  await target.click({ position: { x: 80, y: 35 } });
  await page.waitForFunction(() => !document.querySelector('#peSelectionBox')?.hidden);
  const start = await target.boundingBox();
  assert(start, 'title object must be visible');
  const sequence = await page.evaluate(() => window.EInviteProfessionalEditor.commandSequence);
  const point = { x: start.x + Math.min(100, start.width / 2), y: start.y + Math.min(45, start.height / 2) };

  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  await page.mouse.move(point.x + 3, point.y + 2);
  await page.mouse.move(point.x + 72, point.y + 48, { steps: 5 });
  await page.waitForTimeout(100);

  const during = await page.evaluate(() => {
    const object = document.querySelector('#stage .object[data-id="title"]');
    const overlay = document.querySelector('#peSelectionBox');
    const handle = overlay.querySelector('[data-pe-handle="se"]');
    const label = overlay.querySelector('.pe-selection-label');
    const rect = node => { const r = node.getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; };
    return {
      object: rect(object), overlay: rect(overlay), handle: rect(handle), label: rect(label),
      visibility: getComputedStyle(overlay).visibility,
      hidden: overlay.hidden,
      active: window.EInviteProfessionalEditor.activeInteraction,
      sequence: window.EInviteProfessionalEditor.commandSequence,
    };
  });
  const close = (a, b, tolerance = 2.5) => Math.abs(a - b) <= tolerance;
  assert.equal(during.hidden, false, 'overlay must remain rendered while moving');
  assert.equal(during.visibility, 'visible', 'overlay must remain visible while moving');
  assert.equal(during.active.type, 'move');
  assert.deepEqual(during.active.ids, ['title']);
  assert.equal(during.sequence, sequence, 'move must not commit before pointer-up');
  assert(close(during.overlay.x, during.object.x) && close(during.overlay.y, during.object.y), 'overlay must track object position during drag');
  assert(close(during.overlay.width, during.object.width) && close(during.overlay.height, during.object.height), 'overlay dimensions must track the object');
  assert(during.handle.width > 0 && during.handle.height > 0, 'resize handles must stay visible during drag');
  assert(during.label.width > 0 && during.label.height > 0, 'selection label must stay visible during drag');

  await page.mouse.up();
  await page.waitForTimeout(120);
  const after = await page.evaluate(() => {
    const object = document.querySelector('#stage .object[data-id="title"]').getBoundingClientRect();
    const overlay = document.querySelector('#peSelectionBox').getBoundingClientRect();
    return {
      object: { x: object.x, y: object.y }, overlay: { x: overlay.x, y: overlay.y },
      selected: window.EInviteEditorBridge.getSelectedIds(),
      command: window.EInviteProfessionalEditor.lastCommand,
      active: window.EInviteProfessionalEditor.activeInteraction,
    };
  });
  assert(close(after.overlay.x, after.object.x) && close(after.overlay.y, after.object.y), 'overlay must remain aligned after commit');
  assert.deepEqual(after.selected, ['title']);
  assert.equal(after.command.label, 'Move objects');
  assert.deepEqual(after.command.selection, ['title']);
  assert.equal(after.active, null);

  await browser.close();
  console.log('V0_52_MOVE_OVERLAY_TRACKING_BROWSER_TEST_PASSED');
})().catch(error => {
  console.error(error);
  browser?.close().finally(() => { process.exitCode = 1; });
});
