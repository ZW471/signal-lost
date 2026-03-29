#!/usr/bin/env python3
"""
Download music assets from Google Drive.

Run this script before starting the game to download background music.
Files are saved to assets/music/ in the project root.

Usage:
    uv run scripts/download_music.py
    python scripts/download_music.py
"""

import os
import sys
import urllib.request

# ---------------------------------------------------------------------------
# Google Drive file IDs (shared publicly)
# Folder: agentic_games/signal_lost/assets/music/
# ---------------------------------------------------------------------------

MUSIC_FILES = {
    "Menu.mp3":            "1U_CUaXvxwLPOlVOX4BI5hpsF04r7KDtH",
    "The Sprawl.mp3":      "18NGjT_ZjIQcegnYV-ARks5hxLNf2WJhf",
    "Neon Row.mp3":        "1LhumbmF7aHl3ItwtsiNnI6f3y_4pLl_G",
    "The Undercroft.mp3":  "1fnVxCqlqR8DBpU8w7bZCIJsSvaIeKGWL",
    "Sector7.mp3":         "1KFtkjv4zhwcGLcfbfnwRSWc-6sHxi6ih",
    "The Resonance .mp3":  "1L6Ft6z5bA0Stq_k8oKjuegkxP_BB2s7q",
    "Chrome Heights.mp3":  "1Lx_21HLsFQv2VBxcJTrXPWtWpaM4RnTr",
    "The Spire.mp3":       "1DLkmpz9PFymGQ_-5lCqUfaIvavnPcfJh",
}

# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def progress_bar(current, total, width=40, prefix=""):
    """Print a progress bar to stderr."""
    if total <= 0:
        return
    frac = current / total
    filled = int(width * frac)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    pct = frac * 100
    size_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    sys.stderr.write(f"\r  {prefix} [{bar}] {pct:5.1f}%  {size_mb:.1f}/{total_mb:.1f} MB")
    sys.stderr.flush()


def download_gdrive_file(file_id: str, dest_path: str, filename: str) -> bool:
    """Download a file from Google Drive by file ID with progress bar."""
    # Google Drive direct download URL (for small files)
    # For large files, a confirmation redirect is needed
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")

        with urllib.request.urlopen(req) as response:
            # Check for virus scan warning redirect (large files)
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                # Need confirmation token — read HTML page for confirm token
                html = response.read().decode("utf-8", errors="replace")
                # Extract confirm token
                import re
                # Look for the confirm URL pattern
                match = re.search(r'href="(/uc\?export=download[^"]*)"', html)
                if match:
                    confirm_url = "https://drive.google.com" + match.group(1).replace("&amp;", "&")
                else:
                    # Try the uuid pattern
                    match = re.search(r'name="uuid" value="([^"]*)"', html)
                    if match:
                        uuid = match.group(1)
                        confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t&uuid={uuid}"
                    else:
                        # Fallback: just add confirm=t
                        confirm_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"

                req2 = urllib.request.Request(confirm_url)
                req2.add_header("User-Agent", "Mozilla/5.0")
                response = urllib.request.urlopen(req2)

            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024  # 64KB chunks

            with open(dest_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress_bar(downloaded, total if total else downloaded, prefix=filename)

            sys.stderr.write("\n")
            return True

    except Exception as e:
        sys.stderr.write(f"\n  ERROR: {e}\n")
        return False


def main():
    # Determine project root (parent of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    music_dir = os.path.join(project_root, "assets", "music")

    # Create directory
    os.makedirs(music_dir, exist_ok=True)

    print("=" * 60)
    print("  SIGNAL LOST — Music Asset Downloader")
    print("=" * 60)
    print()

    # Check which files already exist
    to_download = {}
    already_have = 0
    for filename, file_id in MUSIC_FILES.items():
        dest = os.path.join(music_dir, filename)
        if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
            already_have += 1
        else:
            to_download[filename] = file_id

    if not to_download:
        print(f"  All {len(MUSIC_FILES)} music files already present.")
        print(f"  Location: {music_dir}")
        print()
        return

    if already_have > 0:
        print(f"  {already_have} files already downloaded, {len(to_download)} remaining.")
    else:
        print(f"  Downloading {len(to_download)} music files from Google Drive...")
    print(f"  Destination: {music_dir}")
    print()

    success = 0
    failed = 0

    for i, (filename, file_id) in enumerate(to_download.items(), 1):
        dest = os.path.join(music_dir, filename)
        print(f"  [{i}/{len(to_download)}] {filename}")
        if download_gdrive_file(file_id, dest, filename):
            success += 1
        else:
            failed += 1

    print()
    print("-" * 60)
    print(f"  Done: {success} downloaded, {failed} failed, {already_have} already present.")
    if failed > 0:
        print("  Some downloads failed. Try running the script again.")
        sys.exit(1)
    print()


if __name__ == "__main__":
    main()
