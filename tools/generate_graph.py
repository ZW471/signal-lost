#!/usr/bin/env python3
"""
Generate a PNG visualization of the Signal Lost game engine graph.

Usage:
    uv run tools/generate_graph.py                # → engine/graph.png
    uv run tools/generate_graph.py -o my_graph.png
    uv run tools/generate_graph.py --format mermaid  # print Mermaid source
"""

from __future__ import annotations

import argparse
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from engine.graph import compile_graph


def main():
    parser = argparse.ArgumentParser(description="Generate Signal Lost engine graph visualization")
    parser.add_argument("-o", "--output", default=os.path.join(_GAME_ROOT, "engine", "graph.png"),
                        help="Output file path (default: engine/graph.png)")
    parser.add_argument("--format", choices=["png", "mermaid"], default="png",
                        help="Output format (default: png)")
    args = parser.parse_args()

    graph = compile_graph()
    drawable = graph.get_graph()

    if args.format == "mermaid":
        print(drawable.draw_mermaid())
        return

    png_bytes = drawable.draw_mermaid_png()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(png_bytes)
    print(f"Graph saved to {args.output}")


if __name__ == "__main__":
    main()
