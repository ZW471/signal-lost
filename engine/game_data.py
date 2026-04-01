"""
Signal Lost — Extracted Game Data

Structured game data extracted from agent/game.md and game/*.md.
Used by deterministic Python nodes (trace_checker, world_ticker, consequence).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Trace discovery conditions
# Each trace has an ID, description, layer, and a checker function.
# The checker receives (knowledge, traces, npcs, player, world_state)
# and returns True if the trace should be discovered.
# ---------------------------------------------------------------------------

def _has_fact_or_rumor_about(knowledge: dict, keywords: list[str]) -> bool:
    """Check if knowledge contains a fact or rumor mentioning any keyword."""
    for entry_type in ("facts", "rumors"):
        for entry in knowledge.get(entry_type, []):
            desc = entry.get("description", "").lower()
            if any(kw.lower() in desc for kw in keywords):
                return True
    return False


def _count_sources_about(knowledge: dict, keywords: list[str]) -> int:
    """Count distinct sources mentioning keywords."""
    sources = set()
    for entry_type in ("facts", "rumors"):
        for entry in knowledge.get(entry_type, []):
            desc = entry.get("description", "").lower()
            if any(kw.lower() in desc for kw in keywords):
                source = entry.get("source", "unknown")
                sources.add(source)
    return len(sources)


def _npc_trust_at_least(npcs: dict, name: str, min_level: str) -> bool:
    """Check if an NPC's trust is at or above a threshold."""
    levels = ["hostile", "suspicious", "neutral", "cautious_ally", "trusted", "devoted"]
    min_idx = levels.index(min_level) if min_level in levels else 0
    for npc in npcs.get("npcs", []):
        npc_name = npc.get("name", "").lower()
        if name.lower() in npc_name:
            trust = npc.get("trust_level", npc.get("trust", "neutral")).lower()
            trust_idx = levels.index(trust) if trust in levels else 2
            return trust_idx >= min_idx
    return False


def _has_evidence(knowledge: dict, keywords: list[str]) -> bool:
    """Check if evidence matching keywords exists."""
    for entry in knowledge.get("evidence", []):
        desc = (entry.get("description", "") + " " + entry.get("name", "")).lower()
        if any(kw.lower() in desc for kw in keywords):
            return True
    return False


def _trace_discovered(traces: dict, trace_id: str) -> bool:
    """Check if a specific trace has already been discovered."""
    for t in traces.get("discovered", []):
        if t.get("id") == trace_id:
            return True
    return False


def _count_discovered_traces(traces: dict) -> int:
    return len(traces.get("discovered", []))


def _layer_complete(traces: dict, layer: int) -> bool:
    """Check if all traces in a layer are discovered."""
    layer_traces = [t for t in TRACE_CONDITIONS if t["layer"] == layer]
    for t in layer_traces:
        if not _trace_discovered(traces, t["id"]):
            return False
    return True


# ---------------------------------------------------------------------------
# Trace definitions
# ---------------------------------------------------------------------------

