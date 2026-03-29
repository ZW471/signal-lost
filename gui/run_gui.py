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
import os
import subprocess
import sys
import threading
import time
import webbrowser

import uvicorn


def _ensure_music_assets():
    """Check if music files exist; download from Google Drive if missing."""
    gui_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(gui_dir, ".."))
    music_dir = os.path.join(project_root, "assets", "music")
    script_path = os.path.join(project_root, "scripts", "download_music.py")

    if not os.path.isfile(script_path):
        return  # No download script available

    # Check if any music files are missing
    expected = [
        "Menu.mp3", "The Sprawl.mp3", "Neon Row.mp3", "The Undercroft.mp3",
        "Sector7.mp3", "The Resonance .mp3", "Chrome Heights.mp3", "The Spire.mp3",
    ]
    missing = [f for f in expected if not os.path.isfile(os.path.join(music_dir, f))]

    if not missing:
        return  # All files present

    print(f"\n  Music assets missing ({len(missing)} files). Downloading...")
    subprocess.run([sys.executable, script_path], check=False)


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Browser GUI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to (default: 8765)")
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open browser")
    args = parser.parse_args()

    _ensure_music_assets()

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
