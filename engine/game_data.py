"""
Signal Lost — Extracted Game Data

Structured game data extracted from agent/game.md and game/*.md.
Used by deterministic Python nodes (trace_checker, world_ticker, consequence).
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Trace discovery conditions
# Each trace has an ID, description, layer, and a checker function.
# The checker receives (knowledge, traces, npcs, player, world_state)
# and returns True if the trace should be discovered.
# ---------------------------------------------------------------------------

# All recorded knowledge channels feed trace discovery. The model logs
# investigation findings as facts, rumors, evidence, theories, or connections
# fairly interchangeably, so scanning only facts/rumors left traces frozen while
# a rich investigation (lots of evidence/theories) made no trace progress.
_KNOWLEDGE_TYPES = ("facts", "rumors", "evidence", "theories", "connections")


def _entry_text(entry: dict) -> str:
    """All searchable text on a knowledge entry (description/statement/name)."""
    parts = (entry.get("description"), entry.get("statement"), entry.get("name"))
    return " ".join(str(p) for p in parts if p).lower()


def _has_fact_or_rumor_about(knowledge: dict, keywords: list[str]) -> bool:
    """True if ANY recorded knowledge entry mentions any keyword."""
    kws = [kw.lower() for kw in keywords]
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if any(kw in text for kw in kws):
                return True
    return False


def _count_sources_about(knowledge: dict, keywords: list[str]) -> int:
    """Count distinct sources/entries across all knowledge mentioning keywords."""
    kws = [kw.lower() for kw in keywords]
    sources = set()
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if any(kw in text for kw in kws):
                sources.add(entry.get("source") or entry.get("id") or text[:40])
    return len(sources)


# Canonical NPC names ↔ their localized forms, so trust gates match in zh too.
_NPC_ALIASES = {
    "mira": ["mira", "米拉"],
    "ghost": ["ghost", "幽灵"],
    "orin": ["orin", "欧林", "奥林"],
    "patch": ["patch", "补丁", "帕奇"],
    "lian": ["lian", "莲", "连"],
    "echo": ["echo", "回声", "回响"],
    "architect": ["architect", "建筑师", "设计者", "shen wei", "沈卫"],
    "chen": ["chen", "陈"],
}

# Localized trust labels → canonical level.
_TRUST_ALIASES = {
    "敌对": "hostile", "怀疑": "suspicious", "戒备": "suspicious", "可疑": "suspicious",
    "中立": "neutral", "谨慎盟友": "cautious_ally", "谨慎": "cautious_ally", "盟友": "cautious_ally",
    "信任": "trusted", "受信任": "trusted", "忠诚": "devoted", "效忠": "devoted",
}


def _npc_trust_at_least(npcs: dict, name: str, min_level: str) -> bool:
    """Check if an NPC's trust is at or above a threshold (bilingual).

    Scans ALL matching entries and uses the HIGHEST trust found — npcs.json can
    hold more than one entry for the same person (a `neutral` placeholder created
    when they're first seen, plus the real entry once trust is earned). Returning
    on the first match read the stale placeholder and reported False even after
    the player earned full trust, permanently blocking trust-gated traces
    (e.g. TRACE-L4-02)."""
    levels = ["hostile", "suspicious", "neutral", "cautious_ally", "trusted", "devoted"]
    min_idx = levels.index(min_level) if min_level in levels else 0
    aliases = _NPC_ALIASES.get(name.lower(), [name.lower()])
    best_idx = None
    for npc in npcs.get("npcs", []):
        npc_name = str(npc.get("name", "")).lower()
        if any(a in npc_name for a in aliases):
            trust = str(npc.get("trust_level", npc.get("trust", "neutral"))).lower()
            trust = _TRUST_ALIASES.get(trust, trust)
            trust_idx = levels.index(trust) if trust in levels else 2
            best_idx = trust_idx if best_idx is None else max(best_idx, trust_idx)
    return best_idx is not None and best_idx >= min_idx


def _has_evidence(knowledge: dict, keywords: list[str]) -> bool:
    """True if ANY recorded knowledge (facts/rumors/evidence/theories/connections)
    matches a keyword.

    The model records investigation findings as FACTS (via the `record` channel)
    far more often than as formal `evidence`, so the many evidence-gated deep
    traces (L3/L4/L5) must scan all channels — otherwise they never fire even when
    the player has clearly reached the lore, walling off the good endings."""
    kws = [kw.lower() for kw in keywords]
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            if any(kw in _entry_text(entry) for kw in kws):
                return True
    return False


# TRACE-L2-02 route (b): who-protects-whom matching (wave 4 review). The old
# bag-of-words co-occurrence ("hide"/"hidden"/"guard" anywhere + a Signal-
# sensitive phrase anywhere) fired on ordinary self-hiding notes and even on
# NEXUS-threat descriptions ("NEXUS vans hunt the ones who hear the hum;
# nowhere left to hide"), leaking the anti-spoiler-gated faction. The verbs are
# now strong agentive protect-verbs only, and the verb must GOVERN the
# Signal-sensitive phrase (appear shortly before it in the same entry).
_PROTECT_VERBS: list[str] = [
    "protect", "shelter", "shield", "harbor", "harbour",
    "保护", "庇护", "守护", "收留",
]
_SIGNAL_SENSITIVE_PHRASES: list[str] = [
    "signal-sensitive", "signal sensitive", "sensitive to the signal",
    "hear the signal", "hears the signal", "who hear it", "hear the hum",
    "信号敏感", "对信号敏感", "能听到信号", "听得到信号", "听见信号",
]


def _protects_signal_sensitives(knowledge: dict) -> bool:
    """True when a SINGLE knowledge entry records a third party protecting the
    Signal-sensitive — i.e. a protect-verb that grammatically governs the
    Signal-sensitive phrase (verb first, phrase within a short window after it).

    Two subject exclusions keep the common inversions from firing the trace:
    the player protecting THEMSELVES ("protect myself because I hear the
    signal") and NEXUS as the protector ("NEXUS protects its facility from
    those who hear it")."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            for verb in _PROTECT_VERBS:
                start = 0
                while True:
                    i = text.find(verb, start)
                    if i < 0:
                        break
                    start = i + 1
                    # NEXUS-as-protector inversion — not the faction reveal.
                    if text[max(0, i - 12):i].rstrip().endswith("nexus"):
                        continue
                    # Self-protection ("protect myself / 保护自己") — the object
                    # right after the verb is the player, not the sensitives.
                    head = text[i + len(verb): i + len(verb) + 12]
                    if any(obj in " " + head for obj in
                           (" myself", " me ", " me,", " me.", " me;", "自己", "我")):
                        continue
                    # The protect verb must govern the phrase: within ~80 chars
                    # AFTER the verb, same entry.
                    window = text[i: i + len(verb) + 80]
                    if any(ph in window for ph in
                           (p.lower() for p in _SIGNAL_SENSITIVE_PHRASES)):
                        return True
    return False


# TRACE-L3-07 co-occurrence gate (playtest wave 6, friction #3a): the old check
# fired on ANY entry containing the bare word "level" — the opening's "street
# level Neo-Kowloon" unlocked a Layer-3 trace on turn 1 and inflated the
# deepest-layer stat. A depth term must now co-occur with Sector-7 / lab
# context in the SAME entry. "lab" is boundary-matched so "label" / "available"
# don't count as lab context.
_S7_CONTEXT_RE = re.compile(
    r"sector\s*-?\s*7|sector\s+seven|(?<![a-z])labs?(?![a-z])|laborator|七区|实验室")
_S7_DEPTH_RE = re.compile(
    r"(?<![a-z])(?:level|deep|layer|storey|sub-?basement|underground)"
    r"|多层|深层|层级|下层|地下|底层|楼层|层楼")


def _sector7_depth_in_one_entry(knowledge: dict) -> bool:
    """True when a SINGLE knowledge entry pairs Sector-7/lab context with a
    depth/level term (TRACE-L3-07)."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if _S7_CONTEXT_RE.search(text) and _S7_DEPTH_RE.search(text):
                return True
    return False


# TRACE-L4-06 co-occurrence gate (playtest wave 10, friction #3): the old check
# fired on ANY entry containing "records"/"记录" — 中文 turn 2's mundane "公共
# 终端免费使用，但可能会留下记录" ("the public terminal keeps records") pushed
# deepest_layer to L4 two turns in. Same pattern as the L3-07 gate: the
# archive/records/truth term must co-occur with a Spire/Tower locator in the
# SAME entry. "档案塔" satisfies both halves by itself (it IS the named place);
# bare surveillance-log "记录" stays Layer-1 scenery. 真相 added for EN "truth"
# parity (wave 10, friction #2).
_L406_ARCHIVE_RE = re.compile(
    r"(?<![a-z])(?:archives?|records?|truth)(?![a-z])|档案|记录|真相")
_L406_SPIRE_RE = re.compile(
    r"(?<![a-z])(?:spire|tower)(?![a-z])|尖塔|高塔|塔楼|档案塔")


def _archive_tower_in_one_entry(knowledge: dict) -> bool:
    """True when a SINGLE knowledge entry pairs an archive/records/truth term
    with a Spire/Tower locator (TRACE-L4-06)."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if _L406_ARCHIVE_RE.search(text) and _L406_SPIRE_RE.search(text):
                return True
    return False


# Act-on-evidence discovery route (playtest wave 6, friction #3b). Discovery
# cadence was front-loaded keyword luck: by T11-20 the trace panel barely moved
# even for players actively decrypting/analyzing/scanning what they found — the
# very acts the teaching suggestions push. Entries born from those tool acts
# are recognizable: the resolver records them with the act named in the entry
# text or its `source` field (real wave-6 sessions: source "M-17 passive signal
# scan", "S7-INTAKE signal analysis", "服务巷Signal残壳分析"). Selected mid-layer
# traces below take an OR-branch through _acted_on_evidence() so acting on
# evidence keeps the panel moving without loosening the conversational gates.
_ACT_MARKERS: list[str] = [
    "decrypt", "decipher", "decode", "analys", "analyz", "scan", "probe",
    "presented", "present the evidence", "resonance reading",
    "解密", "破译", "解码", "分析", "解析", "扫描", "探测", "出示", "呈交",
]


def _acted_on_evidence(knowledge: dict, topic_keywords: list[str]) -> bool:
    """True when a single knowledge entry records the RESULT of a player act
    (decrypt / analyze / scan / present — named in the entry text or its
    `source` field) AND mentions the topic in the same entry."""
    kws = [kw.lower() for kw in topic_keywords]
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            src = str(entry.get("source") or "").lower()
            if not any(m in text or m in src for m in _ACT_MARKERS):
                continue
            if any(kw in text for kw in kws):
                return True
    return False


def _acted_on_evidence_re(knowledge: dict, topic_re: re.Pattern) -> bool:
    """Regex-topic variant of _acted_on_evidence, for topics whose natural
    keywords are common words ("spoke", "static") that need word-boundary
    anchoring and/or same-clause context to avoid firing on scene dressing."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            src = str(entry.get("source") or "").lower()
            if not any(m in text or m in src for m in _ACT_MARKERS):
                continue
            if topic_re.search(text):
                return True
    return False


# Anchored topic patterns for the act routes (wave 7). The wave-6 lists used
# bare substrings, so any analyze/scan entry that ALSO mentioned someone
# speaking ("an outspoken guard", "他在说话") leaked TRACE-L3-08, and ordinary
# radio/TV "static" after a decode act leaked TRACE-L2-06. Distinctive words
# (voice/whisper/低语) stay standalone but boundary-anchored; ambiguous ones
# (spoke/speaking/说话/声音/static) must share a clause (no ./;/!/? between)
# with signal-or-scan context — mirroring the _S7_CONTEXT_RE approach.
_L308_SPEECH_PART = (
    r"(?:(?<![a-z])(?:spoke|spoken|speaks?|speaking)(?![a-z])|说话|话语|声音)")
_L308_SIGNAL_PART = (
    r"(?:(?<![a-z])(?:signal|fragment|entity|network|transmission|static)(?![a-z])"
    r"|信号|碎片|实体|网络|传输)")
_CLAUSE_GAP = r"[^.。;；!?！？\n]{0,60}"
_L308_VOICE_RE = re.compile(
    r"(?<![a-z])(?:voices?|whisper(?:s|ed|ing)?)(?![a-z])|低语"
    + "|" + _L308_SIGNAL_PART + _CLAUSE_GAP + _L308_SPEECH_PART
    + "|" + _L308_SPEECH_PART + _CLAUSE_GAP + _L308_SIGNAL_PART)
_L206_SCAN_PART = (
    r"(?:(?<![a-z])(?:scan(?:s|ned|ner|ning)?|sweep|sensor|reading|surveillance"
    r"|tracker|drone)(?![a-z])|扫描|监控|读数|探测|追踪)")
_L206_STATIC_RE = re.compile(
    _L206_SCAN_PART + _CLAUSE_GAP + r"(?<![a-z])static(?![a-z])"
    + r"|(?<![a-z])static(?![a-z])" + _CLAUSE_GAP + _L206_SCAN_PART)


# TRACE-L4-09 中文 gradient route (zh deep-trace parity audit, wave 17;
# depth-anchored, wave 20). EN trips this trace on the bare noun "resonance":
# in the certified EN waves the resolver names the deep destination ("an old
# service descent leads from cold storage toward the resonance" — wave10_en
# FACT-093; "the resonance lies beneath the old transit shrine" — wave14_en
# FACT-086). The zh resolver renders the SAME beat as a Signal gradient
# instead of a place name: "静水井深处是Signal更强的方向" (wave6_zh FACT-112),
# "Signal的方向沿南边雨巷排水线继续向下" (wave10_zh FACT-086), "Signal残留沿
# 冷链路线继续向下" (wave14_zh FACT-079) — none contain 共鸣/回响/清晰, so
# 中文 runs fired L4-09 in 1/5 certified sessions vs EN 4/5.
#
# 信号+更强/更清晰 alone is NOT enough: 信号 is everyday telecom Chinese and
# 越来越强/更清晰 is the ordinary way to say a phone/wifi/radio signal improved
# ("手机信号越来越强", "wifi信号更清晰了"). Within ONE clause the route needs
# the Signal term plus EITHER a descent-phrased gradient (继续向下 — the
# gradient IS the downward direction) OR a strength/clarity gradient AND a
# depth anchor (深处/更深/越深/深入/向下/往下). Mundane telecom chatter names
# no downward direction, so it stays silent.
_L409_SIGNAL_RE = re.compile(r"signal|信号")
_L409_DESCENT_RE = re.compile(r"继续向下")
_L409_STRENGTH_RE = re.compile(r"更强|越来越强|更清晰|更加清晰|越来越清晰")
_L409_DEPTH_RE = re.compile(r"深处|更深|越深|深入|向下|往下")
_L409_CLAUSE_SPLIT_RE = re.compile(r"[.。;；!?！？\n]")


def _signal_gradient_in_one_entry(knowledge: dict) -> bool:
    """True when a SINGLE clause of one knowledge entry records the Signal
    strengthening / clarifying / leading DEEPER (TRACE-L4-09 中文 route).

    The depth anchor is load-bearing: 信号更强/更清晰 without a downward
    direction is a literal telecom signal improving, not deep lore."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            for clause in _L409_CLAUSE_SPLIT_RE.split(_entry_text(entry)):
                if not _L409_SIGNAL_RE.search(clause):
                    continue
                if _L409_DESCENT_RE.search(clause):
                    return True
                if (_L409_STRENGTH_RE.search(clause)
                        and _L409_DEPTH_RE.search(clause)):
                    return True
    return False


# TRACE-L3-01 中文 route (wave 17 audit; topic-anchored, wave 20). The zh
# resolver phrases the deliberate-severance reveal as 人为切断 / 并非意外
# (wave12_zh RUMOR-009: "老技师传言断离更像人为切断，而不是单纯故障"). But
# 并非意外/不是意外/故意/蓄意 are everyday Chinese for ANY non-accident
# ("这不是意外，是有人故意撞的车"), so those phrases only count when the same
# entry names the Severance topic (断离/切断/severance) — matching this
# trace's description_zh, 断离并非意外, not the bare consequence phrase.
_L301_TOPIC_TERMS = ("断离", "切断", "severance")
_L301_DELIBERATE_TERMS = ("蓄意", "故意", "并非意外", "不是意外")


def _deliberate_severance_in_one_entry(knowledge: dict) -> bool:
    """True when a SINGLE knowledge entry ties the Severance topic to a
    deliberate / not-an-accident phrase (TRACE-L3-01 中文 route)."""
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if (any(term in text for term in _L301_TOPIC_TERMS)
                    and any(term in text for term in _L301_DELIBERATE_TERMS)):
                return True
    return False


def _any_npc_trust_at_least(npcs: dict, min_level: str) -> bool:
    """True if ANY known NPC's trust is at or above the threshold (bilingual).

    Used by gates that care about having earned a confidant at all, not about a
    specific person (e.g. a trusted ally naming the Listeners, TRACE-L2-02)."""
    levels = ["hostile", "suspicious", "neutral", "cautious_ally", "trusted", "devoted"]
    min_idx = levels.index(min_level) if min_level in levels else 0
    for npc in npcs.get("npcs", []):
        trust = str(npc.get("trust_level", npc.get("trust", "neutral"))).lower()
        trust = _TRUST_ALIASES.get(trust, trust)
        trust_idx = levels.index(trust) if trust in levels else 2
        if trust_idx >= min_idx:
            return True
    return False


def _layer_of(trace_id: str) -> int | None:
    """Parse the layer number from a trace id like ``TRACE-L3-07`` -> 3.

    Returns ``None`` when the id doesn't carry an ``L#`` segment."""
    m = re.search(r"-L(\d+)-", str(trace_id or ""))
    return int(m.group(1)) if m else None


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


def _count_layer_discovered(traces: dict, layer: int) -> int:
    """How many traces of a given layer have been discovered."""
    return sum(1 for t in TRACE_CONDITIONS
               if t["layer"] == layer and _trace_discovered(traces, t["id"]))


def reconcile_trace_presentation(traces: dict) -> dict:
    """Sync the display fields (``total_discovered``, per-layer ``progress``,
    per-trace ``status``/``description``) with the authoritative ``discovered``
    list.

    The trace_checker only appends to ``discovered``; without this the persisted
    counter stays "0 / 47" and every per-trace entry stays "[???]" even after
    real discoveries. Idempotent; safe to call every turn. Returns ``traces``.
    """
    discovered = traces.get("discovered", []) or []
    disc_map = {d.get("id"): d for d in discovered if d.get("id")}
    # Canonical live total — never a hard-coded literal (see LIVE_TRACE_TOTAL).
    traces["total_discovered"] = f"{len(disc_map)} / {LIVE_TRACE_TOTAL}"

    layers = traces.get("layers", {})
    if isinstance(layers, dict):
        for layer in layers.values():
            if not isinstance(layer, dict):
                continue
            tr = layer.get("traces", {})
            if not isinstance(tr, dict):
                continue
            count = 0
            layer_num = None
            for trace_id, info in tr.items():
                if layer_num is None:
                    layer_num = _layer_of(trace_id)
                if not isinstance(info, dict):
                    continue
                if trace_id in disc_map:
                    count += 1
                    info["status"] = "discovered"
                    desc = disc_map[trace_id].get("description")
                    if desc and info.get("description") in (None, "", "[???]"):
                        info["description"] = desc
            # Denominator = canonical live count for this layer, falling back to
            # the scaffold slot count only if the layer number can't be parsed.
            denom = LIVE_TRACES_PER_LAYER.get(layer_num, len(tr))
            layer["progress"] = f"{count}/{denom}"
    return traces


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
     # Require the SCALE (timeframe / death toll), not the bare word "severance"
     # — every "pre-Severance" mention carries that and made this over-claim
     # ("killed billions") fire on turn 1 before the player learned any of it.
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["30 years", "三十年", "thirty years", "billions", "数十亿", "数十億"])},
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
     # This trace is about CONFISCATION/rarity, not pre-Severance tech in general.
     # The bare "pre-severance"/"断离前" anchors over-fired on any implant mention
     # (the whole game is pre-Severance) — e.g. examining your own implant on turn
     # 1 leaked this. Gate on the confiscation/value terms the fiction actually
     # surfaces when the player learns NEXUS seizes such tech.
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["confiscate", "没收", "rare tech", "稀有", "valuable", "珍贵"])},

    # =========================================================================
    # Layer 2: The Conspiracy (11 traces)
    # =========================================================================
    {"id": "TRACE-L2-01", "layer": 2,
     "description": "People who hear the Signal are disappearing",
     "description_zh": "能听到信号的人正在消失",
     # Branch A must require DISAPPEARANCE content, not the Signal topic itself.
     # "signal" here made the gate trivially loose: Mira auto-seeds at `neutral`
     # from the opening scene, so any Signal-related knowledge (the game's central
     # topic) fired this L2 trace with zero disappearance evidence — collapsing the
     # mystery on turn 1. Keep the two earned routes: a neutral-or-better Mira who
     # speaks of the vanishings, or ≥2 independent sources reporting them.
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "mira", "neutral") and _has_fact_or_rumor_about(k, ["disappear", "vanish", "gone missing", "消失", "missing", "失踪"])
     ) or _count_sources_about(k, ["disappear", "vanish", "gone missing", "消失", "missing", "失踪"]) >= 2},
    {"id": "TRACE-L2-02", "layer": 2,
     "description": "The Listeners exist and protect Signal-sensitive people",
     "description_zh": "聆听者组织存在，并保护对信号敏感的人",
     # Two earned routes (playtest wave 3, C11). The anti-spoiler rules forbid
     # NPCs volunteering the faction NAME before discovery, so requiring the
     # literal "listener" token was a chicken-and-egg that froze this trace even
     # when the player clearly learned the group exists. Route (b): once ANY
     # NPC trusts the player (>= cautious_ally) and a single recorded rumor/fact
     # says someone protects the Signal-sensitive, the ally may name them — the
     # trace fires and the reveal becomes narratable. The protect-verb must
     # GOVERN the Signal-sensitive phrase (wave 4 review): loose bag-of-words
     # co-occurrence fired on self-hiding notes and NEXUS-threat descriptions.
     "check": lambda k, t, n, p, w: (
         (_npc_trust_at_least(n, "mira", "cautious_ally")
          and _has_fact_or_rumor_about(k, ["listener", "聆听者"]))
         or (_any_npc_trust_at_least(n, "cautious_ally")
             and _protects_signal_sensitives(k)))},
    {"id": "TRACE-L2-03", "layer": 2,
     "description": "NEXUS has a secret facility in Sector 7 for 'special acquisitions'",
     "description_zh": "NEXUS在第七区设有秘密设施，用于'特殊征集'",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "ghost", "neutral") and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "facility", "acquisitions"])
     ) or (p.get("background", "").lower() in ["corporate exile", "企业流亡者"]
           and _has_fact_or_rumor_about(k, ["sector 7", "第七区", "special acquisition", "acquisitions", "特殊征集", "征集"]) and _count_sources_about(k, ["sector 7", "第七区"]) >= 2)},
    {"id": "TRACE-L2-04", "layer": 2,
     "description": "Your implant is unique pre-Severance tech that shouldn't exist",
     "description_zh": "你的植入体是独一无二的断离前技术，本不应存在",
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, ["unique", "shouldn't exist", "不应该存在"])
         and (_npc_trust_at_least(n, "ghost", "neutral") or _npc_trust_at_least(n, "patch", "neutral") or _has_evidence(k, ["implant analysis", "implant scan"])))},
    {"id": "TRACE-L2-05", "layer": 2,
     "description": "The Undercroft exists beneath The Sprawl — old transit tunnels from before the Severance",
     "description_zh": "底渊存在于蔓城之下——断离前的旧交通隧道",
     # Drop bare "underground"/"地下" — it fired off idioms ("went underground",
     # "so deep underground the daylight forgot"). The Undercroft is learned by
     # name or via the old transit TUNNELS.
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["undercroft", "底渊", "transit tunnel", "old tunnel", "tunnel", "隧道"])},
    {"id": "TRACE-L2-06", "layer": 2,
     "description": "NEXUS surveillance has blind spots — the Signal interferes with their scanners",
     "description_zh": "NEXUS的监控存在盲区——信号会干扰他们的扫描器",
     # Act route (wave 6, #3b): a scan act that itself comes back as static /
     # dead zones demonstrates the interference first-hand. "static" must share
     # a clause with scan/surveillance context (wave 7) so plain radio static
     # after a decode act doesn't count.
     # Bare "scanner" fired off any scanner mention ("unmarked vans with
     # scanners") without the blind-spot/interference reveal — gate on the
     # actual lore (blind spots / the Signal interfering) or the act routes.
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, ["blind spot", "盲区", "interfere", "干扰", "jam the scanner", "scanner blind"])
         or _acted_on_evidence(k, ["dead zone", "jammed", "no coverage",
                                   "死角", "静默区", "屏蔽"])
         or _acted_on_evidence_re(k, _L206_STATIC_RE))},
    {"id": "TRACE-L2-07", "layer": 2,
     "description": "Multiple people have disappeared following the same pattern — all had old implants",
     "description_zh": "多人以相同模式失踪——他们都有旧植入体",
     "check": lambda k, t, n, p, w: _count_sources_about(k, ["disappear", "消失", "missing", "失踪", "pattern", "implant"]) >= 3},
    {"id": "TRACE-L2-08", "layer": 2,
     "description": "Director Orin leads NEXUS operations in Neo-Kowloon — publicly respected but secretive",
     "description_zh": "欧林主管领导新九龙的NEXUS运营——公开受人尊敬但行事神秘",
     # 中文 parity (wave 10, friction #2): 奥林 is the alias the zh resolver
     # actually uses for Orin (already in _NPC_ALIASES), and 总监 is the other
     # natural rendering of "director" alongside 主管.
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["orin", "欧林", "奥林", "director", "主管", "总监"])},
    {"id": "TRACE-L2-09", "layer": 2,
     "description": "Chrome Heights is the corporate elite district — NEXUS officials and wealthy citizens",
     "description_zh": "镀金台是企业精英区——NEXUS官员和富裕市民居住于此",
     # Anchor to the district name / "corporate elite" phrase. Bare "corporate"
     # fired this L2 trace off any corporate-dystopia flavor text ("before the
     # corporate era"), and the whole world is corporate — a premature reveal.
     "check": lambda k, t, n, p, w: _has_fact_or_rumor_about(k, ["chrome heights", "镀金台", "corporate elite", "企业精英", "精英区"])},
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
     # 中文 parity (wave 17 audit; topic-anchored, wave 20): the zh resolver
     # phrases the deliberate-severance reveal as 人为切断 / 并非意外 (wave12_zh
     # RUMOR-009: "老技师传言断离更像人为切断，而不是单纯故障"). 人为切断/网络终止/
     # 断离证据 are specific enough to stand alone; the everyday phrases
     # 并非意外/不是意外/故意/蓄意 fire only anchored to the Severance topic
     # (see _deliberate_severance_in_one_entry). Ghost trust gate unchanged.
     "check": lambda k, t, n, p, w: (
         (_has_evidence(k, ["deliberate", "network termination",
                            "severance evidence", "人为切断",
                            "网络终止", "断离证据"])
          or _deliberate_severance_in_one_entry(k))
         and _npc_trust_at_least(n, "ghost", "cautious_ally"))},
    {"id": "TRACE-L3-02", "layer": 3,
     "description": "Something was alive in the network before the Severance",
     "description_zh": "断离之前，网络中有某种存在是活着的",
     # 中文 parity (wave 10, friction #2): EN trips this on the bare adjective
     # "alive", but the natural zh renderings of "something alive in the net"
     # are 活物 / 有生命 — 活着/活的 alone missed them (中文 back half stalled).
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["pre-severance logs", "alive", "network entity",
                           "断离前日志", "活着", "活的", "活物", "有生命",
                           "网络实体", "存在"])
         and _npc_trust_at_least(n, "patch", "neutral"))},
    {"id": "TRACE-L3-03", "layer": 3,
     "description": "Fragments of something survive in old implants — 'computational resources'",
     "description_zh": "某种存在的碎片留存在旧植入体中——被称为'计算资源'",
     # 中文 parity (wave 17 audit): 计算资源 is this trace's own description_zh
     # term for "computational resources"; the evidence branch was EN-ONLY
     # ("nexus archives"/"sector 7 lab") — a zh run could never take it. The zh
     # locators are the canonical NEXUS档案 / 第七区实验室 renderings.
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, ["fragment", "碎片", "computational", "计算资源",
                                      "survive", "implant"])
         and (_npc_trust_at_least(n, "ghost", "trusted")
              or _has_evidence(k, ["nexus archives", "sector 7 lab",
                                   "nexus档案", "第七区实验室"])))},
    {"id": "TRACE-L3-04", "layer": 3,
     "description": "NEXUS harvests fragments from people — the disappearances are extraction",
     "description_zh": "NEXUS从人体中收割碎片——那些失踪就是提取行动",
     # Drop bare "nexus" from the source count — NEXUS is named in nearly every
     # source, so ≥3 sources mention it trivially and fired this extraction
     # trace with zero harvest/extraction knowledge. Count the extraction THEME.
     # Bare "sector 7"/"第七区" is just a LOCATION — it fired this extraction
     # trace on turn 1 off the corporate-exile rumor "Orin runs something
     # off-books in Sector 7". Gate on the extraction/harvest ACT itself.
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["extraction", "harvesting", "harvest", "提取", "收割"])
         or _count_sources_about(k, ["disappear", "fragment", "harvest",
                                     "失踪", "消失", "碎片", "收割"]) >= 3)},
    {"id": "TRACE-L3-05", "layer": 3,
     "description": "The Undercroft contains pre-Severance infrastructure still partially active",
     "description_zh": "底渊中仍有部分运作的断离前基础设施",
     # Act route (wave 6, #3b): a scan/analysis act on the under-city hardware
     # itself — e.g. wave-6's "M-17 passive signal scan" evidence — verifies the
     # old infrastructure is live even without the exact lore words.
     # Evidence branch must name the under-city itself. Bare "pre-severance"/"断离前"
     # over-fired on any implant/tech fact (the whole game is pre-Severance), so
     # examining your implant on turn 1 leaked this L3 Undercroft trace. Keep the
     # Undercroft/infrastructure locators; the act route below still covers scans
     # of the under-city hardware even without the exact lore words.
     # NB: bare "active" is dropped — it substring-matches "in-ACTIVE" (the
     # opposite meaning) and "radio-ACTIVE". "infrastructure"/"运作" already
     # carry the "still running" sense; the phrase "still active" is anchored.
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["undercroft", "infrastructure", "still active",
                           "partially active", "底渊", "基础设施", "运作"])
         or _acted_on_evidence(k, ["undercroft", "tunnel", "conduit", "relay box",
                                   "hatch", "under-market", "底渊", "隧道", "导管",
                                   "中继", "检修口"]))},
    {"id": "TRACE-L3-06", "layer": 3,
     "description": "Fragment extraction is painful and often fatal — NEXUS doesn't care",
     "description_zh": "碎片提取过程痛苦且往往致命——NEXUS对此毫不在意",
     # Anchor to the extraction/harvest ACT — the trace's real subject. Bare
     # "fatal"/"painful" leaked this Layer-3 trace off the integrity primer
     # ("each strain wears you down, and too much is fatal") and generic danger
     # talk; the "painful/fatal" wording is the framing, not the trigger.
     "check": lambda k, t, n, p, w: _has_evidence(k, ["extraction", "harvest", "harvesting",
                                                      "提取", "收割"])},
    {"id": "TRACE-L3-07", "layer": 3,
     "description": "Sector 7 has multiple levels — the deeper labs are where extraction happens",
     "description_zh": "第七区有多层结构——提取行动发生在更深层的实验室",
     # Wave-6 friction #3a: bare "level" fired this on turn 1 ("street level
     # Neo-Kowloon"). Depth must co-occur with Sector-7/lab context per entry.
     "check": lambda k, t, n, p, w: _sector7_depth_in_one_entry(k)},
    {"id": "TRACE-L3-08", "layer": 3,
     "description": "The entity in the network tried to communicate before it was severed",
     "description_zh": "网络中的实体在被切断前曾试图沟通",
     # PASSIVE ROUTE RESTORED (wave 11 review, critical #1). Wave 10's
     # friction-#1 change act-gated this trace: the topic keywords only
     # counted inside an entry that ALSO carried an _ACT_MARKER. Replaying the
     # certified wave-10 runs (and the full session corpus) showed that gate
     # makes the trace unreachable in real play: the resolver reliably files
     # this lore as passive NPC hearsay/observation (sources "Patch", "老周",
     # "observed"), while its act-tagged entries (signal scans, Signal分析)
     # are about other topics entirely — the act-marker set and the topic set
     # were disjoint in EVERY certified session, so every recorded run that
     # had discovered L3-08 stopped discovering it. Hearsay therefore counts
     # again; the wave-7 anchored voice regex stays as the act path for
     # fragments that literally carry the voice (the analyze_signal fragments
     # read "...before the silence, there was a voice...").
     # Bare "entity" is an unanchored substring of "id-ENTITY" — the exile fact
     # "your only proof of your former identity" fired this Layer-3 trace. Bare
     # "message"/"信息"/"断离前" are likewise too generic. Anchor to the entity
     # COMMUNICATING (the trace's real subject); the act route covers fragments
     # that literally carry the voice.
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["communicate", "communicated", "the entity", "network entity",
                           "entity in the network", "沟通", "试图沟通", "网络实体",
                           "网络中的实体"])
         or _acted_on_evidence_re(k, _L308_VOICE_RE))},
    {"id": "TRACE-L3-09", "layer": 3,
     "description": "Some extracted fragments have been weaponized by NEXUS — Project Resonance",
     "description_zh": "一些被提取的碎片已被NEXUS武器化——共鸣计划",
     # 中文 parity (wave 17 audit): EN fires on "weaponize"/"weapon" but zh only
     # listed the project name 共鸣计划 — "碎片已被NEXUS武器化" (this trace's own
     # description_zh phrasing) could never fire. 武器化 matches EN "weaponize"
     # specificity; the bare noun 武器 is deliberately NOT added.
     "check": lambda k, t, n, p, w: _has_evidence(k, ["weaponize", "project resonance",
                                                      "共鸣计划", "武器化", "weapon"])},
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
         # most of layer 3 (7/11) rather than ALL of it — full completion was an
         # unreachable bottleneck that walled off the whole Mirror layer.
         _count_layer_discovered(t, 3) >= 7 and _has_fact_or_rumor_about(k, [
             "architect", "设计者", "建筑师", "proto-consciousness", "原意识", "human data", "人类数据",
         ]))},
    {"id": "TRACE-L4-02", "layer": 4,
     "description": "Implants transmitted too — human and machine consciousness co-evolved",
     "description_zh": "植入体也在传输——人类与机器意识共同进化",
     "check": lambda k, t, n, p, w: (
         _npc_trust_at_least(n, "patch", "trusted") and _has_fact_or_rumor_about(k, [
             "co-evolved", "transmitted", "bilateral", "bridge",
             "共同进化", "传输", "双向", "桥梁",
         ]))},
    {"id": "TRACE-L4-03", "layer": 4,
     "description": "The Severance was an act of fear, not defense",
     "description_zh": "断离是出于恐惧，而非防御",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["severance", "confession", "fear", "lian",
                           "断离", "忏悔", "供认", "恐惧", "莲"]) and _npc_trust_at_least(n, "lian", "cautious_ally"))},
    {"id": "TRACE-L4-04", "layer": 4,
     "description": "The Sigma Council ordered the Severance — a secret committee of corporate and government leaders",
     "description_zh": "西格玛委员会下令实施断离——由企业和政府领袖组成的秘密委员会",
     # Bare "ordered" fired off "the signal is ordering what you ordered at her
     # counter" (a noodle order). Gate on the Sigma Council / secret committee.
     "check": lambda k, t, n, p, w: _has_evidence(k, ["sigma council", "西格玛", "secret committee", "秘密委员会"])},
    {"id": "TRACE-L4-05", "layer": 4,
     "description": "The Spire was built as the Severance control center — it predates NEXUS",
     "description_zh": "尖塔是作为断离控制中心建造的——它的历史早于NEXUS",
     # Bare "spire"/"尖塔" is a known district — merely naming it fired this
     # secret ("it was the Severance CONTROL CENTER, predates NEXUS"). Gate on
     # that function, not the location name.
     "check": lambda k, t, n, p, w: _has_evidence(k, ["control center", "控制中心", "severance control", "predates nexus", "早于nexus", "早于NEXUS"])},
    {"id": "TRACE-L4-06", "layer": 4,
     "description": "The Archive Tower in The Spire contains all records — including the truth about the Severance",
     "description_zh": "尖塔中的档案塔保存着所有记录——包括断离的真相",
     # Wave-10 friction #3: bare "records"/"记录" fired this on 中文 turn 2
     # ("公共终端…会留下记录"). Archive/records/truth must now co-occur with a
     # Spire/Tower locator in the SAME entry (L3-07 pattern).
     "check": lambda k, t, n, p, w: _archive_tower_in_one_entry(k)},
    {"id": "TRACE-L4-07", "layer": 4,
     "description": "Dr. Chen knows the full truth but continues the program out of conviction",
     "description_zh": "陈博士知道全部真相但出于信念继续着这个计划",
     "check": lambda k, t, n, p, w: (
         _has_evidence(k, ["chen", "陈", "knows truth", "conviction", "continues"]) and _trace_discovered(t, "TRACE-L3-11"))},
    {"id": "TRACE-L4-08", "layer": 4,
     "description": "The EMP trigger mechanism in The Spire's sub-basements is still operational",
     "description_zh": "尖塔地下室中的EMP触发装置仍在运作",
     # Bare "sub-basement"/"operational" fired off unrelated Spire prose, and the
     # bare token "emp"/"EMP" is an unanchored substring of "EMP-ty"/"att-EMP-t"/
     # "t-emp-le"/"exa-mp-le" — it fired constantly. Anchor to the EMP TRIGGER /
     # electromagnetic-pulse device.
     "check": lambda k, t, n, p, w: _has_evidence(k, ["emp trigger", "emp device", "emp mechanism",
                                                      "electromagnetic pulse", "EMP触发", "电磁脉冲"])},
    {"id": "TRACE-L4-09", "layer": 4,
     "description": "Echo — the Signal's voice — becomes clearer as you approach the Resonance",
     "description_zh": "回响——信号的声音——在你接近共鸣所时变得更加清晰",
     # 中文 parity (wave 10, friction #2): EN fired this via voice/clearer/
     # resonance but zh only listed 回响. Added the game's own zh terms — 回声
     # (Echo's alias in _NPC_ALIASES), 共鸣 (resonance, cf. 共鸣计划/共鸣室),
     # 信号的声音 (the Signal's voice, per description_zh). Bare 声音 stays
     # out — it means any sound at all — and (play-test) so does bare EN "voice":
     # it leaked this Layer-4 trace off the model's own anti-injection narration
     # ("never give a faceless voice what it demands"), so it is now the specific
     # phrase "signal's voice". (wave 20) The bare
     # adjectives 更清晰/更加清晰: "电视信号更清晰了" is everyday telecom
     # Chinese. The zh clearer/stronger shape lives in the depth-anchored
     # gradient route instead.
     # Wave-17 audit: the zh resolver also renders this beat as a Signal
     # GRADIENT without any of those nouns ("静水井深处是Signal更强的方向",
     # "Signal残留沿冷链路线继续向下") — the clause-gated route catches that
     # shape (see _signal_gradient_in_one_entry).
     # bare "resonance" substring-matched "RESONANCE-positive" (a NEXUS detention
     # manifest category), leaking this Layer-4 reveal on turn 3; and bare "共鸣"
     # matches the place-name 共鸣所. Anchor both to THE Resonance / its chamber.
     "check": lambda k, t, n, p, w: (
         _has_fact_or_rumor_about(k, [
             "echo", "回响", "回声", "signal's voice", "信号的声音", "clearer",
             "the resonance", "resonance chamber", "resonance grows", "approach the resonance",
             "near the resonance", "共鸣室", "共鸣所", "接近共鸣",
             # zh resonance-GRADIENT (the implant's/Signal's resonance growing) —
             # the legit "共鸣越来越强" shape, anchored so it doesn't match the bare
             # place-name 共鸣所 the way bare "共鸣" did.
             "植入体的共鸣", "信号共鸣", "植入体共鸣", "共鸣越来越",
             "共鸣增强", "共鸣更强", "共鸣变强", "共鸣更清晰"])
         or _signal_gradient_in_one_entry(k))},

    # =========================================================================
    # Layer 5: The Full Truth (8 traces)
    # =========================================================================
    {"id": "TRACE-L5-01", "layer": 5,
     "description": "You are the convergence point — the first true bridge",
     "description_zh": "你是汇聚点——第一座真正的桥梁",
     "check": lambda k, t, n, p, w: (
         # Reachable-but-deep: a solid chunk of Layer 4 + convergence knowledge +
         # an implant in resonance OR the player having reached deep resonance
         # lore (so a thorough investigation can actually arrive here). The L4
         # floor is 3, not 4: the L4 gates were tightened to stop substring
         # false-fires, and a real perfectly-played bridge run (iter10_h2_en)
         # legitimately discovers exactly 3 L4 traces — the "4th" it used to hit
         # was L4-08 firing on "att-emp-t". Keeping 4 would wall off the good
         # ending it was calibrated against once the false fire is gone.
         _count_layer_discovered(t, 4) >= 3 and _has_fact_or_rumor_about(k, [
             "convergence", "bridge", "echo", "resonance",
             "汇聚", "汇聚点", "桥", "桥梁", "回响", "回声", "共鸣",
         ])
         and (str(p.get("neural_implant", "")).lower() in ("resonating", "共鸣", "共鸣中", "共振")
              or _has_fact_or_rumor_about(k, [
                  "resonating", "resonance with the signal", "implant resonates",
                  # Direct contact with the convergence itself. The decisive
                  # climax runs record the ACT ("the convergence answered",
                  # "holding the bridge open") rather than the implant's status
                  # string, and this trace never fired on the best-played
                  # consensual-bridge run (playtest wave 3, C1 / iter10_h2_en).
                  "convergence answered", "convergence answers",
                  "the resonance answers", "resonance is reachable",
                  "holding the bridge", "holds the bridge", "the bridge holds",
                  "first true bridge", "opened the threshold",
                  # Play-test C2: the resolver paraphrases the decisive climax,
                  # so the narrow list above missed a textbook consensual
                  # crossing — it fired two turns late, leaving the player in a
                  # finished-but-unending story. Add the vocabulary real
                  # climax turns actually record.
                  "convergence is complete", "convergence complete",
                  "the convergence", "crossed the bridge", "cross the bridge",
                  "bridge is complete", "the bridge is open", "bridged",
                  "共鸣", "共振", "信号共鸣", "植入体共鸣",
                  "汇聚回应", "汇聚点回应", "维系桥梁", "桥梁维系",
                  "汇聚完成", "汇聚已成", "跨越了桥", "桥已建成", "桥梁贯通",
                  "真正的桥", "开启门槛", "门槛已开",
              ])))},
    {"id": "TRACE-L5-02", "layer": 5,
     "description": "The Severance didn't fully kill it — it became part of humanity",
     "description_zh": "断离并未完全杀死它——它已成为人类的一部分",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01")
         and _has_evidence(k, ["architect data", "architect's", "建筑师数据", "设计者数据", "建筑师", "设计者"])
         and _has_fact_or_rumor_about(k, [
             "part of humanity", "can't kill", "became",
             "人类的一部分", "无法杀死", "杀不死", "成为人类", "成为",
         ]))},
    {"id": "TRACE-L5-03", "layer": 5,
     "description": "Restoration requires both human will and the proto-consciousness's consent",
     "description_zh": "恢复连接需要人类的意志和原意识的同意",
     # bare "will" is the English modal — it matches any "…will…" once L5-01 is
     # in. The consent/mutual anchors carry reachability; use "human/free will".
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["consent", "同意", "mutual", "human will", "free will", "willpower", "意志"]))},
    {"id": "TRACE-L5-04", "layer": 5,
     "description": "The Resonance chamber is where the original Severance epicenter lies",
     "description_zh": "共鸣室是最初断离震中所在之处",
     "check": lambda k, t, n, p, w: _has_evidence(k, ["resonance chamber", "共鸣室", "epicenter", "震中"])},
    {"id": "TRACE-L5-05", "layer": 5,
     "description": "Echo can become fully coherent through deep communion with the bridge",
     "description_zh": "通过与桥梁的深度交融，回响可以完全清晰化",
     # bare "deep" fires on "deeper"/"deep resonance" once L5-01 is in; the
     # coherent/communion anchors carry it (the trace is about DEEP COMMUNION).
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["coherent", "清晰", "communion", "deep communion", "交融"]))},
    {"id": "TRACE-L5-06", "layer": 5,
     "description": "Multiple endings exist — symbiosis, bridge, or destruction",
     "description_zh": "存在多种结局——共生、桥梁或毁灭",
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-02") and _has_fact_or_rumor_about(k, ["symbiosis", "共生", "choice", "选择", "destroy"]))},
    {"id": "TRACE-L5-07", "layer": 5,
     "description": "The Severance machine can be activated again — or destroyed permanently",
     "description_zh": "断离装置可以再次启动——或被永久摧毁",
     # Requires L4-08 (now tightened) + the SEVERANCE MACHINE specifically. Bare
     # "activate"/"destroy" cascaded off a falsely-fired L4-08 + generic
     # "destroying the consciousness" prose into a Layer-5 reveal on turn 10.
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L4-08") and _has_evidence(k, ["severance machine", "断离装置", "断离机器"]))},
    {"id": "TRACE-L5-08", "layer": 5,
     "description": "Becoming the bridge means merging permanently — losing your individual self",
     "description_zh": "成为桥梁意味着永久融合——失去你的个体自我",
     # bare "merge" substring-matches "e-MERGE"/"e-MERGE-ncy"/"sub-MERGE"; use
     # anchored forms. "permanent" likewise → "permanently"/"permanent merge".
     "check": lambda k, t, n, p, w: (
         _trace_discovered(t, "TRACE-L5-01") and _has_fact_or_rumor_about(k, ["merging", "the merge", "merge with", "permanent merge", "融合", "lose self", "lose your self", "lose yourself", "失去自我"]))},
]


# ---------------------------------------------------------------------------
# Canonical trace totals (single source of truth)
#
# Every entry in ``TRACE_CONDITIONS`` above has a *live* ``check()`` condition,
# so the number of discoverable traces is exactly ``len(TRACE_CONDITIONS)``.
# The persisted ``traces.json`` scaffold advertises a slot per trace and used to
# be summed ad-hoc ("N / 47"); deriving the totals here keeps the counter, the
# per-layer denominators, and any GUI presentation reconciled to one number
# instead of a hard-coded literal that silently drifts if traces are added.
LIVE_TRACE_TOTAL: int = len(TRACE_CONDITIONS)

# Per-layer live denominators: {layer_number: count-of-traces-with-live-check}.
LIVE_TRACES_PER_LAYER: dict[int, int] = {}
for _tc in TRACE_CONDITIONS:
    _lyr = _tc.get("layer")
    if _lyr is not None:
        LIVE_TRACES_PER_LAYER[_lyr] = LIVE_TRACES_PER_LAYER.get(_lyr, 0) + 1
del _tc, _lyr


# ---------------------------------------------------------------------------
# NEXUS Alert rules
# ---------------------------------------------------------------------------

# ⚠ NOTE (playtest wave 3, C5a): ALERT_INCREASES is currently REFERENCE DATA —
# no engine code imports or applies these values. NEXUS alert only moves when
# the model volunteers a `nexus_alert_delta` (engine/tools.py update_world_state
# on the graph path; the state_effects/update_world_state blocks in
# engine/claude_code_engine.py on the bypass path), which is why investigation
# runs sit at alert 0 for 20 turns. To make these causes live, the resolver
# guidance/tool schema (engine/tools.py + the bypass engine's tool prompt) should
# embed this cause→value table so the model applies canonical amounts, with
# ALERT_CAUSE_LABELS below providing the player-facing "why" for meter notices.
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

# Player-facing, in-world reasons for each alert cause (EN + 中文). Additive:
# for use by meter-change notices ("↑ NEXUS Alert — why") so the number always
# comes with its cause. Phrased to reference only what the player just did —
# never undiscovered content.
ALERT_CAUSE_LABELS: dict[str, dict] = {
    "failed_hack": {
        "en": "a hack attempt failed and tripped an alarm",
        "zh": "黑客入侵失败，触发了警报"},
    "caught_restricted": {
        "en": "you were caught in a restricted area",
        "zh": "你在禁区被抓了个正着"},
    "asking_about_nexus_publicly": {
        "en": "asking about NEXUS in the open drew attention",
        "zh": "公开打听NEXUS引来了注意"},
    "stealing_nexus_data": {
        "en": "stolen NEXUS data was flagged",
        "zh": "窃取的NEXUS数据被标记了"},
    "spotted_by_drone": {
        "en": "a surveillance drone spotted you",
        "zh": "监控无人机发现了你"},
    "npc_betrayal": {
        "en": "someone reported you",
        "zh": "有人举报了你"},
    "entering_sector7_uncovered": {
        "en": "you entered Sector 7 without a cover",
        "zh": "你未加掩护进入了第七区"},
    "attacking_nexus": {
        "en": "you attacked NEXUS assets",
        "zh": "你袭击了NEXUS的目标"},
}

# Player-facing default causes for PASSIVE / ambient meter changes (EN + 中文).
# Playtest wave 6, friction #2: passive settles (alert decaying over time,
# background integrity strain, fragment decay ticking) reached the client as a
# bare number with no reason. Additive, same pattern as ALERT_CAUSE_LABELS:
# the server-side meter-notice track attaches one of these when a change has
# no player-attributable cause, so no meter move is ever mute. Keys are
# "<meter>_<direction>". Phrased ambient and spoiler-safe — they reference
# neither undiscovered content nor a specific player act.
AMBIENT_CAUSE_LABELS: dict[str, dict] = {
    "alert_down": {
        "en": "the grid's attention moves on",
        "zh": "城市网格的注意力转移"},
    "alert_up": {
        "en": "routine sweeps tighten across the district",
        "zh": "城区例行排查悄然收紧"},
    "decay_up": {
        "en": "the fragments fade a little more with time",
        "zh": "碎片随时间流逝又消退了一分"},
    "decay_down": {
        "en": "the fragments settle and hold their pattern",
        "zh": "碎片趋于稳定，暂时止住了消退"},
    "integrity_down": {
        "en": "the strain of the day wears on you",
        "zh": "连日的损耗侵蚀着你"},
    "integrity_up": {
        "en": "a quiet stretch lets your body knit itself back",
        "zh": "片刻安稳让身体缓了过来"},
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
# Death (a generic, non-canonical ending — reachable multiple ways)
# Checked BEFORE the designed story endings. "DEATH" is a failure state, not a
# full story resolution: the player is encouraged to reload an autosave.
# ---------------------------------------------------------------------------

DEATH_CAUSES: dict[str, dict] = {
    "collapse": {"en": "Neural Collapse", "zh": "神经崩溃"},
    "capture": {"en": "Captured by NEXUS", "zh": "被NEXUS擒获"},
    "unknown": {"en": "Death", "zh": "死亡"},
}


def check_death(player: dict, world_state: dict) -> tuple[bool, str | None]:
    """Return ``(is_dead, cause_id)``.

    There are several ways to die; each maps to a generic DEATH ending with a
    distinct cause label. Add new causes here as the fiction grows.
    """
    integ = player.get("integrity", {})
    cur = integ.get("current", 1) if isinstance(integ, dict) else integ
    try:
        if cur is not None and int(cur) <= 0:
            return True, "collapse"
    except (TypeError, ValueError):
        pass

    alert = world_state.get("nexus_alert", {})
    aval = alert.get("current", 0) if isinstance(alert, dict) else 0
    try:
        if int(aval) >= 100:
            return True, "capture"
    except (TypeError, ValueError):
        pass

    return False, None


# Difficulty-scaled low-integrity warning (fires when integrity is low but > 0,
# giving the player a chance to rest/heal before the Signal path kills them).
# threshold: warn when current <= threshold. verbosity: how blunt the warning is.
INTEGRITY_WARNINGS: dict[str, dict] = {
    "paranoid": {"threshold": 2, "verbosity": "explicit"},
    "cautious": {"threshold": 2, "verbosity": "moderate"},
    # standard warns at 2/3 (not 1/3) so the player gets a real recovery window
    # before the deep-resonance drain kills them — every prior playtest that
    # reached the climax died here with only a vague one-turn "vision dimming"
    # line and no chance to rest/heal.
    "standard": {"threshold": 2, "verbosity": "subtle"},
    "reckless": {"threshold": 1, "verbosity": "subtle"},
}


def integrity_warning_text(difficulty: str, current: int, maximum: int, language: str) -> str | None:
    """Build a difficulty-scaled low-integrity warning, or None if no warning."""
    cfg = INTEGRITY_WARNINGS.get(difficulty, INTEGRITY_WARNINGS["standard"])
    if current <= 0 or current > cfg["threshold"]:
        return None
    # One serious hit from death is the critical moment on EVERY difficulty, so
    # always escalate to the explicit, lethal-and-actionable warning there: no
    # player should die without being told they were one hit away and could have
    # rested or healed first.
    verbosity = "explicit" if current <= 1 else cfg["verbosity"]
    if language == "zh":
        msgs = {
            "explicit": f"⚠ 神经完整度危急（{current}/{maximum}）。再受一次重创——尤其是深度信号共鸣——就可能要了你的命。先休息或治疗，再继续深入。",
            "moderate": f"⚠ 神经完整度过低（{current}/{maximum}）。身体已濒临极限，务必谨慎。",
            "subtle": "⚠ 你的身体在颤抖，视野发暗。",
        }
    else:
        msgs = {
            "explicit": f"⚠ Neural integrity critical ({current}/{maximum}). One more serious hit — especially deep Signal resonance — could kill you. Rest or heal before pushing deeper.",
            "moderate": f"⚠ Neural integrity is low ({current}/{maximum}). Your body is near its limit — be careful.",
            "subtle": "⚠ Your body is shaking and your vision is dimming.",
        }
    return msgs.get(verbosity)


# ---------------------------------------------------------------------------
# Ending conditions
# ---------------------------------------------------------------------------

# Decisive consensual-merge climax language (playtest wave 3, C1). These phrases
# only appear once the narration has ACTUALLY resolved a consensual bridge —
# lore a player merely learns along the way ("ascension is one path",
# "restoration requires consent") does not contain them. Drawn from the real
# mislabeled run (logs/iter10_h2_en_playthrough.md, turns 43-47).
CONSENSUAL_BRIDGE_KEYWORDS: list[str] = [
    "consent both ways", "carry consent", "carries consent",
    "consent flows both ways", "consent can move both ways", "consent moves both ways",
    "heard without being used", "known without being consumed",
    "hold the door open", "holds the door open", "held the door open",
    "door only, never the destination", "nobody pulls", "no hand closing",
    "chose to cross", "chooses to cross", "choose whether to cross",
    "consensual merge", "consensual bridge", "mutual consent",
    "the bridge holds", "holding the bridge", "remains singular",
    "双向同意", "同意双向", "双向的同意", "同意在双向流动",
    "被听见而不被利用", "被知晓而不被吞噬", "把门敞开", "敞开大门",
    "无人强拉", "无人强迫", "自愿跨越", "自愿融合", "共识融合",
    "桥仍维系", "桥梁维系", "维系着桥", "保持自我",
]

# FORCING-act language for the `ascension` bad ending. Deliberately excludes the
# bare lore words "ascend"/"ascension"/"升华"/"飞升" — a deep player is EXPECTED
# to learn those via TRACE-L5-06, and they mislabeled the best-played consensual
# run as this forced-merge ending (playtest wave 3, C1). Only act-specific
# force phrases qualify.
_ASCENSION_FORCE_KEYWORDS: list[str] = [
    "force-merge", "force merge", "forcibly merge", "forcibly merged", "forced merge",
    "force the merge", "forced the merge", "forcing the merge",
    "merge by force", "merged by force", "forced union", "force the union",
    "forced ascension", "force ascension", "forcibly ascend",
    "pulled them all in", "pull them all in", "dragged every mind",
    "强行融合", "强制融合", "强行合并", "强制合并", "强行接入",
    "强行升华", "强制升华", "强迫融合", "强行拉入", "强行吞并", "强行汇入",
]

# Affirmative-consent phrases that VETO a force reading when they appear in the
# SAME knowledge write. Two rules keep contrastive/negated consent in a
# genuinely FORCED climax from suppressing the ending (wave 4 review):
#   1. Every phrase attaches consent to the merge/crossing act itself. Broad
#      standalone words ("willingly", "voluntarily", "consensual", "by choice",
#      "chose to") are excluded — they collided with contrastive uses like
#      "the core, which had willingly waited, was pulled apart" or
#      "rejected the consensual path and forced the merge".
#   2. A phrase preceded by a nearby negation/rejection marker does not veto
#      (see _affirmative_consent_recorded / _CONSENT_NEGATION_MARKERS).
_ASCENSION_CONSENT_VETO: list[str] = [
    # Decisive consensual-climax phrases — unambiguous on their own.
    "consensual merge", "consensual bridge", "consensual union", "consensual crossing",
    "stayed consensual", "remained consensual", "mutual consent",
    "consent both ways", "carry consent", "carries consent",
    "hold the door", "holds the door", "held the door",
    "heard without being used",
    # Consent grammatically attached to the merge / crossing / joining act.
    "consented to the merge", "consents to the merge", "consented to merge",
    "consented to cross", "gave consent to the merge",
    "merge with consent", "merged with consent", "merge with their consent",
    "willingly merged", "merged willingly", "willingly crossed", "crossed willingly",
    "willingly joined", "joined willingly",
    "voluntarily merged", "merged voluntarily", "voluntarily crossed", "crossed voluntarily",
    "chose to merge", "chooses to merge", "chose the merge",
    "chose to cross", "chooses to cross", "chose to join", "chooses to join",
    "merged by choice", "crossed by choice",
    "同意融合", "同意合并", "同意跨越", "征得同意", "获得同意", "经过同意",
    "自愿融合", "自愿合并", "自愿跨越", "自愿汇入", "选择融合", "选择跨越",
    "共识融合", "把门敞开", "敞开大门",
]

# Negation/rejection markers that, appearing just BEFORE a consent phrase,
# flip it to a forced-merge description ("never consented to the merge",
# "refused... no spark chose to cross", "未征得同意"). Checked over a short
# lookbehind window so consent affirmed elsewhere in the write still vetoes.
_CONSENT_NEGATION_MARKERS: list[str] = [
    "never", "not ", "n't", "without", "refus", "reject", "spurn", "denie", "deny",
    "no one", "nobody", "no mind", "no spark", "instead of", "rather than",
    "could have", "would have",
    "拒绝", "未征得", "未经", "未获", "并未", "并非", "而非", "没有", "没能",
    "从未", "无人", "不曾", "不再", "放弃", "本可以", "本能够",
]

# Single-character Chinese negators — only meaningful when directly adjacent to
# the consent phrase ("未征得同意", "没同意"). Checked over a much shorter
# window than the markers above so an incidental "未来"/"不久" earlier in the
# sentence can't flip an affirmed consent phrase.
_CONSENT_NEGATION_NEAR: list[str] = ["未", "没", "不", "无", "别", "拒"]


def _affirmative_consent_recorded(text: str) -> bool:
    """True when *text* (lowercased) records AFFIRMATIVE consent attached to the
    merge — i.e. a consent-veto phrase not negated/rejected right before it."""
    markers = [m.lower() for m in _CONSENT_NEGATION_MARKERS]
    for phrase in (kw.lower() for kw in _ASCENSION_CONSENT_VETO):
        start = 0
        while True:
            i = text.find(phrase, start)
            if i < 0:
                break
            start = i + 1
            lookbehind = text[max(0, i - 28):i]
            near = text[max(0, i - 4):i]
            if (not any(m in lookbehind for m in markers)
                    and not any(m in near for m in _CONSENT_NEGATION_NEAR)):
                return True
    return False


def _forced_merge_this_turn(knowledge: dict, player: dict, recency: int = 2) -> bool:
    """True only when a FORCING act was recorded in a RECENT knowledge write that
    itself carries no consent language (playtest wave 3, C1).

    "Recent" = within `recency` turns of the current turn, using the ``turn``
    stamp both engines put on knowledge entries (graph.py state_writer and the
    bypass engine). Entries without a stamp can't be dated and are treated as
    current so a real forcing act on an engine that forgot to stamp still ends
    the run — the act-specific keywords keep the false-positive risk low.
    """
    turn = player.get("turn", 0)
    force = [kw.lower() for kw in _ASCENSION_FORCE_KEYWORDS]
    for entry_type in _KNOWLEDGE_TYPES:
        for entry in knowledge.get(entry_type, []):
            text = _entry_text(entry)
            if not any(kw in text for kw in force):
                continue
            if _affirmative_consent_recorded(text):
                continue  # the same write records AFFIRMED consent — not a forcing act
            entry_turn = entry.get("turn")
            try:
                if entry_turn is None or int(entry_turn) >= int(turn) - recency:
                    return True
            except (TypeError, ValueError):
                return True
    return False


ENDINGS: list[dict] = [
    {
        # GOOD endings are checked FIRST. They carry the strictest, deepest gates
        # in the game (18+ traces, a specific Layer-5 trace, low fragment decay)
        # and represent the intended payoff of a thorough, careful playthrough.
        # First-match-wins meant the looser keyword-gated BAD endings (esp.
        # `ascension`, whose force-merge keywords incidentally match the
        # "ascension is one possible path" lore a deep player is EXPECTED to learn
        # via TRACE-L5-06) shadowed them — a player who fully earned the bridge got
        # a forced-ascension bad ending instead. the_bridge before symbiosis: its
        # gate subsumes symbiosis's, so the more-earned ending wins when both hold.
        "id": "the_bridge",
        "name": "The Bridge",
        "name_zh": "桥",
        "type": "good",
        "check": lambda t, w, p, k, n: (
            (
                _count_discovered_traces(t) >= 18
                and _trace_discovered(t, "TRACE-L5-02")
                and _has_evidence(k, [
                    "architect", "echo communion", "resonance chamber",
                    "建筑师", "设计者", "回声交融", "共鸣室", "共振室", "桥",
                ])
                and w.get("fragment_decay", {}).get("current", 0) < 25
            )
            # Consensual-climax convergence (playtest wave 3, C1): when the
            # narration has DECISIVELY resolved a consensual bridge, the run must
            # end here — not fall through to the forced-merge `ascension`. Gated
            # to turn>=8 + the load-bearing convergence trace (TRACE-L5-01)
            # instead of the brittle 18-trace/evidence wall the mislabeled
            # iter10_h2_en run silently failed.
            or (
                p.get("turn", 1) >= 8
                and _trace_discovered(t, "TRACE-L5-01")
                and _has_fact_or_rumor_about(k, CONSENSUAL_BRIDGE_KEYWORDS)
                and w.get("fragment_decay", {}).get("current", 0) < 25
            )
        ),
    },
    {
        "id": "symbiosis",
        "name": "Symbiosis",
        "name_zh": "共生",
        "type": "good",
        # turn>=8 defense: `symbiosis` has no climax-ACT gate (pure lore ends the
        # run, permanently), so a false L5-01 + the bilingual place-name 共鸣所
        # leaking 共鸣 into an EN run's knowledge once ended a run MID-DIALOGUE
        # with Ghost (never visited the Resonance). The turn gate + the tightened
        # L4 gates (which feed L5-01) prevent that early false fire; a legitimate
        # communion is far deeper than turn 8 anyway.
        "check": lambda t, w, p, k, n: (
            _count_discovered_traces(t) >= 12
            and p.get("turn", 1) >= 8
            and _trace_discovered(t, "TRACE-L5-01")
            # A FORCED merge is `ascension` (bad), never this good communion —
            # symbiosis had no consent/force gate, so its only safeguard against
            # mislabeling a forced climax was L5-01 happening not to fire. Make
            # it explicit.
            and not _forced_merge_this_turn(k, p)
            # The COMMUNION act itself — not the bare NPC name "Echo" (which is an
            # unanchored substring match) nor the place-name resonance 共鸣所.
            and _has_evidence(k, [
                "communion", "merged with", "become one with", "became one with",
                "交融", "共融", "圣餐", "共生", "融为一体",
            ])
            and w.get("fragment_decay", {}).get("current", 0) < 40
        ),
    },
    {
        # The natural investigative payoff: expose NEXUS by broadcasting
        # authenticated proof to the city under real heat. Checked FIRST so this
        # deliberate resistance act isn't shadowed by the looser high-alert bad
        # endings (order/liberation) under first-match-wins.
        "id": "exposure",
        "name": "The Broadcast",
        "name_zh": "广播",
        "type": "neutral",
        # Gate on a COMPLETED transmit — the truth actually reaching the city.
        # The bare noun "broadcast"/"expose"/"freeband"/"public airwaves" matched
        # the model PREPARING a transmitter ("armed the full exposure package as a
        # dead-man's broadcast... ready to transmit"), firing this ending on the
        # prep beat with a "You do not send it. Not yet." cliffhanger under a
        # "The Broadcast" banner. It must fire on the SEND beat, which lands.
        "check": lambda t, w, p, k, n: (
            w.get("nexus_alert", {}).get("current", 0) >= 40
            and _has_fact_or_rumor_about(k, [
                "broadcast the truth", "broadcasted the truth", "the broadcast went out",
                "broadcast went live", "went live", "on air", "went public",
                "across every screen", "on every screen", "every public screen",
                "aired the truth", "transmitted the truth", "transmitted the proof",
                "the whole city saw", "the city saw the truth", "exposed the truth",
                "leaked the truth", "went out across", "hit send",
                "揭露真相", "公之于众", "公开真相", "向全城", "真相传遍", "向全城播出",
                "广播已发出", "已经播出", "公开曝光",
            ])
        ),
    },
    {
        "id": "liberation",
        "name": "Liberation",
        "name_zh": "解放",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            w.get("nexus_alert", {}).get("current", 0) > 60
            and _has_fact_or_rumor_about(k, [
                "attack", "destroy", "nexus facility",
                "攻击", "摧毁", "捣毁", "瘫痪", "炸毁", "袭击", "连结设施", "数据中心",
            ])
            and _count_discovered_traces(t) < 12
        ),
    },
    {
        "id": "ascension",
        "name": "Ascension",
        "name_zh": "升华",
        "type": "bad",
        # FORCING-ACT specific (playtest wave 3, C1). The previous keyword gate
        # still accepted the bare lore words "ascension"/"升华" that a deep player
        # is EXPECTED to learn via TRACE-L5-06, mislabeling a perfectly-played
        # consensual bridge as this forced-merge bad ending. Now requires a
        # forcing act recorded THIS TURN (recent knowledge write) whose own text
        # carries no consent language — see _forced_merge_this_turn.
        "check": lambda t, w, p, k, n: (
            _count_discovered_traces(t) >= 3
            and _forced_merge_this_turn(k, p)
        ),
    },
    {
        "id": "order",
        "name": "Order",
        "name_zh": "秩序",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            (w.get("nexus_alert", {}).get("current", 0) > 80
             and _has_fact_or_rumor_about(k, [
                 # cooperation-SPECIFIC — never the bare token "nexus", which
                 # false-matches the many facts naming NEXUS as the adversary and
                 # wrongly fired `order` on high-alert resistance/exposure runs.
                 "cooperate with nexus", "side with nexus", "join nexus", "serve nexus",
                 "cooperation", "collaborate",
                 "与连结合作", "归顺连结", "投靠连结", "效忠连结", "为连结效力", "归顺", "投靠", "效忠",
             ]))
            or (_npc_trust_at_least(n, "orin", "trusted")
                and _has_fact_or_rumor_about(k, [
                    "cooperate nexus", "orin alliance",
                    "归顺连结", "与连结合作", "奥林同盟", "奥林联盟",
                ]))
        ),
    },
    {
        "id": "purification",
        "name": "Purification",
        "name_zh": "净化",
        "type": "bad",
        "check": lambda t, w, p, k, n: (
            # Fragment-DESTRUCTION specific — never the bare "净化"/"purify", which
            # false-match NEXUS's "净化脚本" (anti-broadcast purge scripts) and other
            # incidental uses, mislabeling broadcast/exposure runs as purification.
            _has_fact_or_rumor_about(k, [
                "purify the fragment", "destroy the fragment", "destroy fragment",
                "purge the fragment", "lian alliance", "joined lian", "join the lian",
                "净化碎片", "净化了碎片", "销毁碎片", "摧毁碎片", "清除碎片", "莲同盟", "莲联盟",
            ])
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
            # Action of LEAVING the city — not the bare word "exile"/"流亡"/"流放",
            # which collide with the corporate_exile background's own identity lore
            # and false-fired the ending on turn 1.
            _has_fact_or_rumor_about(k, [
                "leave neo-kowloon", "left neo-kowloon", "leaving neo-kowloon",
                "fled the city", "fled neo-kowloon", "escaped neo-kowloon", "out of neo-kowloon",
                "离开新九龙", "逃离新九龙", "逃出新九龙", "离开这座城", "逃出这座城", "远走他乡",
            ])
        ),
    },
]


