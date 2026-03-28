#!/usr/bin/env python3
"""
Signal Lost — Dice / Probability Check Tool
Usage:
    python dice.py d100                  # Roll d100
    python dice.py d100 --target 60      # Roll d100 vs target (success if ≤ target)
    python dice.py d100 --target 60 --modifier 10  # Roll with bonus
    python dice.py d20                   # Roll d20
    python dice.py 2d6+3                 # Roll 2d6+3
"""
import argparse
import random
import re
import sys


def parse_dice(expr: str) -> tuple[int, int, int]:
    """Parse dice expression like '2d6+3' → (count, sides, modifier)."""
    m = re.match(r'^(\d*)d(\d+)([+-]\d+)?$', expr.strip().lower())
    if not m:
        print(f"Error: Invalid dice expression '{expr}'. Use format: [N]dS[+/-M]", file=sys.stderr)
        sys.exit(1)
    count = int(m.group(1)) if m.group(1) else 1
    sides = int(m.group(2))
    modifier = int(m.group(3)) if m.group(3) else 0
    return count, sides, modifier


def roll(count: int, sides: int, modifier: int = 0) -> dict:
    """Roll dice and return results."""
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    return {
        "expression": f"{count}d{sides}{'+' + str(modifier) if modifier > 0 else str(modifier) if modifier < 0 else ''}",
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
        "min_possible": count + modifier,
        "max_possible": count * sides + modifier,
    }


def check(total: int, target: int) -> dict:
    """Check roll against target (success if total ≤ target for d100 checks)."""
    success = total <= target
    margin = target - total
    # Critical success/failure for d100
    critical = None
    if total <= 5:
        critical = "critical_success"
    elif total >= 96:
        critical = "critical_failure"
    return {
        "success": success,
        "margin": margin,
        "critical": critical,
    }


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Dice Roller")
    parser.add_argument("dice", help="Dice expression (e.g., d100, 2d6+3)")
    parser.add_argument("--target", "-t", type=int, help="Target number for success check (roll ≤ target)")
    parser.add_argument("--modifier", "-m", type=int, default=0, help="Additional modifier to add")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output (just the number)")
    args = parser.parse_args()

    count, sides, modifier = parse_dice(args.dice)
    modifier += args.modifier
    result = roll(count, sides, modifier)

    if args.quiet:
        print(result["total"])
        return

    print(f"╔══════════════════════════════╗")
    print(f"║  🎲 ROLL: {result['expression']:>18s}  ║")
    print(f"╠══════════════════════════════╣")
    if count > 1:
        print(f"║  Rolls: {str(result['rolls']):>20s}  ║")
    if modifier != 0:
        print(f"║  Modifier: {modifier:>+18d}  ║")
    print(f"║  Total: {result['total']:>21d}  ║")

    if args.target is not None:
        c = check(result["total"], args.target)
        status = "✓ SUCCESS" if c["success"] else "✗ FAILURE"
        if c["critical"] == "critical_success":
            status = "★ CRITICAL SUCCESS"
        elif c["critical"] == "critical_failure":
            status = "✗ CRITICAL FAILURE"
        print(f"╠══════════════════════════════╣")
        print(f"║  Target: ≤{args.target:<19d}  ║")
        print(f"║  Result: {status:>20s}  ║")
        print(f"║  Margin: {c['margin']:>+20d}  ║")

    print(f"╚══════════════════════════════╝")


if __name__ == "__main__":
    main()