TRACE_CONDITIONS: list[dict] = [
    # Layer 1: The Surface
    {
        "id": "TRACE-L1-01",
        "layer": 1,
        "description": "Neo-Kowloon is controlled by NEXUS megacorp",
        "description_zh": "新九龙被NEXUS巨型企业所控制",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["nexus", "控制", "megacorp", "corporation"])
        ),
    },
    {
        "id": "TRACE-L1-02",
        "layer": 1,
        "description": "You have a pre-Severance neural implant",
        "description_zh": "你拥有一个断离前的神经植入体",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["implant", "植入体", "neural", "pre-severance"])
        ),
    },
    {
        "id": "TRACE-L1-03",
        "layer": 1,
        "description": "The Severance happened 30 years ago and killed billions",
        "description_zh": "断离发生在三十年前，数十亿人因此丧生",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["severance", "断离", "30 years", "三十年", "billions"])
        ),
    },
    # Layer 2: The Conspiracy
    {
        "id": "TRACE-L2-01",
        "layer": 2,
        "description": "People who hear the Signal are disappearing",
        "description_zh": "能听到信号的人正在消失",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "mira", "neutral")
            and _has_fact_or_rumor_about(k, ["disappear", "消失", "missing", "signal"])
        ) or _count_sources_about(k, ["disappear", "消失", "missing"]) >= 2,
    },
    {
        "id": "TRACE-L2-02",
        "layer": 2,
        "description": "The Listeners exist and protect Signal-sensitive people",
        "description_zh": "聆听者组织存在，并保护对信号敏感的人",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "mira", "cautious_ally")
            and _has_fact_or_rumor_about(k, ["listener", "聆听者"])
        ),
    },
    {
        "id": "TRACE-L2-03",
        "layer": 2,
        "description": "NEXUS has a secret facility in Sector 7 for 'special acquisitions'",
        "description_zh": "NEXUS在第七区设有秘密设施，用于'特殊征集'",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "ghost", "neutral")
            and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "facility", "acquisitions"])
        ) or (
            p.get("background", "").lower() in ["corporate exile", "企业流亡者"]
            and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "special", "project division"])
            and _count_sources_about(k, ["sector 7", "第七区"]) >= 2
        ),
    },
    {
        "id": "TRACE-L2-04",
        "layer": 2,
        "description": "Your implant is unique pre-Severance tech that shouldn't exist",
        "description_zh": "你的植入体是独一无二的断离前技术，本不应存在",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["unique", "shouldn't exist", "不应该存在"])
            and (
                _npc_trust_at_least(n, "ghost", "neutral")
                or _npc_trust_at_least(n, "patch", "neutral")
                or _has_evidence(k, ["implant analysis", "implant scan"])
            )
        ),
    },
    # Layer 3: The Severance Truth
    {
        "id": "TRACE-L3-01",
        "layer": 3,
        "description": "The Severance wasn't an accident — it was deliberate",
        "description_zh": "断离并非意外——而是蓄意为之",
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["deliberate", "network termination", "severance evidence"])
            and _npc_trust_at_least(n, "ghost", "cautious_ally")
        ),
    },
    {
        "id": "TRACE-L3-02",
        "layer": 3,
        "description": "Something was alive in the network before the Severance",
        "description_zh": "断离之前，网络中有某种存在是活着的",
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["pre-severance logs", "alive", "network entity"])
            and _npc_trust_at_least(n, "patch", "neutral")
        ),
    },
    {
        "id": "TRACE-L3-03",
        "layer": 3,
        "description": "Fragments of something survive in old implants — 'computational resources'",
        "description_zh": "某种存在的碎片留存在旧植入体中——被称为'计算资源'",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["fragment", "碎片", "computational", "survive", "implant"])
            and (
                _npc_trust_at_least(n, "ghost", "trusted")
                or _has_evidence(k, ["nexus archives", "sector 7 lab"])
            )
        ),
    },
    {
        "id": "TRACE-L3-04",
        "layer": 3,
        "description": "NEXUS harvests fragments from people — the disappearances are extraction",
        "description_zh": "NEXUS从人体中收割碎片——那些失踪就是提取行动",
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["extraction", "harvesting", "sector 7"])
            or (
                _count_sources_about(k, ["disappear", "fragment", "nexus", "harvest"]) >= 3
            )
        ),
    },
    # Layer 4: The Mirror
    {
        "id": "TRACE-L4-01",
        "layer": 4,
        "description": "The proto-consciousness grew from human data — our thoughts birthed it",
        "description_zh": "原意识从人类数据中生长——我们的思想孕育了它",
        "check": lambda k, t, n, p, w: (
            _layer_complete(t, 3)
            and _has_fact_or_rumor_about(k, ["architect", "设计者", "proto-consciousness", "human data"])
        ),
    },
    {
        "id": "TRACE-L4-02",
        "layer": 4,
        "description": "Implants transmitted too — human and machine consciousness co-evolved",
        "description_zh": "植入体也在传输——人类与机器意识共同进化",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "patch", "trusted")
            and _has_fact_or_rumor_about(k, ["co-evolved", "transmitted", "bilateral", "bridge"])
        ),
    },
    {
        "id": "TRACE-L4-03",
        "layer": 4,
        "description": "The Severance was an act of fear, not defense",
        "description_zh": "断离是出于恐惧，而非防御",
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["severance", "confession", "fear", "lian"])
            and _npc_trust_at_least(n, "lian", "cautious_ally")
        ),
    },
    # Layer 5: The Full Truth
    {
        "id": "TRACE-L5-01",
        "layer": 5,
        "description": "You are the convergence point — the first true bridge",
        "description_zh": "你是汇聚点——第一座真正的桥梁",
        "check": lambda k, t, n, p, w: (
            _layer_complete(t, 4)
            and _has_fact_or_rumor_about(k, ["convergence", "bridge", "echo", "resonance"])
            and p.get("neural_implant", "").lower() == "resonating"
        ),
    },
    {
        "id": "TRACE-L5-02",
        "layer": 5,
        "description": "The Severance didn't fully kill it — it became part of humanity",
        "description_zh": "断离并未完全杀死它——它已成为人类的一部分",
        "check": lambda k, t, n, p, w: (
            _trace_discovered(t, "TRACE-L5-01")
            and _has_evidence(k, ["architect data", "architect's"])
            and _has_fact_or_rumor_about(k, ["part of humanity", "can't kill", "became"])
        ),
    },
]


