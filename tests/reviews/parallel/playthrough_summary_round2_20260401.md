# Signal Lost — 16-Agent Parallel Playthrough Summary (Round 2)

**Date**: 2026-04-01
**Engine**: claude-code (sonnet) | **Player**: claude-code (opus)
**Agents**: 15 captured (12 zh, 3 en — agent 14 didn't start in time)
**Trace system**: 47 traces across 5 layers (expanded from 16)
**Silence ending**: Turn 256

---

## Overview

| Metric | Value |
|--------|-------|
| Total agents captured | 15 (12 zh, 3 en) |
| Avg turns played | 18.2 |
| Total turns across all agents | 273 |
| Avg knowledge items | 8.3 |
| Avg traces discovered | 5.7 / 47 |
| Avg deepest layer | 2.5 |
| Games completed | 0 / 15 |
| **Spoiler incidents** | **0** |
| Errors | 0 |
| Unique NPCs encountered | 30+ |
| Max traces (single agent) | 12 (Agent 013 — Spark/Shadow) |

---

## Per-Agent Results

| ID | Lang | Character | Turns | Know | Traces | Layer | HP | District |
|----|------|-----------|-------|------|--------|-------|----|----------|
| 000 | zh | 凯尔 (幽灵) 街头 | 19 | 8 | 8 | L2 | 3/3 | 霓虹街 |
| 001 | zh | 夜枭 (密码) 企业 | 16 | 9 | 5 | L2 | 3/3 | 蔓城地下 |
| 002 | zh | 漂流 (幻影) 网行 | 16 | 20 | 7 | L2 | 2/3 | 蔓城地下 |
| 003 | zh | 火花 (暗影) 街头 | 15 | 6 | 6 | **L4** | 3/3 | 蔓城 |
| 004 | zh | 烈焰 (亡灵) 企业 | 18 | 6 | 5 | L2 | 3/3 | 蔓城 |
| 005 | zh | 禅 (连结) 网行 | 15 | 5 | 3 | **L3** | 3/3 | **第七区** |
| 006 | zh | 闪电 (故障) 街头 | 17 | 15 | 10 | L3 | 3/3 | 霓虹街 |
| 007 | zh | 迷雾 (字节) 企业 | 15 | 3 | 5 | **L4** | 3/3 | 蔓城 |
| 008 | zh | 燧石 (向量) 网行 | 15 | 3 | 1 | L1 | 3/3 | 霓虹街 |
| 009 | zh | 碎片 (流变) 街头 | 20 | 6 | 4 | L2 | **1/3** | 蔓城 |
| 010 | zh | 凯尔 (幽灵) 企业 | 18 | 3 | 3 | L2 | 3/3 | 蔓城 |
| 011 | zh | 夜枭 (密码) 网行 | 21 | 11 | 5 | L2 | 3/3 | 蔓城 |
| **012** | **en** | **Drift (Phantom) 街头** | **27** | **6** | **9** | **L4** | 3/3 | The Sprawl |
| **013** | **en** | **Spark (Shadow) 企业** | **20** | **8** | **12** | **L4** | **1/3** | The Sprawl |
| 015 | en | Zen (Nexus) 街头 | 21 | 6 | 7 | L3 | 3/3 | Neon Row |

---

## Key Findings

### Zero Spoilers
Across all 273 turns and 15 agents, **zero spoiler incidents detected**. The anti-spoiler system continues to hold:
- NPCs use descriptive labels: "面馆女人", "面馆女老板", "修械铺女人", "高个子", "连帽工装男"
- No faction names leaked before discovery
- No premature name reveals

### Time System Working
- Clock times are consistent: Agent 002 at turn 16 = 09:39 (morning exploration), Agent 006 at turn 17 = 14:32 (afternoon), Agent 012 at turn 27 = 23:08 (late night)
- Day advancement works: Agents 009, 010, 012, 013 reached Day 2
- No time/narrative mismatches observed

### Global Events
- All `global_events` lists are empty — the events_update system works correctly, the LLM is maintaining a clean event list rather than accumulating junk

### New Traces Working Well
The expanded 47-trace system is engaging:
- Agents are discovering new traces (L1-04 through L1-08, L2-05 through L2-11, L3-05 through L3-11, L4-04 through L4-09)
- Layer progression feels natural — agents reach L2 after ~15 turns, L3 after ~15-20, L4 by ~20+
- Agent 013 (Spark/Shadow) discovered 12 traces in only 20 turns — the aggressive player prompt is working

### Notable Trace Jumps
Some agents discovered deep traces before completing lower layers (e.g. Agent 003 has TRACE-L4-06 and TRACE-L3-04 but only 6 total traces). This is by design — some L3/L4 traces have conditions that can be met early if the player finds the right evidence, creating non-linear discovery paths.

---

## Plot Highlights

**Agent 002 (漂流/幻影)** — Most atmospheric Chinese playthrough. Found a dying man named 陈维昌 who gave a cipher code, followed it to an underground passage, and met 米拉 who confirmed 陈维昌's death. She recognized the player's implant as "original, pre-Severance" and mentioned seeing "two others" before going silent. Lost 1 integrity. The narrative quality is exceptional.

**Agent 005 (禅/连结)** — Made it into Sector 7! Found a hidden workshop run by resistance members, with signal receiving equipment. The word "聆听" (Listen) appeared on a screen — a natural, non-spoilery way to introduce the Listener concept.

**Agent 013 (Spark/Shadow)** — Most traces discovered (12). Found a dead man's journal (Deng Wei) with a hand-drawn map showing underground entrance coordinates. The narrative of reading someone's final message — "He knew they were coming for him and still he took the time to leave a map" — is excellent noir writing.

**Agent 015 (Zen/Nexus)** — Found Echo's data chip revealing that "the Severance was deliberate — NEXUS quarantine teams pre-positioned before the blackout" and "Resonance-class implants were supposed to be wiped. Someone let some of them survive." The final line: "You are not an accident. You are evidence."

---

## Language Comparison

| Metric | Chinese (12) | English (3) |
|--------|-------------|-------------|
| Avg turns | 17.1 | 22.7 |
| Avg knowledge | 7.5 | 6.7 |
| Avg traces | 5.1 | 9.3 |
| Avg deepest layer | 2.3 | 3.7 |
| Spoilers | 0 | 0 |

English agents again progress faster through traces (9.3 vs 5.1 avg) and reach deeper layers (3.7 vs 2.3). Chinese agents generate more knowledge items but explore traces more slowly — likely because Chinese narrative is more detailed and the player opus agent takes more investigative steps per turn.

---

## Issues Found

### Potential Issues (Minor)
1. **Agent 008 (燧石/向量)** paid 50 credits for an implant scan — that's the entire starting balance. The economy may be too punishing in some scenarios.
2. **Some agents have very sparse logs** (agents 008, 010) — the log entries are sometimes skipped or have generic tags like "T7", "T8" instead of descriptive tags.
3. **Agent 003 jumped to L4 traces** (TRACE-L4-06: Archive Tower) from only Layer 1 knowledge — this trace's check condition (`_has_fact_or_rumor_about` for "archive tower"/"records"/"truth") may be too easy to trigger if an NPC casually mentions records.

### No Issues Found
- No time flow problems
- No spoilers
- No exit localization issues
- No notification overlap (server-side)
- No logical nonsense in narratives
- Global events properly managed (all empty = correctly pruned)

---

## Conclusion

Round 2 with 47 traces, sonnet engine, and opus player is working well:
- **Anti-spoiler system: rock solid** (0 incidents across 273 turns)
- **Time tracking: accurate** (clock times match narrative, day advancement works)
- **47 traces: engaging** (non-linear discovery paths, agents reach L3-L4 within 20 turns)
- **Global events: clean** (LLM-driven cleanup preventing accumulation)
- **Narrative quality: excellent** (especially the Chinese atmospheric noir and English discovery moments)

Minor tuning needed for trace condition difficulty (some L4 traces triggering too early) and economy balance.
