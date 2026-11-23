#!/usr/bin/env python3
"""Serve the Rea Studio app from this folder.

Rea Studio is a separate, self-contained design workspace. It is not served by
the eInvite Python server and shares no code, storage or routes with it.

    python3 rea_canva/serve.py --port 8123
"""

from __future__ import annotations

import argparse
import functools
import http.server
import pathlib
import sys

APP_ROOT = pathlib.Path(__file__).resolve().parent / "app"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".woff2": "font/woff2",
        ".jpg": "image/jpeg",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Rea Studio on localhost.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    args = parser.parse_args()

    if not APP_ROOT.is_dir():
        print(f"missing app folder: {APP_ROOT}", file=sys.stderr)
        return 2

    handler = functools.partial(Handler, directory=str(APP_ROOT))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Rea Studio: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
