"""Serve the installable PWA with Python's standard library for local testing."""

from __future__ import annotations

import argparse
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB_ROOT = Path(__file__).resolve().parent / "web"
mimetypes.add_type("application/manifest+json", ".webmanifest")


class PWAHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; connect-src 'self' https://generativelanguage.googleapis.com "
            "https://openrouter.ai; worker-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'",
        )
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        # Keep local logs useful without printing request bodies or query data.
        super().log_message(fmt, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kerala PSC Coach as a local progressive web app.")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"), help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")), help="HTTP port (default: 8000)")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), PWAHandler)
    print(f"Kerala PSC Coach PWA is available at http://127.0.0.1:{args.port}/")
    print("Press Ctrl+C to stop. For Android/iPhone installation, use the public HTTPS site or another HTTPS host.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local PWA server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
