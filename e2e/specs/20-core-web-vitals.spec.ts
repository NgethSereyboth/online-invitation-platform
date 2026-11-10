import fs from 'node:fs';
import path from 'node:path';
import { expect, states, test } from '../support/fixtures';

/**
 * @core-web-vitals — lab measurements for the two unauthenticated/entry routes
 * that Sprint 10 optimises. LCP and CLS come from web-vitals (the same
 * implementation used in production monitoring); TBT is the sum of long-task
 * time beyond 50 ms, the standard lab approximation. The thresholds are the
 * product gate, not a report: a regression fails the test.
 */
const WEB_VITALS_SOURCE = fs.readFileSync(
  path.resolve(process.cwd(), 'node_modules/web-vitals/dist/web-vitals.iife.js'),
  'utf8',
);

const BUDGETS = {
  lcpMs: 2_500,
  cls: 0.1,
  tbtMs: 150,
} as const;

test.skip(({ browserName }) => browserName !== 'chromium', 'Core Web Vitals are gated on Chromium');

type Vitals = {
  lcp: number;
  cls: number;
  tbt: number;
  longTasks: number;
  fcp: number | null;
};

function installObservers() {
  const store: Vitals = { lcp: 0, cls: 0, tbt: 0, longTasks: 0, fcp: null };
  (window as unknown as { __cwv: Vitals }).__cwv = store;
  const vitals = (window as unknown as {
    webVitals?: {
      onLCP: (callback: (metric: { value: number }) => void, options: { reportAllChanges: boolean }) => void;
      onCLS: (callback: (metric: { value: number }) => void, options: { reportAllChanges: boolean }) => void;
    };
  }).webVitals;
  if (!vitals) throw new Error('web-vitals IIFE did not expose window.webVitals');

  vitals.onLCP((metric) => { store.lcp = metric.value; }, { reportAllChanges: true });
  vitals.onCLS((metric) => { store.cls = metric.value; }, { reportAllChanges: true });

  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.entryType !== 'longtask') continue;
      store.longTasks += 1;
      store.tbt += Math.max(0, entry.duration - 50);
    }
  }).observe({ type: 'longtask', buffered: true });

  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.name === 'first-contentful-paint') store.fcp = entry.startTime;
    }
  }).observe({ type: 'paint', buffered: true });
}

async function install(page: import('@playwright/test').Page) {
  await page.addInitScript({
    // addInitScript evaluates in a wrapper, so bind the IIFE's `var` to the
    // page global explicitly before the observer bootstrap reads it.
    content: `${WEB_VITALS_SOURCE}\nwindow.webVitals = webVitals;\n(${installObservers.toString()})();`,
  });
}

async function read(page: import('@playwright/test').Page): Promise<Vitals> {
  return page.evaluate(() => {
    const value = (window as unknown as { __cwv?: Vitals }).__cwv;
    return value ?? { lcp: 0, cls: 0, tbt: 0, longTasks: 0, fcp: null };
  });
}

function nonceOf(response: import('@playwright/test').Response | null): string {
  const csp = response?.headers()['content-security-policy'] || '';
  return /'nonce-([^']+)'/.exec(csp)?.[1] || '';
}

