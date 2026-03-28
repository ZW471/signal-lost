#!/usr/bin/env python3
"""
Signal Lost — Minor NPC Profile Generator
Creates background NPCs for scene population.

Usage:
    python profile.py                           # Random NPC
    python profile.py --district "The Sprawl"   # NPC from specific district
    python profile.py --count 3                 # Generate 3 NPCs
    python profile.py --faction "NEXUS"         # NPC from specific faction
"""
import argparse
import random

# Name pools
SURNAMES_EN = ["Chen", "Park", "Volkov", "Santos", "Okafor", "Kim", "Reyes", "Singh", "Tanaka", "Liu",
               "Müller", "Costa", "Nakamura", "Zhang", "Petrov", "Ahmad", "Sato", "Wong", "Hernandez", "Yoon"]
GIVEN_EN = ["Kai", "Ren", "Yuki", "Ash", "Jin", "Sol", "Ava", "Zane", "Miko", "Rex",
            "Lux", "Neo", "Vex", "Ori", "Tao", "Dex", "Ivy", "Zen", "Lex", "Rue"]
SURNAMES_ZH = ["陈", "朴", "沃尔科夫", "桑托斯", "奥卡弗", "金", "雷耶斯", "辛格", "田中", "刘",
               "穆勒", "科斯塔", "中村", "张", "彼得罗夫", "艾哈迈德", "佐藤", "黄", "埃尔南德斯", "尹"]

OCCUPATIONS = {
    "The Sprawl": ["Street vendor", "Mechanic", "Courier", "Scrap dealer", "Noodle cook",
                   "Implant technician", "Fixer", "Street medic", "Recycler", "Tattoo artist"],
    "Neon Row": ["Club bouncer", "Bartender", "Sensory parlor operator", "Street performer",
                 "Black market dealer", "DJ", "Escort", "Gambling den runner", "Drug courier", "Promoter"],
    "Sector 7": ["NEXUS technician", "Security guard", "Lab assistant", "Data analyst",
                 "Corporate intern", "Maintenance worker", "Drone operator", "Receptionist"],
    "The Undercroft": ["Scavenger", "Tunnel guide", "Relic hunter", "Squatter",
                       "Underground farmer", "Signal listener", "Rat catcher", "Ghost hunter"],
    "Chrome Heights": ["Personal assistant", "Private security", "House servant", "Chauffeur",
                       "Garden designer", "Art dealer", "Private tutor", "Wine sommelier"],
}

PERSONALITIES = ["nervous", "cheerful", "suspicious", "tired", "curious", "aggressive",
                 "helpful", "distracted", "melancholic", "sarcastic", "paranoid", "kind",
                 "ambitious", "drunk", "quiet", "talkative", "secretive", "naive"]

RUMORS = {
    "L1": [
        "NEXUS raised prices again — they own everything",
        "The Severance anniversary is next week. Bad memories.",
        "Don't go to the Undercroft at night. Things move down there.",
        "NEXUS drones are watching more than usual lately",
        "They say the old network was paradise compared to now",
        "联结公司控制着一切——水、电、信息",
        "有人说断离前的世界更好",
    ],
    "L2": [
        "People with old implants have been disappearing. Just... gone.",
        "There's a group that protects people who hear things. The Listeners.",
        "NEXUS has a special division — not on any org chart",
        "有人说听到了信号的人都消失了",
        "有个地下组织叫聆听者——他们帮助那些听到声音的人",
        "My cousin had an old implant. NEXUS 'relocated' her. Haven't heard from her since.",
    ],
    "L3": [
        "The Severance wasn't what they told us. Someone pulled the plug on purpose.",
        "NEXUS doesn't just collect old implants — they extract something from them",
        "I heard the old network had something alive in it before it went down",
        "断离不是意外——有人故意切断了网络",
        "联结从旧植入体里提取什么东西——不只是数据",
    ],
}

