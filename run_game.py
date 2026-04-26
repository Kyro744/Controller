#!/usr/bin/env python3
"""One-command launcher for the HTML ecosystem game.

Usage:
  python run_game.py
  python run_game.py --port 9000 --no-browser
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the Pixel Ecosystem Empire HTML game")
    parser.add_argument("--port", type=int, default=8000, help="Port for local HTTP server (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    target_file = root / "ecosystem_rpg.html"
    if not target_file.exists():
        raise SystemExit("ecosystem_rpg.html was not found in this directory.")

    handler = http.server.SimpleHTTPRequestHandler
    with ReusableTCPServer(("", args.port), handler) as httpd:
        url = f"http://localhost:{args.port}/ecosystem_rpg.html"
        print(f"Serving {root}")
        print(f"Open: {url}")
        print("Press Ctrl+C to stop")

        if not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
