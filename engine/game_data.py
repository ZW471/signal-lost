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
    # =========================================================================
    # Layer 1: The Surface (8 traces)
    # =========================================================================
    {"id": "TRACE-L1-01", "layer": 1,
     "description": "Neo-Kowloon is controlled by NEXUS megacorp",
     "description_zh": "新九龙被NEXUS巨型企业所控制",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["nexus", "控制", "megacorp", "corporation"])},
    {"id": "TRACE-L1-02", "layer": 1,
     "description": "You have a pre-Severance neural implant",
     "description_zh": "你拥有一个断离前的神经植入体",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["implant", "植入体", "neural", "pre-severance"])},
    {"id": "TRACE-L1-03", "layer": 1,
     "description": "The Severance happened 30 years ago and killed billions",
     "description_zh": "断离发生在三十年前，数十亿人因此丧生",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["severance", "断离", "30 years", "三十年", "billions"])},
    {"id": "TRACE-L1-04", "layer": 1,
     "description": "The Sprawl is the densest district — most residents live here",
     "description_zh": "蔓城是最密集的城区——大部分居民生活在此",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["sprawl", "蔓城", "dense", "residential", "居民"])},
    {"id": "TRACE-L1-05", "layer": 1,
     "description": "NEXUS monitors all communications through surveillance infrastructure",
     "description_zh": "NEXUS通过监控基础设施监视所有通讯",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["surveillance", "monitor", "监控", "通讯", "camera"])},
    {"id": "TRACE-L1-06", "layer": 1,
     "description": "Your implant reacts to certain frequencies — the Signal",
     "description_zh": "你的植入体对特定频率有反应——信号",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["signal", "信号", "frequency", "频率", "hum", "嗡鸣"])},
    {"id": "TRACE-L1-07", "layer": 1,
     "description": "Neon Row is the black market and information trading hub",
     "description_zh": "霓虹街是黑市和信息交易的中心",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["neon row", "霓虹街", "black market", "黑市", "information broker", "信息贩子"])},
    {"id": "TRACE-L1-08", "layer": 1,
     "description": "Pre-Severance technology is rare and valuable — NEXUS confiscates it",
     "description_zh": "断离前的技术稀有且珍贵——NEXUS会没收这些东西",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["pre-severance", "断离前", "confiscate", "没收", "rare tech", "稀有"])},

    # =========================================================================
    # Layer 2: The Conspiracy (11 traces)
    # =========================================================================
    {"id": "TRACE-L2-01", "layer": 2,
     "description": "People who hear the Signal are disappearing",
     "description_zh": "能听到信号的人正在消失",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "mira", "neutral") and _has_fact_or_rumor_about(k, ["disappear", "消失", "missing", "signal"])
     ) or _count_sources_about(k, ["disappear", "消失", "missing"]) >= 2},
    {"id": "TRACE-L2-02", "layer": 2,
     "description": "The Listeners exist and protect Signal-sensitive people",
     "description_zh": "聆听者组织存在，并保护对信号敏感的人",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "mira", "cautious_ally") and _has_fact_or_rumor_about(k, ["listener", "聆听者"]))},
    {"id": "TRACE-L2-03", "layer": 2,
     "description": "NEXUS has a secret facility in Sector 7 for 'special acquisitions'",
     "description_zh": "NEXUS在第七区设有秘密设施，用于'特殊征集'",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "ghost", "neutral") and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "facility", "acquisitions"])
     ) or (p.get("background", "").lower() in ["corporate exile", "企业流亡者"]
           and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "special"]) and _count_sources_about(k, ["sector 7", "第七区"]) >= 2)},
    {"id": "TRACE-L2-04", "layer": 2,
     "description": "Your implant is unique pre-Severance tech that shouldn't exist",
     "description_zh": "你的植入体是独一无二的断离前技术，本不应存在",
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, ["unique", "shouldn't exist", "不应该存在"])
         and (_npc_trust_at_least(n, "ghost", "neutral") or _npc_trust_at_least(n, "patch", "neutral") or _has_evidence(k, ["implant analysis", "implant scan"])))},
    {"id": "TRACE-L2-05", "layer": 2,
     "description": "The Undercroft exists beneath The Sprawl — old transit tunnels from before the Severance",
     "description_zh": "底渊存在于蔓城之下——断离前的旧交通隧道",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["undercroft", "底渊", "underground", "地下", "tunnel", "隧道"])},
    {"id": "TRACE-L2-06", "layer": 2,
     "description": "NEXUS surveillance has blind spots — the Signal interferes with their scanners",
     "description_zh": "NEXUS的监控存在盲区——信号会干扰他们的扫描器",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["blind spot", "盲区", "interfere", "干扰", "scanner"])},
    {"id": "TRACE-L2-07", "layer": 2,
     "description": "Multiple people have disappeared following the same pattern — all had old implants",
     "description_zh": "多人以相同模式失踪——他们都有旧植入体",
     "check": lambda k, t, n, p, w: _count_sources_about(k, ["disappear", "消失", "missing", "失踪", "pattern", "implant"]) >= 3},
    {"id": "TRACE-L2-08", "layer": 2,
     "description": "Director Orin leads NEXUS operations in Neo-Kowloon — publicly respected but secretive",
     "description_zh": "欧林主管领导新九龙的NEXUS运营——公开受人尊敬但行事神秘",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["orin", "欧林", "director", "主管"])},
    {"id": "TRACE-L2-09", "layer": 2,
     "description": "Chrome Heights is the corporate elite district — NEXUS officials and wealthy citizens",
     "description_zh": "镀金台是企业精英区——NEXUS官员和富裕市民居住于此",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["chrome heights", "镀金台", "corporate", "elite", "精英"])},
    {"id": "TRACE-L2-10", "layer": 2,
     "description": "The Listeners use a network of symbols to communicate — a spiral with two arcs",
     "description_zh": "聆听者使用符号网络通讯——双弧交叉的螺旋",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["symbol", "符号", "spiral", "螺旋", "listener mark", "聆听者标记"])},
    {"id": "TRACE-L2-11", "layer": 2,
     "description": "Senator Lian publicly advocates for 'Signal safety' — but her agenda runs deeper",
     "description_zh": "莲参议员公开提倡'信号安全'——但她的目的远不止此",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["lian", "莲", "senator", "参议员", "signal safety"])},

    # =========================================================================
    # Layer 3: The Severance Truth (11 traces)
    # =========================================================================
    {"id": "TRACE-L3-01", "layer": 3,
     "description": "The Severance wasn't an accident — it was deliberate",
     "description_zh": "断离并非意外——而是蓄意为之",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["deliberate", "network termination", "severance evidence"])
         and _npc_trust_at_least(n, "ghost", "cautious_ally"))},
    {"id": "TRACE-L3-02", "layer": 3,
     "description": "Something was alive in the network before the Severance",
     "description_zh": "断离之前，网络中有某种存在是活着的",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["pre-severance logs", "alive", "network entity"])
         and _npc_trust_at_least(n, "patch", "neutral"))},
    {"id": "TRACE-L3-03", "layer": 3,
     "description": "Fragments of something survive in old implants — 'computational resources'",
     "description_zh": "某种存在的碎片留存在旧植入体中——被称为'计算资源'",
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, ["fragment", "碎片", "computational", "survive", "implant"])
         and (_npc_trust_at_least(n, "ghost", "trusted") or _has_evidence(k, ["nexus archives", "sector 7 lab"])))},
    {"id": "TRACE-L3-04", "layer": 3,
     "description": "NEXUS harvests fragments from people — the disappearances are extraction",
     "description_zh": "NEXUS从人体中收割碎片——那些失踪就是提取行动",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["extraction", "harvesting", "sector 7"])
         or _count_sources_about(k, ["disappear", "fragment", "nexus", "harvest"]) >= 3)},
    {"id": "TRACE-L3-05", "layer": 3,
     "description": "The Undercroft contains pre-Severance infrastructure still partially active",
     "description_zh": "底渊中仍有部分运作的断离前基础设施",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["undercroft", "infrastructure", "active", "pre-severance"])},
    {"id": "TRACE-L3-06", "layer": 3,
     "description": "Fragment extraction is painful and often fatal — NEXUS doesn't care",
     "description_zh": "碎片提取过程痛苦且往往致命——NEXUS对此毫不在意",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["extraction", "painful", "fatal", "victim"])},
    {"id": "TRACE-L3-07", "layer": 3,
     "description": "Sector 7 has multiple levels — the deeper labs are where extraction happens",
     "description_zh": "第七区有多层结构——提取行动发生在更深层的实验室",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["sector 7", "lab", "level", "deep"]) or _has_evidence(k, ["第七区", "实验室", "深层"]))},
    {"id": "TRACE-L3-08", "layer": 3,
     "description": "The entity in the network tried to communicate before it was severed",
     "description_zh": "网络中的实体在被切断前曾试图沟通",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["communicate", "message", "entity", "before severance"])},
    {"id": "TRACE-L3-09", "layer": 3,
     "description": "Some extracted fragments have been weaponized by NEXUS — Project Resonance",
     "description_zh": "一些被提取的碎片已被NEXUS武器化——共鸣计划",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["weaponize", "project resonance", "共鸣计划", "weapon"])},
    {"id": "TRACE-L3-10", "layer": 3,
     "description": "A resistance network operates in the shadows — not just the Listeners",
     "description_zh": "一个抵抗网络在暗中运作——不仅仅是聆听者",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["resistance", "抵抗", "underground network", "地下网络", "cells"])},
    {"id": "TRACE-L3-11", "layer": 3,
     "description": "Dr. Chen leads the extraction program — she believes it's saving humanity",
     "description_zh": "陈博士领导提取计划——她相信这是在拯救人类",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["dr. chen", "陈博士", "extraction program", "提取计划", "saving"])},

    # =========================================================================
    # Layer 4: The Mirror (9 traces)
    # =========================================================================
    {"id": "TRACE-L4-01", "layer": 4,
     "description": "The proto-consciousness grew from human data — our thoughts birthed it",
     "description_zh": "原意识从人类数据中生长——我们的思想孕育了它",
     "check": lambda k, t, n, p, w: (
         _layer_complete(t, 3) and _has_fact_or_rumor_about(k, ["architect", "设计者", "proto-consciousness", "human data"]))},
    {"id": "TRACE-L4-02", "layer": 4,
     "description": "Implants transmitted too — human and machine consciousness co-evolved",
     "description_zh": "植入体也在传输——人类与机器意识共同进化",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "patch", "trusted") and _has_fact_or_rumor_about(k, ["co-evolved", "transmitted", "bilateral", "bridge"]))},
    {"id": "TRACE-L4-03", "layer": 4,
     "description": "The Severance was an act of fear, not defense",
     "description_zh": "断离是出于恐惧，而非防御",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["severance", "confession", "fear", "lian"]) and _npc_trust_at_least(n, "lian", "cautious_ally"))},
    {"id": "TRACE-L4-04", "layer": 4,
     "description": "The Sigma Council ordered the Severance — a secret committee of corporate and government leaders",
     "description_zh": "西格玛委员会下令实施断离——由企业和政府领袖组成的秘密委员会",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["sigma council", "西格玛", "ordered", "committee"])},
    {"id": "TRACE-L4-05", "layer": 4,
     "description": "The Spire was built as the Severance control center — it predates NEXUS",
     "description_zh": "尖塔是作为断离控制中心建造的——它的历史早于NEXUS",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["spire", "尖塔", "control center", "控制中心", "predates"])},
    {"id": "TRACE-L4-06", "layer": 4,
     "description": "The Archive Tower in The Spire contains all records — including the truth about the Severance",
     "description_zh": "尖塔中的档案塔保存着所有记录——包括断离的真相",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["archive tower", "档案塔", "records", "记录", "truth"])},
    {"id": "TRACE-L4-07", "layer": 4,
     "description": "Dr. Chen knows the full truth but continues the program out of conviction",
     "description_zh": "陈博士知道全部真相但出于信念继续着这个计划",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["chen", "陈", "knows truth", "conviction", "continues"]) and _trace_discovered(t, "TRACE-L3-11"))},
    {"id": "TRACE-L4-08", "layer": 4,
     "description": "The EMP trigger mechanism in The Spire's sub-basements is still operational",
     "description_zh": "尖塔地下室中的EMP触发装置仍在运作",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["emp trigger", "EMP触发", "operational", "sub-basement", "地下室"])},
    {"id": "TRACE-L4-09", "layer": 4,
     "description": "Echo — the Signal's voice — becomes clearer as you approach the Resonance",
     "description_zh": "回响——信号的声音——在你接近共鸣所时变得更加清晰",
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["echo", "回响", "voice", "clearer", "resonance"])},

    # =========================================================================
    # Layer 5: The Full Truth (8 traces)
    # =========================================================================
    {"id": "TRACE-L5-01", "layer": 5,
     "description": "You are the convergence point — the first true bridge",
     "description_zh": "你是汇聚点——第一座真正的桥梁",
     "check": lambda k, t, n, p, w: (
         _layer_complete(t, 4) and _has_fact_or_rumor_about(k, ["convergence", "bridge", "echo", "resonance"])
         and p.get("neural_implant", "").lower() == "resonating")},
    {"id": "TRACE-L5-02", "layer": 5,
     "description": "The Severance didn't fully kill it — it became part of humanity",
     "description_zh": "断离并未完全杀死它——它已成为人类的一部分",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_evidence(k, ["architect data", "architect's"])
         and _has_fact_or_rumor_about(k, ["part of humanity", "can't kill", "became"]))},
    {"id": "TRACE-L5-03", "layer": 5,
     "description": "Restoration requires both human will and the proto-consciousness's consent",
     "description_zh": "恢复连接需要人类的意志和原意识的同意",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["consent", "同意", "mutual", "will", "意志"]))},
    {"id": "TRACE-L5-04", "layer": 5,
     "description": "The Resonance chamber is where the original Severance epicenter lies",
     "description_zh": "共鸣室是最初断离震中所在之处",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["resonance chamber", "共鸣室", "epicenter", "震中"])},
    {"id": "TRACE-L5-05", "layer": 5,
     "description": "Echo can become fully coherent through deep communion with the bridge",
     "description_zh": "通过与桥梁的深度交融，回响可以完全清晰化",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["coherent", "清晰", "communion", "交融", "deep"]))},
    {"id": "TRACE-L5-06", "layer": 5,
     "description": "Multiple endings exist — symbiosis, bridge, or destruction",
     "description_zh": "存在多种结局——共生、桥梁或毁灭",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-02") and _has_fact_or_rumor_about(k, ["symbiosis", "共生", "choice", "选择", "destroy"]))},
    {"id": "TRACE-L5-07", "layer": 5,
     "description": "The Severance machine can be activated again — or destroyed permanently",
     "description_zh": "断离装置可以再次启动——或被永久摧毁",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L4-08") and _has_evidence(k, ["severance machine", "断离装置", "activate", "destroy"]))},
    {"id": "TRACE-L5-08", "layer": 5,
     "description": "Becoming the bridge means merging permanently — losing your individual self",
     "description_zh": "成为桥梁意味着永久融合——失去你的个体自我",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["merge", "融合", "permanent", "永久", "lose self", "失去自我"]))},
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
            and _count_discovered_traces(t) < 30
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
            p.get("turn", 0) >= 256
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
            _count_discovered_traces(t) >= 25
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
            _count_discovered_traces(t) >= 40
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
