/**
 * inline-editor.js — Inline rich text editing layer for EInvite studio (v56).
 *
 * Double-click a text element on the canvas → a transparent contenteditable
 * layer is mounted exactly over the rendered text. While editing:
 *
 *   • Ctrl+B / Ctrl+I / Ctrl+U toggle bold / italic / underline via
 *     `document.execCommand` (deprecated but universally supported — see
 *     ROADMAP-v0.54-to-v1.0 §3.2.1; do NOT chase InputEvent APIs).
 *   • Range + `surroundContents` is used to apply color / font-family /
 *     font-size to the current selection.
 *   • Khmer: `letter-spacing` is disabled while editing (Khmer shaping breaks
 *     under spacing). The `.inline-editor:lang(km)` CSS rule handles this.
 *
 * On commit (Escape / blur / click outside):
 *
 *   • The HTML is run through `InlineEditor.sanitize()` — a pure function that
 *     mirrors the server-side `_RichTextSanitizer` and strips every tag
 *     except `<b>`, `<i>`, `<u>`, `<strong>`, `<em>`,
 *     `<span style="color:...">`, and `<br>`.
 *   • The sanitized HTML is written back to the document model via the editor
 *     bridge, the underlying canvas text is re-rendered, and the
 *     contenteditable layer is destroyed.
 *
 * The module is idempotent — second load is a no-op (guarded by
 * `window.EInviteInlineEditor?.version`). It is also safe to load on
 * non-designer routes: if the editor bridge / canvas are missing the module
 * exposes its pure helpers but does not bind any listeners.
 */
