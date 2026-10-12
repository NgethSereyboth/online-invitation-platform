#!/usr/bin/env bash
# The read-only commands quoted in docs/reviews/bulk-guest-import-research.md, in
# report order, each printed with its output. Re-running this file reproduces
# every Goal-1 quotation; the report quotes them as individual `$` blocks so
# `node tools/report-verify.mjs` can re-derive them one by one.
cd "$(dirname "$0")/../.." || exit 1

run() {
  printf '$ %s\n' "$1"
  eval "$1"
  printf '\n'
}

# --- 1a guest data model -----------------------------------------------------
run "sed -n 1429p src/python/server.py | cut -c1-700"
run "sed -n 1408p src/python/server.py | cut -c1-330"
run "grep -o 'id=\"importFile\".\\{0,40\\}' src/html/guests.html"
run "grep -c 'xlsx' src/html/guests.html src/js/guests.js || echo 'no xlsx matches'"
run "sed -n 35p src/js/guests.js | cut -c1-200"
run "sed -n 36p src/js/guests.js | cut -c1-160"

# --- 1b editor text fields ---------------------------------------------------
run "sed -n 205p src/js/app.js | cut -c1-300"
run "sed -n 12p src/js/template-bindings-v25.js | cut -c1-300"
run "sed -n 16,17p src/js/canva-scale-v31.js | cut -c1-220"
run "grep -c 'dataMergeV47:f.dataMergeV47!==false' src/js/document-schema-v32.js"

# --- 1c public page routing --------------------------------------------------
run "grep -n 'def serve_public(self, slug)' src/python/server.py"
run "sed -n 3536p src/python/server.py"
run "grep -n 'einvite-invitation-slug\|/api/public/' src/js/public-page.js | cut -c1-170"
run "grep -n 'einvite-invitation-slug' src/html/public.html"

# --- 1d Open Graph tags ------------------------------------------------------
run "grep -n 'og:\\|twitter:\\|<title\\|name=\"description\"' src/html/public.html"

# --- 1e spreadsheet parsing --------------------------------------------------
run "grep -rn 'xlsx\\|SheetJS\\|papaparse\\|openpyxl' package.json docs/requirements-production.txt || echo 'no spreadsheet library in either manifest'"

# --- 1f slug and URL generation ----------------------------------------------
run "sed -n 2512,2514p src/python/server.py"
run "grep -n 'clean_slug' src/python/server.py | cut -c1-110"
run "grep -n 'function guestUrl' src/js/guests.js | cut -c1-230"

# --- 1g server rendering capability -----------------------------------------
run "sed -n 9499p src/python/server.py | cut -c1-240"
run "grep -n 'def render_social_card_png_bytes\\|def social_cache_path\\|def invalidate_social_cache\\|def warm_social_card_cache\\|def available_social_image_format' src/python/server.py"

# --- 1h render deployment ----------------------------------------------------
run "grep -n 'type: web\\|runtime: python\\|autoDeploy\\|startCommand\\|buildCommand\\|healthCheckPath\\|plan:' render.yaml"

# --- 3a prior art: the v52 bulk-generation surface ---------------------------
run "grep -n 'data-merge' src/js/future-studio-loader-v52.js | cut -c1-120"
run "grep -n 'generated_invitation_variants_v47\\|data_merge_sources_v47' future_platform_v52/schema.py | cut -c1-200"
run "grep -n 'def _bulk_generation_job' future_platform_v52/service.py"
run "grep -n 'api.telegram.org\\|parse_mode\\|disable_web_page_preview' src/python/delivery_channels/telegram_channel.py"