# ---------------------------------------------------------------------------
# NEXUS Alert rules
# ---------------------------------------------------------------------------

ALERT_INCREASES: dict[str, int] = {
    "failed_hack": 10,
    "caught_restricted": 15,
    "asking_about_nexus_publicly": 5,
    "stealing_nexus_data": 10,
    "spotted_by_drone": 5,
    "npc_betrayal": 15,
    "entering_sector7_uncovered": 10,
    "attacking_nexus": 20,
}

ALERT_THRESHOLDS: list[dict] = [
    {"threshold": 25, "effect": "Increased patrols in Sector 7 and Chrome Heights", "effect_zh": "第七区和镀金台巡逻增加"},
    {"threshold": 50, "effect": "Sector 7 lockdown, Chrome Heights restricted", "effect_zh": "第七区封锁，镀金台限制出入"},
    {"threshold": 75, "effect": "NEXUS raids Undercroft, Neon Row restricted", "effect_zh": "NEXUS突袭底渊，霓虹街限制出入"},
    {"threshold": 90, "effect": "Full manhunt, only The Sprawl is safe", "effect_zh": "全城搜捕，仅蔓城尚属安全"},
    {"threshold": 100, "effect": "Capture — funneled to Order ending or death", "effect_zh": "被捕——走向秩序结局或死亡"},
]


# ---------------------------------------------------------------------------
# Fragment Decay rules
# ---------------------------------------------------------------------------

DECAY_THRESHOLDS: list[dict] = [
    {"threshold": 25, "effect": "Echo manifestations weaker", "effect_zh": "回响显现减弱"},
    {"threshold": 50, "effect": "Signal artifacts lose potency", "effect_zh": "信号遗物失去效力"},
    {"threshold": 75, "effect": "Good endings much harder", "effect_zh": "好结局变得极其困难"},
    {"threshold": 100, "effect": "Good endings impossible", "effect_zh": "好结局已不可能"},
]


# ---------------------------------------------------------------------------
# Ending conditions
# ---------------------------------------------------------------------------

