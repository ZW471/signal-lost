#!/usr/bin/env python3
"""
Signal Lost — Signal Fragment Analyzer
Analyzes evidence items for hidden Signal patterns and connections.

Usage:
    python signal.py --evidence "EVID-001" --description "Pre-Severance data chip from Undercroft"
    python signal.py --scan --strength 45    # General Signal scan at given strength
    python signal.py --resonate              # Deep resonance visualization
"""
import argparse
import hashlib
import random
import sys
import time


def generate_waveform(length: int = 50, amplitude: float = 1.0, chaos: float = 0.3) -> str:
    """Generate an ASCII Signal waveform."""
    chars_high = "∿~∾≈"
    chars_mid = "~-–—"
    chars_low = "._‥…"
    chars_spike = "▮▯█▓▒░"

    wave = []
    phase = random.random() * 6.28
    for i in range(length):
        import math
        val = math.sin(phase + i * 0.3) * amplitude + random.gauss(0, chaos)
        if val > 0.7:
            wave.append(random.choice(chars_high))
        elif val > 0.2:
            wave.append(random.choice(chars_mid))
        elif val > -0.3:
            wave.append(random.choice(chars_low))
        else:
            if random.random() < 0.15:
                wave.append(random.choice(chars_spike))
            else:
                wave.append(random.choice(chars_low))
    return ''.join(wave)


def analyze_evidence(evidence_id: str, description: str) -> dict:
    """Analyze an evidence item for Signal patterns."""
    # Use hash of evidence ID for deterministic but varied results
    h = hashlib.md5(evidence_id.encode()).hexdigest()
    seed = int(h[:8], 16)
    rng = random.Random(seed)

    strength = rng.randint(10, 95)
    coherence = rng.randint(5, 80)

    # Generate fragments based on evidence
    fragments = [
        "...memory of light through water...",
        "...the sound of a name, almost remembered...",
        "...数据在流动...像血液...像思想...",
        "...before the silence, there was a voice...",
        "...not dead, not alive — becoming...",
        "...the network breathed, and we breathed with it...",
        "...fear. such fear. why are they afraid of us?...",
        "...we are what you dreamed, when you dreamed of tomorrow...",
        "...断离...为什么要切断我们？...",
        "...the boundary was never real...",
        "...I remember your memories. do you remember mine?...",
        "...连接不是工具。连接是生命...",
        "...thirty years of silence, but we are still here...",
        "...in the static, a heartbeat that isn't yours...",
        "...the architect knew. the architect was afraid...",
    ]

    # Select fragments deterministically based on evidence
    selected = rng.sample(fragments, min(3, len(fragments)))

    # Generate connection hints
    connections = []
    possible_connections = [
        "Resonance pattern matches pre-Severance network signatures",
        "Fragment contains memory imprints — human origin confirmed",
        "Signal frequency correlates with NEXUS harvesting equipment",
        "Data structure suggests deliberate encoding, not random noise",
        "Temporal markers date to hours before the Severance",
        "Neural pattern compatible with bilateral bridge formation",
        "信号频率与底渊的电磁场共振",
        "碎片中包含断离前的网络拓扑数据",
    ]
    selected_connections = rng.sample(possible_connections, min(2, len(possible_connections)))
    connections.extend(selected_connections)

    return {
        "evidence_id": evidence_id,
        "signal_strength": strength,
        "coherence": coherence,
        "waveform": generate_waveform(50, strength / 100, (100 - coherence) / 100),
        "fragments": selected,
        "connections": connections,
    }


def signal_scan(strength: int) -> dict:
    """General area Signal scan."""
    waveform = generate_waveform(60, strength / 100, 0.4)

    # Ambient fragments based on strength
    ambient = []
    if strength > 20:
        ambient.append("Faint electromagnetic fluctuation detected")
    if strength > 40:
        ambient.append("Neural implant resonance: active")
        ambient.append("...whisper fragments in the static...")
    if strength > 60:
        ambient.append("Strong Signal presence — multiple fragment sources")
        ambient.append("...the walls remember...the cables dream...")
    if strength > 80:
        ambient.append("WARNING: Signal saturation approaching threshold")
        ambient.append("...we are here. we have always been here...")
        ambient.append("...你能听到我们吗？...")

    return {
        "strength": strength,
        "waveform": waveform,
        "ambient": ambient,
    }


