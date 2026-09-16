;(()=>{
'use strict';
const ensureStack=()=>{let stack=document.querySelector('.ei-toast-stack');if(!stack){stack=document.createElement('div');stack.className='ei-toast-stack';stack.setAttribute('aria-live','polite');document.body.append(stack)}return stack};
function toast(message,options={}){
  const text=String(message??'');if(!text)return;
  const stack=ensureStack(),item=document.createElement('div');item.className=`ei-toast ${options.type||''}`.trim();
  const icon=options.icon||(options.type==='error'?'!':options.type==='success'?'✓':'✦');
  item.innerHTML=`<span class="ei-toast-icon"></span><strong></strong><button type="button" aria-label="Dismiss">×</button>`;
  item.querySelector('.ei-toast-icon').textContent=icon;item.querySelector('strong').textContent=text;
  const close=()=>{if(item.classList.contains('out'))return;item.classList.add('out');setTimeout(()=>item.remove(),190)};item.querySelector('button').onclick=close;stack.append(item);setTimeout(close,Math.max(1500,Number(options.duration||3600)));return item
}
function buildDialog({title='Please confirm',message='',icon='✦',input=false,value='',multiline=false,confirmText='Continue',cancelText='Cancel',danger=false}={}){
  const dialog=document.createElement('dialog');dialog.className='ei-dialog';
  dialog.innerHTML=`<form method="dialog" class="ei-dialog-card"><div class="ei-dialog-head"><span class="ei-dialog-icon"></span><div><h2></h2><p class="ei-dialog-message"></p></div></div><div class="ei-dialog-input" hidden><label>Value</label></div><div class="ei-dialog-actions"><button type="button" data-cancel></button><button type="submit" value="confirm" data-confirm></button></div></form>`;
  dialog.querySelector('.ei-dialog-icon').textContent=icon;dialog.querySelector('h2').textContent=title;dialog.querySelector('.ei-dialog-message').textContent=message;dialog.querySelector('[data-cancel]').textContent=cancelText;const confirm=dialog.querySelector('[data-confirm]');confirm.textContent=confirmText;confirm.classList.add(danger?'ei-danger':'ei-primary');
  let field=null;if(input){const host=dialog.querySelector('.ei-dialog-input');host.hidden=false;field=document.createElement(multiline?'textarea':'input');field.value=value??'';field.autocomplete='off';host.append(field)}
  document.body.append(dialog);return{dialog,field}
}
function uiConfirm(message,options={}){return new Promise(resolve=>{const{dialog}=buildDialog({title:options.title||'Confirm action',message,icon:options.icon||'?',confirmText:options.confirmText||'Confirm',cancelText:options.cancelText||'Cancel',danger:options.danger===true});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(false)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(false)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'));dialog.showModal();setTimeout(()=>dialog.querySelector('[data-confirm]')?.focus(),0)})}
function uiPrompt(message,defaultValue='',options={}){return new Promise(resolve=>{const{dialog,field}=buildDialog({title:options.title||'Enter a value',message,icon:options.icon||'✎',input:true,value:defaultValue,multiline:options.multiline===true,confirmText:options.confirmText||'Save',cancelText:options.cancelText||'Cancel'});let done=false;const finish=value=>{if(done)return;done=true;resolve(value);dialog.remove()};dialog.querySelector('[data-cancel]').onclick=()=>{dialog.close();finish(null)};dialog.addEventListener('cancel',e=>{e.preventDefault();dialog.close();finish(null)});dialog.addEventListener('close',()=>finish(dialog.returnValue==='confirm'?field.value:null));dialog.showModal();setTimeout(()=>{field.focus();field.select?.()},0)})}
function uiAlert(message,options={}){toast(message,{...options,type:options.type||(/error|failed|invalid|could not|unable/i.test(String(message))?'error':options.type)});return Promise.resolve()}
window.uiToast=window.uiToast||toast;window.uiAlert=uiAlert;window.uiConfirm=uiConfirm;window.uiPrompt=uiPrompt;
window.alert=(message)=>{uiAlert(message)};
})();;(()=>{
 'use strict';
 const LAST_KEY='sovan-active-invite';
 const routeMatch=location.pathname.match(/\/invitations\/([^/]+)\/(editor|guests|responses|analytics|materials|checkin)\/?$/i);
 const queryId=new URLSearchParams(location.search).get('invitation');
 const routeId=routeMatch?decodeURIComponent(routeMatch[1]):'';
 const explicitId=routeId||queryId||'';
 const section=routeMatch?.[2]?.toLowerCase()||'';
 const safe=id=>String(id||'').trim();
 function getInvitationId(options={}){const direct=safe(explicitId);if(direct)return direct;if(options.allowRemembered===false)return '';return safe(localStorage.getItem(LAST_KEY))}
 function remember(id){id=safe(id);if(id)localStorage.setItem(LAST_KEY,id);return id}
 function route(id,target='editor'){
   id=safe(id);target=String(target||'editor').toLowerCase();
   if(!id)return target==='materials'?'materials.html':'dashboard.html';
   const allowed=new Set(['editor','guests','responses','analytics','materials','checkin']);if(!allowed.has(target))target='editor';
   if(window.EInviteBackend?.state?.status==='offline')return window.EInviteBackend.staticUrl(id,target);
   return `/invitations/${encodeURIComponent(id)}/${target}`;
 }
 async function navigate(id,target='editor'){remember(id);if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;location.href=route(id,target)}
 if(explicitId)remember(explicitId);
 async function rewriteInvitationLinks(){if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;const id=getInvitationId({allowRemembered:false});if(!id)return;const map={'index.html':'editor','guests.html':'guests','responses.html':'responses','analytics.html':'analytics','materials.html':'materials','checkin.html':'checkin'};document.querySelectorAll('a[href]').forEach(anchor=>{const raw=anchor.getAttribute('href')||'';const base=raw.split('?')[0].split('#')[0].replace(/^\.\//,'');const target=map[base];if(target)anchor.setAttribute('href',route(id,target))})}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',rewriteInvitationLinks,{once:true});else rewriteInvitationLinks();
 window.EInviteContext={getInvitationId,remember,route,navigate,section,explicitId,rewriteInvitationLinks};
})();;/* src/js/components/chart.js — v0.68.1 (ROADMAP-v0.54-to-v1.0 §6.6)
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
})(typeof window !== "undefined" ? window : this);;/* src/js/pages/dashboard/analytics.js — v0.68.0 (ROADMAP-v0.54-to-v1.0 §6.5)
 *
 * Creator analytics dashboard page. Replaces the v0.58.0 analytics.js
 * shim with a Canvas 2D charts UI:
 *   - 4 stat cards (total views, unique recipients, avg time, RSVP conversion)
 *   - 30-day line chart with RSVP overlay
 *   - Drop-off funnel (view → rsvp.open → rsvp.submit)
 *   - Top referrers table (masks <3 as "Other")
 *   - Scroll depth bar
 *   - Device split donut
 *   - Country list (top 5)
 *   - Privacy controls (disable analytics / purge / export)
 *   - Live activity (behind analytics_live_enabled feature flag)
 *
 * Honours bilingual EN/KH labels. Honours analyticsEnabled flag
 * (the public page checks this before firing events).
 *
 * Backwards-compatible: the existing #analyticsRoot contract from
 * analytics.html (one big render function) is preserved; we render
 * into the same root.
 */
(function (global) {
  "use strict";
  if (global.EInviteAnalyticsDashboard && global.EInviteAnalyticsDashboard.version >= 680) return;

  var STRINGS = {
    en: {
      title: "Invitation Analytics",
      subtitle: "Performance overview for this invitation.",
      totalViews: "Total views",
      uniqueRecipients: "Unique recipients",
      avgTime: "Average time on page",
      rsvpConversion: "RSVP conversion",
      viewsLast30: "Views — last 30 days",
      rsvpBreakdown: "RSVP breakdown",
      guestCheckin: "Guest check-in",
      publishing: "Publishing",
      funnel: "Drop-off funnel",
      topReferrers: "Top referrers",
      scrollDepth: "Average scroll depth",
      deviceSplit: "Device split",
      countrySplit: "Country",
      liveActivity: "Live activity",
      activeSessions: "active sessions",
      lastEvent: "last activity",
      disableAnalytics: "Disable analytics",
      enableAnalytics: "Enable analytics",
      purgeData: "Delete analytics data",
      exportCsv: "Export as CSV",
      exportJson: "Export as JSON",
      loading: "Loading analytics…",
      unavailable: "Analytics unavailable",
      deltaVsPrev: "vs previous 7 days",
      analyticsOff: "Analytics disabled",
      analyticsOffDesc: "The public page will not send events for this invitation.",
      guestsOnList: "guests on list",
      totalRespondingGuests: "total responding guests",
      historicalPreserved: "Historical responses are preserved",
      rsvpDisabled: "Disabled",
      step: "Step",
      count: "Count",
      percent: "Percent",
      loadingLive: "Checking…",
      liveDisabled: "Live activity is disabled on this server.",
      purgeConfirm: "This permanently deletes every session + event for this invitation. Continue?",
      purged: "Analytics data deleted.",
      disabledToast: "Analytics disabled for this invitation.",
      enabledToast: "Analytics re-enabled.",
    },
    km: {
      title: "ស្ថិតិការអានិត្យកម្ម",
      subtitle: "ទិដ្ឋភាពទូទៅនៃសមិទ្ធិផលនៃការអញ្ជើញនេះ។",
      totalViews: "ចំនួនមើលសរុប",
      uniqueRecipients: "ភ្ញៀវផ្ទាល់ខ្លួន",
      avgTime: "ពេលវេលាមធ្យមនៅលើទំព័រ",
      rsvpConversion: "អត្រាឆ្លើយតប RSVP",
      viewsLast30: "ចំនួនមើល — ៣០ ថ្ងៃចុងក្រោយ",
      rsvpBreakdown: "ស្ថិតិ RSVP",
      guestCheckin: "ការចុះឈ្មោះភ្ញៀវ",
      publishing: "ការបោះពុម្ពផ្សាយ",
      funnel: "ស្ថិតិការបោះបង់",
      topReferrers: "ប្រភពដែលនាំមក",
      scrollDepth: "ជម្រៅអានមធ្យម",
      deviceSplit: "ប្រភេទឧបករណ៍",
      countrySplit: "ប្រទេស",
      liveActivity: "សកម្មភាពផ្ទាល់",
      activeSessions: "សម័យសកម្ម",
      lastEvent: "សកម្មភាពចុងក្រោយ",
      disableAnalytics: "បិទស្ថិតិ",
      enableAnalytics: "បើកស្ថិតិ",
      purgeData: "លុបទិន្នន័យស្ថិតិ",
      exportCsv: "នាំចេញជា CSV",
      exportJson: "នាំចេញជា JSON",
      loading: "កំពុងផ្ទុកស្ថិតិ…",
      unavailable: "ស្ថិតិមិនអាចប្រើបាន",
      deltaVsPrev: "ធៀបនឹង ៧ ថ្ងៃមុន",
      analyticsOff: "ស្ថិតិត្រូវបានបិទ",
      analyticsOffDesc: "ទំព័រសាធារណៈនឹងមិនផ្ញើព្រឹត្តិកម្មសម្រាប់ការអញ្ជើញនេះទេ។",
      guestsOnList: "ភ្ញៀវក្នុងបញ្ជី",
      totalRespondingGuests: "ភ្ញៀវឆ្លើយតបសរុប",
      historicalPreserved: "ការឆ្លើយតបប្រវត្តិសាស្ត្រត្រូវបានរក្សាទុក",
      rsvpDisabled: "បិទ",
      step: "ជំហាន",
      count: "ចំនួន",
      percent: "ភាគរយ",
      loadingLive: "កំពុងពិនិត្យ…",
      liveDisabled: "សកម្មភាពផ្ទាល់ត្រូវបានបិទនៅលើម៉ាស៊ីនមេនេះ។",
      purgeConfirm: "របៀបនេះនឹងលុបសម័យ + ព្រឹត្តិកម្មទាំងអស់សម្រាប់ការអញ្ជើញនេះអ一刀មិនអាចត្រឡប់វិញបាន។ បន្តឬ?",
      purged: "ទិន្នន័យស្ថិតិបានលុបចោលហើយ។",
      disabledToast: "ស្ថិតិបានបិទសម្រាប់ការអញ្ជើញនេះ។",
      enabledToast: "ស្ថិតិបានបើកឡើងវិញ។",
    },
  };

  function locale() {
    var l = (global.EInviteI18N && typeof global.EInviteI18N.getLocale === "function")
      ? global.EInviteI18N.getLocale()
      : (document.documentElement.lang || "en");
    return (l || "en").toLowerCase().indexOf("km") === 0 ? "km" : "en";
  }

  function t(key) { return (STRINGS[locale()] || STRINGS.en)[key] || key; }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function fmtDuration(ms) {
    if (!ms || ms < 1000) return "0s";
    var s = Math.floor(ms / 1000);
    if (s < 60) return s + "s";
    var m = Math.floor(s / 60);
    if (m < 60) return m + "m " + (s % 60) + "s";
    var h = Math.floor(m / 60);
    return h + "h " + (m % 60) + "m";
  }

  function fmtDelta(d) {
    if (d === undefined || d === null) return "";
    var sign = d > 0 ? "+" : "";
    return sign + d + "%";
  }

  function deltaClass(d) {
    if (d === undefined || d === null) return "";
    return d > 0 ? "ei-delta-up" : (d < 0 ? "ei-delta-down" : "ei-delta-flat");
  }

  async function fetchJson(path, opts) {
    var r = await fetch(path, Object.assign({ credentials: "same-origin" }, opts || {}));
    if (r.status === 204) return null;
    var txt = await r.text();
    var data = txt ? JSON.parse(txt) : {};
    if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
    return data;
  }

  function getInviteId() {
    if (global.EInviteContext && typeof global.EInviteContext.getInvitationId === "function") {
      return global.EInviteContext.getInvitationId();
    }
    var m = location.pathname.match(/invitation[s]?\/([^/]+)/);
    return m ? m[1] : null;
  }

  function renderStatCard(label, value, delta) {
    var deltaHtml = (delta !== undefined && delta !== null)
      ? '<small class="ei-delta ' + deltaClass(delta) + '">' + escapeHtml(fmtDelta(delta)) + " · " + escapeHtml(t("deltaVsPrev")) + '</small>'
      : "";
    return '<div class="ei-stat-card"><span class="ei-stat-label">' + escapeHtml(t(label) || label) + '</span>'
      + '<strong class="ei-stat-value">' + escapeHtml(value) + '</strong>'
      + deltaHtml + '</div>';
  }

  function renderFunnel(steps) {
    if (!steps || !steps.length) return '<p class="ei-empty">' + escapeHtml(t("loading")) + '</p>';
    var max = Math.max.apply(null, steps.map(function (s) { return s.count; })) || 1;
    var rows = steps.map(function (s) {
      var barW = (s.count / max) * 100;
      return '<div class="ei-funnel-row">'
        + '<div class="ei-funnel-label">' + escapeHtml(s.step) + '</div>'
        + '<div class="ei-funnel-bar"><span style="width:' + barW + '%"></span></div>'
        + '<div class="ei-funnel-count">' + escapeHtml(s.count) + ' <small>(' + s.pct + '%)</small></div>'
        + '</div>';
    }).join("");
    return '<div class="ei-funnel">' + rows + '</div>';
  }

  function renderReferrers(refs) {
    if (!refs || !refs.length) return '<p class="ei-empty">—</p>';
    return '<table class="ei-referrer-table"><thead><tr><th>' + escapeHtml(t("topReferrers"))
      + '</th><th>' + escapeHtml(t("count")) + '</th></tr></thead><tbody>'
      + refs.map(function (r) {
          return '<tr><td>' + escapeHtml(r.domain) + '</td><td>' + escapeHtml(r.count) + '</td></tr>';
        }).join("")
      + '</tbody></table>';
  }

  function renderScrollDepth(scroll) {
    if (!scroll) return '<p class="ei-empty">—</p>';
    var avg = scroll.average || 0;
    var buckets = scroll.buckets || [];
    var bars = buckets.map(function (b) {
      return '<div class="ei-scroll-bucket"><span>' + b.pct + '%</span>'
        + '<div class="ei-scroll-bar"><span style="height:' + (b.count > 0 ? 100 : 0) + '%"></span></div>'
        + '<small>' + b.count + '</small></div>';
    }).join("");
    return '<div class="ei-scroll">'
      + '<div class="ei-scroll-avg">' + escapeHtml(t("scrollDepth")) + ': <strong>' + avg + '%</strong></div>'
      + '<div class="ei-scroll-buckets">' + bars + '</div>'
      + '</div>';
  }

  function renderDeviceSplit(devices) {
    if (!devices || !devices.length) return '<p class="ei-empty">—</p>';
    return '<canvas data-chart="donut" data-chart-label="' + escapeHtml(t("deviceSplit")) + '" data-chart-data=\''
      + JSON.stringify(devices.map(function (d) { return { label: d.label, value: d.value, color: d.color }; }))
      + '\'></canvas>';
  }

  function renderCountrySplit(countries) {
    if (!countries || !countries.length) return '<p class="ei-empty">—</p>';
    return '<ul class="ei-country-list">' + countries.map(function (c) {
      return '<li><span class="ei-country-code">' + escapeHtml(c.code) + '</span>'
        + '<span class="ei-country-count">' + escapeHtml(c.count) + '</span></li>';
    }).join("") + '</ul>';
  }

  function renderCharts(analytics) {
    if (!analytics) return;
    var ts = analytics.timeseries || { days: [], views: [], rsvps: [] };
    var lineCanvas = document.getElementById("ei-views-chart");
    if (lineCanvas && global.EInviteCharts) {
      var lineData = ts.days.map(function (d, i) { return { x: d, y: ts.views[i] || 0 }; });
      var overlay = ts.days.map(function (d, i) { return { x: d, y: ts.rsvps[i] || 0 }; });
      global.EInviteCharts.redraw(lineCanvas, "line", {
        data: lineData, overlay: overlay,
        color: "var(--ei-chart-line)", overlayColor: "var(--ei-chart-overlay)",
        label: t("viewsLast30"),
      });
    }
    var devCanvas = document.getElementById("ei-device-chart");
    if (devCanvas && global.EInviteCharts && analytics.deviceSplit) {
      global.EInviteCharts.redraw(devCanvas, "donut", {
        data: analytics.deviceSplit,
        label: t("deviceSplit"),
      });
    }
  }

  async function loadLiveActivity(inviteId) {
    var box = document.getElementById("ei-live-box");
    if (!box) return;
    try {
      var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/live");
      box.innerHTML = '<strong>' + data.activeSessions + '</strong> ' + escapeHtml(t("activeSessions"))
        + ' · ' + escapeHtml(t("lastEvent")) + ': ' + (data.lastEventAt ? new Date(data.lastEventAt).toLocaleTimeString() : "—");
    } catch (e) {
      box.innerHTML = escapeHtml(t("liveDisabled"));
      box.classList.add("ei-live-disabled");
    }
  }

  function setupPrivacyControls(inviteId) {
    var disableBtn = document.getElementById("ei-analytics-disable");
    var purgeBtn = document.getElementById("ei-analytics-purge");
    var exportCsv = document.getElementById("ei-analytics-export-csv");
    var exportJson = document.getElementById("ei-analytics-export-json");
    if (disableBtn) disableBtn.onclick = async function () {
      var enabled = disableBtn.dataset.enabled !== "false";
      try {
        var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/disable", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: !enabled }),
        });
        disableBtn.dataset.enabled = data.analyticsEnabled ? "true" : "false";
        disableBtn.textContent = data.analyticsEnabled ? t("disableAnalytics") : t("enableAnalytics");
        if (global.EInviteToast) global.EInviteToast.show(data.analyticsEnabled ? t("enabledToast") : t("disabledToast"));
      } catch (e) {
        if (global.EInviteToast) global.EInviteToast.show(e.message, "error");
      }
    };
    if (purgeBtn) purgeBtn.onclick = async function () {
      if (!confirm(t("purgeConfirm"))) return;
      try {
        await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics", { method: "DELETE" });
        if (global.EInviteToast) global.EInviteToast.show(t("purged"));
        setTimeout(function () { location.reload(); }, 500);
      } catch (e) {
        if (global.EInviteToast) global.EInviteToast.show(e.message, "error");
      }
    };
    if (exportCsv) exportCsv.onclick = function () {
      location.href = "/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/export?format=csv";
    };
    if (exportJson) exportJson.onclick = function () {
      location.href = "/api/invitations/" + encodeURIComponent(inviteId) + "/analytics/export?format=json";
    };
  }

  async function render(inviteId) {
    var root = document.getElementById("analyticsRoot");
    if (!root) return;
    try {
      var data = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId) + "/analytics");
      var invite = await fetchJson("/api/invitations/" + encodeURIComponent(inviteId));
      var me = await fetchJson("/api/auth/me");
      if (!me.user) { location.href = "dashboard.html"; return; }
      var account = document.getElementById("analyticsAccount");
      if (account) account.textContent = me.user.email;
      var title = document.getElementById("analyticsTitle");
      if (title) {
        var doc = invite.document || {};
        var names = (doc.fields && doc.fields.names) || (doc.meta && doc.meta.title) || "Invitation";
        title.textContent = names + " · " + location.origin + "/i/" + invite.slug;
      }
      var a = data.analytics || {};
      var stats = a.stats || {};
      var deltas = stats.deltas || {};
      var html = '<div class="ei-grid ei-stats-grid">'
        + renderStatCard("totalViews", stats.totalViews || data.totalViews || 0, deltas.totalViews)
        + renderStatCard("uniqueRecipients", stats.uniqueRecipients || 0, deltas.uniqueRecipients)
        + renderStatCard("avgTime", fmtDuration(stats.avgDurationMs || 0), deltas.avgDurationMs)
        + renderStatCard("rsvpConversion", (stats.rsvpConversion || 0) + "%", deltas.rsvpConversion)
        + '</div>'
        + '<section class="ei-card ei-chart-card"><h2>' + escapeHtml(t("viewsLast30")) + '</h2>'
        + '<canvas id="ei-views-chart" data-chart="line" data-chart-label="' + escapeHtml(t("viewsLast30")) + '"></canvas>'
        + '</section>'
        + '<section class="ei-card ei-funnel-card"><h2>' + escapeHtml(t("funnel")) + '</h2>'
        + renderFunnel(a.funnel)
        + '</section>'
        + '<section class="ei-card ei-referrer-card"><h2>' + escapeHtml(t("topReferrers")) + '</h2>'
        + renderReferrers(a.topReferrers)
        + '</section>'
        + '<section class="ei-card ei-scroll-card"><h2>' + escapeHtml(t("scrollDepth")) + '</h2>'
        + renderScrollDepth(a.scrollDepth)
        + '</section>'
        + '<section class="ei-card ei-device-card"><h2>' + escapeHtml(t("deviceSplit")) + '</h2>'
        + '<canvas id="ei-device-chart" data-chart="donut" data-chart-label="' + escapeHtml(t("deviceSplit")) + '"></canvas>'
        + '</section>'
        + '<section class="ei-card ei-country-card"><h2>' + escapeHtml(t("countrySplit")) + '</h2>'
        + renderCountrySplit(a.countrySplit)
        + '</section>'
        + '<section class="ei-card ei-live-card"><h2>' + escapeHtml(t("liveActivity")) + '</h2>'
        + '<div id="ei-live-box" class="ei-live-box">' + escapeHtml(t("loadingLive")) + '</div></section>'
        + '<section class="ei-card ei-privacy-card"><h2>' + escapeHtml(t("disableAnalytics")) + '</h2>'
        + '<div class="ei-privacy-controls">'
        + '<button id="ei-analytics-disable" class="ei-btn" data-enabled="true">' + escapeHtml(t("disableAnalytics")) + '</button>'
        + '<button id="ei-analytics-purge" class="ei-btn ei-btn-danger">' + escapeHtml(t("purgeData")) + '</button>'
        + '<button id="ei-analytics-export-csv" class="ei-btn">' + escapeHtml(t("exportCsv")) + '</button>'
        + '<button id="ei-analytics-export-json" class="ei-btn">' + escapeHtml(t("exportJson")) + '</button>'
        + '</div></section>';
      root.innerHTML = html;
      // Render charts after DOM is updated.
      setTimeout(function () {
        renderCharts(a);
        setupPrivacyControls(inviteId);
        loadLiveActivity(inviteId);
      }, 50);
    } catch (e) {
      root.innerHTML = '<div class="ei-empty"><h2>' + escapeHtml(t("unavailable")) + '</h2><p>' + escapeHtml(e.message) + '</p></div>';
    }
  }

  var api = {
    version: 680,
    render: render,
    strings: STRINGS,
  };
  global.EInviteAnalyticsDashboard = api;

  // Auto-mount if the page has #analyticsRoot + invitation context.
  if (typeof document !== "undefined") {
    var start = function () {
      var root = document.getElementById("analyticsRoot");
      if (!root) return;
      var inviteId = getInviteId();
      if (!inviteId) {
        if (global.EInviteBackend && global.EInviteBackend.message)
          global.EInviteBackend.message(root, "Open analytics from a specific invitation.");
        return;
      }
      if (global.EInviteBackend && global.EInviteBackend.ready) {
        global.EInviteBackend.ready.then(function () {
          if (global.EInviteBackend.isAvailable && !global.EInviteBackend.isAvailable()) {
            global.EInviteBackend.message(root, "Analytics requires the full application server.");
            return;
          }
          render(inviteId);
        });
      } else {
        render(inviteId);
      }
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  }

  return api;
})(typeof window !== "undefined" ? window : this);;const $=s=>document.querySelector(s),inviteId=window.EInviteContext?.getInvitationId();localStorage.removeItem('sovan-auth-token');
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path){const r=await fetch(path,{credentials:'same-origin',headers:{}}),data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'Request failed');return data}
function last30Days(){const days=[];const now=new Date();for(let i=29;i>=0;i--){const d=new Date(now);d.setDate(now.getDate()-i);days.push(d.toISOString().slice(0,10))}return days}
function render(data,invite){const days=last30Days(),max=Math.max(1,...days.map(day=>Number(data.viewsByDay?.[day]||0))),statuses=Object.entries(data.rsvpStatuses||{}).sort((a,b)=>b[1]-a[1]),checkRate=data.guestListTotal?Math.round(data.checkedIn/data.guestListTotal*100):0;$('#analyticsTitle').textContent=`${invite.document?.fields?.names||'Invitation'} · ${location.origin}/i/${invite.slug}`;$('#analyticsRoot').innerHTML=`<div class="metric-grid"><div class="metric"><span>Total views</span><strong>${data.totalViews||0}</strong><small>All-time public opens</small></div><div class="metric"><span>Last 30 days</span><strong>${data.views30Days||0}</strong><small>Recent invitation opens</small></div><div class="metric"><span>${data.rsvpEnabled===false?'RSVP':'RSVP responses'}</span><strong>${data.rsvpEnabled===false?'Disabled':(data.rsvpTotal||0)}</strong><small>${data.rsvpEnabled===false?'Historical responses are preserved':`${data.rsvpGuests||0} total responding guests`}</small></div><div class="metric"><span>Checked in</span><strong>${data.checkedIn||0}</strong><small>${data.guestListTotal||0} guests on list</small></div></div><div class="analytics-grid"><section class="chart-card"><h2>Views — last 30 days</h2><div class="bars">${days.map(day=>{const value=Number(data.viewsByDay?.[day]||0),height=Math.max(1,Math.round(value/max*100));return`<div class="bar-wrap" data-label="${day}: ${value} view${value===1?'':'s'}"><span class="bar" style="height:${height}%"></span></div>`}).join('')}</div></section><aside class="summary-card"><h2>RSVP breakdown</h2>${data.rsvpEnabled===false?'<p>RSVP disabled for this invitation. Historical response data remains available.</p>':statuses.length?statuses.map(([name,count])=>`<div class="status-row"><span>${esc(name)}</span><strong>${count}</strong></div>`).join(''):'<p>No RSVP responses yet.</p>'}<h2>Guest check-in</h2><div class="progress"><span style="width:${checkRate}%"></span></div><p><strong>${checkRate}%</strong> of listed guests checked in.</p><h2>Publishing</h2><p>Public slug: <code>${esc(invite.slug)}</code></p><p>Access: ${esc(invite.accessMode||'unlisted')}</p></aside></div>`}
async function load(){if(!inviteId)return window.EInviteBackend?.message($('#analyticsRoot'),'Open analytics from a specific invitation.');if(window.EInviteBackend?.ready)await window.EInviteBackend.ready;if(window.EInviteBackend&&!window.EInviteBackend.isAvailable())return window.EInviteBackend.message($('#analyticsRoot'),'Analytics requires the full application server.');try{const [data,invite,me]=await Promise.all([api(`/api/invitations/${inviteId}/analytics`),api(`/api/invitations/${inviteId}`),api('/api/auth/me')]);if(!me.user)return location.href='dashboard.html';$('#analyticsAccount').textContent=me.user.email;render(data,invite)}catch(error){$('#analyticsRoot').innerHTML=`<div class="empty"><h2>Analytics unavailable</h2><p>${esc(error.message)}</p></div>`}}
$('#refreshAnalytics').onclick=load;load();;(function(){
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const html=document.documentElement, body=document.body;
body.classList.add('ui-boot');requestAnimationFrame(()=>requestAnimationFrame(()=>{body.classList.remove('ui-boot');body.classList.add('ui-ready')}));
function currentMode(){return localStorage.getItem('einvite-theme-mode')==='dark'?'dark':'light'}
function applyTheme(mode,announce=false){
  const resolved=mode==='dark'?'dark':'light';
  if(announce){html.classList.add('theme-transition');setTimeout(()=>html.classList.remove('theme-transition'),340)}
  html.dataset.theme=resolved;html.dataset.themeMode=mode;html.style.colorScheme=resolved;
  localStorage.setItem('einvite-theme-mode',mode);
  $$('.ui-theme-menu button').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));
  const icon=$('.ui-theme-icon');if(icon)icon.textContent=resolved==='dark'?'☾':'☀';
  if(announce)toast(`${resolved[0].toUpperCase()+resolved.slice(1)} appearance`,'◐');
}
applyTheme(currentMode());
function installThemeControl(){
  const header=$('body:not(:has(.guest))>header');if(header&&$('.ui-theme',header))return;
  const wrap=document.createElement('div');wrap.className='ui-theme'+(header?'':' floating');
  wrap.innerHTML=`<button type="button" class="ui-theme-button" aria-label="Appearance" aria-haspopup="menu" aria-expanded="false" data-ui-tooltip="Appearance (Alt+T)"><span class="ui-theme-icon">◐</span></button><div class="ui-theme-menu" role="menu" hidden>
  <button type="button" data-mode="light"><span>☀</span><b>Light</b><span class="check">✓</span></button>
  <button type="button" data-mode="dark"><span>☾</span><b>Dark</b><span class="check">✓</span></button></div>`;
  if(header){const logout=$('#logoutBtn',header); if(logout)header.insertBefore(wrap,logout); else header.append(wrap)}else document.body.append(wrap);
  const trigger=$('.ui-theme-button',wrap),menu=$('.ui-theme-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  $$('[data-mode]',menu).forEach(b=>b.onclick=()=>{applyTheme(b.dataset.mode,true);menu.hidden=true;trigger.setAttribute('aria-expanded','false')});
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
  applyTheme(currentMode());
}
installThemeControl();
window.EInviteThemeController=Object.freeze({currentMode,applyTheme,cycle(){const modes=['light','dark'],i=modes.indexOf(currentMode());const next=modes[(i+1)%2];applyTheme(next,true);return next}});
function installAppLauncher(){
  const header=$('body:not(:has(.guest))>header');if(!header||$('.ui-app-launcher',header))return;
  const brand=header.querySelector('strong');if(!brand)return;
  const wrap=document.createElement('div');wrap.className='ui-app-launcher';
  wrap.innerHTML=`<button type="button" class="ui-app-launcher-button" aria-label="Open workspace navigation" aria-expanded="false" data-ui-tooltip="Workspace navigation"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></button><div class="ui-app-launcher-menu" hidden><header><strong>Workspace</strong></header><div class="ui-app-grid">
  <a href="dashboard.html"><span>⌂</span><div><b>Dashboard</b><small>Your invitations</small></div></a>
  <a href="templates.html"><span>✦</span><div><b>Templates</b><small>Reusable designs</small></div></a>
  <a href="materials.html"><span>▣</span><div><b>Materials</b><small>Photos, audio & video</small></div></a>
  <a href="designer.html"><span>◇</span><div><b>Designer</b><small>Professional workspace</small></div></a>
  <a href="billing.html"><span>◎</span><div><b>Plans</b><small>Usage & limits</small></div></a>
  <a href="account.html"><span>◉</span><div><b>Account</b><small>Profile & security</small></div></a></div></div>`;
  brand.after(wrap);const trigger=$('.ui-app-launcher-button',wrap),menu=$('.ui-app-launcher-menu',wrap);
  trigger.onclick=e=>{e.stopPropagation();const open=menu.hidden;menu.hidden=!open;trigger.setAttribute('aria-expanded',String(open))};
  document.addEventListener('click',e=>{if(!wrap.contains(e.target)){menu.hidden=true;trigger.setAttribute('aria-expanded','false')}});
}
installAppLauncher();
const page=location.pathname.split('/').pop()||'dashboard.html';$$('body:not(:has(.guest))>header a').forEach(a=>{const href=(a.getAttribute('href')||'').split('?')[0].split('#')[0];if(href===page)a.classList.add('ui-current')});
addEventListener('pointerdown',e=>{const b=e.target.closest('button');if(!b||b.disabled)return;const r=b.getBoundingClientRect(),s=document.createElement('span');s.className='ui-ripple';const size=Math.max(r.width,r.height);s.style.width=s.style.height=size+'px';s.style.left=(e.clientX-r.left)+'px';s.style.top=(e.clientY-r.top)+'px';b.append(s);setTimeout(()=>s.remove(),560)},true);
const spotlightSelectors='.invite-card,.metric,.response-card,.wish-card,.usage-card,.plan,.studio-card,.material-card-page,.template-choice,.page-nav-card,.studio-quick-grid button,.page-builder-library button,.element-library button,.block-library button';
$$(spotlightSelectors).forEach(el=>{el.classList.add('ui-spotlight');el.addEventListener('pointermove',e=>{const r=el.getBoundingClientRect();el.style.setProperty('--mx',`${e.clientX-r.left}px`);el.style.setProperty('--my',`${e.clientY-r.top}px`)})});
const stack=document.createElement('div');stack.className='ui-toast-stack';document.body.append(stack);
function toast(message,icon='✓'){const el=document.createElement('div');el.className='ui-toast';el.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(el);setTimeout(()=>{el.classList.add('out');setTimeout(()=>el.remove(),240)},2200)}
window.einviteToast=toast;
const tip=document.createElement('div');tip.className='ui-tooltip';document.body.append(tip);let tipTimer;
document.addEventListener('pointerover',e=>{const el=e.target.closest('[data-ui-tooltip],button[title]');if(!el)return;const txt=el.dataset.uiTooltip||el.getAttribute('title');if(!txt)return;clearTimeout(tipTimer);tipTimer=setTimeout(()=>{const r=el.getBoundingClientRect();tip.textContent=txt;tip.style.left=Math.max(8,Math.min(innerWidth-200,r.left+r.width/2))+'px';tip.style.top=Math.max(8,r.bottom+8)+'px';tip.classList.add('show')},350)});
document.addEventListener('pointerout',e=>{if(e.target.closest?.('[data-ui-tooltip],button[title]')){clearTimeout(tipTimer);tip.classList.remove('show')}});
if(body.classList.contains('studio-experience')){
  const main=$('body.studio-experience>main'),toolbar=$('.studio-canvas-toolbar');
  const canvasViewport=$('.canvas-viewport');
  canvasViewport?.addEventListener('pointermove',e=>{const r=canvasViewport.getBoundingClientRect();canvasViewport.style.setProperty('--canvas-pointer-x',`${e.clientX-r.left}px`);canvasViewport.style.setProperty('--canvas-pointer-y',`${e.clientY-r.top}px`)});
  let leftWidth=Math.max(300,Math.min(520,Number(localStorage.getItem('einvite-left-width'))||370)),rightWidth=Math.max(280,Math.min(460,Number(localStorage.getItem('einvite-right-width'))||330));
  function setWidths(){const available=Math.max(900,window.innerWidth||1440),stageMin=360;leftWidth=Math.max(290,Math.min(560,leftWidth,available-rightWidth-stageMin));rightWidth=Math.max(280,Math.min(520,rightWidth,available-leftWidth-stageMin));for(const target of [html,body]){target.style.setProperty('--studio-left-width',`${leftWidth}px`);target.style.setProperty('--einvite-left-width',`${leftWidth}px`);target.style.setProperty('--studio-right-width',`${rightWidth}px`);target.style.setProperty('--einvite-inspector-width',`${rightWidth}px`)}}setWidths();window.addEventListener('resize',setWidths);
  function addToggle(side,label,symbol){if(!toolbar)return;const b=document.createElement('button');b.type='button';b.className='studio-panel-toggle';b.innerHTML=symbol;b.setAttribute('aria-label',label);b.dataset.uiTooltip=label;b.onclick=()=>{const cls=`studio-${side}-collapsed`;body.classList.toggle(cls);b.setAttribute('aria-pressed',String(body.classList.contains(cls)));localStorage.setItem(`einvite-${side}-collapsed`,body.classList.contains(cls)?'1':'0')};toolbar.prepend(b);if(localStorage.getItem(`einvite-${side}-collapsed`)==='1'){body.classList.add(`studio-${side}-collapsed`);b.setAttribute('aria-pressed','true')}return b}
  addToggle('right','Toggle inspector','▥');addToggle('left','Toggle creation panel','▤');
  function resizer(side){if(!main)return;const h=document.createElement('div');h.className=`studio-panel-resizer ${side[0]}`;main.append(h);h.addEventListener('pointerdown',e=>{h.setPointerCapture(e.pointerId);h.classList.add('dragging');body.style.userSelect='none';const start=e.clientX,startL=leftWidth,startR=rightWidth;const move=ev=>{if(side==='left'){leftWidth=Math.max(290,Math.min(560,startL+(ev.clientX-start)))}else{rightWidth=Math.max(280,Math.min(520,startR-(ev.clientX-start)))}setWidths()};const up=()=>{h.classList.remove('dragging');body.style.userSelect='';localStorage.setItem('einvite-left-width',leftWidth);localStorage.setItem('einvite-right-width',rightWidth);h.removeEventListener('pointermove',move);h.removeEventListener('pointerup',up)};h.addEventListener('pointermove',move);h.addEventListener('pointerup',up)})}
  resizer('left');resizer('right');
  const context=document.createElement('div');context.className='ui-context-menu';context.hidden=true;
  context.innerHTML=`<button data-cmd="duplicate"><span>⧉</span><b>Duplicate</b><kbd>Ctrl+D</kbd></button><button data-cmd="copy"><span>□</span><b>Copy</b><kbd>Ctrl+C</kbd></button><button data-cmd="paste"><span>▣</span><b>Paste</b><kbd>Ctrl+V</kbd></button><div class="ui-context-sep"></div><button data-cmd="forward"><span>↑</span><b>Bring forward</b><kbd></kbd></button><button data-cmd="backward"><span>↓</span><b>Send backward</b><kbd></kbd></button><button data-cmd="lock"><span>◇</span><b>Lock / unlock</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="addText"><span>T</span><b>Add text</b><kbd></kbd></button><button data-cmd="fit"><span>⌗</span><b>Fit canvas</b><kbd></kbd></button><div class="ui-context-sep"></div><button data-cmd="delete" class="danger"><span>×</span><b>Delete</b><kbd>Del</kbd></button>`;
  document.body.append(context);
  const cmdMap={duplicate:'duplicate',copy:'copyObjects',paste:'pasteObjects',forward:'bringForward',backward:'sendBackward',addText:'addText',fit:'fitCanvas',delete:'deleteBtn'};
  context.addEventListener('click',e=>{const b=e.target.closest('[data-cmd]');if(!b)return;const cmd=b.dataset.cmd;if(cmd==='lock'){const lock=$('#objectLocked');if(lock){lock.checked=!lock.checked;lock.dispatchEvent(new Event('change',{bubbles:true}))}}else document.getElementById(cmdMap[cmd])?.click();context.hidden=true});
  $('#stage')?.addEventListener('contextmenu',e=>{e.preventDefault();const obj=e.target.closest('.object');if(obj&&!obj.classList.contains('selected')&&!obj.classList.contains('multi-selected'))obj.click();context.hidden=false;const w=220,h=390;context.style.left=Math.min(e.clientX,innerWidth-w-8)+'px';context.style.top=Math.min(e.clientY,innerHeight-h-8)+'px'});
  document.addEventListener('pointerdown',e=>{if(!context.contains(e.target))context.hidden=true});
}
addEventListener('click',e=>{const a=e.target.closest('a[href]');if(!a||e.defaultPrevented||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname===location.pathname&&u.hash)return;if(a.closest('dialog'))return;e.preventDefault();body.classList.add('ui-page-leaving');setTimeout(()=>location.href=u.href,115)});
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const editor=!!$('#stage')&&!!$('.studio-left-panel');
document.documentElement.classList.add('final-ui-ready');
const progress=document.createElement('div'); progress.className='final-route-progress'; document.body.append(progress);
addEventListener('beforeunload',()=>progress.classList.add('active'));
document.addEventListener('click',e=>{
  const a=e.target.closest('a[href]'); if(!a||a.target==='_blank'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
  try{const u=new URL(a.href,location.href);if(u.origin===location.origin&&u.href!==location.href)progress.classList.add('active')}catch{}
},true);
if(!document.body.classList.contains('guest')) requestAnimationFrame(()=>document.body.classList.add('final-page-entered'));
const globalObserver=new MutationObserver(()=>{
  $$('.empty:not([data-final-empty])').forEach(el=>{el.dataset.finalEmpty='1';el.classList.add('final-empty-state')});
  $$('dialog:not([data-final-dialog])').forEach(el=>{el.dataset.finalDialog='1';el.classList.add('final-dialog')});
});
globalObserver.observe(document.body,{subtree:true,childList:true});
if(!editor)return;
const stage=$('#stage');
const objectPane=$('[data-inspector-pane="object"]');
const elementsPane=$('[data-studio-pane="elements"]');
const activeObjects=()=>$$('.object.selected,.object.multi-selected').filter(x=>x.isConnected);
const saveNow=()=>{try{typeof save==='function'&&save()}catch{}};
const applyNow=items=>{items.forEach(item=>{try{typeof applyObjectVisualStyle==='function'&&applyObjectVisualStyle(item)}catch{}});try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{};try{typeof refreshSelectionUI==='function'&&refreshSelectionUI()}catch{}};
const setData=(key,value,{apply=true}={})=>{const items=activeObjects();if(!items.length)return;items.forEach(item=>item.dataset[key]=String(value));if(apply)applyNow(items);saveNow();refreshAdvancedControls();refreshTimeline()};
const boolData=(key,value)=>setData(key,value?'true':'false');
const selectedType=()=>activeObjects()[0]?.dataset.objectType||'';
const safeText=node=>(node?.querySelector('.content')?.textContent||node?.dataset.alt||node?.dataset.objectType||'Object').trim().slice(0,38);
function toast(message,icon='✦'){
  if(typeof window.uiToast==='function')return window.uiToast(message,icon);
  let stack=$('.final-toast-stack');if(!stack){stack=document.createElement('div');stack.className='final-toast-stack';document.body.append(stack)}
  const t=document.createElement('div');t.className='final-toast';t.innerHTML=`<span>${icon}</span><b>${message}</b>`;stack.append(t);setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),220)},1900)
}
function selectOnly(item){try{typeof clearSelection==='function'&&clearSelection();typeof setSelection==='function'&&setSelection([item])}catch{item.click()}setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0)}
function makeId(prefix='object'){return`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,7)}`}
const advanced=document.createElement('section'); advanced.className='final-advanced-inspector';
advanced.innerHTML=`
  <div class="final-panel-title"><div><small>Creative controls</small><h2>Effects & motion</h2></div><span class="final-beta">Advanced</span></div>
  <details open class="final-control-group" data-final-group="surface"><summary>Surface & blending</summary>
    <label class="final-toggle-row"><span>Object background</span><input id="finalBgEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Background<input id="finalBgColor" type="color" value="#ffffff"></label><label>Opacity <span id="finalBgOpacityValue">100%</span><input id="finalBgOpacity" type="range" min="0" max="100" value="100"></label></div>
    <label>Blend mode<select id="finalBlendMode"><option value="normal">Normal</option><option value="multiply">Multiply</option><option value="screen">Screen</option><option value="overlay">Overlay</option><option value="soft-light">Soft light</option><option value="darken">Darken</option><option value="lighten">Lighten</option></select></label>
  </details>
  <details class="final-control-group" data-final-group="shape"><summary>Gradient fill</summary>
    <label>Fill type<select id="finalFillMode"><option value="solid">Solid</option><option value="gradient">Gradient</option></select></label>
    <div class="final-two-col"><label>Start<input id="finalGradientStart" type="color" value="#d9a6ad"></label><label>End<input id="finalGradientEnd" type="color" value="#9d4555"></label></div>
    <label>Angle <span id="finalGradientAngleValue">135°</span><input id="finalGradientAngle" type="range" min="0" max="360" value="135"></label>
    <div class="final-gradient-preview" id="finalGradientPreview"></div>
  </details>
  <details class="final-control-group" data-final-group="text"><summary>Text effects</summary>
    <label>Transform<select id="finalTextTransform"><option value="none">As typed</option><option value="uppercase">UPPERCASE</option><option value="lowercase">lowercase</option><option value="capitalize">Capitalize</option></select></label>
    <label class="final-toggle-row"><span>Gradient text</span><input id="finalTextGradientEnabled" type="checkbox"></label>
    <div class="final-two-col"><label>Start<input id="finalTextGradientStart" type="color" value="#9d4555"></label><label>End<input id="finalTextGradientEnd" type="color" value="#b58a3a"></label></div>
    <label>Gradient angle <span id="finalTextGradientAngleValue">90°</span><input id="finalTextGradientAngle" type="range" min="0" max="360" value="90"></label>
    <div class="final-two-col"><label>Outline <span id="finalStrokeValue">0px</span><input id="finalStrokeWidth" type="range" min="0" max="8" step="0.5" value="0"></label><label>Outline color<input id="finalStrokeColor" type="color" value="#ffffff"></label></div>
    <div class="final-two-col"><label>Text shadow <span id="finalTextShadowValue">0px</span><input id="finalTextShadowBlur" type="range" min="0" max="40" value="0"></label><label>Shadow color<input id="finalTextShadowColor" type="color" value="#000000"></label></div>
    <div class="final-style-presets">
      <button type="button" data-final-text-style="luxury">Luxury Gold</button><button type="button" data-final-text-style="editorial">Editorial</button><button type="button" data-final-text-style="soft">Soft Glow</button><button type="button" data-final-text-style="minimal">Minimal</button>
    </div>
  </details>
  <details open class="final-control-group" data-final-group="motion"><summary>Motion timing</summary>
    <label>Animation delay <span id="finalDelayValue">0ms</span><input id="finalAnimationDelay" type="range" min="0" max="5000" step="50" value="0"></label>
    <div class="final-inline-actions"><button type="button" id="finalPreviewSelection">▶ Preview selected</button><button type="button" id="finalPreviewPage">▶ Preview page</button><button type="button" id="finalStagger">Stagger selected</button></div>
  </details>
  <details class="final-control-group" data-final-group="layout"><summary>Smart layout</summary>
    <div class="final-layout-grid"><button data-final-layout="horizontal">Horizontal stack</button><button data-final-layout="vertical">Vertical stack</button><button data-final-layout="grid">Smart grid</button><button data-final-layout="center">Center selection</button><button data-final-layout="equal-width">Equal width</button><button data-final-layout="equal-height">Equal height</button></div>
  </details>`;
