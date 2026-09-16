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
  await page.locator('#email').fill(`resize-ownership-${Date.now()}@example.com`);
  await page.locator('#password').fill('Resize-ownership-123!');
  await page.locator('#registerConfirmPassword').fill('Resize-ownership-123!');
  await page.locator('#loginBtn').click();
  await page.locator('#dashboardView:not([hidden])').waitFor();
  await page.locator('.dashboard-home-hero .create:visible,#emptyCreate:visible').first().click();
  await page.locator('#createDialog[open]').waitFor();
  await page.locator('#newTitle').fill('Resize ownership test');
  await page.locator('#confirmCreate').click();
  await page.waitForURL('**/invitations/*/editor');
  await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true');
  await page.waitForFunction(() => window.EInviteProfessionalEditor?.version >= 17);
  for (const selector of ['#studioOnboarding [data-onboarding-skip]', '#studioOnboarding .close', '[data-dismiss-onboarding]', '#finalTourDismiss']) {
    const button = page.locator(selector);
    if (await button.count() && await button.isVisible()) await button.click();
  }

  const imageId = 'resize-test-image';
  await page.evaluate(id => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420"><rect width="640" height="420" fill="#d9a6ad"/><circle cx="320" cy="210" r="130" fill="#fff7f3"/></svg>`;
    window.EInviteEditorBridge.transact('Add resize test image', doc => {
      doc.objects[id] = {
        type: 'image', src: `data:image/svg+xml,${encodeURIComponent(svg)}`, alt: 'Resize test image',
        left: '64%', top: '58%', width: '25%', height: '20%', zIndex: 30,
        rotation: 0, visible: true, locked: false,
      };
    });
  }, imageId);
  await page.locator(`#stage .object[data-id="${imageId}"][data-object-type="image"]`).waitFor();
  assert(imageId, 'photo-frame image object must be created');

  await page.evaluate(() => {
    window.__resizeSelectionHijack = event => {
      if (document.body.dataset.pePointerInteraction === 'resize') {
        window.EInviteEditorBridge.select(['roseArc']);
      }
    };
    document.addEventListener('pointermove', window.__resizeSelectionHijack, true);
  });

  const handles = {
    nw: [12, 10], n: [0, 10], ne: [12, 10], e: [12, 0],
    se: [12, 10], s: [0, 10], sw: [-12, 10], w: [-12, 0],
  };
  const readFrames = () => page.evaluate(() => Object.fromEntries(
    [...document.querySelectorAll('#stage .object')].map(node => [node.dataset.id, {
      left: node.style.left, top: node.style.top, width: node.style.width,
      height: node.style.height, rotation: node.dataset.rotation || '0',
    }])
  ));

  async function resizeEveryHandle(id) {
    for (const [handle, [dx, dy]] of Object.entries(handles)) {
      await page.locator(`#stage .object[data-id="${id}"]`).click({ position: { x: 20, y: 20 } });
      await page.waitForFunction(expected => window.EInviteEditorBridge.getSelectedIds().length === 1 && window.EInviteEditorBridge.getSelectedIds()[0] === expected, id);
      const before = await readFrames();
      const box = await page.locator(`[data-pe-handle="${handle}"]`).boundingBox();
      assert(box, `${handle} handle must be visible for ${id}`);
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      await page.mouse.move(x, y);
      await page.mouse.down();
      await page.mouse.move(x + Math.sign(dx || 1) * 3, y + Math.sign(dy || 1) * 3, { steps: 1 });
      await page.mouse.move(x + dx, y + dy, { steps: 3 });
      await page.mouse.up();
      await page.waitForTimeout(80);

      const result = await page.evaluate(() => ({
        selected: window.EInviteEditorBridge.getSelectedIds(),
        command: window.EInviteProfessionalEditor.lastCommand,
        active: window.EInviteProfessionalEditor.activeInteraction,
      }));
      const after = await readFrames();
      assert.deepEqual(result.selected, [id], `${handle}: selected id must remain ${id}`);
      assert.equal(result.command.label, 'Resize objects', `${handle}: command label`);
      assert.deepEqual(result.command.selection, [id], `${handle}: command target`);
      assert.equal(result.active, null, `${handle}: gesture must finish cleanly`);
      assert.notDeepEqual(after[id], before[id], `${handle}: target frame must change`);
      for (const otherId of Object.keys(before).filter(value => value !== id)) {
        assert.deepEqual(after[otherId], before[otherId], `${handle}: unrelated ${otherId} must not change`);
      }
    }
  }

  await resizeEveryHandle('title');
  await resizeEveryHandle(imageId);
  await page.evaluate(() => document.removeEventListener('pointermove', window.__resizeSelectionHijack, true));
  await browser.close();
  console.log('V0_52_RESIZE_HANDLE_OWNERSHIP_BROWSER_TEST_PASSED');
})().catch(error => {
  console.error(error);
  browser?.close().finally(() => { process.exitCode = 1; });
});
