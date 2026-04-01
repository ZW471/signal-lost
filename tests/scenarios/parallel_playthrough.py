#!/usr/bin/env python3
"""
Signal Lost — Parallel Playthrough Test

Runs N agents in parallel, each playing up to max_turns or until game over.
Generates an LLM-driven player that makes autonomous decisions.
Writes per-agent logs and a combined summary.

Usage:
    python tests/scenarios/parallel_playthrough.py [--agents N] [--turns N]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)


# ---------------------------------------------------------------------------
# Player agent prompts (agentic player that makes its own decisions)
# ---------------------------------------------------------------------------

_PLAYER_PROMPT_EN = """\
You are an autonomous player of Signal Lost, a cyberpunk mystery RPG.
Your goal is to aggressively explore, uncover every secret, and reach a game ending.

Strategy — be PROACTIVE and AGGRESSIVE:
- Explore EVERYWHERE: search every alley, examine every terminal, look behind every door
- Talk to EVERY NPC — ask about Signal, NEXUS, disappearances, Listeners, Sector 7
- Push NPCs hard: bribe them, present evidence, build trust, then ask deeper questions
- Travel to EVERY district you can access — don't stay in one place too long
- When you hear about a new location, GO THERE immediately
- Decrypt everything, analyze every signal artifact, resonate when Signal is strong
- Present evidence to NPCs to unlock deeper dialogue — cross-reference what different NPCs tell you
- Form theories and share them with NPCs to test reactions
- Buy intel from information brokers — spend credits aggressively
- Try to access restricted areas — find keycards, disguises, alternate routes
- When you have enough knowledge, push toward an ENDING

Based on the game's narrative response, decide your NEXT action as a player.
Respond with ONLY your action (what you want to do), nothing else.
Keep it natural — you're a character in this world, not a commander giving orders.
"""

_PLAYER_PROMPT_ZH = """\
你是一个自主玩家，正在游玩《信号遗失》——一款赛博朋克悬疑RPG。
你的目标是积极探索所有角落、揭开每个秘密，并最终达到游戏结局。

策略——积极主动，大胆探索：
- 到处探索：搜查每条巷子，检查每个终端，看看每扇门后面
- 与每个NPC交谈——询问信号、NEXUS、失踪事件、聆听者、第七区
- 积极推动NPC：贿赂他们，出示证据，建立信任，然后深入提问
- 前往每个能到达的区域——不要在一个地方停留太久
- 听到新地点就立即前往
- 解密所有东西，分析每个信号遗物，信号强的时候尝试共鸣
- 向NPC出示证据以解锁更深层对话——交叉对比不同NPC告诉你的内容
- 形成理论并与NPC分享以测试反应
- 向信息贩子购买情报——积极花费信用点
- 尝试进入限制区域——寻找钥匙卡、伪装或替代路线
- 当知识足够时，推动游戏走向结局

