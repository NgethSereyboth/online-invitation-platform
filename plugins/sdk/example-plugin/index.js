/* eInvite Confetti Plugin — entrypoint script.
 *
 * Bilingual strings (EN+KH) per ROADMAP ground rule 5.
 * Uses the eInvite plugin SDK (../einvite-plugin.js) to communicate with the host.
 *
 * This plugin:
 *   1. Reads the host's locale (en|km) and renders bilingual UI.
 *   2. Listens for RSVP updates (via onContextChanged) and triggers a confetti burst
 *      when an RSVP transitions to "confirmed".
 *   3. Provides a manual "Burst" button for the host to preview the animation.
 *   4. Uses only the declared permission `invitation:{current}:rsvp:read` — the
 *      host will refuse any other capability the plugin might attempt.
 */

(function () {
  'use strict';

  var STRINGS = {
    label:     { en: 'Confetti animation',            km: 'អានីម៉េសិនផ្កាយរត់' },
    intensity: { en: 'Intensity',                    km: 'Intensity' /* technical term, often untranslated in Khmer UIs */ },
    burst:     { en: 'Burst',                        km: 'បាញ់ផ្កាយរត់' },
    hint:      { en: 'Triggers a confetti burst on RSVP confirm.',
                 km: 'បាញ់ផ្កាយរត់នៅពេលភ្ញៀវឆ្លើយឆ្លងពិតប្រាកដ។' }
  };

  var palette = ['#8b465b', '#9c6cff', '#2b9b68', '#c98322', '#1f2026'];

  function applyLocale(locale) {
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var key = els[i].getAttribute('data-i18n');
      var entry = STRINGS[key];
      if (entry) els[i].textContent = entry[locale] || entry.en;
    }
    document.documentElement.setAttribute('lang', locale === 'km' ? 'km' : 'en');
  }

  function burst(intensity) {
    var stage = document.getElementById('stage');
    if (!stage) return;
    var count = Math.max(1, Math.min(100, intensity || 50));
    var rect = stage.getBoundingClientRect();
    for (var i = 0; i < count; i++) {
      var p = document.createElement('div');
      p.className = 'confetti-particle';
      p.style.background = palette[i % palette.length];
      p.style.left = (Math.random() * (rect.width - 8)) + 'px';
      p.style.top = '-10px';
      stage.appendChild(p);
      // animate
      var dx = (Math.random() - 0.5) * 60;
      var dy = rect.height + 20;
      var rot = (Math.random() - 0.5) * 720;
      var dur = 800 + Math.random() * 600;
      p.animate(
        [
          { transform: 'translate(0, 0) rotate(0deg)', opacity: 1 },
          { transform: 'translate(' + dx + 'px, ' + dy + 'px) rotate(' + rot + 'deg)', opacity: 0 }
        ],
        { duration: dur, easing: 'cubic-bezier(0.2, 0.6, 0.4, 1)' }
      ).onfinish = function () { if (this && this.effect && this.effect.target) this.effect.target.remove(); }.bind({ effect: { target: p } });
    }
  }

  // ─── Boot ───────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    var intensityInput = document.getElementById('intensity');
    var intensityValue = document.getElementById('intensityValue');
    var burstBtn = document.getElementById('burst');

    intensityInput.addEventListener('input', function () {
      intensityValue.textContent = intensityInput.value;
    });
    burstBtn.addEventListener('click', function () {
      burst(parseInt(intensityInput.value, 10) || 50);
    });

    // Apply default locale before the SDK reports the host locale.
    applyLocale('en');

    // Wire up the eInvite plugin SDK if it is available (the host injects ../einvite-plugin.js).
    var plugin = window.EInvitePlugin;
    if (!plugin) {
      // The plugin can still render its UI without the SDK — useful in dev preview.
      console.warn('[confetti] eInvitePlugin SDK not found; running in standalone preview mode.');
      return;
    }

    plugin.onReady(function (info) {
      applyLocale(info.locale || 'en');
      // Log that we're alive (rate-limited by the host to 10/sec).
      plugin.log('info', 'Confetti plugin ready', { pluginId: info.pluginId, version: info.version });
    });

    plugin.onLocaleChanged(function (locale) {
      applyLocale(locale);
    });

    plugin.onContextChanged(function (ctx) {
      // When the RSVP count changes (host fires context_changed with the new rsvp_count),
      // trigger a small celebratory burst.
      if (!ctx) return;
      var previous = window.__previousRsvpCount || 0;
      var current = ctx.rsvp_count || 0;
      if (current > previous) {
        burst(parseInt(intensityInput.value, 10) || 50);
      }
      window.__previousRsvpCount = current;
    });

    plugin.onSuspend(function () {
      // Drop any in-flight animations to free memory (per PLUGIN-SANDBOX.md §3.4).
      var stage = document.getElementById('stage');
      if (stage) stage.replaceChildren();
    });

    plugin.onUninstall(function () {
      // Clean up; the host will tear down the iframe next.
      var stage = document.getElementById('stage');
      if (stage) stage.replaceChildren();
    });
  });
})();
