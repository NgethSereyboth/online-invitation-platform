# E-invitation platform — developer entry points.
#
# Every generated frontend artifact is produced by `build.py` (see
# CONTRIBUTING.md). Nothing here writes to src/ except through that script.

PYTHON ?= python3
PORT   ?= 8124
STATIC_ROOT ?= src/python

.PHONY: help build check test serve dev perf clean

help:
	@echo "make build   - regenerate every generated artifact (python3 build.py all)"
	@echo "make check   - verify generated artifacts without writing (route bundles gate)"
	@echo "make test    - run the Python test suite"
	@echo "make serve   - static preview of the built site on http://127.0.0.1:$(PORT)"
	@echo "make dev     - real development server (API + assets)"
	@echo "make perf    - run Lighthouse CI (requires @lhci/cli)"
	@echo "make clean   - remove local build caches"

build:
	$(PYTHON) build.py all

check:
	$(PYTHON) build.py bundles --check

test:
	$(PYTHON) -m pytest tests/

# Static preview only: no API, so authenticated pages render their signed-out
# state. Use `make dev` for the full application.
serve:
	$(PYTHON) -m http.server $(PORT) --directory $(STATIC_ROOT)

# The real server. Its ROOT is src/python/, and it imports modules from
# src/python/ and vendor code from the repo root.
dev:
	PYTHONPATH=$(STATIC_ROOT):. $(PYTHON) $(STATIC_ROOT)/server.py

perf:
	npx lhci autorun

clean:
	rm -rf /tmp/build-cache
