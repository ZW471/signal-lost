#!/usr/bin/env python3
"""
Signal Lost — District Map Generator
Generates an ASCII map of Neo-Kowloon with current position, access status, and danger levels.

Usage:
    python map.py --session-dir ./session   # Read from session files
    python map.py --current "The Sprawl" --alert 25  # Manual override
"""
import argparse
import json
import os
import re
import sys


# District layout (conceptual positions for ASCII map)
DISTRICTS = {
    "Chrome Heights": {"pos": (1, 0), "zh": "镀金台", "icon": "◇"},
    "Sector 7":       {"pos": (2, 0), "zh": "第七区", "icon": "◈"},
    "Neon Row":        {"pos": (0, 1), "zh": "霓虹街", "icon": "♦"},
    "The Sprawl":      {"pos": (1, 1), "zh": "蔓城",   "icon": "◆"},
    "The Undercroft":  {"pos": (2, 1), "zh": "底渊",   "icon": "▼"},
    "The Resonance":   {"pos": (1, 2), "zh": "共鸣所", "icon": "✦"},
}

# Access status display
ACCESS_STYLES = {
    "Open":       ("OPEN",       "█"),
    "Restricted": ("RSTRCT",     "▓"),
    "Locked":     ("LOCKED",     "░"),
    "Hidden":     ("??????",     "·"),
}

DANGER_INDICATOR = {
    "safe":     "○",
    "low":      "◔",
    "moderate": "◑",
    "high":     "◕",
    "extreme":  "●",
}


def read_session(session_dir: str) -> dict:
    """Read world state and location from session files."""
    data = {"current": "The Sprawl", "alert": 0, "decay": 0, "access": {}}

    ws_path = os.path.join(session_dir, "world_state.md")
    if os.path.exists(ws_path):
        with open(ws_path, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'\*\*NEXUS Alert:\*\*\s*(\d+)%', content)
        if m:
            data["alert"] = int(m.group(1))
        m = re.search(r'\*\*Fragment Decay:\*\*\s*(\d+)%', content)
        if m:
            data["decay"] = int(m.group(1))
        # Parse district access table
        for line in content.split('\n'):
            for dist_en, info in DISTRICTS.items():
                if dist_en in line or info["zh"] in line:
                    for status in ["Open", "Restricted", "Locked", "Hidden"]:
                        if status in line:
                            data["access"][dist_en] = status
                            break

    loc_path = os.path.join(session_dir, "location.md")
    if os.path.exists(loc_path):
        with open(loc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'\*\*District:\*\*\s*(.+?)(?:\s*/|$)', content)
        if m:
            district = m.group(1).strip()
            for dist_en in DISTRICTS:
                if dist_en.lower() in district.lower():
                    data["current"] = dist_en
                    break

    return data


