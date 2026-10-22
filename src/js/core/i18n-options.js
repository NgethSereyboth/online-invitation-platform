/*! core/i18n-options.js — NW-4.1 bilingual <option> labels, route-scoped (FB-03)
 * <option> cannot hold spans, so labels ride on data-i18n-en/km and this helper
 * rewrites option.textContent at boot and on every language change (value
 * survives; never resets the user's choice). Lives here, not in core/i18n.js,
 * because every route folds core/i18n.js and only materials/responses render
 * data-i18n <option> elements: keeping it out of the shared core is what pays
 * the admin route's frozen v55 weight budget. Call
 * EInviteI18n.applyOptionLabels(root) after building dynamic options too.
 */
(function (global) {
  "use strict";
  var core = global.EInviteI18n;
  if (!core || (core.applyOptionLabels && core.applyOptionLabels.routeScoped)) return;
  var doc = global.document;
  function applyOptionLabels(root) {
    if (!doc) return;
    var scope = root || doc;
    var list;
    try {
      list = scope.querySelectorAll("option[data-i18n-en], option[data-i18n-km]");
    } catch (e) { return; }
    for (var i = 0; i < list.length; i++) {
      var option = list[i];
      var en = option.getAttribute("data-i18n-en") || option.getAttribute("data-i18n-km") || "";
      var km = option.getAttribute("data-i18n-km") || en;
      option.textContent = core.get() === "km" ? km : en;
    }
  }
  applyOptionLabels.routeScoped = true;
  core.applyOptionLabels = applyOptionLabels;
  // Runs after DOM parse (bundles load blocking in <head>) and on every
  // einvite:lang-changed dispatch.
  function boot() { try { applyOptionLabels(); } catch (e) { /* keep going */ } }
  try { doc.addEventListener("einvite:lang-changed", boot); } catch (e) { /* noop */ }
  if (doc && doc.addEventListener) {
    doc.addEventListener("DOMContentLoaded", boot);
    if (doc.readyState === "interactive" || doc.readyState === "complete") boot();
  }
})(typeof window !== "undefined" ? window : this);
