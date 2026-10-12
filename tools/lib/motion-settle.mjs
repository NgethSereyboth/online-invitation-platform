/**
 * motion-settle.js — wait for a forced state's motion to finish before reading.
 *
 * This file is injected into the page as a plain script (no imports), so every
 * probe that samples a computed style after forcing a state reads the SETTLED
 * value rather than a mid-interpolation frame. Node callers read the file and
 * `page.addScriptTag({ content })` it; after that `globalThis.MotionSettle`
 * exists.
 *
 * The defect this exists to prevent
 * ---------------------------------
 * A property with a running transition makes `getComputedStyle` return the
 * *interpolated* value, which is a function of when you sample rather than of the
 * CSS. `tools/lib/browser.mjs` `freezeMotion()` zeroes `transition-duration
 * !important`, but some route bundles re-declare `transition:...!important` and
 * win the cascade, so the freeze does not always take effect. Waiting for the
 * animation to finish is independent of who wins the cascade.
 *
 * Measured cost of not doing this (hover-audit.mjs, which fixed the same defect
 * one probe earlier): two runs of an unchanged page disagreed on 72 of 813 hover
 * rows, all `transform` matrices a few thousandths apart — a noise floor that
 * hides a real regression and makes "this change altered nothing" unfalsifiable.
 *
 * The same defect one probe later: `important-lift-test.mjs` forced `:hover` and
 * read immediately, so its per-declaration verdict was unstable. Five runs over
 * the SAME page and the SAME tree (artifacts/lift-index-before-run{1,2}.json and
 * artifacts/unanimity-demo/lift-index*.json, this pass's §1.1) split on three
 * declarations — `.studio-rail-button:hover {background}`, `.studio-rail-button
 * :hover {color}` and `.flow-action-grid button:hover {transform}` — each either
 * `redundant` (0 computed-value differences) or `load-bearing` (3–10) depending
 * on the run. The diff counts of the declarations that did not flip wobbled too
 * (9 → 98 on one `transform`), which is the same interpolation signature.
 *
 * The sequence (order matters, and each step is why the next one works)
 *   1. one `requestAnimationFrame`: a CSS transition does not enter
 *      `getAnimations()` until the forced pseudo-state has been recalculated, so
 *      settling immediately after `CSS.forcePseudoState` samples an empty list
 *      and then reads a value the transition is still moving;
 *   2. await every *finite* running animation on every element being read —
 *      infinite animations (spinners, `forwards` ripples) never finish, so they
 *      are excluded, and a hard cap keeps one stuck element from stalling the
 *      sweep;
 *   3. two more frames, so the settled value is committed to the style system
 *      before the read, not merely scheduled.
 *
 * Not `document.getAnimations()`: settling only the elements a probe is about to
 * read keeps the wait proportional to the measurement, and avoids waiting on a
 * page-wide spinner that will never stop.
 */
export const MOTION_SETTLE_SOURCE = String.raw`
globalThis.MotionSettle = (() => {
  const finiteRunning = (el) => {
    if (!el || !el.getAnimations) return [];
    let all;
    try { all = el.getAnimations(); } catch { return []; }
    return all.filter((a) => a.playState === 'running' && a.effect
      && a.effect.getTiming().iterations !== Infinity);
  };

  const settleOne = (el) => {
    const running = finiteRunning(el);
    if (!running.length) return Promise.resolve(0);
    return Promise.race([
      Promise.allSettled(running.map((a) => a.finished)),
      new Promise((r) => setTimeout(r, 500)),
    ]).then(() => running.length);
  };

  const stats = { calls: 0, elementsSettled: 0, motionFound: 0 };

  return {
    finiteRunning,
    stats,
    /**
     * Resolve once every finite animation on every supplied element has finished
     * (or the per-element cap elapsed). Returns the number of elements that were
     * mid-motion when it was called, so a caller can report whether the fix was
     * exercised rather than merely present.
     */
    async settleAll(els) {
      const list = (els || []).filter(Boolean);
      stats.calls++;
      stats.elementsSettled += list.length;
      await new Promise((r) => requestAnimationFrame(r));
      const counts = await Promise.all(list.map(settleOne));
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      const motion = counts.reduce((n, c) => n + c, 0);
      stats.motionFound += motion;
      return motion;
    },
  };
})();
`;