(() => {
  'use strict';

  if (window.EInviteInlineEditor?.version >= 56) return;

  /** Public namespace. Pure helpers (sanitize, format selection) are exposed
   *  so unit tests can drive them without the editor DOM. */
  const api = { version: 56, destroy: null, sanitize: null, formatSelection: null, beginEdit: null, commit: null };

  // --- Pure HTML sanitizer --------------------------------------------------
  // Tags that are kept verbatim (their attributes are filtered). Matches the
  // server-side `_ALLOWED_RICH_TAGS` minus the link tag — inline editing does
  // not produce links (the user types text, not URLs). The server-side
  // sanitizer remains authoritative on save.
  const ALLOWED_TAGS = new Set(['b', 'i', 'u', 'strong', 'em', 'span', 'br']);
  // Tags whose entire subtree is dropped (script, iframe, …) — mirrors
  // server-side `_DROP_RICH_TAGS` for parity.
  const DROP_TAGS = new Set([
    'script', 'style', 'iframe', 'object', 'embed', 'svg', 'math',
    'template', 'noscript', 'form', 'input', 'button', 'textarea', 'select',
    'meta', 'link', 'base', 'title', 'head', 'html', 'body',
  ]);
  // Allowed style properties on a `<span>`. Server-side allows a broader
  // set (background-color, font-weight, etc.) but inline editing only
  // produces color — keep the client-side surface tight.
  const ALLOWED_STYLES = new Set(['color']);
  // Safe style value charset — letters, digits, #, %, -, spaces, parens (rgb()).
  const SAFE_STYLE_VALUE = /^[#(),.%\-\s\w]+$/;

  /** Escape a string for HTML text insertion. */
  function escText(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }
  /** Escape a string for use inside a double-quoted attribute. */
  function escAttr(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  /**
   * Sanitize a rich-text HTML fragment client-side.
   *
   * Strips everything except the allowed tag set, drops the entire subtree
   * of dangerous tags (`<script>`, `<iframe>`, …), filters `<span>` styles
   * down to `color: <safe-value>`.
   *
   * @param {string} html Raw HTML from the contenteditable layer.
   * @returns {string} Sanitized HTML safe to store in the document model.
   */
  function sanitize(html) {
    if (html == null) return '';
    const wrapped = `<div id="root">${String(html)}</div>`;
    const doc = new DOMParser().parseFromString(wrapped, 'text/html');
    const root = doc.getElementById('root') || doc.body;
    return walk(root);
  }

  /** Walk a DOM node, emitting only safe tags + escaped text. */
  function walk(node) {
    let out = '';
    node.childNodes.forEach(child => {
      if (child.nodeType === Node.TEXT_NODE) {
        out += escText(child.nodeValue);
        return;
      }
      if (child.nodeType !== Node.ELEMENT_NODE) return; // comments, PIs dropped
      const tag = child.tagName.toLowerCase();
      if (DROP_TAGS.has(tag)) return; // entire subtree dropped
      if (tag === 'br') { out += '<br>'; return; }
      if (!ALLOWED_TAGS.has(tag)) {
        // Unknown tag — keep its children (text content), drop the tag itself.
        out += walk(child);
        return;
      }
      // Filter attributes for span (style only); all others drop attrs.
      let attrs = '';
      if (tag === 'span') {
        const style = filterSpanStyle(child.getAttribute('style') || '');
        if (style) attrs = ` style="${escAttr(style)}"`;
      }
      out += `<${tag}${attrs}>`;
      out += walk(child);
      // `<br>` is void; everything else gets a close tag.
      if (tag !== 'br') out += `</${tag}>`;
    });
    return out;
  }

  /** Filter a `style="..."` attribute on a span down to `color: value`. */
  function filterSpanStyle(rawStyle) {
    const safe = [];
    for (const decl of String(rawStyle || '').split(';')) {
      if (!decl.includes(':')) continue;
      const idx = decl.indexOf(':');
      const name = decl.slice(0, idx).trim().toLowerCase();
      const value = decl.slice(idx + 1).trim();
      if (!ALLOWED_STYLES.has(name)) continue;
      if (!value || !SAFE_STYLE_VALUE.test(value)) continue;
      const lowered = value.toLowerCase().replace(/\s+/g, '');
      if (lowered.includes('url(') || lowered.includes('expression(') || lowered.includes('javascript:')) continue;
      safe.push(`${name}:${value}`);
    }
    return safe.join(';');
  }

  // --- Editor binding -------------------------------------------------------
  // Late-binding globals — captured lazily so the module can be loaded before
  // the editor-core bundle is fully initialised.
  const bridge = () => window.EInviteEditorBridge;
  const schema = () => window.EInviteEditorSchema;
  const controller = () => window.EInviteCanvasViewController;

  /** Currently active contenteditable layer (or null). */
  let activeLayer = null;
  /** The object id we are currently editing. */
  let activeObjectId = null;
  /** Snapshot of the original HTML before editing (for Escape-cancel). */
  let originalHtml = null;
  /** Stack of removable event listeners. */
  const listeners = [];

  /** Get the canvas stage element. */
  function getStage() {
    return document.querySelector('#canvasViewport .stage, #stage, .stage-wrap');
  }

  /** Find the DOM node for a given object id. */
  function findObjectNode(objectId) {
    return document.querySelector(`[data-object-id="${CSS.escape(objectId)}"]`);
  }

  /** Begin editing a text element by id (or DOM node). */
  function beginEdit(target) {
    if (activeLayer) commit();
    const node = typeof target === 'string' ? findObjectNode(target) : target;
    if (!node) return null;
    const objectId = node.getAttribute('data-object-id') || node.id;
    if (!objectId) return null;
    const b = bridge();
    if (!b) return null;

    const doc = b.getDocument?.() || b.doc || {};
    const obj = (b.getObjectById?.(objectId) || findObjectInDoc(doc, objectId));
    if (!obj || obj.type !== 'text') return null;

    activeObjectId = objectId;
    originalHtml = obj.html || obj.text || node.textContent || '';

    // Build the contenteditable overlay — positioned exactly over the text
    // node, transparent background, no border, inherits font metrics.
    const layer = document.createElement('div');
    layer.className = 'inline-editor';
    layer.setAttribute('contenteditable', 'true');
    layer.setAttribute('spellcheck', 'false');
    layer.setAttribute('role', 'textbox');
    layer.setAttribute('aria-multiline', 'true');
    layer.setAttribute('aria-label', 'Inline text editor');
    // Copy the rendered font metrics from the source node so caret and text
    // align with the underlying canvas text.
    const cs = window.getComputedStyle(node);
    layer.style.fontFamily = cs.fontFamily;
    layer.style.fontSize = cs.fontSize;
    layer.style.fontWeight = cs.fontWeight;
    layer.style.fontStyle = cs.fontStyle;
    layer.style.color = cs.color;
    layer.style.textAlign = cs.textAlign;
    layer.style.lineHeight = cs.lineHeight;
    layer.style.letterSpacing = 'normal'; // Khmer-safe: no spacing while typing
    // Place over the source node.
    const rect = node.getBoundingClientRect();
    const stage = getStage();
    const stageRect = stage ? stage.getBoundingClientRect() : { left: 0, top: 0 };
    layer.style.left = `${rect.left - stageRect.left}px`;
    layer.style.top = `${rect.top - stageRect.top}px`;
    layer.style.width = `${rect.width}px`;
    layer.style.height = `${rect.height}px`;
    layer.innerHTML = sanitize(originalHtml) || escText(originalHtml);
    if (stage) stage.appendChild(layer); else document.body.appendChild(layer);
    activeLayer = layer;

    // Hide underlying canvas text to avoid double rendering.
    node.classList.add('inline-editing-source');

    // Listeners.
    bind(layer, 'keydown', onKey);
    bind(layer, 'blur', () => commit(), true);
    bind(document, 'mousedown', onOutsideClick, true);

    // Focus + place caret at end.
    layer.focus();
    const sel = window.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    range.selectNodeContents(layer);
    range.collapse(false);
    sel.addRange(range);

    return layer;
  }

  /** Find an object anywhere in the editor document (hero + pages). */
  function findObjectInDoc(doc, objectId) {
    if (!doc) return null;
    const hero = (doc.objects || {})[objectId];
    if (hero) return hero;
    for (const page of doc.designPages || []) {
      const obj = (page.objects || {})[objectId];
      if (obj) return obj;
    }
    return null;
  }

  /** Bind an event and remember how to remove it. */
  function bind(target, type, fn, options) {
    target.addEventListener(type, fn, options);
    listeners.push(() => target.removeEventListener(type, fn, options));
  }

  /** Keydown handler — Ctrl+B/I/U + Escape commit / cancel. */
  function onKey(event) {
    const mod = event.ctrlKey || event.metaKey;
    if (mod && (event.key === 'b' || event.key === 'B')) {
      event.preventDefault();
      document.execCommand('bold', false, null);
      return;
    }
    if (mod && (event.key === 'i' || event.key === 'I')) {
      event.preventDefault();
      document.execCommand('italic', false, null);
      return;
    }
    if (mod && (event.key === 'u' || event.key === 'U')) {
      event.preventDefault();
      document.execCommand('underline', false, null);
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      // Escape cancels — restore original HTML without committing.
      cancel();
      return;
    }
    if (mod && event.key === 'Enter') {
      // Ctrl+Enter commits.
      event.preventDefault();
      commit();
    }
  }

  /** Click outside the layer → commit. */
  function onOutsideClick(event) {
    if (!activeLayer) return;
    if (activeLayer.contains(event.target)) return;
    commit();
  }

  /** Cancel editing — restore original HTML, do not commit. */
  function cancel() {
    if (!activeLayer) return;
    const id = activeObjectId;
    destroyLayer();
    const node = id ? findObjectNode(id) : null;
    node?.classList.remove('inline-editing-source');
  }

  /** Destroy the contenteditable layer + unbind listeners. */
  function destroyLayer() {
    if (!activeLayer) return;
    while (listeners.length) listeners.pop()();
    activeLayer.remove();
    activeLayer = null;
    activeObjectId = null;
    originalHtml = null;
  }

  /** Commit the current HTML to the document model + re-render. */
  function commit() {
    if (!activeLayer || !activeObjectId) return null;
    const rawHtml = activeLayer.innerHTML;
    const clean = sanitize(rawHtml);
    const b = bridge();
    const c = controller();
    const id = activeObjectId;
    // Update the document model via the bridge.
    if (b?.updateObject) {
      b.updateObject(id, { html: clean, text: textFromHtml(clean) });
    } else if (b?.getObjectById) {
      const obj = b.getObjectById(id);
      if (obj) { obj.html = clean; obj.text = textFromHtml(clean); }
    }
    destroyLayer();
    // Re-render the underlying canvas text node (hide the editing class).
    const node = findObjectNode(id);
    if (node) {
      node.classList.remove('inline-editing-source');
      // Trigger re-render via the controller if present.
      c?.renderObject?.(id);
    }
    return clean;
  }

  /** Extract plain text from an HTML fragment (used for the `text` field). */
  function textFromHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = String(html || '');
    // `<br>` → newline so multi-line text round-trips.
    tmp.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
    return tmp.textContent || '';
  }

  /**
   * Apply a style (color / font-family / font-size) to the current selection.
   * Uses Range + surroundContents so the wrapping span is well-formed. Falls
   * back to execCommand('foreColor', ...) if no Range is selected.
   * @param {object} style E.g. `{ color: '#ff0', fontFamily: 'Inter', fontSize: '24px' }`
   */
  function formatSelection(style) {
    if (!activeLayer) return false;
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return false;
    const range = sel.getRangeAt(0);
    if (range.collapsed) return false;
    const span = document.createElement('span');
    const styleStr = Object.entries(style || {})
      .filter(([name, value]) => ALLOWED_STYLES.has(name) || name === 'fontFamily' || name === 'fontSize')
      .map(([name, value]) => `${name}: ${value}`)
      .join('; ');
    if (!styleStr) return false;
    span.setAttribute('style', styleStr);
    try {
      range.surroundContents(span);
    } catch {
      // surroundContents fails if the range crosses element boundaries —
      // fall back to execCommand for color.
      if (style.color) {
        document.execCommand('foreColor', false, style.color);
      }
      if (style.fontFamily) {
        document.execCommand('fontName', false, style.fontFamily);
      }
      if (style.fontSize) {
        document.execCommand('fontSize', false, mapFontSize(style.fontSize));
      }
    }
    return true;
  }

  /** Map a px font-size to execCommand's 1-7 scale (legacy API). */
  function mapFontSize(px) {
    const n = parseInt(px, 10);
    if (n <= 10) return '1';
    if (n <= 13) return '2';
    if (n <= 16) return '3';
    if (n <= 18) return '4';
    if (n <= 24) return '5';
    if (n <= 32) return '6';
    return '7';
  }

  // --- Inspector binding -----------------------------------------------------
  /** Wire up double-click on text elements on the canvas. Safe no-op if no
   *  stage is present. */
  function bindDblClick() {
    const stage = getStage();
    if (!stage) return;
    stage.addEventListener('dblclick', event => {
      const target = event.target.closest('[data-object-id]');
      if (!target) return;
      const b = bridge();
      const doc = b?.getDocument?.() || b?.doc || {};
      const obj = b?.getObjectById?.(target.getAttribute('data-object-id')) ||
        findObjectInDoc(doc, target.getAttribute('data-object-id'));
      if (!obj || obj.type !== 'text') return;
      event.preventDefault();
      beginEdit(target);
    });
  }

  // --- Lifecycle ------------------------------------------------------------
  function init() {
    // Defer to next tick so the rest of the editor bundle has run.
    requestAnimationFrame(() => {
      bindDblClick();
    });
  }

  function destroy() {
    destroyLayer();
  }

  // Expose API.
  api.sanitize = sanitize;
  api.filterSpanStyle = filterSpanStyle;
  api.beginEdit = beginEdit;
  api.commit = commit;
  api.cancel = cancel;
  api.formatSelection = formatSelection;
  api.textFromHtml = textFromHtml;
  api.init = init;
  api.destroy = destroy;
  api.ALLOWED_TAGS = ALLOWED_TAGS;
  api.DROP_TAGS = DROP_TAGS;
  window.EInviteInlineEditor = api;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