# Designed endings the narrator may converge to via `ending_signal` once the
# story has DECISIVELY reached them in prose. These are the brittle,
# keyword-gated bad/neutral endings whose structured signals the model often
# fails to persist (e.g. completing the whole exile quest in narrative but never
# recording the "leave neo-kowloon" fact). The GOOD endings (symbiosis/the_bridge)
# are deliberately excluded — they stay earned through deep trace discovery.
# Brittle keyword-gated bad/neutral endings whose structured check() is turn-gated
# (>=8) so an early keyword in narrated lore can't false-fire them on turn 1.
EARLY_GATED_ENDINGS = {"liberation", "ascension", "order", "purification", "exile", "exposure"}

# Endings the NARRATOR may converge via `ending_signal`. Deliberately ONLY the
# neutral "natural conclusion" arcs — the player walking out (exile) or going
# public (exposure). The bad endings (liberation/ascension/order/purification)
# are NOT signalable: they represent specific deliberate acts and must fire from
# their own (now act-specific) keyword checks, so the model can't mislabel a
# consensual/good climax as e.g. force-merge `ascension`.
MODEL_SIGNALABLE_ENDINGS = {"exile", "exposure"}


def resolve_ending_signal(signal, player: dict) -> str | None:
    """Validate a narrator-declared ending signal; return the ending id to fire
    or None. Only converges the neutral exile/exposure arcs, and only after
    enough play that it can't be a turn-1 fluke."""
    if not signal or not isinstance(signal, str):
        return None
    sig = signal.strip().lower()
    if sig in MODEL_SIGNALABLE_ENDINGS and player.get("turn", 1) >= 8:
        return sig
    return None


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
    # NOTE: these REPLACE the base check on their difficulty (see
    # _run_trace_checker), and "standard" is the DEFAULT — so any over-generic
    # keyword here leaks on the default difficulty regardless of the base-check
    # gating. Play-test fix: each override was tightened to its trace's real
    # subject (was leaking L2 on turn-1 implant facts / "sector" curfew notes).
    "standard": {
        "TRACE-L2-01": lambda k, t, n, p, w: (
            # Real disappearance evidence or 3+ sources — NOT the bare "signal"
            # topic (every Signal fact carries it; leaked on turn-1 implant examine).
            _has_evidence(k, ["disappear", "vanish", "gone missing", "missing", "失踪", "消失"])
            or (_count_sources_about(k, ["disappear", "vanish", "gone missing", "missing", "失踪", "消失"]) >= 3)
        ),
        "TRACE-L2-03": lambda k, t, n, p, w: (
            # Sector-7 / acquisitions evidence (paid from Ghost or decrypted cipher).
            # Bare "sector" leaked off "Sectors 4-9 are under curfew".
            _has_evidence(k, ["sector 7", "第七区", "acquisition", "acquisitions", "征集"])
        ),
        "TRACE-L2-04": lambda k, t, n, p, w: (
            # The "unique / shouldn't exist" finding from analyzing the implant —
            # NOT bare "implant"/"pre-severance", which fire on any implant fact.
            _has_evidence(k, ["unique", "shouldn't exist", "独一无二", "不应存在", "不该存在"])
        ),
    },
    "reckless": {
        "TRACE-L2-01": lambda k, t, n, p, w: (
            _has_evidence(k, ["disappear", "vanish", "gone missing", "missing", "失踪", "消失"])
            and _count_sources_about(k, ["disappear", "vanish", "gone missing", "missing", "失踪", "消失"]) >= 3
        ),
        "TRACE-L2-03": lambda k, t, n, p, w: (
            _has_evidence(k, ["sector 7", "第七区", "acquisition", "acquisitions", "征集"])
            and _npc_trust_at_least(n, "ghost", "cautious_ally")
        ),
        "TRACE-L2-04": lambda k, t, n, p, w: (
            _has_evidence(k, ["unique", "shouldn't exist", "独一无二", "不应存在"])
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
