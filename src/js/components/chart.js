/* src/js/components/chart.js — v0.68.1 (ROADMAP-v0.54-to-v1.0 §6.6)
 *
 * Canvas 2D charts. No third-party library. Vanilla IIFE, exposes
 * window.EInviteCharts. Supports:
 *   - LineChart   : time-series with optional overlay line
 *   - BarChart    : categorical bars
 *   - DonutChart   : mobile/tablet/desktop split
 *   - Sparkline    : tiny inline trend
 *
 * Honours devicePixelRatio (multiplies canvas size + scales context).
 * Honours ResizeObserver (redraws on parent resize).
 * Reads CSS custom properties (--ei-chart-line, --ei-chart-bar, etc.)
 * so the same chart adapts to dark mode automatically.
 *
 * Declarative API:
 *   <canvas data-chart="line"
 *           data-chart-data='[{"x":"2024-01-01","y":3}]'
 *           data-chart-color="var(--ei-chart-line)"
 *           aria-label="Views over time"></canvas>
 *
 * Accessibility:
 *   - aria-label always set (chart type + label)
 *   - Visually-hidden data table of the underlying values appended
 *     after the canvas so screen readers have the raw numbers.
 */
(function (global) {
  "use strict";
  if (global.EInviteCharts && global.EInviteCharts.version >= 681) return global.EInviteCharts;

  var STRINGS = {
    en: {
      views: "Views",
      rsvps: "RSVPs",
      mobile: "Mobile",
      tablet: "Tablet",
      desktop: "Desktop",
      noData: "No data yet",
      chartOf: "Chart of",
      data: "Data",
      value: "Value",
      label: "Label",
    },
    km: {
      views: "ចំនួនមើល",
      rsvps: "RSVPs",
      mobile: "ទូរស័ព្ទ",
      tablet: "ថេប្លេត",
      desktop: "ដេស្គトップ",
      noData: "មិនមានទិន្នន័យទេ",
      chartOf: "ក្រាហ្វិចនៃ",
      data: "ទិន្នន័យ",
      value: "តម្លៃ",
      label: "ស្លាក",
    },
  };

  function locale() {
    var l = (global.EInviteI18N && typeof global.EInviteI18N.getLocale === "function")
      ? global.EInviteI18N.getLocale()
      : (document.documentElement.lang || "en");
    return (l || "en").toLowerCase().indexOf("km") === 0 ? "km" : "en";
  }

  function t(key) {
    return (STRINGS[locale()] || STRINGS.en)[key] || key;
  }

  function cssVar(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      if (v) return v;
    } catch (e) {}
    return fallback;
  }

  function setupCanvas(canvas) {
    var dpr = (global.devicePixelRatio || 1);
    var rect = canvas.getBoundingClientRect();
    var w = Math.max(1, Math.floor(rect.width || canvas.getAttribute("width") || 320));
    var h = Math.max(1, Math.floor(rect.height || canvas.getAttribute("height") || 160));
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    var ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h };
  }

  function ensureAriaLabel(canvas, kind, label) {
    if (!canvas.getAttribute("aria-label")) {
      canvas.setAttribute("aria-label", t("chartOf") + " " + (label || kind));
    }
    if (!canvas.getAttribute("role")) canvas.setAttribute("role", "img");
  }

  function ensureDataTable(canvas, headers, rows) {
    // Visually-hidden data table for screen readers.
    var id = canvas.getAttribute("data-chart-table-id");
    var table;
    if (id) table = document.getElementById(id);
    if (!table) {
      table = document.createElement("table");
      table.className = "ei-chart-data-table";
      table.setAttribute("aria-hidden", "false");
      canvas.parentNode.appendChild(table);
      canvas.setAttribute("data-chart-table-id", table.id = "ei-chart-table-" + Math.random().toString(36).slice(2, 10));
    }
    var thead = "<thead><tr>" + headers.map(function (h) { return "<th>" + escapeHtml(h) + "</th>"; }).join("") + "</tr></thead>";
    var tbody = "<tbody>" + rows.map(function (r) {
      return "<tr>" + r.map(function (c) { return "<td>" + escapeHtml(String(c)) + "</td>"; }).join("") + "</tr>";
    }).join("") + "</tbody>";
    table.innerHTML = thead + tbody;
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function drawNoData(ctx, w, h) {
    ctx.save();
    ctx.fillStyle = cssVar("--ei-chart-empty", "#94a3b8");
    ctx.font = "13px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(t("noData"), w / 2, h / 2);
    ctx.restore();
  }

  // --- LineChart -------------------------------------------------------
  function LineChart(canvas, opts) {
    opts = opts || {};
    ensureAriaLabel(canvas, "line", opts.label);
    var setup = setupCanvas(canvas);
    var ctx = setup.ctx, w = setup.w, h = setup.h;
    var data = (opts.data || []).slice();
    if (!data.length) {
      drawNoData(ctx, w, h);
      ensureDataTable(canvas, [t("label"), t("value")], []);
      return;
    }
    var pad = { l: 32, r: 12, t: 12, b: 24 };
    var plotW = Math.max(1, w - pad.l - pad.r);
    var plotH = Math.max(1, h - pad.t - pad.b);
    var xs = data.map(function (d) { return d.x; });
    var ys = data.map(function (d) { return Number(d.y || 0); });
    var overlay = (opts.overlay || []).slice();
    var max = Math.max.apply(null, ys.concat(overlay.map(function (d) { return Number(d.y || 0); })).concat([1]));
    var min = 0;
    var stepX = data.length > 1 ? plotW / (data.length - 1) : plotW;
    var lineColor = opts.color || cssVar("--ei-chart-line", "#3b82f6");
    var overlayColor = opts.overlayColor || cssVar("--ei-chart-overlay", "#a855f7");

    // Y-axis gridlines (4 lines).
    ctx.save();
    ctx.strokeStyle = cssVar("--ei-chart-grid", "#e2e8f0");
    ctx.fillStyle = cssVar("--ei-chart-axis", "#64748b");
    ctx.lineWidth = 1;
    ctx.font = "10px system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (var i = 0; i <= 4; i++) {
      var y = pad.t + (plotH * i) / 4;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + plotW, y); ctx.stroke();
      var v = Math.round(max - (max - min) * i / 4);
      ctx.fillText(String(v), pad.l - 4, y);
    }
    ctx.restore();

    function plotSeries(series, color, fill) {
      if (!series.length) return;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      series.forEach(function (d, i) {
        var x = pad.l + i * stepX;
        var y = pad.t + plotH - ((Number(d.y || 0) - min) / (max - min || 1)) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      if (fill) {
        ctx.lineTo(pad.l + (series.length - 1) * stepX, pad.t + plotH);
        ctx.lineTo(pad.l, pad.t + plotH);
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.fill();
      }
      ctx.restore();
    }

    if (opts.fill) {
      // Fill under the primary series only.
      ctx.save();
      ctx.beginPath();
      data.forEach(function (d, i) {
        var x = pad.l + i * stepX;
        var y = pad.t + plotH - ((Number(d.y || 0) - min) / (max - min || 1)) * plotH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.lineTo(pad.l + (data.length - 1) * stepX, pad.t + plotH);
      ctx.lineTo(pad.l, pad.t + plotH);
      ctx.closePath();
      ctx.fillStyle = opts.fill;
      ctx.globalAlpha = 0.18;
      ctx.fill();
      ctx.restore();
    }

    plotSeries(data, lineColor, null);
    plotSeries(overlay, overlayColor, null);

    // X-axis labels (first, middle, last).
    ctx.save();
    ctx.fillStyle = cssVar("--ei-chart-axis", "#64748b");
    ctx.font = "10px system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    [0, Math.floor(data.length / 2), data.length - 1].forEach(function (i) {
      var x = pad.l + i * stepX;
      var label = String(data[i].x || "");
      if (label.length > 10) label = label.slice(5);
      ctx.fillText(label, x, pad.t + plotH + 4);
    });
    ctx.restore();

    ensureDataTable(canvas, [t("label"), t("value")],
      data.map(function (d) { return [d.x, d.y]; }));
  }

  // --- BarChart --------------------------------------------------------
  function BarChart(canvas, opts) {
    opts = opts || {};
    ensureAriaLabel(canvas, "bar", opts.label);
    var setup = setupCanvas(canvas);
    var ctx = setup.ctx, w = setup.w, h = setup.h;
    var data = (opts.data || []).slice();
    if (!data.length) {
      drawNoData(ctx, w, h);
      ensureDataTable(canvas, [t("label"), t("value")], []);
      return;
    }
    var pad = { l: 32, r: 12, t: 12, b: 32 };
    var plotW = Math.max(1, w - pad.l - pad.r);
    var plotH = Math.max(1, h - pad.t - pad.b);
    var max = Math.max.apply(null, data.map(function (d) { return Number(d.value || 0); }).concat([1]));
    var barColor = opts.color || cssVar("--ei-chart-bar", "#10b981");
    var barW = Math.max(2, plotW / data.length - 6);
    ctx.save();
    ctx.strokeStyle = cssVar("--ei-chart-grid", "#e2e8f0");
    ctx.fillStyle = cssVar("--ei-chart-axis", "#64748b");
    ctx.lineWidth = 1;
    ctx.font = "10px system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (var i = 0; i <= 4; i++) {
      var y = pad.t + (plotH * i) / 4;
      ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + plotW, y); ctx.stroke();
      var v = Math.round(max - (max * i) / 4);
      ctx.fillText(String(v), pad.l - 4, y);
    }
    ctx.restore();
    data.forEach(function (d, i) {
      var x = pad.l + i * (plotW / data.length) + 3;
      var v = Number(d.value || 0);
      var barH = Math.max(1, (v / max) * plotH);
      ctx.fillStyle = d.color || barColor;
      ctx.fillRect(x, pad.t + plotH - barH, barW, barH);
      ctx.save();
      ctx.fillStyle = cssVar("--ei-chart-axis", "#64748b");
      ctx.font = "10px system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      var label = String(d.label || "");
      if (label.length > 8) label = label.slice(0, 7) + "…";
      ctx.fillText(label, x + barW / 2, pad.t + plotH + 4);
      ctx.restore();
    });
    ensureDataTable(canvas, [t("label"), t("value")],
      data.map(function (d) { return [d.label, d.value]; }));
  }

  // --- DonutChart ------------------------------------------------------
  function DonutChart(canvas, opts) {
    opts = opts || {};
    ensureAriaLabel(canvas, "donut", opts.label);
    var setup = setupCanvas(canvas);
    var ctx = setup.ctx, w = setup.w, h = setup.h;
    var data = (opts.data || []).slice();
    if (!data.length || data.every(function (d) { return !Number(d.value || 0); })) {
      drawNoData(ctx, w, h);
      ensureDataTable(canvas, [t("label"), t("value")], []);
      return;
    }
    var cx = w / 2, cy = h / 2;
    var radius = Math.max(8, Math.min(w, h) / 2 - 12);
    var inner = Math.max(4, radius * 0.6);
    var total = data.reduce(function (s, d) { return s + Number(d.value || 0); }, 0) || 1;
    var start = -Math.PI / 2;
    data.forEach(function (d) {
      var v = Number(d.value || 0);
      if (!v) return;
      var angle = (v / total) * Math.PI * 2;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, start, start + angle);
      ctx.closePath();
      ctx.fillStyle = d.color || cssVar("--ei-chart-slice", "#3b82f6");
      ctx.fill();
      ctx.restore();
      start += angle;
    });
    // Cut out the inner circle (donut hole).
    ctx.save();
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath();
    ctx.arc(cx, cy, inner, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    // Center label = total.
    ctx.save();
    ctx.fillStyle = cssVar("--ei-chart-axis", "#64748b");
    ctx.font = "12px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(total), cx, cy);
    ctx.restore();
    ensureDataTable(canvas, [t("label"), t("value")],
      data.map(function (d) { return [d.label, d.value]; }));
  }

  // --- Sparkline -------------------------------------------------------
  function Sparkline(canvas, opts) {
    opts = opts || {};
    ensureAriaLabel(canvas, "sparkline", opts.label);
    var setup = setupCanvas(canvas);
    var ctx = setup.ctx, w = setup.w, h = setup.h;
    var data = (opts.data || []).slice();
    if (!data.length) {
      drawNoData(ctx, w, h);
      return;
    }
    var max = Math.max.apply(null, data);
    var min = Math.min.apply(null, data);
    var range = (max - min) || 1;
    var stepX = data.length > 1 ? w / (data.length - 1) : w;
    ctx.save();
    ctx.strokeStyle = opts.color || cssVar("--ei-chart-sparkline", "#3b82f6");
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    data.forEach(function (v, i) {
      var x = i * stepX;
      var y = h - ((Number(v) - min) / range) * (h - 4) - 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();
  }

  // --- Declarative init ------------------------------------------------
  function initDeclarative() {
    var canvases = document.querySelectorAll("canvas[data-chart]");
    canvases.forEach(function (canvas) {
      if (canvas.__ei_chart_init) return;
      canvas.__ei_chart_init = true;
      try {
        var kind = canvas.getAttribute("data-chart");
        var raw = canvas.getAttribute("data-chart-data") || "[]";
        var data = JSON.parse(raw);
        var color = canvas.getAttribute("data-chart-color");
        var overlayRaw = canvas.getAttribute("data-chart-overlay");
        var overlay = overlayRaw ? JSON.parse(overlayRaw) : null;
        var overlayColor = canvas.getAttribute("data-chart-overlay-color");
        var label = canvas.getAttribute("data-chart-label");
        var fill = canvas.getAttribute("data-chart-fill");
        var opts = { data: data, color: color || undefined, label: label, fill: fill || undefined };
        if (overlay) { opts.overlay = overlay; opts.overlayColor = overlayColor || undefined; }
        redraw(canvas, kind, opts);
        // ResizeObserver for responsiveness.
        if (global.ResizeObserver) {
          var ro = new ResizeObserver(function () { redraw(canvas, kind, opts); });
          ro.observe(canvas);
          canvas.__ei_chart_ro = ro;
        }
      } catch (e) {
        if (global.console) console.warn("ei-chart init failed", e);
      }
    });
  }

  function redraw(canvas, kind, opts) {
    if (kind === "line") LineChart(canvas, opts);
    else if (kind === "bar") BarChart(canvas, opts);
    else if (kind === "donut") DonutChart(canvas, opts);
    else if (kind === "sparkline") Sparkline(canvas, opts);
  }

  function destroy(canvas) {
    if (canvas.__ei_chart_ro) {
      try { canvas.__ei_chart_ro.disconnect(); } catch (e) {}
      canvas.__ei_chart_ro = null;
    }
    var id = canvas.getAttribute("data-chart-table-id");
    if (id) {
      var t = document.getElementById(id);
      if (t && t.parentNode) t.parentNode.removeChild(t);
    }
    canvas.__ei_chart_init = false;
  }

  var api = {
    version: 681,
    LineChart: LineChart,
    BarChart: BarChart,
    DonutChart: DonutChart,
    Sparkline: Sparkline,
    initDeclarative: initDeclarative,
    redraw: redraw,
    destroy: destroy,
    strings: STRINGS,
  };
  global.EInviteCharts = api;

  // Auto-init on DOMContentLoaded.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDeclarative);
  } else {
    initDeclarative();
  }

  return api;
})(typeof window !== "undefined" ? window : this);
