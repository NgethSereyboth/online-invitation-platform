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
import os
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

from server import create_app  # noqa: E402

app = create_app()

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
        # 10 MB ceiling — the Handler.body() default is 20 MB but per-endpoint
        # limits are far smaller (login: 100 KB, admin settings: 20 KB). 10 MB
        # accommodates authenticated uploads while preventing trivial DoS.
        max_request_body_size=10_485_760,
        max_request_header_size=16_386,  # RFC 9110 maximum
        channel_timeout=30,  # idle-connection lifetime in seconds
    )