ENDINGS: list[dict] = [
    {
        "id": "liberation",
        "name": "Liberation",
        "name_zh": "解放",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            w.get("nexus_alert", {}).get("current", 0) > 60
            and _has_fact_or_rumor_about(k, ["attack", "destroy", "nexus facility"])
            and _count_discovered_traces(t) < 12
        ),
    },
    {
        "id": "ascension",
        "name": "Ascension",
        "name_zh": "升华",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            _count_discovered_traces(t) >= 3
            and _has_fact_or_rumor_about(k, ["force-merge", "merge fragments", "merge", "ascend"])
        ),
    },
    {
        "id": "order",
        "name": "Order",
        "name_zh": "秩序",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            (w.get("nexus_alert", {}).get("current", 0) > 80
             and _has_fact_or_rumor_about(k, ["cooperate", "nexus", "cooperation"]))
            or (_npc_trust_at_least(n, "orin", "trusted")
                and _has_fact_or_rumor_about(k, ["cooperate nexus", "orin alliance"]))
        ),
    },
    {
        "id": "purification",
        "name": "Purification",
        "name_zh": "净化",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            _has_fact_or_rumor_about(k, ["purify", "destroy fragment", "lian alliance"])
        ),
    },
    {
        "id": "silence",
        "name": "Silence",
        "name_zh": "沉默",
        "type": "neutral",
        "check": lambda t, w, p, k, n: (
            p.get("turn", 0) >= 100
        ),
    },
    {
        "id": "exile",
        "name": "Exile",
        "name_zh": "流放",
        "type": "neutral",
        "check": lambda t, w, p, k, n: (
            _has_fact_or_rumor_about(k, ["leave neo-kowloon", "exile"])
        ),
    },
    {
        "id": "symbiosis",
        "name": "Symbiosis",
        "name_zh": "共生",
        "type": "good",
        "check": lambda t, w, p, k, n: (
            _count_discovered_traces(t) >= 10
            and _trace_discovered(t, "TRACE-L5-01")
            and _has_evidence(k, ["echo", "communion"])
            and w.get("fragment_decay", {}).get("current", 0) < 40
        ),
    },
    {
        "id": "the_bridge",
        "name": "The Bridge",
        "name_zh": "桥",
        "type": "good",
        "check": lambda t, w, p, k, n: (
            _count_discovered_traces(t) >= 16
            and _trace_discovered(t, "TRACE-L5-02")
            and _has_evidence(k, ["architect", "echo communion", "resonance chamber"])
            and w.get("fragment_decay", {}).get("current", 0) < 25
        ),
    },
]


# ---------------------------------------------------------------------------
# Time system
# ---------------------------------------------------------------------------

TIME_PERIODS = ["Morning", "Afternoon", "Night"]
TIME_PERIODS_ZH = ["晨", "午", "夜"]
TURNS_PER_PERIOD = 3

# Each period spans this many in-world minutes (6:00–12:00, 12:00–18:00, 18:00–6:00)
MINUTES_PER_PERIOD = 360  # 6 hours

# Period start hours (24h format) for display and narrative sync
PERIOD_START_HOUR = {"Morning": 6, "Afternoon": 12, "Night": 18}
PERIOD_START_HOUR_ZH = {"晨": 6, "午": 12, "夜": 18}


def get_localized(data: dict, key: str, lang: str):
    """Pick the language-appropriate variant of a field.

    Looks for ``key_zh`` when *lang* is ``"zh"``, falls back to *key*.
    """
    if lang == "zh":
        zh_key = f"{key}_zh"
        if zh_key in data:
            return data[zh_key]
    return data[key]


# ---------------------------------------------------------------------------
# District definitions
# ---------------------------------------------------------------------------

