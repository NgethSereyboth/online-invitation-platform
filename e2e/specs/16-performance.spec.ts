import fs from 'node:fs';
import path from 'node:path';
import { expect, states, test } from '../support/fixtures';

const PERF_DIR = path.resolve(__dirname, '../../artifacts/playwright-e2e/perf');

/**
 * @performance — navigation timing, FCP/LCP, request count and transfer bytes
 * per route. The ceilings are deliberately generous (this is a laptop, not a
 * lab) but a regression above them is a real signal.
 */
const BUDGET = {
  domContentLoadedMs: 4_000,
  lcpMs: 3_000,
  requests: 180,
  transferBytes: 4_000_000,
};

type Metrics = {
  route: string;
  domContentLoadedMs: number;
  loadMs: number;
  fcpMs: number | null;
  lcpMs: number | null;
  requests: number;
  transferBytes: number;
  jsBytes: number;
  cssBytes: number;
};

const observeLcp = () => {
  const store = { lcp: 0 };
  (window as unknown as { __perf: typeof store }).__perf = store;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) store.lcp = Math.max(store.lcp, entry.startTime);
  }).observe({ type: 'largest-contentful-paint', buffered: true });
};

const collect = () => {
  const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
  const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
  const paint = performance.getEntriesByType('paint');
  const fcp = paint.find((entry) => entry.name === 'first-contentful-paint');
  const sum = (list: PerformanceResourceTiming[]) =>
    list.reduce((total, entry) => total + (entry.transferSize || 0), 0);
  const lcp = (window as unknown as { __perf?: { lcp: number } }).__perf?.lcp ?? 0;
  return {
    domContentLoadedMs: Math.round(nav.domContentLoadedEventEnd),
    loadMs: Math.round(nav.loadEventEnd),
    fcpMs: fcp ? Math.round(fcp.startTime) : null,
    lcpMs: lcp ? Math.round(lcp) : null,
    requests: resources.length + 1,
    transferBytes: sum(resources) + (nav.transferSize || 0),
    jsBytes: sum(resources.filter((entry) => entry.name.endsWith('.js'))),
    cssBytes: sum(resources.filter((entry) => entry.name.endsWith('.css'))),
  };
};

test.describe('@performance route budgets', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'timings are recorded once, on chromium');

  const routes = [
    { name: 'editor', path: '/index.html' },
    { name: 'dashboard', path: '/dashboard.html' },
    { name: 'guests', path: '/guests.html' },
    { name: 'templates', path: '/templates.html' },
    { name: 'privacy', path: '/privacy.html' },
  ];

  test.beforeAll(() => fs.mkdirSync(PERF_DIR, { recursive: true }));

  for (const route of routes) {
    test(`${route.name} is inside its performance budget`, async ({ page }) => {
      await page.addInitScript(observeLcp);
      await page.goto(route.path, { waitUntil: 'load' });
      await expect
        .poll(async () => page.evaluate(() => (window as unknown as { __perf?: { lcp: number } }).__perf?.lcp ?? 0), {
          timeout: 8_000,
          message: 'LCP entry should be recorded for a rendered page',
        })
        .toBeGreaterThan(0);

      const metrics = { route: route.name, ...(await page.evaluate(collect)) } satisfies Metrics;
      fs.writeFileSync(path.join(PERF_DIR, `${route.name}.json`), JSON.stringify(metrics, null, 2));
      await test.info().attach(`perf-${route.name}`, {
        body: JSON.stringify(metrics, null, 2),
        contentType: 'application/json',
      });

      expect(metrics.domContentLoadedMs, `DCL ${metrics.domContentLoadedMs}ms`).toBeLessThan(BUDGET.domContentLoadedMs);
      expect(metrics.lcpMs!, `LCP ${metrics.lcpMs}ms`).toBeLessThan(BUDGET.lcpMs);
      expect(metrics.requests, `requests ${metrics.requests}`).toBeLessThanOrEqual(BUDGET.requests);
      expect(metrics.transferBytes, `transfer ${metrics.transferBytes}B`).toBeLessThanOrEqual(BUDGET.transferBytes);
    });
  }
});

test.describe('@performance guest page budget', () => {
  test.use({ storageState: states.owner() });

  test('published guest page is inside its budget', async ({ page, seed }) => {
    await page.addInitScript(observeLcp);
    await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'load' });
    await page.locator('#rsvp').waitFor({ state: 'visible' });

    await expect
      .poll(async () => page.evaluate(() => (window as unknown as { __perf?: { lcp: number } }).__perf?.lcp ?? 0), {
        timeout: 8_000,
      })
      .toBeGreaterThan(0);

    const metrics = { route: 'guest', ...(await page.evaluate(collect)) } satisfies Metrics;
    await test.info().attach('perf-guest', {
      body: JSON.stringify(metrics, null, 2),
      contentType: 'application/json',
    });
    expect(metrics.domContentLoadedMs, `DCL ${metrics.domContentLoadedMs}ms`).toBeLessThan(BUDGET.domContentLoadedMs);
    expect(metrics.lcpMs!, `LCP ${metrics.lcpMs}ms`).toBeLessThan(BUDGET.lcpMs);
    expect(metrics.transferBytes, `transfer ${metrics.transferBytes}B`).toBeLessThanOrEqual(BUDGET.transferBytes);
  });
});
