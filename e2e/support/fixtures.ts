import { test as base, expect, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { ApiClient } from './api';
import { ADMIN, AUTH_DIR, OWNER, TENANT_B, readSeed, type Seed } from './seed';

export { ROUTES, uniqueSlug } from './seed';

export type Diagnostics = {
  pageErrors: string[];
  consoleErrors: string[];
  failedRequests: string[];
  /** Silence a known-benign message for this test, with a reason in the argument. */
  allow(pattern: RegExp, reason: string): void;
  assertClean(options?: { console?: boolean }): void;
};

type Fixtures = {
  seed: Seed;
  api: ApiClient;
  diag: Diagnostics;
};

/**
 * Every test gets a diagnostics collector. Uncaught page errors always fail the
 * test at teardown; console errors and failed requests are only fatal when a
 * spec opts in via `diag.assertClean()`, because a deliberately mocked 500 in
 * the network suite is an expected failure, not a defect.
 */
export const test = base.extend<Fixtures>({
  seed: async ({}, use) => {
    await use(readSeed());
  },

  api: async ({ playwright, baseURL }, use) => {
    // Reuse the session created by global setup. Logging in per test used to
    // exhaust the server's 30-per-10-minute login limit and turn every later
    // test into a 429, so the CSRF token is read from the stored cookie instead.
    const state = JSON.parse(fs.readFileSync(path.join(AUTH_DIR, 'owner.json'), 'utf8')) as {
      cookies: {
        name: string;
        value: string;
        domain: string;
        path: string;
        expires: number;
        httpOnly: boolean;
        secure: boolean;
        sameSite: 'Strict' | 'Lax' | 'None';
      }[];
    };
    const csrf = state.cookies.find((cookie) => cookie.name === 'einvite_csrf')?.value ?? '';
    const context = await playwright.request.newContext({
      baseURL,
      storageState: { cookies: state.cookies, origins: [] },
      extraHTTPHeaders: { Origin: baseURL!, 'X-CSRF-Token': csrf },
    });
    const api = new ApiClient(context, baseURL!, csrf);
    await use(api);
    await context.dispose();
  },

  diag: [
    async ({ page }, use, testInfo) => {
      const pageErrors: string[] = [];
      const consoleErrors: string[] = [];
      const failedRequests: string[] = [];
      const allowances: { pattern: RegExp; reason: string }[] = [];

      page.on('pageerror', (error) => pageErrors.push(String(error).split('\n')[0]));
      page.on('console', (message) => {
        if (message.type() !== 'error') return;
        const text = message.text();
        if (allowances.some((entry) => entry.pattern.test(text))) return;
        consoleErrors.push(text.slice(0, 300));
      });
      page.on('requestfailed', (request) => {
        const text = `${request.method()} ${request.url()} — ${request.failure()?.errorText ?? 'failed'}`;
        if (allowances.some((entry) => entry.pattern.test(text))) return;
        // Navigation aborts caused by the test itself are not app failures.
        if (/net::ERR_ABORTED/.test(text)) return;
        failedRequests.push(text);
      });

      const diag: Diagnostics = {
        pageErrors,
        consoleErrors,
        failedRequests,
        allow(pattern, reason) {
          allowances.push({ pattern, reason });
        },
        assertClean(options = {}) {
          if (pageErrors.length) expect(pageErrors, 'uncaught page errors').toEqual([]);
          if (options.console) {
            if (consoleErrors.length) expect(consoleErrors, 'console errors').toEqual([]);
            if (failedRequests.length) expect(failedRequests, 'failed network requests').toEqual([]);
          }
        },
      };

      await use(diag);

      await testInfo.attach('diagnostics', {
        body: JSON.stringify({ pageErrors, consoleErrors, failedRequests, allowances }, null, 2),
        contentType: 'application/json',
      });
      expect(pageErrors, 'uncaught page errors').toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

export const states = {
  owner: () => path.join(AUTH_DIR, 'owner.json'),
  tenantB: () => path.join(AUTH_DIR, 'tenant-b.json'),
  admin: () => path.join(AUTH_DIR, 'admin.json'),
};

export const accounts = { owner: OWNER, tenantB: TENANT_B, admin: ADMIN };

/** Wait until the app has finished its first client-side render. */
export async function waitForAppReady(page: Page) {
  await page.waitForLoadState('domcontentloaded');
  await page.locator('main').first().waitFor({ state: 'visible' });
}

/** True when the document does not scroll horizontally beyond the viewport. */
export async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}
