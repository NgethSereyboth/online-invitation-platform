# E-invitation platform — developer entry points.
#
# Every generated frontend artifact is produced by `build.py` (see
# CONTRIBUTING.md). Nothing here writes to src/ except through that script.
#
# Measurement tools live in tools/ (see tools/README.md). Two rules they encode:
#   * `npx lhci autorun` MUST run against tools/serve-gzip.py. Against an
#     uncompressed server index.html reads 54 instead of 73 and every byte
#     budget looks violated.
#   * every tool writes its output to artifacts/ (gitignored), never to /tmp.

PYTHON ?= python3
PORT   ?= 8124
STATIC_ROOT ?= src/python
LHCI_CONFIG ?= tools/lighthouserc.js

.PHONY: help build check test serve dev serve-gzip perf smoke reproduce clean

help:
	@echo "make build      - regenerate every generated artifact (python3 build.py all)"
	@echo "make check      - verify generated artifacts without writing (route bundles gate)"
	@echo "make test       - run the Python test suite"
	@echo "make serve      - plain static preview on http://127.0.0.1:$(PORT) (no gzip)"
	@echo "make serve-gzip - gzip static server; REQUIRED for every Lighthouse number"
	@echo "make dev        - real development server (API + assets)"
	@echo "make perf       - Lighthouse CI against the gzip server (requires @lhci/cli)"
	@echo "make smoke      - load all 16 pages, report console errors and non-2xx"
	@echo "make reproduce  - full verification sequence from scratch (build, tests, lhci, determinism)"
	@echo "make clean      - remove local build caches and tool artifacts"

build:
	$(PYTHON) build.py all

check:
	$(PYTHON) build.py bundles --check

test:
	$(PYTHON) -m pytest tests/

# Static preview only: no API, so authenticated pages render their signed-out
# state. Use `make dev` for the full application. Not gzip-correct — do not
# measure byte weights or Lighthouse scores through it.
serve:
	$(PYTHON) -m http.server $(PORT) --directory $(STATIC_ROOT)

# The compression-correct server. This is the default for every Lighthouse
# command and for anything that reports transfer bytes.
serve-gzip:
	$(PYTHON) tools/serve-gzip.py --port $(PORT) --root $(STATIC_ROOT)

# The real server. Its ROOT is src/python/, and it imports modules from
# src/python/ and vendor code from the repo root.
dev:
	PYTHONPATH=$(STATIC_ROOT):. $(PYTHON) $(STATIC_ROOT)/server.py

perf:
	npx lhci autorun --config=$(LHCI_CONFIG)

# Cheap post-change gate: every page loads with no console error and no 404.
# Needs the gzip server running (`make serve-gzip &`).
smoke:
	node tools/page-errors.mjs --all

# From-scratch reproduction of every number in docs/reviews/*.md. Starts and
# stops its own gzip server. Prerequisites: npm install, and
# pip install -r tools/requirements.txt.
#
# Extra flags go through REPRO_ARGS, because make would otherwise eat them:
#   make reproduce REPRO_ARGS=--skip-lhci
reproduce:
	bash tools/reproduce.sh --port $(PORT) $(REPRO_ARGS)

clean:
	rm -rf /tmp/build-cache artifacts .lighthouseci
