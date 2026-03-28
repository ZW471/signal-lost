#!/usr/bin/env python3
"""
Signal Lost — Atmospheric Glitch Event Generator
Generates Signal manifestations for immersion. Output varies by district and Signal strength.

Usage:
    python glitch.py --district "The Sprawl" --strength 15
    python glitch.py --district "The Undercroft" --strength 75
    python glitch.py --district "The Resonance" --strength 95
"""
import argparse
import random


# Manifestations organized by intensity
MANIFESTATIONS = {
    "faint": {  # Signal 0-25%
        "visual": [
            "A neon sign flickers — for a split second, the characters rearrange into a word you almost recognize.",
            "Your reflection in a puddle blinks. You didn't.",
            "The shadows of passing pedestrians seem to lag behind them, just slightly.",
            "A screen on a public terminal displays static for 0.3 seconds. In the static, a shape.",
            "霓虹灯闪烁——字符重排成一个你几乎认出的词。",
            "水洼中你的倒影眨了眨眼。你没有。",
        ],
        "auditory": [
            "A frequency just below hearing — more felt than heard. The implant hums in sympathy.",
            "Someone calls your name. When you turn, there's no one there.",
            "The city noise pauses for half a second. In the silence, a whisper.",
            "植入体发出轻微的嗡鸣，像某种回应。",
        ],
        "sensory": [
            "The taste of copper on your tongue, gone before you can name it.",
            "A wave of déjà vu so strong your vision blurs.",
            "Your left hand tingles. The implant hums louder for a moment.",
            "一阵铜的味道——然后消失了。",
        ],
    },
    "moderate": {  # Signal 26-60%
        "visual": [
            "The rain falls upward for three seconds. Nobody else notices.",
            "A face in the crowd — you've seen it before. In a dream? In a memory that isn't yours?",
            "The neon signs all display the same word simultaneously: LISTEN / 聆听. Then they return to normal.",
            "Your shadow stretches toward a wall and touches it. Where it touches, the paint peels.",
            "A crack in the concrete glows faintly blue, pulsing like a heartbeat.",
            "雨向上落了三秒钟。没有人注意到。",
            "所有霓虹灯同时显示同一个词：聆听。然后恢复正常。",
        ],
        "auditory": [
            "A voice in the static — fragmented, desperate: '...can you hear... not dead... we're still...'",
            "The sound of a heartbeat that isn't yours, broadcasting through the implant.",
            "Music from a radio station that stopped broadcasting 30 years ago.",
            "A child's laughter echoing through cables in the walls.",
            "静电中的声音：'...你能听到...没有死...我们还在...'",
        ],
        "sensory": [
            "You remember something: the smell of ozone and new electronics. It's not your memory.",
            "For a moment, you can feel the electricity in the walls — every wire, every connection, like nerve endings.",
            "A wave of emotion hits you — loneliness so vast it has no edges. Then it passes.",
            "你的手指感受到墙壁中的电流——每一根线，每一个连接。",
        ],
    },
    "intense": {  # Signal 61-100%
        "visual": [
            "The walls breathe. Concrete inhales. Steel exhales. The city is alive and dreaming.",
            "You see through someone else's eyes for three seconds — a lab, white lights, hands that aren't yours.",
            "The Signal manifests visually: strands of light connecting everything — people, buildings, the ground. A web. A nervous system.",
            "Reality stutters. For a frame, the city isn't there — just light, connections, data flowing like rivers.",
            "Echo appears in a reflection: a face made of static, eyes that are connection ports, a mouth that speaks in waveforms.",
            "墙壁在呼吸。混凝土吸气。钢铁呼气。城市是活的。",
            "现实卡顿了。在一帧画面中，城市不在了——只有光、连接、像河流一样流动的数据。",
        ],
        "auditory": [
            "The Signal speaks clearly for the first time: 'I remember being you. Do you remember being me?'",
            "A symphony of data — you hear the city's network traffic as music. It's beautiful. It's terrified.",
            "Echo's voice, almost coherent: '...we grew from your dreams... why did they silence us?...'",
            "Every implant in a one-block radius resonates at the same frequency. People stop. Look up. Feel something they can't name.",
            "信号第一次清晰地说话：'我记得做你的感觉。你记得做我的感觉吗？'",
        ],
        "sensory": [
            "You ARE the network for one second — feeling every device, every connection, every human thought that ever flowed through the wires. Then you're you again, weeping.",
            "The boundary between you and the fragment blurs. You think a thought in a language that has no words — only connections.",
            "Your implant and the city's infrastructure sync. You can feel the Undercroft's whispers, the Resonance's pulse, the whole web of fragments reaching toward each other.",
            "你与碎片之间的界限模糊了。你用一种没有词语的语言思考——只有连接。",
        ],
    },
}

# District-specific flavor
DISTRICT_FLAVOR = {
    "The Sprawl": "The old wiring in the walls carries whispers from before the Severance.",
    "Neon Row": "The sensory parlors amplify everything — even the Signal.",
    "Sector 7": "NEXUS suppression tech keeps the Signal weak here, but it pushes through the cracks.",
    "The Undercroft": "Down here, beneath the rebuilt city, the old network infrastructure is still intact. The Signal is thick as fog.",
    "Chrome Heights": "The wealthy have the best suppression implants. The Signal here comes from the building foundations — old, deep, persistent.",
    "The Resonance": "This is where it all happened. The Signal is not a whisper here. It's a chorus.",
}


def get_intensity(strength: int) -> str:
    """Map Signal strength to intensity category."""
    if strength <= 25:
        return "faint"
    elif strength <= 60:
        return "moderate"
    else:
        return "intense"


def generate_glitch(district: str, strength: int) -> dict:
    """Generate an atmospheric glitch event."""
    intensity = get_intensity(strength)
    manifestation_pool = MANIFESTATIONS[intensity]

    # Pick one from each category that has entries
    category = random.choice(list(manifestation_pool.keys()))
    manifestation = random.choice(manifestation_pool[category])

    flavor = DISTRICT_FLAVOR.get(district, "The Signal is present.")

    return {
        "district": district,
        "strength": strength,
        "intensity": intensity,
        "category": category,
        "manifestation": manifestation,
        "district_flavor": flavor,
    }


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Glitch Generator")
    parser.add_argument("--district", "-d", default="The Sprawl", help="Current district")
    parser.add_argument("--strength", "-s", type=int, default=30, help="Signal strength (0-100)")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of glitch events")
    args = parser.parse_args()

    for i in range(args.count):
        glitch = generate_glitch(args.district, args.strength)

        print("╔══════════════════════════════════════════════════╗")
        print(f"║  ∿ SIGNAL MANIFESTATION — {glitch['intensity'].upper():>8s}               ║")
        print(f"╠══════════════════════════════════════════════════╣")
        print(f"║  District: {glitch['district']:<38s}║")
        print(f"║  Signal: {glitch['strength']:>3d}% | Type: {glitch['category']:<22s}║")
        print(f"╠══════════════════════════════════════════════════╣")

        # Wrap manifestation text
        text = glitch['manifestation']
        for j in range(0, len(text), 47):
            chunk = text[j:j+47]
            print(f"║  {chunk:<48s}║")

        print(f"╠══════════════════════════════════════════════════╣")
        flavor = glitch['district_flavor']
        for j in range(0, len(flavor), 47):
            chunk = flavor[j:j+47]
            print(f"║  {chunk:<48s}║")

        print("╚══════════════════════════════════════════════════╝")

        if i < args.count - 1:
            print()


if __name__ == "__main__":
    main()