根据游戏的叙事回应，决定你的下一步行动。
只回答你要做的事（你的行动），不要回答其他内容。
保持自然——你是这个世界中的角色，不是发号施令的指挥官。
"""

# Diverse starting actions to avoid all agents doing the same thing
_START_ACTIONS_EN = [
    "Look around. Where am I? What do I see?",
    "I examine my surroundings carefully, checking every detail.",
    "I check myself — what do I have? What do I remember?",
    "I listen carefully. What sounds can I hear?",
    "I try to stand up and take stock of my situation.",
]

_START_ACTIONS_ZH = [
    "环顾四周。我在哪里？我看到了什么？",
    "我仔细检查周围的环境，注意每一个细节。",
    "我检查一下自己——我有什么？我记得什么？",
    "我仔细聆听。能听到什么声音？",
    "我试着站起来，审视自己的处境。",
]

_BACKGROUNDS = ["street_runner", "corporate_exile", "netrunner"]
_NAMES_EN = ["Kael", "Nyx", "Drift", "Spark", "Raze", "Zen", "Bolt", "Haze", "Flint", "Shard"]
_ALIASES_EN = ["Ghost", "Cipher", "Phantom", "Shadow", "Wraith", "Nexus", "Glitch", "Byte", "Vector", "Flux"]
_NAMES_ZH = ["凯尔", "夜枭", "漂流", "火花", "烈焰", "禅", "闪电", "迷雾", "燧石", "碎片"]
_ALIASES_ZH = ["幽灵", "密码", "幻影", "暗影", "亡灵", "连结", "故障", "字节", "向量", "流变"]


def run_single_agent(agent_id: int, language: str, max_turns: int) -> dict:
    """Run a single agent playthrough. Called in a separate process."""
    # Re-add game root to path in subprocess
    if _GAME_ROOT not in sys.path:
        sys.path.insert(0, _GAME_ROOT)

    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from engine.graph import compile_graph, set_llm
    from engine.state import create_new_session, initial_state
    from engine.llm_factory import create_llm, load_env

    load_env()

    # Create isolated session directory
    session_dir = os.path.join(_GAME_ROOT, "session", f"parallel_agent_{agent_id:03d}")
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)

    # Randomize character
    is_zh = language == "zh"
    names = _NAMES_ZH if is_zh else _NAMES_EN
    aliases = _ALIASES_ZH if is_zh else _ALIASES_EN
    name = names[agent_id % len(names)]
    alias = aliases[agent_id % len(aliases)]
    background = _BACKGROUNDS[agent_id % len(_BACKGROUNDS)]

    create_new_session(
        session_dir=session_dir,
        name=name,
        alias=alias,
        background=background,
        difficulty="standard",
        language=language,
    )

    # Create LLM — sonnet for game engine, opus for player agent
    llm = create_llm("claude-code", "sonnet")
    set_llm(llm, zero_cost=True)

    # Create a separate "player LLM" to decide actions (opus for better play)
    player_llm = create_llm("claude-code", "opus")

    graph = compile_graph()
    state = initial_state(session_dir)

    # Results
    result_data = {
        "agent_id": agent_id,
        "language": language,
        "character": f"{name} ({alias}) — {background}",
        "turns_played": 0,
        "knowledge_count": 0,
        "traces_discovered": 0,
        "deepest_layer": 0,
        "game_over": False,
        "ending": None,
        "errors": [],
        "narrative_samples": [],  # First and last 3 turns
        "spoiler_incidents": [],
        "plot_summary": "",
        "districts_visited": set(),
        "npcs_met": set(),
        "final_integrity": None,
        "final_credits": None,
        "final_alert": None,
    }

    # First action
    start_actions = _START_ACTIONS_ZH if is_zh else _START_ACTIONS_EN
    current_action = random.choice(start_actions)

    player_system = _PLAYER_PROMPT_ZH if is_zh else _PLAYER_PROMPT_EN
    player_history = []

    for turn_idx in range(max_turns):
        state["messages"].append(HumanMessage(content=current_action))

        try:
            result = graph.invoke(state)
            state = result
            result_data["turns_played"] += 1

            narrative = result.get("narrative", "")

            # Collect samples (first 3 + last 3)
            if turn_idx < 3 or turn_idx >= max_turns - 3:
                result_data["narrative_samples"].append({
                    "turn": turn_idx + 1,
                    "action": current_action,
                    "narrative": narrative[:600],
                })

            # Track state
            knowledge = state.get("knowledge", {})
            total_k = sum(len(v) for v in knowledge.values() if isinstance(v, list))
            result_data["knowledge_count"] = total_k

            traces = state.get("traces", {})
            discovered = traces.get("discovered", [])
            result_data["traces_discovered"] = len(discovered)
            if discovered:
                max_layer = 0
                for t in discovered:
                    tid = t.get("id", "")
                    parts = tid.split("-")
                    if len(parts) >= 2:
                        try:
                            max_layer = max(max_layer, int(parts[1][1:]))
                        except (ValueError, IndexError):
                            pass
                result_data["deepest_layer"] = max_layer

            location = state.get("location", {})
            district = location.get("district", "")
            if district:
                result_data["districts_visited"].add(district)

            npcs = state.get("npcs", {})
            for npc in npcs.get("npcs", []):
                result_data["npcs_met"].add(npc.get("name", ""))

            player = state.get("player", {})
            integrity = player.get("integrity", {})
            result_data["final_integrity"] = integrity.get("current") if isinstance(integrity, dict) else integrity
            result_data["final_credits"] = player.get("credits")
            world = state.get("world_state", {})
            alert = world.get("nexus_alert", {})
            result_data["final_alert"] = alert.get("current") if isinstance(alert, dict) else alert

            # --- Spoiler detection ---
            # Check if narrative mentions undiscovered factions/names
            _spoiler_keywords_layer2 = ["listener", "聆听者", "sigma council", "西格玛"]
            _spoiler_keywords_layer3 = ["proto-consciousness", "原意识", "fragment extraction", "碎片提取"]
            narrative_lower = narrative.lower()
            current_layer = result_data["deepest_layer"]
            if current_layer < 2:
                for kw in _spoiler_keywords_layer2:
                    if kw in narrative_lower:
                        result_data["spoiler_incidents"].append({
                            "turn": turn_idx + 1,
                            "type": "faction_spoiler",
                            "keyword": kw,
                            "layer_required": 2,
                            "player_layer": current_layer,
                        })
            if current_layer < 3:
                for kw in _spoiler_keywords_layer3:
                    if kw in narrative_lower:
                        result_data["spoiler_incidents"].append({
                            "turn": turn_idx + 1,
                            "type": "lore_spoiler",
                            "keyword": kw,
                            "layer_required": 3,
                            "player_layer": current_layer,
                        })

            if result.get("game_over"):
                result_data["game_over"] = True
                result_data["ending"] = result.get("ending")
                break

            # --- Generate next player action ---
            player_history.append({"role": "assistant", "content": f"[Game Response]\n{narrative[:800]}"})
            # Keep last 5 exchanges for player LLM context
            if len(player_history) > 10:
                player_history = player_history[-10:]

            try:
                player_msgs = [
                    SystemMessage(content=player_system),
                    *[
                        HumanMessage(content=m["content"]) if m["role"] == "user"
                        else AIMessage(content=m["content"])
                        for m in player_history
                    ],
                    HumanMessage(content="Based on the game's response above, what do you do next? Reply with ONLY your action."),
                ]
                player_response = player_llm.invoke(player_msgs)
                current_action = player_response.content.strip()
                player_history.append({"role": "user", "content": current_action})
            except Exception:
                # Fallback to generic exploration action
                if is_zh:
                    current_action = random.choice([
                        "继续探索周围环境",
                        "和附近的人交谈",
                        "检查周围有什么可以互动的",
                        "寻找更多线索",
                    ])
                else:
                    current_action = random.choice([
                        "Continue exploring the area",
                        "Talk to the nearest person",
                        "Look for anything interesting nearby",
                        "Search for more clues",
                    ])

        except Exception as e:
            result_data["errors"].append({
                "turn": turn_idx + 1,
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
            # Try to continue
            if is_zh:
                current_action = "环顾四周"
            else:
                current_action = "Look around"

    # Convert sets to lists for JSON serialization
    result_data["districts_visited"] = list(result_data["districts_visited"])
    result_data["npcs_met"] = list(result_data["npcs_met"])

    # Save per-agent log
    log_dir = os.path.join(_GAME_ROOT, "tests", "reviews", "parallel")
    os.makedirs(log_dir, exist_ok=True)
    agent_log = os.path.join(log_dir, f"agent_{agent_id:03d}_{language}.json")
    with open(agent_log, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    # Cleanup session
    try:
        shutil.rmtree(session_dir)
    except Exception:
        pass

    return result_data


def write_summary(results: list[dict], output_dir: str):
    """Write a comprehensive summary of all playthroughs."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    summary_path = os.path.join(output_dir, f"parallel_summary_{timestamp}.md")

    # Aggregate stats
    total = len(results)
    zh_results = [r for r in results if r["language"] == "zh"]
    en_results = [r for r in results if r["language"] == "en"]

    avg_turns = sum(r["turns_played"] for r in results) / max(total, 1)
    avg_knowledge = sum(r["knowledge_count"] for r in results) / max(total, 1)
    avg_traces = sum(r["traces_discovered"] for r in results) / max(total, 1)
    avg_layer = sum(r["deepest_layer"] for r in results) / max(total, 1)

    game_overs = [r for r in results if r["game_over"]]
    endings = {}
    for r in game_overs:
        e = r.get("ending", "unknown")
        endings[e] = endings.get(e, 0) + 1

    total_spoilers = sum(len(r.get("spoiler_incidents", [])) for r in results)
    agents_with_spoilers = sum(1 for r in results if r.get("spoiler_incidents"))
    total_errors = sum(len(r.get("errors", [])) for r in results)
    agents_with_errors = sum(1 for r in results if r.get("errors"))

    all_districts = set()
    for r in results:
        all_districts.update(r.get("districts_visited", []))

    all_npcs = set()
    for r in results:
        all_npcs.update(r.get("npcs_met", []))

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Signal Lost — Parallel Playthrough Summary\n\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Total agents**: {total} ({len(zh_results)} Chinese, {len(en_results)} English)\n")
        f.write(f"**Provider**: claude-code\n\n")

        f.write(f"## Overview\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|--------|-------|\n")
        f.write(f"| Avg turns played | {avg_turns:.1f} |\n")
        f.write(f"| Avg knowledge items | {avg_knowledge:.1f} |\n")
        f.write(f"| Avg traces discovered | {avg_traces:.1f} |\n")
        f.write(f"| Avg deepest layer | {avg_layer:.1f} |\n")
        f.write(f"| Games completed | {len(game_overs)}/{total} |\n")
        f.write(f"| Agents with errors | {agents_with_errors}/{total} ({total_errors} total errors) |\n")
        f.write(f"| Agents with spoilers | {agents_with_spoilers}/{total} ({total_spoilers} total incidents) |\n")
        f.write(f"| Districts explored | {len(all_districts)} unique |\n")
        f.write(f"| NPCs encountered | {len(all_npcs)} unique |\n\n")

        if endings:
            f.write(f"## Endings Reached\n\n")
            for ending, count in sorted(endings.items(), key=lambda x: -x[1]):
                f.write(f"- **{ending}**: {count} agent(s)\n")
            f.write("\n")

        f.write(f"## Districts Explored\n\n")
        for d in sorted(all_districts):
            count = sum(1 for r in results if d in r.get("districts_visited", []))
            f.write(f"- {d}: visited by {count}/{total} agents\n")
        f.write("\n")

        f.write(f"## NPCs Encountered\n\n")
        npc_counts = {}
        for r in results:
            for npc in r.get("npcs_met", []):
                npc_counts[npc] = npc_counts.get(npc, 0) + 1
        for npc, count in sorted(npc_counts.items(), key=lambda x: -x[1])[:20]:
            f.write(f"- {npc}: met by {count}/{total} agents\n")
        f.write("\n")

        # Spoiler analysis
        f.write(f"## Spoiler Analysis\n\n")
        if total_spoilers == 0:
            f.write("No spoiler incidents detected across all playthroughs.\n\n")
        else:
            f.write(f"**{total_spoilers} spoiler incidents** across {agents_with_spoilers} agents:\n\n")
            spoiler_types = {}
            for r in results:
                for s in r.get("spoiler_incidents", []):
                    key = f"{s.get('type', '?')}: {s.get('keyword', '?')}"
                    spoiler_types[key] = spoiler_types.get(key, 0) + 1
            for stype, count in sorted(spoiler_types.items(), key=lambda x: -x[1]):
                f.write(f"- {stype}: {count} occurrence(s)\n")
            f.write("\n")

        # Error analysis
        if total_errors > 0:
            f.write(f"## Error Analysis\n\n")
            f.write(f"**{total_errors} errors** across {agents_with_errors} agents:\n\n")
            error_types = {}
            for r in results:
                for e in r.get("errors", []):
                    err_msg = e.get("error", "unknown")[:100]
                    error_types[err_msg] = error_types.get(err_msg, 0) + 1
            for etype, count in sorted(error_types.items(), key=lambda x: -x[1])[:10]:
                f.write(f"- `{etype}`: {count} occurrence(s)\n")
            f.write("\n")

        # Per-language comparison
        f.write(f"## Language Comparison\n\n")
        f.write(f"| Metric | Chinese ({len(zh_results)}) | English ({len(en_results)}) |\n")
        f.write(f"|--------|----------|----------|\n")
        zh_turns = sum(r["turns_played"] for r in zh_results) / max(len(zh_results), 1)
        en_turns = sum(r["turns_played"] for r in en_results) / max(len(en_results), 1)
        zh_know = sum(r["knowledge_count"] for r in zh_results) / max(len(zh_results), 1)
        en_know = sum(r["knowledge_count"] for r in en_results) / max(len(en_results), 1)
        zh_traces = sum(r["traces_discovered"] for r in zh_results) / max(len(zh_results), 1)
        en_traces = sum(r["traces_discovered"] for r in en_results) / max(len(en_results), 1)
        zh_spoilers = sum(len(r.get("spoiler_incidents", [])) for r in zh_results)
        en_spoilers = sum(len(r.get("spoiler_incidents", [])) for r in en_results)
        f.write(f"| Avg turns | {zh_turns:.1f} | {en_turns:.1f} |\n")
        f.write(f"| Avg knowledge | {zh_know:.1f} | {en_know:.1f} |\n")
        f.write(f"| Avg traces | {zh_traces:.1f} | {en_traces:.1f} |\n")
        f.write(f"| Total spoilers | {zh_spoilers} | {en_spoilers} |\n\n")

        # Narrative samples from a few agents
        f.write(f"## Sample Narratives\n\n")
        sample_agents = results[:3] + results[-2:]
        for r in sample_agents:
            f.write(f"### Agent {r['agent_id']} ({r['language']}) — {r['character']}\n\n")
            f.write(f"Turns: {r['turns_played']} | Traces: {r['traces_discovered']} | ")
            f.write(f"Layer: {r['deepest_layer']} | Game Over: {r['game_over']}\n\n")
            for sample in r.get("narrative_samples", [])[:2]:
                f.write(f"**Turn {sample['turn']}** — *{sample['action']}*\n\n")
                f.write(f"> {sample['narrative'][:300]}...\n\n")
            f.write("---\n\n")

    print(f"\nSummary saved to: {summary_path}")

    # Also save raw JSON
    json_path = os.path.join(output_dir, f"parallel_results_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Raw data saved to: {json_path}")

    return summary_path


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Parallel Playthrough")
    parser.add_argument("--agents", type=int, default=40, help="Total agents (default: 40)")
    parser.add_argument("--turns", type=int, default=100, help="Max turns per agent (default: 100)")
    parser.add_argument("--zh", type=int, default=30, help="Chinese agents (default: 30)")
    parser.add_argument("--en", type=int, default=10, help="English agents (default: 10)")
    parser.add_argument("--workers", type=int, default=8, help="Parallel workers (default: 8)")
    args = parser.parse_args()

    total = args.zh + args.en
    print("=" * 60)
    print("Signal Lost — Parallel Playthrough Test")
    print(f"Agents: {total} ({args.zh} Chinese, {args.en} English)")
    print(f"Max turns: {args.turns}")
    print(f"Workers: {args.workers}")
    print("=" * 60)
    print()

    # Build agent configs: first N are Chinese, rest English
    agent_configs = []
    for i in range(args.zh):
        agent_configs.append((i, "zh", args.turns))
    for i in range(args.en):
        agent_configs.append((args.zh + i, "en", args.turns))

    # Run in parallel
    results = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(run_single_agent, cfg[0], cfg[1], cfg[2]): cfg[0]
            for cfg in agent_configs
        }

        for future in as_completed(futures):
            agent_id = futures[future]
            try:
                result = future.result()
                results.append(result)
                elapsed = time.time() - start_time
                lang = result["language"]
                turns = result["turns_played"]
                traces = result["traces_discovered"]
                errors = len(result.get("errors", []))
                spoilers = len(result.get("spoiler_incidents", []))
                status = "GAME OVER" if result["game_over"] else "IN PROGRESS"
                print(f"  Agent {agent_id:03d} [{lang}] done: {turns} turns, "
                      f"{traces} traces, {errors} errors, {spoilers} spoilers, "
                      f"{status} ({elapsed:.0f}s)")
            except Exception as e:
                print(f"  Agent {agent_id:03d} CRASHED: {e}")
                results.append({
                    "agent_id": agent_id,
                    "language": "?",
                    "character": "CRASHED",
                    "turns_played": 0,
                    "knowledge_count": 0,
                    "traces_discovered": 0,
                    "deepest_layer": 0,
                    "game_over": False,
                    "ending": None,
                    "errors": [{"turn": 0, "error": str(e)}],
                    "narrative_samples": [],
                    "spoiler_incidents": [],
                    "districts_visited": [],
                    "npcs_met": [],
                    "final_integrity": None,
                    "final_credits": None,
                    "final_alert": None,
                })

    total_elapsed = time.time() - start_time
    print(f"\nAll agents complete in {total_elapsed:.0f}s")

    # Sort by agent_id
    results.sort(key=lambda r: r.get("agent_id", 0))

    # Write summary
    output_dir = os.path.join(_GAME_ROOT, "tests", "reviews", "parallel")
    os.makedirs(output_dir, exist_ok=True)
    write_summary(results, output_dir)


if __name__ == "__main__":
    main()
