import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

/**
 * eInvite QA harness.
 *
 * The application is a Python/SQLite server plus static bundles; this config does
 * NOT start it. `support/global-setup.ts` waits for an already-running origin
 * (default http://127.0.0.1:4310, override with E2E_BASE_URL) and seeds accounts
 * and invitations through the public API.
 *
 * Every artifact lands under artifacts/playwright-e2e/ (gitignored) except the
 * visual baselines, which must survive between runs and live in e2e/__screenshots__/.
 */
const ARTIFACTS = path.resolve(__dirname, '../artifacts/playwright-e2e');

export default defineConfig({
  testDir: './specs',
  outputDir: path.join(ARTIFACTS, 'test-results'),
  snapshotPathTemplate: '{testDir}/../__screenshots__/{testFilePath}/{arg}{ext}',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      threshold: 0.2,
      animations: 'disabled',
      caret: 'hide',
    },
  },
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : 3,
  reporter: [
    ['failures'],
    ['html', { onlyFailures: true, outputFolder: path.join(ARTIFACTS, 'html-report'), open: 'never' }],
    ['json', { outputFile: path.join(ARTIFACTS, 'results.json') }],
    ['junit', { outputFile: path.join(ARTIFACTS, 'junit.xml') }],
  ],
  globalSetup: './support/global-setup.ts',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:4310',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
    navigationTimeout: 30_000,
    actionTimeout: 15_000,
    locale: 'en-US',
    timezoneId: 'Asia/Phnom_Penh',
    colorScheme: 'light',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } },
    },
    {
      // WebKit 27.2 launches on this host after libavif16 was installed;
      // route smoke passed 33/33 on 2026-11-07 (logs/webkit-retry.log).
      name: 'webkit',
      testMatch: /01-smoke-routes\.spec\.ts/,
      use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-chrome',
      testMatch: /(01-smoke-routes|05-guest-rsvp|08-responsive)\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'tablet-chromium',
      testMatch: /08-responsive\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 }, hasTouch: true },
    },
  ],
});
