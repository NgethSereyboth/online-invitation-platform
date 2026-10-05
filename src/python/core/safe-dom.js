/**
 * Centralized DOM safety helpers.
 *
 * The eInvite frontend has ~30 places that write user data into the DOM.
 * CodeQL flags each one as "DOM text reinterpreted as HTML". Rather than
 * fix each callsite ad-hoc, use these functions everywhere.
 *
 * Apply this file as `src/js/core/safe-dom.js` and add it to the FIRST
 * bundle source in docs/route-bundle-sources-v15.json so it loads before
 * any page code.
 *
 * See: docs/security/SECURITY-FIX-GUIDE.md §4.2
 */
(function () {
  'use strict';

  var FORBIDDEN_KEYS = ['__proto__', 'constructor', 'prototype'];

  /**
   * Set the text of an element safely. Equivalent to `.textContent =`,
   * but explicit about intent and grep-able.
   */
  function setText(el, value) {
    if (!el) return;
    el.textContent = value == null ? '' : String(value);
  }

  /**
   * Replace the children of `el` with a single text node.
   * Use this instead of `el.innerHTML = userValue`.
   */
  function setTextContent(el, value) {
    if (!el) return;
    while (el.firstChild) el.removeChild(el.firstChild);
    el.appendChild(document.createTextNode(value == null ? '' : String(value)));
  }

  /**
   * Set an attribute only if both the name and value pass safety checks.
   * Rejects event-handler attributes (on*) and javascript: URLs.
   */
  function setSafeAttribute(el, name, value) {
    if (!el) return;
    var n = String(name).toLowerCase();
    if (n.indexOf('on') === 0) return;         // reject event handlers
    if (n === 'href' || n === 'src' || n === 'action') {
      var v = String(value);
      // Reject javascript:/data: URLs except for known-safe data: images
      if (/^\s*javascript:/i.test(v)) return;
      if (/^\s*data:/i.test(v) && !/^data:image\//i.test(v)) return;
    }
    el.setAttribute(n, String(value));
  }

  /**
   * Clone a plain object without walking the prototype chain.
   * Use when receiving JSON from a network response or localStorage.
   * Rejects __proto__ / constructor / prototype keys at every level.
   */
  function safeClone(input, depth) {
    depth = depth || 0;
    if (depth > 32) throw new Error('safeClone: max depth exceeded');
    if (input === null || typeof input !== 'object') return input;
    if (Array.isArray(input)) {
      return input.map(function (v) { return safeClone(v, depth + 1); });
    }
    var out = Object.create(null); // no prototype
    Object.keys(input).forEach(function (key) {
      if (FORBIDDEN_KEYS.indexOf(key) !== -1) return;
      out[key] = safeClone(input[key], depth + 1);
    });
    return out;
  }

  /**
   * Safe JSON parse. Refuses to produce objects with polluted prototypes.
   */
  function safeJsonParse(text) {
    var parsed = JSON.parse(text);
    return safeClone(parsed);
  }

  /**
   * Strip all HTML tags from a string by parsing (not by regex).
   * Returns plain text safe to insert via setText.
   */
  function stripTags(input) {
    var div = document.createElement('div');
    div.textContent = String(input == null ? '' : input);
    return div.textContent;
  }

  window.EInviteSafeDom = Object.freeze({
    setText: setText,
    setTextContent: setTextContent,
    setSafeAttribute: setSafeAttribute,
    safeClone: safeClone,
    safeJsonParse: safeJsonParse,
    stripTags: stripTags,
    FORBIDDEN_KEYS: FORBIDDEN_KEYS.slice(),
  });
})();