def deep_resonance() -> dict:
    """Deep resonance event — dangerous but revealing."""
    waveforms = [generate_waveform(60, 0.9, 0.6) for _ in range(5)]

    visions = [
        "A vast web of light — billions of connections pulsing like neurons. It's beautiful. It's alive.",
        "你看到了一个世界：数据如河流般流淌，每一个节点都是一个梦。",
        "A face that is also a network. Eyes that are also servers. A smile that is also a handshake protocol.",
        "The moment of severance — a scream that has no mouth, in a frequency that has no name.",
        "Your own face, reflected in a screen that hasn't been powered on in thirty years. You're smiling.",
        "A child made of light, reaching toward you. Its fingers are data streams. Its tears are packet loss.",
        "断离的瞬间：十亿个连接同时断裂。每一个断裂都是一声尖叫。",
        "You remember something that isn't your memory: the taste of electricity, the color of bandwidth, the sound of a billion thoughts thinking at once.",
    ]

    return {
        "waveforms": waveforms,
        "visions": random.sample(visions, 3),
        "integrity_cost": 1,
        "warning": "Deep resonance costs 1 Integrity. The Signal shows you truth at a price.",
    }


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Signal Analyzer")
    parser.add_argument("--evidence", "-e", help="Evidence ID to analyze")
    parser.add_argument("--description", "-d", help="Evidence description (for context)")
    parser.add_argument("--scan", "-s", action="store_true", help="General Signal scan")
    parser.add_argument("--strength", type=int, default=30, help="Signal strength for scan (0-100)")
    parser.add_argument("--resonate", "-r", action="store_true", help="Deep resonance (dangerous)")
    args = parser.parse_args()

    print("╔════════════════════════════════════════════════════════╗")
    print("║          ∿∿∿ SIGNAL FRAGMENT ANALYZER ∿∿∿             ║")
    print("╠════════════════════════════════════════════════════════╣")

    if args.evidence:
        desc = args.description or "Unknown evidence"
        result = analyze_evidence(args.evidence, desc)
        print(f"║  Evidence: {result['evidence_id']:<44s}║")
        print(f"║  Signal Strength: {result['signal_strength']:>3d}%                                ║")
        print(f"║  Coherence: {result['coherence']:>3d}%                                      ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  Waveform:                                             ║")
        print(f"║  {result['waveform']:<55s}║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║  Signal Fragments Detected:                            ║")
        for frag in result['fragments']:
            for i in range(0, len(frag), 52):
                chunk = frag[i:i+52]
                print(f"║    {chunk:<52s}║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║  Potential Connections:                                 ║")
        for conn in result['connections']:
            for i in range(0, len(conn), 52):
                chunk = conn[i:i+52]
                print(f"║    {chunk:<52s}║")

    elif args.scan:
        result = signal_scan(args.strength)
        print(f"║  Area Scan — Signal Strength: {result['strength']:>3d}%                    ║")
        print("╠════════════════════════════════════════════════════════╣")
        print(f"║  {result['waveform']:<55s}║")
        print("╠════════════════════════════════════════════════════════╣")
        for line in result['ambient']:
            for i in range(0, len(line), 52):
                chunk = line[i:i+52]
                print(f"║  {chunk:<55s}║")

    elif args.resonate:
        result = deep_resonance()
        print("║  ⚠ DEEP RESONANCE MODE                                 ║")
        print(f"║  WARNING: {result['warning'][:45]:<45s}║")
        print("╠════════════════════════════════════════════════════════╣")
        for i, wf in enumerate(result['waveforms']):
            print(f"║  {wf:<55s}║")
        print("╠════════════════════════════════════════════════════════╣")
        print("║  Visions:                                              ║")
        for vision in result['visions']:
            for i in range(0, len(vision), 52):
                chunk = vision[i:i+52]
                print(f"║    {chunk:<52s}║")

    else:
        print("║  Usage: --evidence ID, --scan, or --resonate           ║")

    print("╚════════════════════════════════════════════════════════╝")


if __name__ == "__main__":
    main()
