#!/usr/bin/env python3
"""
Signal Lost — Browser GUI Launcher

Starts the FastAPI server and opens the browser.

Usage:
    python gui/run_gui.py
    python gui/run_gui.py --port 8080
    python gui/run_gui.py --no-open   # don't auto-open browser
"""

import argparse
import threading
import time
import webbrowser

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Browser GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to (default: 8765)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"

    if not args.no_open:
        def open_browser():
            time.sleep(1.5)
            print(f"\n  Opening browser at {url}\n")
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    print(f"""
  ╔══════════════════════════════════════╗
  ║          SIGNAL LOST — GUI           ║
  ║                                      ║
  ║   Server: {url:<24s} ║
  ║   Press Ctrl+C to stop               ║
  ╚══════════════════════════════════════╝
    """)

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        app_dir=__import__("os").path.dirname(__import__("os").path.abspath(__file__)),
    )


if __name__ == "__main__":
    main()
