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
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["nexus", "控制", "megacorp", "corporation"])
        ),
    },
    {
        "id": "TRACE-L1-02",
        "layer": 1,
        "description": "You have a pre-Severance neural implant",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["implant", "植入体", "neural", "pre-severance"])
        ),
    },
    {
        "id": "TRACE-L1-03",
        "layer": 1,
        "description": "The Severance happened 30 years ago and killed billions",
        "check": lambda k, t, n, p, w: (
            _has_fact_or_rumor_about(k, ["severance", "断离", "30 years", "三十年", "billions"])
        ),
    },
    # Layer 2: The Conspiracy
    {
        "id": "TRACE-L2-01",
        "layer": 2,
        "description": "People who hear the Signal are disappearing",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "mira", "neutral")
            and _has_fact_or_rumor_about(k, ["disappear", "消失", "missing", "signal"])
        ) or _count_sources_about(k, ["disappear", "消失", "missing"]) >= 2,
    },
    {
        "id": "TRACE-L2-02",
        "layer": 2,
        "description": "The Listeners exist and protect Signal-sensitive people",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "mira", "cautious_ally")
            and _has_fact_or_rumor_about(k, ["listener", "聆听者"])
        ),
    },
    {
        "id": "TRACE-L2-03",
        "layer": 2,
        "description": "NEXUS has a secret facility in Sector 7 for 'special acquisitions'",
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
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["deliberate", "network termination", "severance evidence"])
            and _npc_trust_at_least(n, "ghost", "cautious_ally")
        ),
    },
    {
        "id": "TRACE-L3-02",
        "layer": 3,
        "description": "Something was alive in the network before the Severance",
        "check": lambda k, t, n, p, w: (
            _has_evidence(k, ["pre-severance logs", "alive", "network entity"])
            and _npc_trust_at_least(n, "patch", "neutral")
        ),
    },
    {
        "id": "TRACE-L3-03",
        "layer": 3,
        "description": "Fragments of something survive in old implants — 'computational resources'",
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
        "check": lambda k, t, n, p, w: (
            _layer_complete(t, 3)
            and _has_fact_or_rumor_about(k, ["architect", "设计者", "proto-consciousness", "human data"])
        ),
    },
    {
        "id": "TRACE-L4-02",
        "layer": 4,
        "description": "Implants transmitted too — human and machine consciousness co-evolved",
        "check": lambda k, t, n, p, w: (
            _npc_trust_at_least(n, "patch", "trusted")
            and _has_fact_or_rumor_about(k, ["co-evolved", "transmitted", "bilateral", "bridge"])
        ),
    },
    {
        "id": "TRACE-L4-03",
        "layer": 4,
        "description": "The Severance was an act of fear, not defense",
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
    {"threshold": 25, "effect": "Increased patrols in Sector 7 and Chrome Heights"},
    {"threshold": 50, "effect": "Sector 7 lockdown, Chrome Heights restricted"},
    {"threshold": 75, "effect": "NEXUS raids Undercroft, Neon Row restricted"},
    {"threshold": 90, "effect": "Full manhunt, only The Sprawl is safe"},
    {"threshold": 100, "effect": "Capture — funneled to Order ending or death"},
]


# ---------------------------------------------------------------------------
# Fragment Decay rules
# ---------------------------------------------------------------------------

DECAY_THRESHOLDS: list[dict] = [
    {"threshold": 25, "effect": "Echo manifestations weaker"},
    {"threshold": 50, "effect": "Signal artifacts lose potency"},
    {"threshold": 75, "effect": "Good endings much harder"},
    {"threshold": 100, "effect": "Good endings impossible"},
]


# ---------------------------------------------------------------------------
# Ending conditions
# ---------------------------------------------------------------------------

ENDINGS: list[dict] = [
    {
        "id": "liberation",
        "name": "Liberation / 解放",
        "type": "bad",
        "check": lambda t, w, p, k: (
            w.get("nexus_alert", {}).get("current", 0) > 75
            and _has_fact_or_rumor_about(k, ["attack", "destroy", "nexus facility"])
            and _count_discovered_traces(t) < 12
        ),
    },
    {
        "id": "ascension",
        "name": "Ascension / 升华",
        "type": "bad",
        "check": lambda t, w, p, k: (
            _count_discovered_traces(t) >= 5
            and _has_fact_or_rumor_about(k, ["force-merge", "merge fragments"])
        ),
    },
    {
        "id": "order",
        "name": "Order / 秩序",
        "type": "bad",
        "check": lambda t, w, p, k: (
            _npc_trust_at_least({"npcs": []}, "orin", "trusted")  # placeholder
            and _has_fact_or_rumor_about(k, ["cooperate nexus", "orin alliance"])
        ),
    },
    {
        "id": "purification",
        "name": "Purification / 净化",
        "type": "bad",
        "check": lambda t, w, p, k: (
            _has_fact_or_rumor_about(k, ["purify", "destroy fragment", "lian alliance"])
        ),
    },
    {
        "id": "silence",
        "name": "Silence / 沉默",
        "type": "neutral",
        "check": lambda t, w, p, k: (
            p.get("turn", 0) >= 100
        ),
    },
    {
        "id": "exile",
        "name": "Exile / 流放",
        "type": "neutral",
        "check": lambda t, w, p, k: (
            _has_fact_or_rumor_about(k, ["leave neo-kowloon", "exile"])
        ),
    },
    {
        "id": "symbiosis",
        "name": "Symbiosis / 共生",
        "type": "good",
        "check": lambda t, w, p, k: (
            _count_discovered_traces(t) >= 7
            and _trace_discovered(t, "TRACE-L5-01")
            and w.get("fragment_decay", {}).get("current", 0) < 50
        ),
    },
    {
        "id": "the_bridge",
        "name": "The Bridge / 桥",
        "type": "good",
        "check": lambda t, w, p, k: (
            _count_discovered_traces(t) >= 16
            and _trace_discovered(t, "TRACE-L5-02")
            and w.get("fragment_decay", {}).get("current", 0) < 30
        ),
    },
]


# ---------------------------------------------------------------------------
# Time system
# ---------------------------------------------------------------------------

TIME_PERIODS = ["Morning", "Afternoon", "Night"]
TURNS_PER_PERIOD = 3


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