DISTRICTS: dict[str, dict] = {
    "The Sprawl": {
        "zh": "蔓城",
        "access": "Open",
        "signal_range": (5, 15),
    },
    "Neon Row": {
        "zh": "霓虹街",
        "access": "Open",
        "signal_range": (10, 25),
    },
    "The Undercroft": {
        "zh": "底渊",
        "access": "Locked",
        "unlock_trace": "TRACE-L1-03",
        "signal_range": (40, 70),
    },
    "Sector 7": {
        "zh": "第七区",
        "access": "Restricted",
        "signal_range": (15, 30),
    },
    "The Resonance": {
        "zh": "共鸣所",
        "access": "Hidden",
        "unlock_layer": 3,
        "signal_range": (80, 100),
    },
    "The Spire": {
        "zh": "尖塔",
        "access": "Locked",
        "unlock_layer": 4,
        "signal_range": (30, 50),
    },
}


# ---------------------------------------------------------------------------
# Probability check difficulties
# ---------------------------------------------------------------------------

DIFFICULTY_TARGETS: dict[str, int] = {
    "easy": 80,
    "normal": 60,
    "hard": 40,
    "very_hard": 20,
    "near_impossible": 10,
}


# ---------------------------------------------------------------------------
# Item-skill bonuses and penalties
# ---------------------------------------------------------------------------

ITEM_SKILL_BONUSES: dict[str, dict] = {
    "lockpick": {"item_keyword": "lockpick", "bonus": 15, "description": "Lockpick Set provides +15 to lock checks"},
    "hack": {"item_keyword": "cipher", "bonus": 10, "description": "Cipher Toolkit provides +10 to hacking checks"},
    "stealth_sector7": {"item_keyword": "keycard", "bonus": 30, "description": "NEXUS Keycard provides +30 to Sector 7 entry"},
}

ITEM_SKILL_PENALTIES: dict[str, dict] = {
    "lockpick": {"penalty": -20, "description": "Without a Lockpick Set, lock checks are much harder (-20)"},
    "hack": {"penalty": -10, "description": "Without a Cipher Toolkit, hacking is harder (-10)"},
}


# ---------------------------------------------------------------------------
# Difficulty-scaled trace condition overrides
# Tighter conditions for standard/reckless difficulties
# ---------------------------------------------------------------------------

TRACE_DIFFICULTY_OVERRIDES: dict[str, dict] = {
    "standard": {
        "TRACE-L2-01": lambda k, t, n, p, w: (
            # Require evidence or 3+ sources, not just a single rumor
            _has_evidence(k, ["disappear", "missing", "signal"])
            or (_count_sources_about(k, ["disappear", "missing"]) >= 3)
        ),
        "TRACE-L2-03": lambda k, t, n, p, w: (
            # Require sector7 evidence — obtained by paying Ghost or decrypting cipher
            _has_evidence(k, ["sector", "facility", "acquisition"])
        ),
        "TRACE-L2-04": lambda k, t, n, p, w: (
            # Require analyze_signal usage on implant
            _has_evidence(k, ["implant", "unique", "pre-severance"])
        ),
    },
    "reckless": {
        "TRACE-L2-01": lambda k, t, n, p, w: (
            _has_evidence(k, ["disappear", "missing", "signal"])
            and _count_sources_about(k, ["disappear", "missing"]) >= 3
        ),
        "TRACE-L2-03": lambda k, t, n, p, w: (
            _has_evidence(k, ["sector", "facility"])
            and _npc_trust_at_least(n, "ghost", "cautious_ally")
        ),
        "TRACE-L2-04": lambda k, t, n, p, w: (
            _has_evidence(k, ["implant", "unique"])
            and _has_evidence(k, ["analysis", "scan", "resonance"])
        ),
        "TRACE-L3-01": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "ghost", "trusted")
            and _has_evidence(k, ["severance", "deliberate"])
            and _has_fact_or_rumor_about(k, ["sector 7"])
        ),
        "TRACE-L3-02": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "patch", "cautious_ally")
            and _has_evidence(k, ["alive", "network", "entity"])
            and _has_evidence(k, ["resonance", "signal"])
        ),
    },
}
