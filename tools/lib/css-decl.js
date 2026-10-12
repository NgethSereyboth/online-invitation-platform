/**
 * css-decl.js — enumerate a CSSStyleDeclaration at DECLARATION level, not longhand level.
 *
 * This file is injected into the page as a plain script (no imports), so both the
 * self-check and the sweep use one implementation. Node callers read the file and
 * `page.addScriptTag({ content })` it; after that `globalThis.CssDecl` exists.
 *
 * The defect this exists to prevent
 * ---------------------------------
 * `CSSStyleDeclaration`'s indexed properties are longhands. `rule.style[0]` for
 *
 *     .ui-theme-menu button:hover { background: var(--app-surface-3) !important; transform: none !important }
 *
 * reports `background-image`, `background-position-x`, ... `background-color`,
 * `transform` — a `style.length` of 10 for two authored declarations. An
 * instrument that iterates `rule.style[i]` therefore reports one authored
 * `!important` as nine independent candidates: eight inert and one load-bearing,
 * where removing the eight deletes the ninth's effect. Measured on this Chrome
 * (see tools/css-declaration-granularity.mjs):
 *
 *     style.length   = 10
 *     style.cssText  = "background: var(--app-surface-3) !important; transform: none !important;"
 *
 * So the serialized form preserves what was authored, and the declarations are
 * read from there. The longhand expansion is still reported, as a count per
 * declaration, so the grouping is visible rather than lost.
 *
 * `expansionOf` measures a shorthand's expansion the same way a style rule does:
 * by parsing the declaration into a throwaway stylesheet and counting the
 * longhands Blink produces for that exact value — including a shorthand whose
 * value is a pending `var()` substitution, which expands to the same longhand
 * names with empty values that the rule under test shows.
 */
(function () {
  /** Split on `sep` only at nesting depth 0, ignoring separators inside quotes. */
  function splitTop(text, sep) {
    const out = [];
    let depth = 0;
    let quote = null;
    let start = 0;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quote) {
        if (c === '\\') { i++; continue; }
        if (c === quote) quote = null;
        continue;
      }
      if (c === '"' || c === "'") { quote = c; continue; }
      if (c === '(' || c === '[' || c === '{') depth++;
      else if (c === ')' || c === ']' || c === '}') depth = Math.max(0, depth - 1);
      else if (c === sep && depth === 0) { out.push(text.slice(start, i)); start = i + 1; }
    }
    out.push(text.slice(start));
    return out;
  }

  /**
   * "background: none !important; color: red" -> two declarations, each with its
   * authored text preserved so a rule can be rebuilt without one of them.
   */
  function parseDeclarations(cssText) {
    const out = [];
    for (const chunk of splitTop(cssText || '', ';')) {
      const text = chunk.trim();
      if (!text) continue;
      const colon = text.indexOf(':');
      if (colon <= 0) continue;
      const name = text.slice(0, colon).trim();
      let value = text.slice(colon + 1).trim();
      let important = false;
      const m = /!\s*important\s*$/i.exec(value);
      if (m) {
        important = true;
        value = value.slice(0, m.index).trim();
      }
      out.push({ name, value, important, text });
    }
    return out;
  }

  let probeStyle = null;
  function probeHost() {
    if (probeStyle && probeStyle.isConnected) return probeStyle;
    probeStyle = document.createElement('style');
    (document.head || document.documentElement).appendChild(probeStyle);
    return probeStyle;
  }

  const expansionCache = new Map();

  /**
   * The longhand names a declaration expands to, measured by the browser.
   * Caveat, measured not assumed: a longhand (`transform: none`) expands to
   * itself, so `names.length === 1 && names[0] === name` is "not a shorthand".
   */
  function expansionOf(name, value) {
    const key = name + '\u0000' + value;
    const hit = expansionCache.get(key);
    if (hit) return hit;
    const host = probeHost();
    host.textContent = 'css-decl-probe{' + name + ': ' + value + ' !important}';
    let names = [name];
    let serialized = null;
    try {
      const rule = host.sheet.cssRules[0];
      names = [];
      for (let i = 0; i < rule.style.length; i++) names.push(rule.style[i]);
      serialized = rule.style.cssText;
      if (!names.length) names = [name];
    } catch {
      names = [name];
    }
    host.textContent = '';
    const result = { names, serialized };
    expansionCache.set(key, result);
    return result;
  }

  /** Authored declarations of a live rule, each with its longhand expansion. */
  function declarationsOf(rule) {
    const original = rule.style.cssText;
    const parsed = parseDeclarations(original).map((d) => {
      const ex = expansionOf(d.name, d.value);
      return { ...d, longhands: ex.names, isShorthand: !(ex.names.length === 1 && ex.names[0] === d.name) };
    });
    return { original, declarations: parsed };
  }

  /** Longhand names the rule currently exposes, whatever their origin. */
  function longhandNamesOf(rule) {
    const names = [];
    for (let i = 0; i < rule.style.length; i++) names.push(rule.style[i]);
    return names;
  }

  globalThis.CssDecl = { splitTop, parseDeclarations, expansionOf, declarationsOf, longhandNamesOf };
})();
