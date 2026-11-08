/*
 * Template-pack loader (TP-1.3).
 *
 * The 100 template-pack designs are *not* in any bundle. This module is loaded on
 * demand by the Template Studio and fetches:
 *
 *   /assets/template-pack/catalog.js        the small catalogue (100 entries)
 *   /assets/template-pack/built/<id>.js     one template's native document
 *
 * Both are ES modules rather than .json because the server's static whitelist
 * refuses every .json (a disclosure fix), and a new API route would add a server
 * surface for assets that are already cacheable. Nothing here is imported by
 * index.html, so the editor bundle cannot grow (TP-OD-4).
 */
(() => {
  'use strict';
  const BASE = '/assets/template-pack';
  const ID = /^[a-z0-9-]+$/;
  const CATALOG_URL = `${BASE}/catalog.js`;
  const ERROR_TEXT = 'Could not load this template. Try again.';
  const CATALOG_ERROR_TEXT = 'Could not load the template list. Try again.';

  /** @type {Map<string, Promise<object>>} */
  const documents = new Map();
  /** @type {Promise<object>|null} */
  let catalog = null;

  class PackLoadError extends Error {
    constructor(message, cause) {
      super(message);
      this.name = 'PackLoadError';
      this.cause = cause;
    }
  }

  function loadCatalog(url = CATALOG_URL) {
    if (catalog) return catalog;
    catalog = import(url)
      .then((module) => {
        const data = module && module.default;
        if (!data || !Array.isArray(data.templates) || data.count !== data.templates.length) {
          throw new Error('catalogue shape is invalid');
        }
        return data;
      })
      .catch((error) => {
        catalog = null;
        throw new PackLoadError(CATALOG_ERROR_TEXT, error);
      });
    return catalog;
  }

  function loadTemplate(id) {
    if (!ID.test(String(id || ''))) {
      return Promise.reject(new PackLoadError(ERROR_TEXT, new Error('invalid template id')));
    }
    const key = String(id);
    if (documents.has(key)) return documents.get(key);
    const request = import(`${BASE}/built/${key}.js`)
      .then((module) => {
        const payload = module && module.default;
        if (!payload || !payload.document || payload.id !== key) {
          throw new Error('template shape is invalid');
        }
        return payload;
      })
      .catch((error) => {
        documents.delete(key);
        throw new PackLoadError(ERROR_TEXT, error);
      });
    documents.set(key, request);
    return request;
  }

  /** Warm the browser cache for every ornament a document references. */
  function preloadOrnaments(documentModel) {
    const urls = new Set();
    for (const page of (documentModel && documentModel.designPages) || []) {
      for (const object of Object.values((page && page.objects) || {})) {
        const src = object && object.type === 'image' ? String(object.src || '') : '';
        if (src.startsWith(`${BASE}/ornaments/`)) urls.add(src);
      }
    }
    return Promise.all(
      [...urls].map(
        (url) =>
          new Promise((resolve) => {
            const image = new Image();
            image.onload = () => resolve(url);
            image.onerror = () => resolve(null);
            image.src = url;
          }),
      ),
    );
  }

  function reset() {
    documents.clear();
    catalog = null;
  }

  window.EInviteTemplatePack = Object.freeze({
    version: 1,
    base: BASE,
    errorText: ERROR_TEXT,
    catalogErrorText: CATALOG_ERROR_TEXT,
    loadCatalog,
    loadTemplate,
    preloadOrnaments,
    reset,
    get loaded() {
      return [...documents.keys()];
    },
  });
})();
