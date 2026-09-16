#!/usr/bin/env node
'use strict';

const { chromium } = require('playwright');
const assert = require('node:assert/strict');
let browser;

(async () => {
  const phase = message => console.log(`UX_BROWSER_PHASE ${message}`);
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  page.setDefaultTimeout(20000);
  const errors = [];
  page.on('pageerror', error => errors.push(`PAGE:${error}`));
  page.on('console', message => {
    if (message.type() === 'error' && !/favicon|youtube|soundcloud|401/i.test(message.text())) errors.push(`CONSOLE:${message.text()}`);
  });
  page.on('dialog', dialog => dialog.accept());

  phase('dashboard');
  await page.goto('http://127.0.0.1:4175/dashboard.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.locator('#authRegisterTab').click();
  await page.locator('#email').fill(`ux-refinement-${Date.now()}@example.com`);
  await page.locator('#password').fill('Strong-ux-refinement-123');
  await page.locator('#registerConfirmPassword').fill('Strong-ux-refinement-123');
  await page.locator('#loginBtn').click();
  await page.locator('#dashboardView:not([hidden])').waitFor();
  phase('create-invitation');
  const create = page.locator('.dashboard-home-hero .create:visible,#emptyCreate:visible').first();
  await create.click();
  await page.locator('#createDialog[open]').waitFor();
  await page.locator('#newTitle').fill('Editor interaction refinement');
  await page.locator('#confirmCreate').click();
  await page.waitForURL('**/invitations/*/editor');
  await page.locator('#stage .object[data-id="title"]').waitFor();
  await page.waitForFunction(() => document.documentElement.dataset.editorReady === 'true');
  await page.waitForFunction(() => window.EInviteDirectManipulation?.version >= 24.2);
  for (const selector of ['#studioOnboarding [data-onboarding-skip]', '#studioOnboarding .close', '[data-dismiss-onboarding]']) {
    const button = page.locator(selector);
    if (await button.count() && await button.isVisible()) await button.click();
  }
  const finalTourDismiss = page.locator('#finalTourDismiss');
  if (await finalTourDismiss.count() && await finalTourDismiss.isVisible()) await finalTourDismiss.click();
  errors.length = 0;

  phase('toolbar');
  const title = page.locator('#stage .object[data-id="title"]');
  await title.click();
  await page.waitForTimeout(250);
  const toolbarState = await page.evaluate(() => {
    const bar = document.querySelector('#v20TypographyToolbar');
    return {
      visible: !!bar && !bar.hidden,
      collapsed: bar?.classList.contains('collapsed'),
      controlsVisible: ['font', 'size', 'bold', 'italic', 'align', 'color'].every(key => {
        const control = bar?._refs?.[key];
        return !!control && getComputedStyle(control).display !== 'none' && control.getBoundingClientRect().width > 0;
      }),
      fontVisible: document.querySelector('#v20VisibleFont')?.getBoundingClientRect().width > 0,
      storedPreference: localStorage.getItem('einvite-typography-toolbar-collapsed'),
      inline: document.querySelectorAll('.v24-inline-toolbar').length,
      rich: document.querySelectorAll('.ei-rich-toolbar').length,
      quick: document.querySelectorAll('#workflowQuickStrip').length,
    };
  });
  assert.deepEqual(toolbarState, { visible: true, collapsed: false, controlsVisible: true, fontVisible: true, storedPreference: '0', inline: 0, rich: 0, quick: 0 });

  await page.locator('#v20ToolbarToggle').click();
  assert.equal(await page.locator('#v20TypographyToolbar').evaluate(node => node.classList.contains('collapsed')), true);
  await page.locator('#v20ToolbarToggle').click();
  assert.equal(await page.locator('#v20TypographyToolbar').evaluate(node => node.classList.contains('collapsed')), false);

  await title.locator('.content').dblclick();
  await page.waitForTimeout(180);
  assert.deepEqual(await page.evaluate(() => ({
    editable: document.querySelector('#stage .object[data-id="title"] .content')?.getAttribute('contenteditable'),
    inlineToolbar: document.querySelectorAll('.v24-inline-toolbar:not([hidden])').length,
    richToolbar: document.querySelectorAll('.ei-rich-toolbar.visible').length,
  })), { editable: 'true', inlineToolbar: 0, richToolbar: 0 });
  await page.keyboard.press('Control+Enter');

  phase('page-menu');
  const pageMore = page.locator('.workflow-page-chip[data-page-id] .workflow-page-more').first();
  if (await pageMore.count()) {
    await pageMore.click();
    await page.locator('#workflowV4PageMenu.open').waitFor();
    const placement = await page.evaluate(() => {
      const menu = document.querySelector('#workflowV4PageMenu').getBoundingClientRect();
      const dock = document.querySelector('#workflowPageDock').getBoundingClientRect();
      return {
        separate: menu.bottom <= dock.top || menu.top >= dock.bottom,
        inViewport: menu.left >= 0 && menu.top >= 0 && menu.right <= innerWidth && menu.bottom <= innerHeight,
      };
    });
    assert.equal(placement.separate && placement.inViewport, true);
  }

  phase('theme-menu');
  await page.locator('.ui-theme-button').click();
  const themeState = await page.evaluate(() => {
    const menu = document.querySelector('.ui-theme-menu');
    const rect = menu.getBoundingClientRect();
    return { modes: [...menu.querySelectorAll('[data-mode]')].map(node => node.dataset.mode), width: rect.width, inViewport: rect.left >= 0 && rect.right <= innerWidth };
  });
  assert.deepEqual(themeState.modes, ['light', 'dark']);
  assert.equal(themeState.width <= 130 && themeState.inViewport, true);
  await page.locator('.ui-theme-menu [data-mode="dark"]').click();
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), 'dark');

  assert.deepEqual(await page.evaluate(() => ({
    labels: [...document.querySelectorAll('.studio-nav-label')].every(label => {
      const a = label.getBoundingClientRect(), b = label.closest('button').getBoundingClientRect();
      return a.left >= b.left - 1 && a.right <= b.right + 1;
    }),
    shortcuts: [...document.querySelectorAll('.ei-tool-rail button > span')].every(node => getComputedStyle(node).display === 'none'),
  })), { labels: true, shortcuts: true });

  phase('narrow-layout');
  await page.setViewportSize({ width: 820, height: 720 });
  await page.locator('.ui-theme-button').click();
  assert.equal(await page.locator('.ui-theme-menu').evaluate(menu => {
    const rect = menu.getBoundingClientRect();
    return rect.left >= 0 && rect.top >= 0 && rect.right <= innerWidth && rect.bottom <= innerHeight;
  }), true);
  await page.locator('.ui-theme-button').click();
  assert.equal(await page.evaluate(() => [...document.querySelectorAll('.studio-nav-label')].every(label => label.scrollWidth <= label.clientWidth + 1)), true);

  phase('account-setting');
  await page.goto('http://127.0.0.1:4175/account.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.locator('#accountAppearance').waitFor();
  assert.equal(await page.locator('#accountAppearance [data-account-theme]').count(), 2);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log('V0_52_EDITOR_INTERACTION_REFINEMENT_BROWSER_TEST_PASSED');
})().catch(error => {
  console.error(error);
  browser?.close().finally(() => { process.exitCode = 1; });
});
