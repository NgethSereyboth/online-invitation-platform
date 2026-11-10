#!/usr/bin/env python3
"""Production WSGI entry point for the E-Invitation Website.

Replaces the single-threaded ``http.server`` development run-mode
(``python -m server`` / the ``__main__`` block in ``server.py``) with
``waitress``, a production-grade WSGI server providing:

  * Bounded worker threads (``threads=N``).
  * Per-connection request body limits (``max_request_body_size``).
  * TCP keep-alive tuning.

The application logic itself lives in :class:`server.Handler` (a
``SimpleHTTPRequestHandler`` subclass).  ``create_app()`` — defined in
``server.py`` — bridges each WSGI request through a lightweight adapter
so the existing handler code runs unmodified under waitress.

Usage
-----
    # Behind a reverse proxy (recommended — handles TLS termination):
    python serve.py

    # Direct exposure (not recommended for production TLS):
    python serve.py --host 0.0.0.0 --port 8000

Environment
-----------
    HOST         Bind address            (default 127.0.0.1)
    PORT         TCP port                (default 8000)
    WORKERS      Waitress thread count   (default 8)
    EINVITE_ALLOW_NO_SCANNER  Set to "1" to skip malware-scanner gate
"""

import argparse
import atexit
import os
import signal
import sys

from waitress import serve

# Import the WSGI application factory from the handler module.
# Under Render's Blueprint (rootDir removed) the whole repository is the
# build context.  ``server.py`` lives in this directory (src/python) and
# imports ``ai_agent``, ``platform_v32``, and ``future_platform_v52`` from
# the repository root.  Both ``src/python`` and the repo root must be on
# ``sys.path`` for the import chain to resolve at runtime.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = _HERE
for _ in range(10):                                           # walk up to find repo root
    _parent = os.path.dirname(_REPO_ROOT)
    if _parent == _REPO_ROOT or os.path.isdir(os.path.join(_parent, "ai_agent")):
        _REPO_ROOT = _parent
        break
    _REPO_ROOT = _parent
sys.path.insert(0, _HERE)                                      # src/python  (server.py, core/)
sys.path.append(_REPO_ROOT)                                    # repo root   (ai_agent/, platform_v32/)

from server import MAX_REQUEST_BODY_BYTES, create_app, shutdown_platform_services  # noqa: E402

app = create_app()
atexit.register(shutdown_platform_services)


def _graceful_stop(_signum, _frame):
    """Join background workers before the process exits on SIGTERM/SIGINT."""
    shutdown_platform_services(timeout=10)
    raise SystemExit(0)


for _signal in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
    if _signal is not None:
        try:
            signal.signal(_signal, _graceful_stop)
        except (ValueError, OSError):
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the E-invitation-website under waitress (WSGI)."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Bind host (default: 127.0.0.1; use 0.0.0.0 behind a reverse proxy).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="HTTP port (default: 8000 or PORT env var).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=int(os.environ.get("WORKERS", "8")),
        help="Number of waitress worker threads (default: 8).",
    )
    args = parser.parse_args()

    serve(
        app,
        host=args.host,
        port=args.port,
        threads=args.threads,
        ident="EInvite",  # suppress "Server: waitress" header (SEC-02 info-disclosure)
        # Sprint 7 — one transport ceiling for every route, shared with the
        # handler's pre-read check (413 before a byte is buffered). The default
        # 25 MiB admits the 15 MB materials limit with base64/JSON overhead while
        # still refusing an unbounded body.
        max_request_body_size=MAX_REQUEST_BODY_BYTES,
        max_request_header_size=16_386,  # RFC 9110 maximum
        channel_timeout=30,  # idle-connection lifetime in seconds
    )