def generate_map(current: str, alert: int, decay: int, access: dict) -> str:
    """Generate ASCII map."""
    lines = []

    # Header
    lines.append("╔══════════════════════════════════════════════════╗")
    lines.append("║           NEO-KOWLOON / 新九龙 — DISTRICT MAP    ║")
    lines.append("╠══════════════════════════════════════════════════╣")

    # Alert and decay meters
    alert_bar_len = 20
    alert_filled = int(alert / 100 * alert_bar_len)
    alert_bar = "█" * alert_filled + "░" * (alert_bar_len - alert_filled)
    decay_filled = int(decay / 100 * alert_bar_len)
    decay_bar = "█" * decay_filled + "░" * (alert_bar_len - decay_filled)

    lines.append(f"║  NEXUS Alert:    {alert_bar} {alert:>3d}%      ║")
    lines.append(f"║  Fragment Decay: {decay_bar} {decay:>3d}%      ║")
    lines.append("╠══════════════════════════════════════════════════╣")

    # Map grid
    lines.append("║                                                  ║")

    # Row 0: Chrome Heights, Sector 7
    ch_mark = ">>>" if current == "Chrome Heights" else "   "
    s7_mark = ">>>" if current == "Sector 7" else "   "
    ch_acc = ACCESS_STYLES.get(access.get("Chrome Heights", "Restricted"), ("???", "?"))[0]
    s7_acc = ACCESS_STYLES.get(access.get("Sector 7", "Restricted"), ("???", "?"))[0]

    lines.append(f"║    {ch_mark}┌──────────┐     ┌──────────┐       ║")
    lines.append(f"║       │◇ CHROME  │─────│◈ SECTOR  │       ║")
    lines.append(f"║       │  HEIGHTS │     │  7       │       ║")
    lines.append(f"║       │  镀金台   │     │  第七区   │       ║")
    lines.append(f"║       │  [{ch_acc:^6s}]│     │  [{s7_acc:^6s}]│       ║")
    lines.append(f"║       └────┬─────┘     └────┬─────┘       ║")
    lines.append(f"║            │                 │             ║")

    # Row 1: Neon Row, The Sprawl, The Undercroft
    nr_mark = ">>>" if current == "Neon Row" else "   "
    sp_mark = ">>>" if current == "The Sprawl" else "   "
    uc_mark = ">>>" if current == "The Undercroft" else "   "
    nr_acc = ACCESS_STYLES.get(access.get("Neon Row", "Open"), ("???", "?"))[0]
    sp_acc = ACCESS_STYLES.get(access.get("The Sprawl", "Open"), ("???", "?"))[0]
    uc_acc = ACCESS_STYLES.get(access.get("The Undercroft", "Open"), ("???", "?"))[0]

    lines.append(f"║ {nr_mark}┌──────────┐┌──────────┐┌──────────┐  ║")
    lines.append(f"║    │♦ NEON    ││◆ THE     ││▼ UNDER-  │  ║")
    lines.append(f"║    │  ROW     ││  SPRAWL  ││  CROFT   │  ║")
    lines.append(f"║    │  霓虹街   ││  蔓城     ││  底渊     │  ║")
    lines.append(f"║    │  [{nr_acc:^6s}]││  [{sp_acc:^6s}]││  [{uc_acc:^6s}]│  ║")
    lines.append(f"║    └──────────┘└────┬─────┘└──────────┘  ║")
    lines.append(f"║                     │                     ║")

    # Row 2: The Resonance
    rs_mark = ">>>" if current == "The Resonance" else "   "
    rs_acc = ACCESS_STYLES.get(access.get("The Resonance", "Hidden"), ("???", "?"))[0]

    lines.append(f"║          {rs_mark}┌──────────┐                  ║")
    lines.append(f"║             │✦ THE     │                  ║")
    lines.append(f"║             │RESONANCE │                  ║")
    lines.append(f"║             │  共鸣所   │                  ║")
    lines.append(f"║             │  [{rs_acc:^6s}]│                  ║")
    lines.append(f"║             └──────────┘                  ║")

    lines.append("║                                                  ║")
    lines.append("╠══════════════════════════════════════════════════╣")
    lines.append("║  >>> = Current Location                          ║")
    lines.append("║  OPEN = Accessible  RSTRCT = Needs clearance     ║")
    lines.append("║  LOCKED = Inaccessible  ?????? = Unknown         ║")
    lines.append("╚══════════════════════════════════════════════════╝")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — District Map")
    parser.add_argument("--session-dir", "-s", help="Path to session directory")
    parser.add_argument("--current", "-c", default="The Sprawl", help="Current district")
    parser.add_argument("--alert", "-a", type=int, default=0, help="NEXUS alert level (0-100)")
    parser.add_argument("--decay", "-d", type=int, default=0, help="Fragment decay (0-100)")
    args = parser.parse_args()

    if args.session_dir:
        data = read_session(args.session_dir)
    else:
        data = {
            "current": args.current,
            "alert": args.alert,
            "decay": args.decay,
            "access": {
                "The Sprawl": "Open",
                "Neon Row": "Open",
                "Sector 7": "Restricted",
                "The Undercroft": "Open",
                "Chrome Heights": "Restricted",
                "The Resonance": "Hidden",
            }
        }

    print(generate_map(data["current"], data["alert"], data["decay"], data["access"]))


if __name__ == "__main__":
    main()
