/**
 * module-loading-strategy.mjs — read the loading strategy a page *declares in its
 * HTML* (not what happened at runtime) and print it as one row per URL.
 *
 * Why this exists
 * ---------------
 * Goal 0 of the Canva-analysis pass compares how Canva loads its editor code with
 * how this project loads its own (`performance-loader-v22.js` and the route
 * bundles). The runtime view of that question is already covered by two existing
 * artifacts — `canva-scripts.json` (what the network delivered, with byte sizes)
 * and the CDP trace (when each request started) — but neither says what the page
 * *asked for*: `async`, `defer`, `type=module`, `rel=modulepreload` and
 * `rel=preload as=script` are HTML-level declarations, and they are the part a
 * project can actually change.
 *
 * So this tool reads the document's HTML and counts those declarations.
 *
 * Why it reads the DOM and not `fetch()`
 * --------------------------------------
 * The first version of this tool fetched the HTML with `fetch()`. Measured, that
 * is wrong for the remote side: `node -e fetch('https://www.canva.com/')` returns
 * **403** and a 755 KB bot-wall document with three inline scripts and no `src`
 * script at all — so the tool would have reported "Canva ships no scripts", which
 * is an artifact of this host, not a finding. A real browser on the same host gets
 * 200 (`artifacts/canva-probe-summary.json`). The tool therefore drives the repo's
 * browser (`tools/lib/browser.mjs`) and reads
 * `document.documentElement.outerHTML`, which is the document the site actually
 * served to a browser; `status` is the response's own status, so a wall remains
 * visible as a number instead of as an empty inventory.
 *
 * One consequence, stated because it changes what the numbers mean: the DOM is
 * read after the parser and after early script execution, so a `src` script that
 * JavaScript injects at load time is counted too. That is closer to "what the page
 * loads" than the raw HTML is, and it is the same rule on both sides of the
 * comparison.
 *
 * What it reports, per URL
 *   declared           <script>/<link> tags in the document's **own HTML text**, read
 *                      by re-fetching the document from inside the page (same origin,
 *                      so the site's own cookies and cache apply). This is the set a
 *                      project can edit.
 *   dom                the same counts over `document.querySelectorAll` after load,
 *                      which additionally sees every script the page injects.
 *   scripts.parserBlocking
 *                      declared `src` scripts with no async, defer or type=module:
 *                      the only ones that can block the parser.
 *
 * Why both, measured
 * ------------------
 * The second version of this tool counted the DOM only, and reported that
 * `index.html` ships 37 parser-blocking scripts. That was wrong by an order of
 * magnitude: the *served HTML* declares three (`core/theme.js`,
 * `backend-mode-v14.js`, `bundle-index-v15.js`), and the other 34 are created by
 * `src/js/performance-loader-v22.js` with `document.createElement('script')` after
 * the parser has finished — a script created that way cannot block a parser that
 * has already parsed the document. Reporting the DOM count as "parser-blocking"
 * would have invented a gap in the project's favour and against it, so the tool now
 * reports the declared set and the injected set separately and says which is which.
 *
 * Usage
 *   node tools/module-loading-strategy.mjs https://www.canva.com/ --label=canva
 *   node tools/module-loading-strategy.mjs --pages=index.html,public.html --label=project
 *   node tools/module-loading-strategy.mjs https://www.canva.com/ --json
 *
 * Writes artifacts/module-loading-<label>.json; prints one row per URL.
 *
 * A real desktop UA is used for the remote case for the same reason the other
 * tools use one: this host's headless Chrome default invites a bot wall, and a bot
 * wall's HTML would be measured instead of the site's.
 */
import { writeFileSync } from 'node:fs';

import { artifactPath, argValue, hasFlag, pageUrl } from './lib/repo.mjs';
import { launch, newPage } from './lib/browser.mjs';

const UA =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/154.0.0.0 Safari/537.36';

const argv = process.argv.slice(2);
const LABEL = String(argValue(argv, 'label', 'run'));
const AS_JSON = hasFlag(argv, 'json');
const pagesFlag = argValue(argv, 'pages', null);
const positional = argv.filter((a) => !a.startsWith('--'));