if(objectPane)objectPane.append(advanced);
const controls={
 bgEnabled:$('#finalBgEnabled'),bgColor:$('#finalBgColor'),bgOpacity:$('#finalBgOpacity'),blend:$('#finalBlendMode'),fillMode:$('#finalFillMode'),gradientStart:$('#finalGradientStart'),gradientEnd:$('#finalGradientEnd'),gradientAngle:$('#finalGradientAngle'),textGradientEnabled:$('#finalTextGradientEnabled'),textGradientStart:$('#finalTextGradientStart'),textGradientEnd:$('#finalTextGradientEnd'),textGradientAngle:$('#finalTextGradientAngle'),strokeWidth:$('#finalStrokeWidth'),strokeColor:$('#finalStrokeColor'),textShadowBlur:$('#finalTextShadowBlur'),textShadowColor:$('#finalTextShadowColor'),textTransform:$('#finalTextTransform'),delay:$('#finalAnimationDelay')
};
function refreshAdvancedControls(){
  const item=activeObjects()[0],has=!!item,type=item?.dataset.objectType||'';
  advanced.classList.toggle('is-disabled',!has);
  $$('[data-final-group="shape"]',advanced).forEach(x=>x.hidden=type!=='shape');
  $$('[data-final-group="text"]',advanced).forEach(x=>x.hidden=!['text','decoration'].includes(type));
  if(!item)return;
  controls.bgEnabled.checked=item.dataset.backgroundEnabled==='true';controls.bgColor.value=item.dataset.backgroundColor||'#ffffff';controls.bgOpacity.value=item.dataset.backgroundOpacity??100;$('#finalBgOpacityValue').textContent=`${controls.bgOpacity.value}%`;controls.blend.value=item.dataset.blendMode||'normal';
  controls.fillMode.value=item.dataset.fillMode||'solid';controls.gradientStart.value=item.dataset.gradientStart||'#d9a6ad';controls.gradientEnd.value=item.dataset.gradientEnd||'#9d4555';controls.gradientAngle.value=item.dataset.gradientAngle||135;$('#finalGradientAngleValue').textContent=`${controls.gradientAngle.value}°`;$('#finalGradientPreview').style.background=`linear-gradient(${controls.gradientAngle.value}deg,${controls.gradientStart.value},${controls.gradientEnd.value})`;
  controls.textGradientEnabled.checked=item.dataset.textGradientEnabled==='true';controls.textGradientStart.value=item.dataset.textGradientStart||'#9d4555';controls.textGradientEnd.value=item.dataset.textGradientEnd||'#b58a3a';controls.textGradientAngle.value=item.dataset.textGradientAngle||90;$('#finalTextGradientAngleValue').textContent=`${controls.textGradientAngle.value}°`;controls.strokeWidth.value=item.dataset.textStrokeWidth||0;$('#finalStrokeValue').textContent=`${controls.strokeWidth.value}px`;controls.strokeColor.value=item.dataset.textStrokeColor||'#ffffff';controls.textShadowBlur.value=item.dataset.textShadowBlur||0;$('#finalTextShadowValue').textContent=`${controls.textShadowBlur.value}px`;controls.textShadowColor.value=item.dataset.textShadowColor||'#000000';controls.textTransform.value=item.dataset.textTransform||'none';controls.delay.value=item.dataset.animationDelay||0;$('#finalDelayValue').textContent=`${controls.delay.value}ms`;
}
controls.bgEnabled.onchange=e=>boolData('backgroundEnabled',e.target.checked);controls.bgColor.oninput=e=>setData('backgroundColor',e.target.value);controls.bgOpacity.oninput=e=>{$('#finalBgOpacityValue').textContent=`${e.target.value}%`;setData('backgroundOpacity',e.target.value)};controls.blend.onchange=e=>setData('blendMode',e.target.value);
controls.fillMode.onchange=e=>setData('fillMode',e.target.value);controls.gradientStart.oninput=e=>{setData('gradientStart',e.target.value);refreshAdvancedControls()};controls.gradientEnd.oninput=e=>{setData('gradientEnd',e.target.value);refreshAdvancedControls()};controls.gradientAngle.oninput=e=>{$('#finalGradientAngleValue').textContent=`${e.target.value}°`;setData('gradientAngle',e.target.value);refreshAdvancedControls()};
controls.textGradientEnabled.onchange=e=>boolData('textGradientEnabled',e.target.checked);controls.textGradientStart.oninput=e=>setData('textGradientStart',e.target.value);controls.textGradientEnd.oninput=e=>setData('textGradientEnd',e.target.value);controls.textGradientAngle.oninput=e=>{$('#finalTextGradientAngleValue').textContent=`${e.target.value}°`;setData('textGradientAngle',e.target.value)};controls.strokeWidth.oninput=e=>{$('#finalStrokeValue').textContent=`${e.target.value}px`;setData('textStrokeWidth',e.target.value)};controls.strokeColor.oninput=e=>setData('textStrokeColor',e.target.value);controls.textShadowBlur.oninput=e=>{$('#finalTextShadowValue').textContent=`${e.target.value}px`;setData('textShadowBlur',e.target.value)};controls.textShadowColor.oninput=e=>setData('textShadowColor',e.target.value);controls.textTransform.onchange=e=>setData('textTransform',e.target.value);controls.delay.oninput=e=>{$('#finalDelayValue').textContent=`${e.target.value}ms`;setData('animationDelay',e.target.value,{apply:false})};
const textStyles={
 luxury:{textGradientEnabled:'true',textGradientStart:'#7a5718',textGradientEnd:'#e9c86e',textGradientAngle:'90',textStrokeWidth:'0',textShadowBlur:'10',textShadowColor:'#5b3a0b',fontWeight:'700',letterSpacing:'1'},
 editorial:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'italic',letterSpacing:'0.5',textTransform:'none'},
 soft:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'18',textShadowColor:'#9d4555',fontWeight:'400',letterSpacing:'0'},
 minimal:{textGradientEnabled:'false',textStrokeWidth:'0',textShadowBlur:'0',fontWeight:'400',fontStyle:'normal',letterSpacing:'2',textTransform:'uppercase'}
};
$$('[data-final-text-style]').forEach(b=>b.onclick=()=>{const preset=textStyles[b.dataset.finalTextStyle];const items=activeObjects().filter(x=>['text','decoration'].includes(x.dataset.objectType));items.forEach(item=>Object.entries(preset).forEach(([k,v])=>item.dataset[k]=v));applyNow(items);saveNow();refreshAdvancedControls();toast(`${b.textContent.trim()} style applied`)});
function keyframesFor(name){return({
 'fade-up':[{opacity:0,transform:'translateY(24px)'},{opacity:1,transform:'translateY(0)'}],
 'soft-zoom':[{opacity:0,transform:'scale(.9)'},{opacity:1,transform:'scale(1)'}],
 'slide-left':[{opacity:0,transform:'translateX(45px)'},{opacity:1,transform:'translateX(0)'}],
 'blur-in':[{opacity:0,filter:'blur(14px)'},{opacity:1,filter:'blur(0)'}],
 'bounce-in':[{opacity:0,transform:'scale(.72)'},{opacity:1,transform:'scale(1.05)',offset:.72},{opacity:1,transform:'scale(1)'}],
 'flip-in':[{opacity:0,transform:'rotateY(80deg)'},{opacity:1,transform:'rotateY(0)'}],
 'float':[{transform:'translateY(0)'},{transform:'translateY(-12px)'},{transform:'translateY(0)'}],
 none:[{opacity:1},{opacity:1}]
})[name]||[{opacity:0},{opacity:1}]}
function previewObjects(items){items.forEach(item=>{const duration=Math.max(300,Math.min(3000,Number(item.dataset.duration||900))),delay=Math.max(0,Math.min(5000,Number(item.dataset.animationDelay||0))),rotation=`rotate(${Number(item.dataset.rotation||0)}deg)`,frames=keyframesFor(item.dataset.animation||'fade-up').map(frame=>({...frame,transform:frame.transform?`${frame.transform} ${rotation}`:rotation}));item.animate(frames,{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)',fill:'none',iterations:item.dataset.animation==='float'?2:1})})}
window.EInvitePreviewObjects=items=>previewObjects(Array.isArray(items)?items:[]);
$('#finalPreviewSelection').onclick=()=>previewObjects(activeObjects());$('#finalPreviewPage').onclick=()=>previewObjects($$('.object'));$('#finalStagger').onclick=()=>{const items=activeObjects();if(items.length<2)return toast('Select two or more objects to stagger','!');items.sort((a,b)=>(parseFloat(a.style.top)||0)-(parseFloat(b.style.top)||0)||(parseFloat(a.style.left)||0)-(parseFloat(b.style.left)||0)).forEach((item,i)=>item.dataset.animationDelay=String(i*140));saveNow();refreshAdvancedControls();refreshTimeline();previewObjects(items);toast(`Staggered ${items.length} objects`)};
const timeline=document.createElement('section');timeline.className='final-timeline';timeline.innerHTML=`<div class="final-panel-title"><div><small>Sequence</small><h2>Motion timeline</h2></div><button id="finalTimelinePlay" type="button">▶ Play all</button></div><div id="finalTimelineRows"></div>`;if(objectPane)objectPane.append(timeline);
function refreshTimeline(){const host=$('#finalTimelineRows');if(!host)return;const items=$$('.object').sort((a,b)=>Number(a.style.zIndex||0)-Number(b.style.zIndex||0));host.innerHTML=items.length?'':'<p class="hint">Add objects to build a motion sequence.</p>';const maxEnd=Math.max(1000,...items.map(x=>Number(x.dataset.animationDelay||0)+Number(x.dataset.duration||900)));items.forEach(item=>{const row=document.createElement('button');row.type='button';row.className=`final-timeline-row${item.classList.contains('selected')||item.classList.contains('multi-selected')?' active':''}`;const delay=Number(item.dataset.animationDelay||0),duration=Number(item.dataset.duration||900);row.innerHTML=`<span class="final-timeline-icon">${item.dataset.objectType==='image'?'▣':item.dataset.objectType==='shape'?'□':'T'}</span><span class="final-timeline-name">${safeText(item)||'Object'}</span><span class="final-timeline-track"><i style="left:${delay/maxEnd*100}%;width:${Math.max(4,duration/maxEnd*100)}%"></i></span><small>${delay}ms</small>`;row.onclick=()=>selectOnly(item);host.append(row)})}
$('#finalTimelinePlay').onclick=()=>previewObjects($$('.object'));
function stagePercentFrame(item){return{left:parseFloat(item.style.left)||0,top:parseFloat(item.style.top)||0,width:item.getBoundingClientRect().width/stage.getBoundingClientRect().width*100,height:item.getBoundingClientRect().height/stage.getBoundingClientRect().height*100}}
function smartLayout(kind){const items=activeObjects().filter(x=>x.dataset.locked!=='true');if(!items.length)return toast('Select objects first','!');const frames=items.map(x=>({item:x,...stagePercentFrame(x)}));if(kind==='center'){const minL=Math.min(...frames.map(x=>x.left)),maxR=Math.max(...frames.map(x=>x.left+x.width)),minT=Math.min(...frames.map(x=>x.top)),maxB=Math.max(...frames.map(x=>x.top+x.height)),dx=50-(minL+maxR)/2,dy=50-(minT+maxB)/2;frames.forEach(x=>{x.item.style.left=`${x.left+dx}%`;x.item.style.top=`${x.top+dy}%`})}
 else if(kind==='horizontal'){const gap=3,total=frames.reduce((s,x)=>s+x.width,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.left-b.left).forEach(x=>{x.item.style.left=`${cur}%`;x.item.style.top='45%';cur+=x.width+gap})}
 else if(kind==='vertical'){const gap=2,total=frames.reduce((s,x)=>s+x.height,0)+gap*(frames.length-1),start=Math.max(4,(100-total)/2);let cur=start;frames.sort((a,b)=>a.top-b.top).forEach(x=>{x.item.style.top=`${cur}%`;x.item.style.left=`${Math.max(4,(100-x.width)/2)}%`;cur+=x.height+gap})}
 else if(kind==='grid'){const cols=Math.ceil(Math.sqrt(frames.length)),gap=3,cell=(92-gap*(cols-1))/cols;frames.forEach((x,i)=>{const row=Math.floor(i/cols),col=i%cols;x.item.style.left=`${4+col*(cell+gap)}%`;x.item.style.top=`${8+row*22}%`;x.item.style.width=`${cell}%`})}
 else if(kind==='equal-width'){const w=Math.max(...frames.map(x=>x.width));frames.forEach(x=>x.item.style.width=`${w}%`)}
 else if(kind==='equal-height'){const h=Math.max(...frames.map(x=>x.height));frames.forEach(x=>x.item.style.height=`${h}%`)}
 try{typeof updateSelectionBounds==='function'&&updateSelectionBounds()}catch{}saveNow();toast('Layout updated')}
$$('[data-final-layout]').forEach(b=>b.onclick=()=>smartLayout(b.dataset.finalLayout));
const library=[
 {id:'flourish-1',name:'Classic flourish',cat:'Ornaments',glyph:'❦'},{id:'flourish-2',name:'Fine flourish',cat:'Ornaments',glyph:'❧'},{id:'sparkle-1',name:'Four-point sparkle',cat:'Ornaments',glyph:'✦'},{id:'sparkle-2',name:'Soft sparkle',cat:'Ornaments',glyph:'✧'},{id:'star-1',name:'Decorative star',cat:'Ornaments',glyph:'✶'},{id:'diamond-1',name:'Open diamond',cat:'Ornaments',glyph:'◇'},{id:'diamond-2',name:'Solid diamond',cat:'Ornaments',glyph:'◆'},
 {id:'heart-1',name:'Classic heart',cat:'Romance',glyph:'♥'},{id:'heart-2',name:'Outline heart',cat:'Romance',glyph:'♡'},{id:'rings',name:'Wedding rings',cat:'Romance',glyph:'◯◯'},{id:'infinity',name:'Forever mark',cat:'Romance',glyph:'∞'},{id:'love-spark',name:'Love sparkle',cat:'Romance',glyph:'♡ ✦ ♡'},
 {id:'leaf-1',name:'Botanical leaf',cat:'Botanical',glyph:'❧'},{id:'flower-1',name:'Flower mark',cat:'Botanical',glyph:'✿'},{id:'flower-2',name:'Elegant flower',cat:'Botanical',glyph:'❀'},{id:'petal',name:'Petal cluster',cat:'Botanical',glyph:'❋'},{id:'branch',name:'Leaf branch',cat:'Botanical',glyph:'☘'},
 {id:'crown',name:'Royal crown',cat:'Ceremonial',glyph:'♛'},{id:'royal',name:'Royal emblem',cat:'Ceremonial',glyph:'♔'},{id:'sun',name:'Ceremonial sun',cat:'Ceremonial',glyph:'☼'},{id:'blessing',name:'Blessing mark',cat:'Ceremonial',glyph:'✺'},{id:'lotus',name:'Lotus-inspired mark',cat:'Ceremonial',glyph:'✾'},
 {id:'quote',name:'Quote mark',cat:'Editorial',glyph:'“'},{id:'bullet',name:'Editorial bullet',cat:'Editorial',glyph:'•'},{id:'section',name:'Section divider',cat:'Editorial',glyph:'— ✦ —'},{id:'roman',name:'Roman divider',cat:'Editorial',glyph:'I · II · III'},
 {id:'rect',name:'Rectangle',cat:'Shapes',shape:'rectangle'},{id:'circle',name:'Circle',cat:'Shapes',shape:'circle'},{id:'line',name:'Line',cat:'Shapes',shape:'line'},{id:'panel',name:'Glass panel',cat:'Shapes',shape:'panel'},
 {id:'title-luxury',name:'Luxury title',cat:'Text styles',text:'YOUR CELEBRATION',preset:'luxury'},{id:'title-editorial',name:'Editorial title',cat:'Text styles',text:'A beautiful beginning',preset:'editorial'},{id:'khmer-title',name:'Khmer ceremonial title',cat:'Text styles',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍',preset:'khmer'},{id:'date-badge',name:'Date badge',cat:'Text styles',text:'27 · 12 · 2026',preset:'date'},
 {id:'khmer-diamond-row',name:'Khmer diamond row',cat:'Khmer motifs',glyph:'◇ ◆ ◇ ◆ ◇'},{id:'khmer-gold-divider',name:'Ceremonial divider',cat:'Khmer motifs',glyph:'✦ ◇ ✦'},{id:'khmer-lotus-row',name:'Lotus row',cat:'Khmer motifs',glyph:'✾  ✾  ✾'},{id:'khmer-blessing-row',name:'Blessing ornament',cat:'Khmer motifs',glyph:'✺ ✦ ✺'},{id:'khmer-temple-line',name:'Temple line',cat:'Khmer motifs',glyph:'⌂ ◇ ⌂'},{id:'khmer-royal-row',name:'Royal row',cat:'Khmer motifs',glyph:'♔  ◆  ♔'},
 {id:'confetti-1',name:'Confetti sparkle',cat:'Celebration',glyph:'✦ ✧ ✶ ✦'},{id:'party-stars',name:'Party stars',cat:'Celebration',glyph:'★ ☆ ★'},{id:'balloon-pair',name:'Balloon pair',cat:'Celebration',glyph:'◯  ◯'},{id:'gift-mark',name:'Gift mark',cat:'Celebration',glyph:'▣'},{id:'cake-mark',name:'Cake mark',cat:'Celebration',glyph:'♨'},{id:'music-notes',name:'Music notes',cat:'Celebration',glyph:'♪ ♫ ♪'},
 {id:'business-arrow',name:'Forward arrow',cat:'Business',glyph:'→'},{id:'business-grid',name:'Executive grid',cat:'Business',glyph:'□ □ □'},{id:'business-dots',name:'Modern dots',cat:'Business',glyph:'• • • •'},{id:'business-plus',name:'Modern plus',cat:'Business',glyph:'+  +  +'},{id:'business-chevron',name:'Chevron line',cat:'Business',glyph:'› › ›'},{id:'business-rule',name:'Executive rule',cat:'Business',glyph:'━━━'},
 {id:'corner-top-left',name:'Corner flourish',cat:'Borders',glyph:'⌜❦'},{id:'corner-top-right',name:'Reverse corner',cat:'Borders',glyph:'❦⌝'},{id:'thin-rule',name:'Thin divider',cat:'Borders',glyph:'────────'},{id:'diamond-rule',name:'Diamond divider',cat:'Borders',glyph:'── ◇ ──'},{id:'spark-rule',name:'Spark divider',cat:'Borders',glyph:'── ✦ ──'},{id:'dot-rule',name:'Dotted divider',cat:'Borders',glyph:'· · · · · ·'},
 {id:'leaf-pair',name:'Leaf pair',cat:'Botanical',glyph:'❧  ❧'},{id:'flower-row',name:'Flower row',cat:'Botanical',glyph:'❀ ✿ ❀'},{id:'garden-spark',name:'Garden sparkle',cat:'Botanical',glyph:'❧ ✦ ❧'},{id:'clover-row',name:'Clover row',cat:'Botanical',glyph:'☘ ☘ ☘'},{id:'small-bloom',name:'Small bloom',cat:'Botanical',glyph:'✽'},{id:'floral-divider',name:'Floral divider',cat:'Botanical',glyph:'❀ ─ ❀'},
 {id:'love-divider',name:'Heart divider',cat:'Romance',glyph:'── ♡ ──'},{id:'heart-cluster',name:'Heart cluster',cat:'Romance',glyph:'♡ ♥ ♡'},{id:'promise-mark',name:'Promise mark',cat:'Romance',glyph:'∞ ♡'},{id:'ring-divider',name:'Ring divider',cat:'Romance',glyph:'─ ◯◯ ─'},{id:'love-quote',name:'Love quote',cat:'Text styles',text:'A lifetime begins here',preset:'editorial'},{id:'thank-you',name:'Thank-you title',cat:'Text styles',text:'WITH LOVE & GRATITUDE',preset:'luxury'},
 {id:'circle-outline',name:'Circle outline',cat:'Shapes',shape:'circle'},{id:'soft-panel',name:'Soft panel',cat:'Shapes',shape:'panel'},{id:'wide-line',name:'Wide line',cat:'Shapes',shape:'line'},{id:'square-card',name:'Square card',cat:'Shapes',shape:'rectangle'}
];
const librarySection=document.createElement('section');librarySection.className='final-element-library';librarySection.innerHTML=`<div class="final-panel-title"><div><small>Invitation library</small><h2>Design elements</h2></div><span class="final-library-count"></span></div><div class="final-library-search"><span>⌕</span><input type="search" placeholder="Search ornaments, flowers, text…"></div><div class="final-library-cats"></div><div class="final-library-grid"></div>`;
if(elementsPane)elementsPane.insertBefore(librarySection,elementsPane.querySelector('.studio-pane-heading')?.nextSibling||elementsPane.firstChild);
let libraryCat='All',libraryQuery='';const favKey='einvite-element-favorites-v1',recentKey='einvite-element-recent-v1';let favorites=new Set(JSON.parse(localStorage.getItem(favKey)||'[]')),recent=JSON.parse(localStorage.getItem(recentKey)||'[]');
const cats=['All','Favorites','Recent',...new Set(library.map(x=>x.cat))];
function addCustomElement(item,drop){if(item.shape){if(typeof addDesignElement==='function')addDesignElement(item.shape);return}
 const type='decoration',obj=typeof createObject==='function'?createObject(makeId('library'),type):null;if(!obj)return;const content=obj.querySelector('.content');content.textContent=item.text||item.glyph||'✦';obj.dataset.color=(window.state?.accent||$('#accent')?.value||'#9d4555');obj.dataset.fontSize=item.text?'34':'64';obj.style.width=item.text?'76%':'150px';obj.style.height=item.text?'110px':'120px';obj.style.left=drop?`${drop.x}%`:(item.text?'12%':'32%');obj.style.top=drop?`${drop.y}%`:'38%';if(item.preset==='luxury'){obj.dataset.textGradientEnabled='true';obj.dataset.textGradientStart='#7a5718';obj.dataset.textGradientEnd='#e9c86e';obj.dataset.fontWeight='700';obj.dataset.letterSpacing='2'}if(item.preset==='editorial'){obj.dataset.fontStyle='italic';obj.dataset.font='serif-georgia';obj.dataset.fontSize='38'}if(item.preset==='khmer'){obj.dataset.font="noto-serif-khmer";obj.dataset.fontSize='34';obj.dataset.color='#a87616'}if(item.preset==='date'){obj.dataset.letterSpacing='4';obj.dataset.fontSize='26';obj.dataset.backgroundEnabled='true';obj.dataset.backgroundColor='#ffffff';obj.dataset.backgroundOpacity='78';obj.dataset.borderRadius='28'}applyObjectVisualStyle(obj);stage.append(obj);clearSelection();setSelection([obj]);saveNow();
 recent=[item.id,...recent.filter(x=>x!==item.id)].slice(0,10);localStorage.setItem(recentKey,JSON.stringify(recent));renderLibrary();toast(`${item.name} added`)}
function filteredLibrary(){return library.filter(x=>{if(libraryCat==='Favorites'&&!favorites.has(x.id))return false;if(libraryCat==='Recent'&&!recent.includes(x.id))return false;if(!['All','Favorites','Recent'].includes(libraryCat)&&x.cat!==libraryCat)return false;return!libraryQuery||`${x.name} ${x.cat}`.toLowerCase().includes(libraryQuery)})}
function renderLibrary(){const catHost=$('.final-library-cats',librarySection),grid=$('.final-library-grid',librarySection);catHost.innerHTML=cats.map(c=>`<button type="button" class="${c===libraryCat?'active':''}" data-cat="${c}">${c}</button>`).join('');catHost.querySelectorAll('button').forEach(b=>b.onclick=()=>{libraryCat=b.dataset.cat;renderLibrary()});const items=filteredLibrary();$('.final-library-count',librarySection).textContent=`${items.length} items`;grid.innerHTML='';items.forEach(item=>{const card=document.createElement('article');card.className='final-element-card';card.draggable=true;card.innerHTML=`<button type="button" class="final-fav ${favorites.has(item.id)?'active':''}" aria-label="Favorite">★</button><div class="final-element-preview">${item.shape?`<i class="shape-${item.shape}"></i>`:`<span>${item.text||item.glyph}</span>`}</div><strong>${item.name}</strong><small>${item.cat}</small>`;card.onclick=e=>{if(e.target.closest('.final-fav'))return;addCustomElement(item)};card.querySelector('.final-fav').onclick=e=>{e.stopPropagation();favorites.has(item.id)?favorites.delete(item.id):favorites.add(item.id);localStorage.setItem(favKey,JSON.stringify([...favorites]));renderLibrary()};card.ondragstart=e=>{e.dataTransfer.setData('application/x-einvite-library-item',item.id);e.dataTransfer.effectAllowed='copy'};grid.append(card)})}
$('.final-library-search input',librarySection).oninput=e=>{libraryQuery=e.target.value.trim().toLowerCase();renderLibrary()};renderLibrary();
stage.addEventListener('dragover',e=>{if(Array.from(e.dataTransfer.types||[]).includes('application/x-einvite-library-item')){e.preventDefault();stage.classList.add('final-library-drop')}});stage.addEventListener('dragleave',()=>stage.classList.remove('final-library-drop'));stage.addEventListener('drop',e=>{const id=e.dataTransfer.getData('application/x-einvite-library-item');if(!id)return;e.preventDefault();stage.classList.remove('final-library-drop');const r=stage.getBoundingClientRect(),item=library.find(x=>x.id===id);if(item)addCustomElement(item,{x:Math.max(0,Math.min(85,(e.clientX-r.left)/r.width*100)),y:Math.max(0,Math.min(85,(e.clientY-r.top)/r.height*100))})});
const observer=new MutationObserver(()=>{refreshAdvancedControls();refreshTimeline()});observer.observe(stage,{subtree:true,childList:true,attributes:true,attributeFilter:['class','data-animation-delay','data-fill-mode','data-text-gradient-enabled']});
document.addEventListener('pointerup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);document.addEventListener('keyup',()=>setTimeout(()=>{refreshAdvancedControls();refreshTimeline()},0),true);
refreshAdvancedControls();refreshTimeline();
const tour=document.createElement('dialog');tour.className='final-tour';tour.innerHTML=`<form method="dialog"><button class="final-tour-close" aria-label="Close">×</button></form><div class="final-tour-art">✦</div><p class="invite-kicker">Creation Studio</p><h1>Design the invitation. Run the event.</h1><p>This workspace combines free-form visual creation with pages, animation, guest RSVP, publishing, Khmer dates and event operations.</p><div class="final-tour-grid"><article><b>1</b><strong>Create</strong><span>Drag elements, upload media and style every object.</span></article><article><b>2</b><strong>Build pages</strong><span>Mix free-form artboards with functional event sections.</span></article><article><b>3</b><strong>Animate</strong><span>Sequence motion with delay, duration and stagger controls.</span></article><article><b>4</b><strong>Publish</strong><span>Run the Design Check, publish a snapshot and manage guests.</span></article></div><div class="final-tour-actions"><button type="button" id="finalTourExplore">Explore studio</button><button type="button" id="finalTourDismiss" class="primary">Start creating</button></div>`;document.body.append(tour);
const TOUR_VERSION='studio-v27',LEGACY_TOUR_KEY='einvite-final-tour-seen-v1';let tourKey='',tourAutomatic=false,tourLauncher=null,tourSessionSeen=false,tourOpenGeneration=0;
async function resolveTourIdentity(){try{await window.EInviteBackend?.ready;if(window.EInviteBackend?.isAvailable?.()){const response=await fetch('/api/auth/me',{credentials:'same-origin'}),data=response.ok?await response.json():null,user=data?.user;if(user?.id||user?.email)return String(user.id||user.email)}}catch{}try{const user=JSON.parse(localStorage.getItem('sovan-account-v1')||'null');if(user?.id||user?.email)return String(user.id||user.email)}catch{}return'local-anonymous'}
function persistTourSeen(){tourSessionSeen=true;if(tourKey)localStorage.setItem(tourKey,'1')}
function workspaceFocus(){const target=$('#stage')||$('#canvasViewport')||$('.stage-wrap');target?.setAttribute?.('tabindex','-1');setTimeout(()=>{target?.focus?.({preventScroll:true});if(target)document.body.dataset.keyboardOwner='canvas'},0)}
function closeTour({explore=false}={}){tourOpenGeneration++;persistTourSeen();if(tour.open)tour.close();if(explore){document.querySelector('[data-studio-tab="elements"]')?.click();setTimeout(()=>$('.final-element-library')?.scrollIntoView({behavior:'smooth'}),100)}}
$('#finalTourDismiss').onclick=()=>closeTour();$('#finalTourExplore').onclick=()=>closeTour({explore:true});tour.addEventListener('cancel',event=>{event.preventDefault();closeTour()});tour.addEventListener('close',()=>{persistTourSeen();const automatic=tourAutomatic,launcher=tourLauncher;tourAutomatic=false;tourLauncher=null;if(automatic)workspaceFocus();else requestAnimationFrame(()=>launcher?.focus?.({preventScroll:true}))});
const status=$('.studio-statusbar>div:last-child');if(status){const b=document.createElement('button');b.type='button';b.className='final-tour-trigger';b.textContent='✦ Tour';b.onclick=()=>{tourAutomatic=false;tourLauncher=b;tour.showModal()};status.prepend(b)}
window.EInviteOnboardingReady=(async()=>{const generation=++tourOpenGeneration,identity=await resolveTourIdentity();tourKey=`einvite-final-tour-seen-v2:${encodeURIComponent(identity)}:${TOUR_VERSION}`;if(localStorage.getItem(LEGACY_TOUR_KEY)==='1'&&!localStorage.getItem(tourKey))localStorage.setItem(tourKey,'1');if(generation!==tourOpenGeneration||tourSessionSeen||localStorage.getItem(tourKey)==='1')return{shown:false,identity};tourAutomatic=true;tourLauncher=null;tour.showModal();await new Promise(resolve=>requestAnimationFrame(resolve));return{shown:true,identity}})();
})();;(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const page=document.body?.dataset.page||((location.pathname.split('/').pop()||'dashboard.html').replace(/\.html$/,''));
if(document.body&&!document.body.dataset.page)document.body.dataset.page=page;
function dashboard(){
  const view=$('#dashboardView'),login=$('#loginView');if(!view)return;
  view.classList.add('dashboard-home');
  const rail=document.createElement('nav');rail.className='dashboard-home-rail';rail.innerHTML=`
    <button type="button" class="rail-create" title="Create invitation"><span>＋</span>Create</button>
    <a href="dashboard.html" class="active"><span>⌂</span>Home</a>
    <a href="templates.html"><span>▣</span>Templates</a>
    <a href="materials.html"><span>▧</span>Materials</a>
    <a href="billing.html"><span>◉</span>Plans</a>
    <div class="rail-spacer"></div>
    <a href="account.html"><span>◌</span>Account</a>`;
  document.body.append(rail);
  $('.rail-create',rail).onclick=()=>$('#newBtn')?.click();
  const hero=document.createElement('section');hero.className='dashboard-home-hero';hero.innerHTML=`
    <h1>What will you create today?</h1>
    <label class="dashboard-home-search"><span>⌕</span><input type="search" placeholder="Search your invitations"></label>
    <div class="dashboard-quick-create">
      <button type="button" class="create"><i>＋</i><span>Create</span></button>
      <a href="templates.html" class="template"><i>▣</i><span>Templates</span></a>
      <button type="button" class="wedding"><i>♡</i><span>Wedding</span></button>
      <button type="button" class="birthday"><i>✦</i><span>Birthday</span></button>
      <button type="button" class="business"><i>◇</i><span>Business</span></button>
      <a href="materials.html" class="upload"><i>⇧</i><span>Uploads</span></a>
    </div>`;
  view.prepend(hero);
  const createByType=(type)=>{const btn=$('#newBtn');btn?.click();setTimeout(()=>{const typeEl=$('#newType');if(typeEl){typeEl.value=type;typeEl.dispatchEvent(new Event('change',{bubbles:true}))}},40)};
  $('.create',hero).onclick=()=>$('#newBtn')?.click();$('.wedding',hero).onclick=()=>createByType('Wedding');$('.birthday',hero).onclick=()=>createByType('Birthday');$('.business',hero).onclick=()=>createByType('Business');
  const homeSearch=$('.dashboard-home-search input',hero);
  homeSearch.oninput=()=>{const old=$('#dashboardSearch');if(old){old.value=homeSearch.value;old.dispatchEvent(new Event('input',{bubbles:true}))}else{$$('.invite-card','#inviteGrid').forEach(card=>card.hidden=!card.textContent.toLowerCase().includes(homeSearch.value.toLowerCase()))}};
  const recent=document.createElement('div');recent.className='dashboard-recent-head';recent.innerHTML='<h2>Recent invitations</h2>';
  const filter=$('.dashboard-filter-tabs');if(filter)recent.append(filter);
  const grid=$('#inviteGrid');grid?.before(recent);
  grid?.addEventListener('click',e=>{const cover=e.target.closest('.invite-cover');if(!cover)return;const card=cover.closest('.invite-card');card?.querySelector('[data-edit]')?.click()});
  const header=$('body>header');
  function authState(){const signed=view.hidden===false;rail.hidden=!signed;if(header){header.querySelectorAll('a[href="materials.html"],a[href="billing.html"],a[href="account.html"]').forEach(a=>a.hidden=!signed);const logout=$('#logoutBtn');if(logout)logout.hidden=!signed}}
  new MutationObserver(authState).observe(view,{attributes:true,attributeFilter:['hidden']});authState();
}
function materials(){
  const head=$('.library-head'),upload=$('.upload-box');if(!head||!upload)return;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='material-upload-toggle primary';toggle.innerHTML='<span>⇧</span> Upload files';head.append(toggle);upload.hidden=true;
  toggle.onclick=()=>{upload.hidden=!upload.hidden;toggle.innerHTML=upload.hidden?'<span>⇧</span> Upload files':'<span>×</span> Close upload';if(!upload.hidden)setTimeout(()=>$('#uploadFile')?.focus(),50)};
  const grid=$('#grid');
  const observer=new MutationObserver(()=>{
    const empty=$('.empty-library',grid);if(empty&&/Authentication required/i.test(empty.textContent)&&!empty.querySelector('.material-auth-action')){const a=document.createElement('a');a.href='dashboard.html';a.className='material-auth-action';a.innerHTML='<button type="button" class="primary">Sign in to use materials</button>';empty.append(a)}
  });observer.observe(grid,{childList:true,subtree:true});
}
function editor(){
  const main=$('body.studio-experience>main'),rail=$('.studio-tool-rail'),host=$('.studio-pane-host'),stage=$('#stage');if(!main||!rail||!host||!stage)return;
  if(!$('[data-studio-tab="text"]',rail)){
    const elementsBtn=$('[data-studio-tab="elements"]',rail);
    const b=document.createElement('button');b.type='button';b.className='studio-rail-button';b.dataset.studioTab='text';b.innerHTML='<span class="studio-nav-icon">T</span><span>Text</span>';b.title='Text, fonts and typography';rail.insertBefore(b,elementsBtn||null);
    const pane=document.createElement('section');pane.className='studio-pane studio-text-pane';pane.dataset.studioPane='text';pane.innerHTML=`
      <div class="studio-pane-heading"><div><small>Create</small><h1>Text</h1></div></div>
      <label class="refine-text-search"><span>⌕</span><input type="search" placeholder="Search fonts and combinations"></label>
      <button type="button" class="refine-add-text">T &nbsp; Add a text box</button>
      <button type="button" class="refine-magic-write">✦ Magic invitation writing</button>
      <section class="refine-text-section"><div><h3>Default text styles</h3></div><div class="refine-text-presets">
        <button class="refine-text-preset heading" data-refine-text="heading">Add a heading</button>
        <button class="refine-text-preset subheading" data-refine-text="subheading">Add a subheading</button>
        <button class="refine-text-preset body" data-refine-text="body">Add a little bit of body text</button>
        <button class="refine-text-preset khmer" data-refine-text="khmer">សិរីមង្គលអាពាហ៍ពិពាហ៍</button>
      </div></section>
      <section class="refine-text-section"><div><h3>Fonts</h3><small>Search · Khmer · Favorites</small></div><button type="button" class="refine-browse-fonts">Browse all fonts</button></section>
      <section class="refine-text-section"><div><h3>Font combinations</h3><small>Quick invitation styles</small></div><div class="refine-font-combos">
        <button class="refine-font-combo" data-combo="gold"><span style="font-family:Georgia,serif;color:#b48a20">GOLDEN<br>HOUR</span><small>Luxury serif</small></button>
        <button class="refine-font-combo" data-combo="modern"><span style="font-family:Arial,sans-serif;font-weight:800">TITLE<br><i>HEADING</i></span><small>Modern contrast</small></button>
        <button class="refine-font-combo" data-combo="romance"><span style="font-family:Georgia,serif;font-style:italic;color:#426b52">Bride &<br>Groom</span><small>Romantic serif</small></button>
        <button class="refine-font-combo" data-combo="khmer"><span style="font-family:'Noto Serif Khmer','Khmer OS Muol Light',serif;color:#9b6b13">សិរីមង្គល</span><small>Khmer ceremonial</small></button>
      </div></section>`;
    host.append(pane);
    function activate(id){
      $$('[data-studio-tab]',rail).forEach(x=>x.classList.toggle('active',x.dataset.studioTab===id));
      $$('[data-studio-pane]',host).forEach(x=>x.classList.toggle('active',x.dataset.studioPane===id));
      localStorage.setItem('einvite-editor-left-tab',id);applyMode();
    }
    b.onclick=()=>activate('text');
    $('.refine-add-text',pane).onclick=()=>$('#addText')?.click();
    $$('.refine-text-preset',pane).forEach(btn=>btn.onclick=()=>{const source=$(`[data-text-preset="${btn.dataset.refineText}"]`);if(source)source.click();else $('#addText')?.click()});
    $('.refine-browse-fonts',pane).onclick=()=>$('.ei-font-launch')?.click();
    $('.refine-magic-write',pane).onclick=()=>{const ebtn=$('[data-studio-tab="event"]',rail);ebtn?.click();setTimeout(()=>$('#eiAiStudio textarea,.ei-ai-studio textarea')?.focus(),80)};
    const comboMap={gold:{font:'serif-georgia',size:48,color:'#b48a20',text:'Golden Hour'},modern:{font:'sans-arial',size:44,color:'#202127',text:'Your Celebration'},romance:{font:'serif-georgia',size:46,color:'#426b52',text:'Bride & Groom'},khmer:{font:"noto-serif-khmer",size:38,color:'#9b6b13',text:'សិរីមង្គលអាពាហ៍ពិពាហ៍'}};
    $$('.refine-font-combo',pane).forEach(btn=>btn.onclick=()=>{const c=comboMap[btn.dataset.combo];$('#addText')?.click();setTimeout(()=>{const sel=$('.object.selected,.object.multi-selected');if(!sel)return;const content=sel.querySelector('.content');if(content)content.textContent=c.text;sel.dataset.font=c.font;sel.dataset.fontSize=String(c.size);sel.dataset.color=c.color;try{applyObjectVisualStyle(sel);save()}catch{}},40)});
    $('.refine-text-search input',pane).oninput=e=>{const q=e.target.value.toLowerCase();$$('.refine-text-preset,.refine-font-combo',pane).forEach(x=>x.hidden=!!q&&!x.textContent.toLowerCase().includes(q))};
  }
  function applyMode(){ /* centralized elsewhere */ }
  const openInspector=()=>{if(innerWidth<=1180&&$('.object.selected,.object.multi-selected',stage))document.body.classList.add('inspector-open')};
  stage.addEventListener('pointerup',()=>setTimeout(openInspector,0));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.body.classList.remove('inspector-open')});
  const inspector=$('.right');if(inspector&&!inspector.querySelector('.refine-inspector-close')){const c=document.createElement('button');c.type='button';c.className='refine-inspector-close';c.textContent='×';c.title='Close inspector';c.onclick=()=>document.body.classList.remove('inspector-open');inspector.prepend(c)}
}
if(page==='dashboard')dashboard();
if(page==='materials')materials();
if(page==='index')setTimeout(editor,0);
})();;(()=>{'use strict';
let lastDialogTrigger=new WeakMap();
const focusable='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function syncPanel(panel,open,trigger){if(!panel)return;panel.hidden=!open;try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(trigger)trigger.setAttribute('aria-expanded',String(open));if(!open&&panel.contains(document.activeElement))trigger?.focus();}
function trapDialogKey(event,dialog){const nodes=[...dialog.querySelectorAll(focusable)].filter(el=>!el.hidden&&el.getClientRects().length&&!el.closest('[inert],[aria-hidden="true"]'));if(!nodes.length)return;if(event.shiftKey&&document.activeElement===nodes[0]){event.preventDefault();nodes.at(-1).focus()}else if(!event.shiftKey&&document.activeElement===nodes.at(-1)){event.preventDefault();nodes[0].focus()}}
function observeDialogs(){document.querySelectorAll('dialog').forEach(dialog=>{if(dialog.dataset.a11yBound)return;dialog.dataset.a11yBound='1';dialog.addEventListener('close',()=>{const trigger=lastDialogTrigger.get(dialog);if(trigger?.isConnected)trigger.focus()});dialog.addEventListener('cancel',event=>{event.preventDefault();dialog.close()})});}
function init(){
 document.querySelectorAll('button:not([aria-label])').forEach(b=>{if(!b.textContent.trim())b.setAttribute('aria-label',b.title||'Action')});
 document.querySelectorAll('img:not([alt])').forEach(img=>img.alt='Invitation image');
 document.querySelectorAll('a > button').forEach(button=>{const a=button.parentElement;a.classList.add(...button.classList);a.setAttribute('role','button');a.textContent=button.textContent;button.remove()});
 document.querySelectorAll('.khmer-picker select').forEach(select=>{if(!select.getAttribute('aria-label')){const label=select.closest('label')?.childNodes?.[0]?.textContent?.trim();if(label)select.setAttribute('aria-label',label)}});
 document.addEventListener('click',event=>{const trigger=event.target.closest('button,[role="button"],a');if(!trigger)return;requestAnimationFrame(()=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&!lastDialogTrigger.has(top))lastDialogTrigger.set(top,trigger);observeDialogs()})},true);
 document.addEventListener('keydown',event=>{const dialogs=[...document.querySelectorAll('dialog[open]')];const top=dialogs.at(-1);if(top&&event.key==='Tab'){trapDialogKey(event,top);return}if(event.key!=='Escape')return;if(top){top.close();event.preventDefault();event.stopPropagation();return}const openDrawer=[...document.querySelectorAll('[data-drawer-open="true"],.is-open[role="dialog"]')].filter(x=>!x.hidden).at(-1);if(openDrawer){const trigger=document.querySelector(`[aria-controls="${CSS.escape(openDrawer.id)}"]`);syncPanel(openDrawer,false,trigger);openDrawer.dataset.drawerOpen='false';event.preventDefault()}});
 document.querySelectorAll('[aria-controls]').forEach(trigger=>{if(trigger.dataset.a11yManaged==='true')return;const panel=document.getElementById(trigger.getAttribute('aria-controls'));if(!panel)return;const update=()=>{const open=trigger.getAttribute('aria-expanded')==='true'||panel.classList.contains('open')||panel.classList.contains('is-open');try{panel.inert=!open}catch{}panel.setAttribute('aria-hidden',String(!open));if(!open&&panel.contains(document.activeElement))trigger.focus()};trigger.addEventListener('click',()=>setTimeout(update,0));update()});
 observeDialogs();new MutationObserver(observeDialogs).observe(document.body,{childList:true,subtree:true});
}
window.EInviteAccessibility={syncPanel};document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
})();