#!/usr/bin/env python3
"""Static server for the served tree with HTTP compression — the repo default.

Why this exists
---------------
The first Lighthouse run in this project served every file uncompressed from a
throwaway ``http.server``. No static host does that, and Lighthouse duly reported
``uses-text-compression`` = 0 with "Est savings of 1,655 KiB" and an estimated
1000 ms on both FCP and LCP — i.e. the harness, not the application, was
deciding the score and every byte-based budget assertion. On a
compression-correct host index.html scores 73 instead of 54.

This server gzips compressible text responses when the client advertises gzip,
which is what Cloudflare / nginx / Netlify do by default, so the gate measures
the application rather than the test harness. It is deliberately minimal: no
directory listing, no range requests, and ``Cache-Control: no-store`` so
repeated automated runs cannot be served from a warm cache and disagree.

Every Lighthouse command in this repo must run against this server. The layout /
DOM harnesses are transport-independent, so they may use it too.

Usage
-----
    python3 tools/serve-gzip.py [--port PORT] [--root DIR]
    PORT=8124 SERVE_ROOT=src/python python3 tools/serve-gzip.py

Defaults: port 8124, root the served frontend tree (``<repo>/src/python``).
The root is resolved relative to this file, not to the caller's directory, so
the server works from anywhere. Layout/DOM harnesses and `make reproduce` both
depend on that.

Requires: Python 3.8+ standard library only. No third-party packages.
Produces: a foreground HTTP server on 127.0.0.1. Writes nothing.
"""
from __future__ import annotations

import argparse
import gzip
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO_ROOT / "src" / "python"

# Text types worth compressing. Everything else is passed through untouched.
COMPRESSIBLE = (
    "text/", "application/javascript", "application/json", "application/xml",
    "image/svg+xml", "application/manifest+json", "text/css",
)
MIN_SIZE = 256          # below this, gzip overhead exceeds the win


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "serve-gzip/1.0"
    root = DEFAULT_ROOT

    def log_message(self, *args):        # keep the log quiet; this is a harness
        pass

    def _resolve(self) -> Path | None:
        rel = self.path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if rel == "":
            rel = "index.html"
        root = type(self).root.resolve()
        target = (root / rel).resolve()
        try:
            target.relative_to(root)                # no traversal above ROOT
        except ValueError:
            return None
        if target.is_dir():
            target = target / "index.html"
        return target if target.is_file() else None

    def do_GET(self):                                   # noqa: N802
        target = self._resolve()
        if target is None:
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        raw = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        # .js must be served as text/javascript, not the legacy
        # application/x-javascript some mimetypes databases still guess for .js.
        if ctype in ("application/x-javascript", "text/x-javascript"):
            ctype = "text/javascript"
        accepts_gzip = "gzip" in (self.headers.get("Accept-Encoding") or "")

        if accepts_gzip and len(raw) >= MIN_SIZE and ctype.startswith(COMPRESSIBLE):
            # mtime=0 so the gzip header carries no timestamp: byte-identical
            # output for identical input, which keeps runs comparable.
            body = gzip.compress(raw, compresslevel=6, mtime=0)
            encoded = True
        else:
            body, encoded = raw, False

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if encoded:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):                                  # noqa: N802
        target = self._resolve()
        self.send_response(200 if target else 404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="serve-gzip.py",
        description="Serve the frontend tree over HTTP with gzip, for Lighthouse and the DOM harnesses.",
    )
    parser.add_argument("--port", type=int, default=8124,
                        help="TCP port on 127.0.0.1 (default 8124)")
    parser.add_argument("--root", default=str(DEFAULT_ROOT),
                        help="directory to serve (default <repo>/src/python, the built frontend tree)")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    root = Path(args.root).expanduser()
    if not root.is_dir():
        sys.stderr.write(f"serve-gzip.py: root is not a directory: {root}\n")
        return 2
    Handler.root = root
    with ThreadingHTTPServer(("127.0.0.1", args.port), Handler) as httpd:
        print(f"serving {root} on http://127.0.0.1:{args.port} (gzip enabled)", flush=True)
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