const TARGETS = pagesFlag
  ? String(pagesFlag)
      .split(',')
      .map((p) => p.trim())
      .filter(Boolean)
      .map((p) => pageUrl(p))
  : positional.length
    ? positional
    : ['https://www.canva.com/'];

const ATTRIBUTE = (tag, name) => {
  const hit = new RegExp(`\\b${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, 'i').exec(tag);
  if (!hit) return null;
  return hit[2] ?? hit[3] ?? hit[4] ?? '';
};

const TAGS = (html, name) =>
  [...html.matchAll(new RegExp(`<${name}\\b[^>]*>`, 'gi'))].map((m) => m[0]);

/** The last path segment, which is what Canva's own chunk names are. */
const shortName = (url) => {
  try {
    const u = new URL(url);
    return u.pathname.split('/').filter(Boolean).pop() || u.host;
  } catch {
    return url;
  }
};

async function describe(browser, url) {
  const page = await newPage(browser, { width: 1440, height: 900 });
  await page.setUserAgent(UA);
  let status = null;
  try {
    const response = await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
    status = response ? response.status() : null;
  } catch (error) {
    // A failure to reach `networkidle2` still leaves a usable document; record it
    // and measure what did arrive rather than losing the row.
    status = `error: ${error && error.message ? error.message.slice(0, 80) : error}`;
  }
  await new Promise((resolve) => setTimeout(resolve, WAIT));
  const finalUrl = page.url();

  // The declared set: the document's own HTML text, re-fetched from inside the page
  // so the request is same-origin and carries whatever the site set for itself.
  const declaredHtml = await page.evaluate(async () => {
    try {
      const r = await fetch(location.href, { credentials: 'same-origin', cache: 'force-cache' });
      return r.ok ? await r.text() : `__FETCH_${r.status}`;
    } catch (error) {
      return `__FETCH_ERROR_${String(error && error.message ? error.message : error).slice(0, 60)}`;
    }
  });

  // The live set: what is in the DOM now, with the two markers that say whether the
  // parser created the element (`dynamic` false) or API code did.
  // When each script was fetched, relative to the document's own timeline. This is
  // what turns "the loader chain is serial" into a number: a serial chain shows as
  // spans that barely overlap, and `chainSerialGapMs` is the wall clock the chain
  // would save if the fetches overlapped instead.
  const timing = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation')[0] || null;
    const paint = Object.fromEntries(
      performance.getEntriesByType('paint').map((p) => [p.name, Math.round(p.startTime)]),
    );
    const byName = new Map();
    for (const entry of performance.getEntriesByType('resource')) {
      if (entry.initiatorType !== 'script' && !/\.js(\?|$)/.test(entry.name)) continue;
      byName.set(new URL(entry.name).pathname, {
        start: Math.round(entry.startTime),
        end: Math.round(entry.responseEnd),
        duration: Math.round(entry.duration),
        transferSize: entry.transferSize ?? 0,
      });
    }
    return {
      domContentLoaded: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
      loadEventEnd: nav ? Math.round(nav.loadEventEnd) : null,
      responseEnd: nav ? Math.round(nav.responseEnd) : null,
      paint,
      scripts: Object.fromEntries(byName),
    };
  });

  const domScripts = await page.evaluate(() =>
    [...document.querySelectorAll('script[src], link[rel]')].map((el) =>
      el.tagName === 'SCRIPT'
        ? {
            kind: 'script',
            src: el.getAttribute('src') || '',
            resolved: el.src,
            type: (el.getAttribute('type') || '').toLowerCase(),
            asyncAttr: el.hasAttribute('async'),
            deferAttr: el.hasAttribute('defer'),
            idlAsync: el.async === true,
            // Per HTML's "prepare a script", an API-created script defaults to
            // async=true with no attribute present; a parser-created one does not.
            dynamic: !el.hasAttribute('async') && el.async === true,
          }
        : {
            kind: 'link',
            rel: (el.getAttribute('rel') || '').toLowerCase(),
            as: (el.getAttribute('as') || '').toLowerCase(),
            href: el.getAttribute('href') || '',
          },
    ),
  );
  await page.close();

  const html = declaredHtml.startsWith('__') ? '' : declaredHtml;
  const declaredOk = !declaredHtml.startsWith('__');
  const scripts = TAGS(html, 'script');
  const links = TAGS(html, 'link');

  const srcScripts = scripts
    .map((tag) => ({
      tag,
      src: ATTRIBUTE(tag, 'src'),
      type: (ATTRIBUTE(tag, 'type') || '').toLowerCase(),
      async: /\basync\b/i.test(tag),
      defer: /\bdefer\b/i.test(tag),
    }))
    .filter((s) => s.src);

  const domScriptsOnly = domScripts.filter((s) => s.kind === 'script' && s.src);
  const domInjected = domScriptsOnly.filter((s) => s.dynamic);
  const domParser = domScriptsOnly.filter((s) => !s.dynamic);

  // A declared script is "parser-blocking" when the tag carries none of the three
  // attributes that lift it off the parser's critical path.
  const declaredBlocking = srcScripts.filter(
    (s) => s.type !== 'module' && !s.async && !s.defer,
  );

  const declaredSrcs = new Set(srcScripts.map((s) => s.src));
  const injected = domScriptsOnly.filter(
    (s) => !declaredSrcs.has(s.src) && !declaredSrcs.has(s.resolved),
  );

  const preloads = links
    .map((tag) => ({
      rel: (ATTRIBUTE(tag, 'rel') || '').toLowerCase(),
      as: (ATTRIBUTE(tag, 'as') || '').toLowerCase(),
      href: ATTRIBUTE(tag, 'href') || '',
    }))
    .filter((l) => l.rel === 'preload' || l.rel === 'modulepreload' || l.rel === 'prefetch');

  const module = srcScripts.filter((s) => s.type === 'module');
  const asyncScripts = srcScripts.filter((s) => s.async);
  const deferScripts = srcScripts.filter((s) => s.defer);
  const preloadDeclared = TAGS(html, 'link')
    .map((tag) => ({
      rel: (ATTRIBUTE(tag, 'rel') || '').toLowerCase(),
      as: (ATTRIBUTE(tag, 'as') || '').toLowerCase(),
      href: ATTRIBUTE(tag, 'href') || '',
    }))
    .filter((l) => l.rel === 'preload' || l.rel === 'modulepreload' || l.rel === 'prefetch');

  const entryChain = [...module, ...asyncScripts.filter((s) => s.type !== 'module')].map((s) => ({
    url: s.src,
    name: shortName(s.src),
    kind: s.type === 'module' ? 'module' : 'async',
  }));

  // The chain, in document order, with its own timing. `serial` is measured, not
  // assumed: the span minus the sum of the individual durations is time the chain
  // spent waiting for the previous script rather than transferring.
  const chainNames = [...srcScripts, ...injected].map((s) => shortName(s.resolved || s.src));
  const timed = chainNames
    .map((name) => {
      const hit = Object.entries(timing.scripts).find(([path]) => path.endsWith(`/${name}`));
      return hit ? { name, ...hit[1] } : null;
    })
    .filter(Boolean)
    .sort((a, b) => a.start - b.start);
  const chainSpanMs = timed.length ? timed.at(-1).end - timed[0].start : 0;
  const chainTransferMs = timed.reduce((sum, t) => sum + t.duration, 0);

  return {
    url,
    finalUrl,
    status,
    documentBytes: Buffer.byteLength(html),
    timing: {
      domContentLoaded: timing.domContentLoaded,
      loadEventEnd: timing.loadEventEnd,
      paint: timing.paint,
      scriptsTimed: timed.length,
      chainSpanMs,
      chainTransferMs,
      chainSerialGapMs: chainSpanMs - chainTransferMs,
      lastChainScriptEnd: timed.length ? timed.at(-1).end : null,
      longestScripts: [...timed].sort((a, b) => b.duration - a.duration).slice(0, 5),
    },
    declaredReadable: declaredOk,
    declaredReadError: declaredOk ? null : declaredHtml.slice(0, 80),
    title: (/<title[^>]*>([^<]*)</i.exec(html) || [])[1] || null,
    declared: {
      scriptsTotal: scripts.length,
      inline: scripts.length - srcScripts.length,
      src: srcScripts.length,
      module: module.length,
      async: asyncScripts.length,
      defer: deferScripts.length,
      parserBlocking: declaredBlocking.length,
      parserBlockingNames: declaredBlocking.map((s) => shortName(s.src)),
      srcNames: srcScripts.map((s) => shortName(s.src)),
    },
    dom: {
      srcScripts: domScriptsOnly.length,
      parserCreated: domParser.length,
      injected: injected.length,
      injectedNames: injected.map((s) => shortName(s.resolved || s.src)),
      idlRuleAgrees: injected.length === domInjected.length,
      srcNames: domScriptsOnly.map((s) => shortName(s.resolved || s.src)),
    },
    preload: {
      declaredModule: preloadDeclared.filter((l) => l.rel === 'modulepreload').length,
      declaredScript: preloadDeclared.filter((l) => l.rel === 'preload' && l.as === 'script').length,
      declaredStyle: preloadDeclared.filter((l) => l.rel === 'preload' && l.as === 'style').length,
      declaredOther: preloadDeclared.filter(
        (l) => l.rel === 'preload' && !['script', 'style'].includes(l.as),
      ).length,
      declaredPrefetch: preloadDeclared.filter((l) => l.rel === 'prefetch').length,
      declaredTotal: preloadDeclared.length,
      domTotal: domScripts.filter((s) => s.kind === 'link').length,
    },
    entryChain,
  };
}

const WAIT = Number(argValue(argv, 'wait', 2500));

const browser = await launch({
  kind: 'full',
  extraArgs: ['--disable-blink-features=AutomationControlled'],
});

const rows = [];
for (const target of TARGETS) {
  process.stdout.write(`  ${target} … `);
  try {
    const row = await describe(browser, target);
    rows.push({ ...row, error: null });
    process.stdout.write(`${row.status}\n`);
  } catch (error) {
    rows.push({ url: target, error: String(error && error.message ? error.message : error) });
    process.stdout.write(`ERROR ${rows.at(-1).error}\n`);
  }
}

await browser.close();

const payload = { label: LABEL, ua: UA, count: rows.length, targets: TARGETS, rows };
writeFileSync(artifactPath(`module-loading-${LABEL}.json`), JSON.stringify(payload, null, 1));

if (AS_JSON) {
  console.log(JSON.stringify(payload, null, 1));
} else {
  console.log(`\nMODULE_LOADING_STRATEGY label=${LABEL} targets=${rows.length}`);
  for (const row of rows) {
    if (row.error) {
      console.log(`  ${row.url}\n    ERROR ${row.error}`);
      continue;
    }
    const d = row.declared;
    const m = row.dom;
    const p = row.preload;
    console.log(
      `  ${row.status} ${row.url}\n` +
        `    documentBytes=${row.documentBytes} declaredReadable=${row.declaredReadable}\n` +
        `    DECLARED scripts=${d.scriptsTotal} (inline=${d.inline} src=${d.src}) ` +
        `module=${d.module} async=${d.async} defer=${d.defer} parserBlocking=${d.parserBlocking}\n` +
        `    DOM srcScripts=${m.srcScripts} parserCreated=${m.parserCreated} injected=${m.injected}\n` +
        `    preload(declared) module=${p.declaredModule} script=${p.declaredScript} ` +
        `style=${p.declaredStyle} other=${p.declaredOther} prefetch=${p.declaredPrefetch} total=${p.declaredTotal}\n` +
        `    TIMING dcl=${row.timing.domContentLoaded} load=${row.timing.loadEventEnd} ` +
        `paint=${JSON.stringify(row.timing.paint)} scriptsTimed=${row.timing.scriptsTimed}\n` +
        `    CHAIN span=${row.timing.chainSpanMs}ms transfer=${row.timing.chainTransferMs}ms ` +
        `serialGap=${row.timing.chainSerialGapMs}ms lastEnd=${row.timing.lastChainScriptEnd}ms\n` +
        `    parserBlocking srcs: ${d.parserBlockingNames.slice(0, 10).join(', ') || '(none)'}`,
    );
    if (m.injectedNames.length) {
      console.log(`    injected srcs: ${m.injectedNames.slice(0, 10).join(', ')}${m.injectedNames.length > 10 ? ' …' : ''}`);
    }
  }
}