FACTS = [
    "NEXUS headquarters is in Sector 7's Central Tower",
    "The Severance happened exactly 30 years ago on March 15",
    "Neural implants were mandatory before the Severance",
    "Chrome Heights was built on the ruins of the old financial district",
    "The Undercroft used to be the city's transit system",
    "联结总部在第七区中央塔",
    "断离发生在整整三十年前",
]


def generate_npc(district: str = None, faction: str = None) -> dict:
    """Generate a random minor NPC."""
    if not district:
        district = random.choice(list(OCCUPATIONS.keys()))

    idx = random.randint(0, len(SURNAMES_EN) - 1)
    name_en = f"{random.choice(GIVEN_EN)} {SURNAMES_EN[idx]}"
    name_zh = f"{SURNAMES_ZH[idx]}{random.choice(['小', '大', '老', '阿'])}{random.choice(['明', '华', '强', '丽', '杰', '芳', '伟', '敏'])}"

    occupation = random.choice(OCCUPATIONS.get(district, OCCUPATIONS["The Sprawl"]))
    personality = random.choice(PERSONALITIES)

    # Each NPC knows one thing — either a rumor or a fact
    if random.random() < 0.7:
        layer = random.choices(["L1", "L2", "L3"], weights=[60, 30, 10])[0]
        knowledge_type = "rumor"
        knowledge = random.choice(RUMORS[layer])
        knowledge_layer = layer
    else:
        knowledge_type = "fact"
        knowledge = random.choice(FACTS)
        knowledge_layer = "L1"

    if not faction:
        faction_weights = {
            "The Sprawl": [("Unaffiliated", 80), ("Listeners", 10), ("Purists", 10)],
            "Neon Row": [("Unaffiliated", 60), ("Listeners", 25), ("Purists", 5), ("NEXUS", 10)],
            "Sector 7": [("NEXUS", 70), ("Unaffiliated", 25), ("Listeners", 5)],
            "The Undercroft": [("Unaffiliated", 50), ("Listeners", 35), ("Purists", 15)],
            "Chrome Heights": [("Unaffiliated", 40), ("NEXUS", 30), ("Purists", 25), ("Listeners", 5)],
        }
        weights = faction_weights.get(district, [("Unaffiliated", 100)])
        factions, probs = zip(*weights)
        faction = random.choices(factions, weights=probs)[0]

    return {
        "name_en": name_en,
        "name_zh": name_zh,
        "district": district,
        "occupation": occupation,
        "personality": personality,
        "faction": faction,
        "knowledge_type": knowledge_type,
        "knowledge": knowledge,
        "knowledge_layer": knowledge_layer,
    }


def format_npc(npc: dict) -> str:
    """Format NPC profile for display."""
    lines = []
    lines.append("┌──────────────────────────────────────────┐")
    lines.append(f"│  {npc['name_en']:<40s}│")
    lines.append(f"│  {npc['name_zh']:<40s}│")
    lines.append(f"├──────────────────────────────────────────┤")
    lines.append(f"│  District:    {npc['district']:<27s}│")
    lines.append(f"│  Occupation:  {npc['occupation']:<27s}│")
    lines.append(f"│  Personality: {npc['personality']:<27s}│")
    lines.append(f"│  Faction:     {npc['faction']:<27s}│")
    lines.append(f"├──────────────────────────────────────────┤")
    lines.append(f"│  Knows ({npc['knowledge_type']}, {npc['knowledge_layer']}):{'':>17s}│")
    knowledge = npc['knowledge']
    for i in range(0, len(knowledge), 38):
        chunk = knowledge[i:i+38]
        lines.append(f"│    \"{chunk:<38s}│")
    lines.append("└──────────────────────────────────────────┘")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — NPC Generator")
    parser.add_argument("--district", "-d", help="District for the NPC")
    parser.add_argument("--faction", "-f", help="Faction affiliation")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of NPCs to generate")
    args = parser.parse_args()

    for i in range(args.count):
        npc = generate_npc(district=args.district, faction=args.faction)
        print(format_npc(npc))
        if i < args.count - 1:
            print()


if __name__ == "__main__":
    main()
