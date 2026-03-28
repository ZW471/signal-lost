#!/usr/bin/env python3
"""
Signal Lost — Cipher Decryption Tool
Decodes encrypted data chips and messages found in the game.
The player must figure out the cipher type and key.

Usage:
    python cipher.py --method caesar --key 3 --text "KHOOR ZRUOG"
    python cipher.py --method xor --key 42 --text "encrypted_hex_string"
    python cipher.py --method substitute --key "ZYXWVUTSRQPONMLKJIHGFEDCBA" --text "SVOOL DLIOW"
    python cipher.py --method reverse --text "dlrow olleh"
    python cipher.py --method base64 --text "aGVsbG8gd29ybGQ="
    python cipher.py --analyze --text "KHOOR ZRUOG"   # Frequency analysis hint
"""
import argparse
import base64
import string
import sys
from collections import Counter


def caesar_decrypt(text: str, shift: int) -> str:
    """Caesar cipher decryption."""
    result = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            result.append(chr((ord(ch) - base - shift) % 26 + base))
        else:
            result.append(ch)
    return ''.join(result)


def xor_decrypt(hex_text: str, key: int) -> str:
    """XOR decryption from hex string."""
    try:
        data = bytes.fromhex(hex_text.replace(' ', ''))
        return ''.join(chr(b ^ (key % 256)) for b in data)
    except ValueError:
        return "[ERROR: Invalid hex string]"


def substitute_decrypt(text: str, key: str) -> str:
    """Substitution cipher. Key is the cipher alphabet (26 chars)."""
    if len(key) != 26:
        return "[ERROR: Substitution key must be exactly 26 characters]"
    key_upper = key.upper()
    key_lower = key.lower()
    result = []
    for ch in text:
        if ch.isupper() and ch in key_upper:
            result.append(string.ascii_uppercase[key_upper.index(ch)])
        elif ch.islower() and ch in key_lower:
            result.append(string.ascii_lowercase[key_lower.index(ch)])
        else:
            result.append(ch)
    return ''.join(result)


def reverse_decrypt(text: str) -> str:
    """Simple reverse."""
    return text[::-1]


def base64_decrypt(text: str) -> str:
    """Base64 decode."""
    try:
        return base64.b64decode(text).decode('utf-8', errors='replace')
    except Exception:
        return "[ERROR: Invalid base64 string]"


def frequency_analysis(text: str) -> dict:
    """Return letter frequency for analysis hints."""
    letters = [ch.upper() for ch in text if ch.isalpha()]
    if not letters:
        return {}
    counts = Counter(letters)
    total = len(letters)
    return {ch: round(count / total * 100, 1) for ch, count in counts.most_common()}


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Cipher Tool")
    parser.add_argument("--method", "-m", choices=["caesar", "xor", "substitute", "reverse", "base64"],
                        help="Decryption method")
    parser.add_argument("--key", "-k", help="Decryption key (number for caesar/xor, alphabet for substitute)")
    parser.add_argument("--text", "-t", required=True, help="Text to decrypt")
    parser.add_argument("--analyze", "-a", action="store_true", help="Run frequency analysis instead of decrypting")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════╗")
    print("║       🔐 CIPHER DECRYPTION TOOL          ║")
    print("╠══════════════════════════════════════════╣")

    if args.analyze:
        freq = frequency_analysis(args.text)
        print("║  Mode: Frequency Analysis                ║")
        print("╠══════════════════════════════════════════╣")
        print(f"║  Input: {args.text[:35]:35s}  ║")
        print("╠══════════════════════════════════════════╣")
        if freq:
            print("║  Letter Frequencies:                     ║")
            for ch, pct in list(freq.items())[:10]:
                bar = "█" * int(pct / 5)
                print(f"║    {ch}: {bar:<12s} {pct:>5.1f}%              ║")
            print("╠══════════════════════════════════════════╣")
            print("║  Hint: In English, E≈13%, T≈9%, A≈8%    ║")
            print("║  Most common bigrams: TH, HE, IN, ER    ║")
        else:
            print("║  No alphabetic characters found.         ║")
        print("╚══════════════════════════════════════════╝")
        return

    if not args.method:
        print("║  ERROR: --method required for decryption  ║")
        print("║  Methods: caesar, xor, substitute,        ║")
        print("║           reverse, base64                  ║")
        print("║  Use --analyze for frequency analysis      ║")
        print("╚══════════════════════════════════════════╝")
        sys.exit(1)

    print(f"║  Method: {args.method:>32s}  ║")
    if args.key:
        display_key = args.key if len(args.key) <= 30 else args.key[:27] + "..."
        print(f"║  Key: {display_key:>35s}  ║")
    print(f"║  Input: {args.text[:34]:34s}  ║")
    print("╠══════════════════════════════════════════╣")

    if args.method == "caesar":
        try:
            shift = int(args.key) if args.key else 0
        except ValueError:
            print("║  ERROR: Caesar key must be a number       ║")
            print("╚══════════════════════════════════════════╝")
            sys.exit(1)
        result = caesar_decrypt(args.text, shift)
    elif args.method == "xor":
        try:
            key = int(args.key) if args.key else 0
        except ValueError:
            print("║  ERROR: XOR key must be a number          ║")
            print("╚══════════════════════════════════════════╝")
            sys.exit(1)
        result = xor_decrypt(args.text, key)
    elif args.method == "substitute":
        if not args.key:
            print("║  ERROR: Substitute needs 26-char key      ║")
            print("╚══════════════════════════════════════════╝")
            sys.exit(1)
        result = substitute_decrypt(args.text, args.key)
    elif args.method == "reverse":
        result = reverse_decrypt(args.text)
    elif args.method == "base64":
        result = base64_decrypt(args.text)
    else:
        result = "[Unknown method]"

    print(f"║  Output:                                  ║")
    # Wrap long output
    for i in range(0, len(result), 38):
        chunk = result[i:i+38]
        print(f"║    {chunk:<38s}  ║")
    print("╚══════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