test.describe('@core-web-vitals public invitation', () => {
  test.use({ storageState: states.owner() });

  test('LCP, CLS and TBT stay within the Sprint 10 budgets', async ({ page, seed }) => {
    await install(page);
    const response = await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'load' });
    expect(response?.status()).toBe(200);
    await page.locator('#rsvp').waitFor({ state: 'visible' });
    // Let deferred chunks and late layout shifts land; measure the settled page.
    await page.waitForTimeout(2_500);
    const metrics = await read(page);
    console.log(`CWV_METRIC public ${JSON.stringify(metrics)}`);
    await test.info().attach('cwv-public', { body: JSON.stringify(metrics, null, 2), contentType: 'application/json' });

    expect(metrics.lcp, `LCP ${metrics.lcp.toFixed(0)}ms`).toBeGreaterThan(0);
    expect(metrics.lcp, `LCP ${metrics.lcp.toFixed(0)}ms`).toBeLessThan(BUDGETS.lcpMs);
    expect(metrics.cls, `CLS ${metrics.cls.toFixed(4)}`).toBeLessThan(BUDGETS.cls);
    expect(metrics.tbt, `TBT ${metrics.tbt.toFixed(0)}ms`).toBeLessThan(BUDGETS.tbtMs);
  });

  test('critical CSS holds the shell when the full stylesheet is unavailable', async ({ page, seed }) => {
    await page.route('**/bundle-public.css', (route) => route.abort());
    const response = await page.goto(`/i/${seed.invitation.slug}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(250);

    const critical = await page.evaluate(() => {
      const style = document.querySelector('style[data-critical]');
      const topbar = document.querySelector<HTMLElement>('.guest-topbar');
      return {
        length: style?.textContent?.length ?? 0,
        nonce: (style as HTMLStyleElement | null)?.nonce || '',
        topbarHeight: topbar?.getBoundingClientRect().height ?? 0,
      };
    });
    expect(critical.length).toBeGreaterThan(1_500);
    expect(critical.nonce).toBe(nonceOf(response));
    expect(critical.topbarHeight).toBe(56);
  });
});

test.describe('@core-web-vitals check-in', () => {
  test.use({ storageState: states.owner() });

  test('LCP, CLS and TBT stay within the Sprint 10 budgets', async ({ page, seed }) => {
    await install(page);
    const response = await page.goto(`/checkin.html?invitation=${encodeURIComponent(seed.invitation.id)}`, {
      waitUntil: 'load',
    });
    expect(response?.status()).toBe(200);
    await page.locator('#checkinSummary').waitFor({ state: 'visible' });
    await page.waitForFunction(() => !document.querySelector('#checkinSummary')?.textContent?.includes('Loading'));
    await page.waitForTimeout(2_500);
    const metrics = await read(page);
    console.log(`CWV_METRIC checkin ${JSON.stringify(metrics)}`);
    await test.info().attach('cwv-checkin', { body: JSON.stringify(metrics, null, 2), contentType: 'application/json' });

    expect(metrics.lcp, `LCP ${metrics.lcp.toFixed(0)}ms`).toBeGreaterThan(0);
    expect(metrics.lcp, `LCP ${metrics.lcp.toFixed(0)}ms`).toBeLessThan(BUDGETS.lcpMs);
    expect(metrics.cls, `CLS ${metrics.cls.toFixed(4)}`).toBeLessThan(BUDGETS.cls);
    expect(metrics.tbt, `TBT ${metrics.tbt.toFixed(0)}ms`).toBeLessThan(BUDGETS.tbtMs);
  });

  test('critical CSS holds the check-in shell when the full stylesheet is unavailable', async ({ page, seed }) => {
    await page.route('**/bundle-checkin.css', (route) => route.abort());
    const response = await page.goto(`/checkin.html?invitation=${encodeURIComponent(seed.invitation.id)}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(250);

    const critical = await page.evaluate(() => {
      const style = document.querySelector('style[data-critical]');
      const header = document.querySelector<HTMLElement>('.checkin-header');
      const shell = document.querySelector<HTMLElement>('.checkin-shell');
      const body = getComputedStyle(document.body);
      return {
        length: style?.textContent?.length ?? 0,
        nonce: (style as HTMLStyleElement | null)?.nonce || '',
        headerHeight: header?.getBoundingClientRect().height ?? 0,
        shellWidth: shell?.getBoundingClientRect().width ?? 0,
        fontFamily: body.fontFamily,
      };
    });
    expect(critical.length).toBeGreaterThan(1_500);
    expect(critical.nonce).toBe(nonceOf(response));
    expect(critical.headerHeight).toBe(56);
    expect(critical.shellWidth).toBe(480);
    expect(critical.fontFamily).toContain('Inter');
  });

  test('startup does not request editor or public-page bundles', async ({ page, seed }) => {
    await page.goto(`/checkin.html?invitation=${encodeURIComponent(seed.invitation.id)}`, {
      waitUntil: 'load',
    });
    await page.waitForTimeout(250);
    const scripts = await page.evaluate(() =>
      performance
        .getEntriesByType('resource')
        .filter((entry) => entry.name.endsWith('.js'))
        .map((entry) => entry.name.split('/').pop() || ''),
    );
    expect(scripts).toContain('bundle-checkin.js');
    expect(scripts.filter((name) => /bundle-(index|templates|public|dashboard)/.test(name))).toEqual([]);
  });
});
