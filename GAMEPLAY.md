# How to Play Signal Lost

*Signal Lost* (信号遗失) is a cyberpunk knowledge-roguelike. You wake in Neo-Kowloon with
no memory and an implant that hears something in the static. There is no combat and no XP —
the only thing that levels up is **what you understand**. You progress by discovering facts,
verifying rumors, decoding ciphers, and stitching clues into theories that crack open new
districts, doors, and conversations.

This guide has two parts:

- **[Part 1 — Human Players](#part-1--human-players)** — how to set up and play in the browser.
- **[Part 2 — Agent Players](#part-2--agent-players-claude-code--codex)** — the protocol an
  AI agent (assume **Claude Code** or **Codex** in almost all cases) must follow when it
  plays the game for testing, review, or a full narrated run.

---

## Part 1 — Human Players

### 1. Install

Requires **Python 3.13+** and [**uv**](https://docs.astral.sh/uv/).

```bash
uv sync
```

### 2. Pick a narrator (LLM provider)

The story is told live by a language model. Configure one in `settings/provider.json`:

```json
{ "provider": "anthropic", "model": "claude-sonnet-4-6-20250514", "temperature": 0.7 }
```

| Provider | Auth | Notes |
|----------|------|-------|
| `anthropic` | `ANTHROPIC_API_KEY` in `.env` | |
| `openai` | `OPENAI_API_KEY` in `.env` | |
| `openrouter` | `OPENROUTER_API_KEY` in `.env` | one gateway, many models (`vendor/model`) |
| `lmstudio` | none | local model, no API cost |
| `claude-code` | Claude Code CLI OAuth (`claude /login`) | no API key |
| `codex` | Codex CLI OAuth (`codex login`) | no API key |

### 3. Launch the browser GUI

```bash
uv run gui/run_gui.py               # opens in your browser
uv run gui/run_gui.py --port 8080   # custom port
uv run gui/run_gui.py --no-open     # don't auto-open
```

### 4. Create an account / log in

The GUI is multi-user. On first visit, **register** a username + password (min 4 chars), or
**log in** if you already have one. Each account gets a stable id (`u1`, `u2`, …) that
namespaces your data on disk — your sessions live in `session/<uid>/` and your saves in
`saves/<uid>/`, so multiple players on the same backend never overwrite each other. Sign-in
tokens last 30 days, so a browser refresh keeps you logged in.

### 5. Start a game

Pick a character background — each opens with different knowledge, contacts, and gear:

- **Street Runner** — knows the undercity.
- **Corporate Exile** — knows how NEXUS thinks.
- **Netrunner** — knows the dead network.

Choose a **difficulty** (`paranoid` → forgiving, `cautious`, `standard`, `reckless` → brutal)
and a **language** (English / 中文, switchable mid-game).

### 6. Play a turn

Type what you want to do in plain language ("ask the fixer about the implant", "examine the
terminal", "head to Neon Row") and submit. The narrator resolves it and the dashboard updates:

- **Knowledge** — facts you've learned (this is your real progress bar).
- **Traces** — 16 hidden discoveries across 5 layers; your `deepest_layer` gates what the
  story will reveal.
- **Integrity** — your hold on yourself; if it hits 0 you collapse (a death ending).
- **NEXUS alert** — how much the corp has noticed you; at 100 you're captured.
- **Inventory / Credits / Location / Time**.

Core mechanics: **talk** (every major NPC runs on trust, loyalty, and knowledge gates — they
can guide you, betray you, or feed you the wrong thing) and **theorize** (stitch discoveries
into a theory; a true one opens new paths, a wrong one tips your hand).

### 7. Suggested actions ("quick actions")

If enabled, after each turn the game offers up to 3 short suggested next actions as clickable
buttons. They are grounded only in what you can currently see — never spoilers. Click one to
take it, or ignore them and type your own. Toggle them in **Settings**
(`features.suggested_actions`, `features.suggested_actions_count`). With `predict_outcome` on,
the game pre-computes likely outcomes so a clicked suggestion feels instant.

### 8. Save & load

- **Autosave** runs every `gameplay.auto_save_turns` turns (default **5**).
- **Save** manually any time from the UI (creates a named snapshot under `saves/<uid>/`).
- **Resume** picks up your live session; **Load** restores a chosen save.

### 9. How the game ends

The game ends when you reach one of several endings (checked every turn in
`engine/game_data.py`). Most endings *look* like victory; few actually are. There are bad
endings (e.g. *liberation*, *ascension*, *order*, *purification*), neutral ones (*silence* at
the turn cap, *exile*), and genuine good endings (*symbiosis*, *the_bridge*) that require deep
trace counts and specific layer-5 discoveries — they cannot be stumbled into by luck. You can
also die early by **collapse** (integrity ≤ 0) or **capture** (NEXUS alert ≥ 100). When the
game is over, the ending text shows and no further actions are accepted.

---

## Part 2 — Agent Players (Claude Code / Codex)

This section is a **playbook**. When an AI agent plays Signal Lost, it must follow the rules
below. Assume the agent is **Claude Code** or **Codex** in almost all cases. The goal of an
agent playthrough is two-fold: (a) actually *play and finish* the game, and (b) *evaluate* it —
producing a written critique, a bug report, and improvement suggestions.

### 2.0 Two ways to play

| Mode | Interface | Use when |
|------|-----------|----------|
| **GUI (recommended)** | Drive the browser via the preview/automation tools | You want the **full** evaluation: frontend layout/interaction, real "quick action" buttons, and screenshots. This is the default. |
| **Headless** | File-polling protocol (`tests/scripts/play_headless.py`) | You only need a fast **backend-logic** run and can't drive a browser. No UI, so no layout-bug detection or screenshots. |

**GUI mode** — launch the server headlessly and connect the preview:

```bash
uv run gui/run_gui.py --no-open --port 8080
```

Then use the `preview_*` tools (`preview_start` → `http://localhost:8080`, `preview_snapshot`,
`preview_click`, `preview_fill`, `preview_screenshot`, `preview_console_logs`,
`preview_network`) to register an account, start a game, read each turn, and act.

**Headless mode** — run the engine and exchange JSON files in `session/headless/`:

- Write your move to `player_action.json`: `{"action": "<text>", "turn": <N>}`.
- Read the result from `game_response.json`: `{"narrative", "turn", "game_over", "ending",
  "state_summary"}`.
- Watch `engine_status.json` (`waiting` → `processing` → `done`).
- The engine increments the turn after each response; finish when `game_over` is `true`.
- Note: headless `game_response.json` does **not** surface suggested-action buttons and the
  headless runner does **not** autosave — see §2.3 and §2.4 for how to compensate.

### 2.1 Pre-play interview (ask the user FIRST, then persist every answer)

Before starting a run, ask the user the questions below and **record every answer** to a config
file (see §2.2). Use the `AskUserQuestion` tool. Do not start playing until these are answered.

1. **Save cadence** — "Every how many turns should I save?" → an integer `N` (default 5).
2. **Quick actions** — "Should I use the precomputed suggested ('quick') actions while
   playing?"
   - If **yes**: "What percentage of my turns should just pick a suggested action vs. compose
     my own move?" → an integer `0–100`.
   - If **never**: disable the feature in settings (see §2.3) — don't merely avoid clicking.
3. **Account / session name** — "What account (or session) name should I play under?" Required
   if more than one agent will play (see §2.5).
4. (Optional) **Character background, difficulty, language, provider** — defaults are
   netrunner / standard / en / whatever `settings/provider.json` already says.

> **Rule:** *Every* question you ask the user during setup or play must have its answer written
> to the config JSON (§2.2). The config is the single source of truth for the run.

### 2.2 Play-log folder (where everything goes)

Create one folder per run and keep all artifacts there. Convention:

```
logs/agent_plays/<session_name>/
├── play_config.json     # all user answers + run metadata (REQUIRED, write first)
├── summary.md           # running pros/cons critique, finalized at game end
├── improvements.md      # suggestions for improving the game
├── bugs/
│   ├── bugs.jsonl       # one JSON object per bug (machine-readable index)
│   └── BUG-<id>.md      # one rich write-up per bug (human-readable)
├── screenshots/         # PNGs of genuinely interesting moments + bug evidence
└── transcript.md        # turn-by-turn record (or link to logs/headless_playthrough.md)
```

**`play_config.json` schema:**

```json
{
  "session_name": "claude-run-01",
  "agent": "claude-code",
  "started_at": "2026-06-15T10:00:00Z",
  "mode": "gui",
  "account": { "username": "claude-run-01", "uid": "u2" },
  "save_every_turns": 5,
  "suggested_actions": { "enabled": true, "quick_action_percentage": 40 },
  "character": { "background": "netrunner", "difficulty": "standard", "language": "en" },
  "provider": { "provider": "codex", "model": "gpt-5.5", "temperature": 0.7 },
  "answers_raw": { "save_cadence": "5", "quick_actions": "yes, 40%", "account": "claude-run-01" }
}
```

If you ask the user anything new mid-run, append it to `answers_raw` and update the relevant
top-level field.

### 2.3 Quick-actions policy

- **Yes + percentage P:** On each turn, with probability `P%` take one of the suggested actions
  offered for the current scene; otherwise compose your own move. Keep it honest over the run
  (e.g. P=40 ≈ 4 of every 10 turns are a clicked suggestion). In GUI mode the suggestions are
  the buttons under the input; in headless mode they aren't surfaced, so emulate them by
  occasionally choosing a short, obvious next action instead.
- **Never:** Disable the feature, don't just avoid it. Set in `settings/custom.json`:

  ```json
  { "features": { "suggested_actions": false } }
  ```

  (`settings/custom.json` overrides `settings/default.json`. A per-session
  `session_settings.json` in the session dir overrides global if present.)

### 2.4 Save cadence

Save every `save_every_turns` turns, per the user's answer.

- **GUI mode:** set `gameplay.auto_save_turns` to `N` in `settings/custom.json` *and* trigger a
  manual save from the UI on the same cadence as a belt-and-suspenders snapshot.
- **Headless mode:** the headless runner does **not** autosave, so you must snapshot yourself —
  every `N` turns copy the live session dir to a timestamped backup:

  ```bash
  cp -r session/<session_name> "saves/<session_name>/turn_$(printf '%03d' "$N")"
  ```

Record the chosen `N` in `play_config.json`.

### 2.5 Account / session isolation (one identity per agent)

Always play under a **dedicated identity** so runs don't interfere. When **multiple agents**
play (e.g. parallel reviewers), give **each one its own** identity:

- **GUI mode:** register a separate account per agent. Each account's `uid` namespaces its data
  to `session/<uid>/` and `saves/<uid>/` — different agents cannot collide.
- **Headless mode:** the bundled `play_headless.py` hardcodes the session name `headless`. For
  multiple concurrent headless agents, give each its own session directory
  (`session/<session_name>/`) — copy/adapt the runner so `HEADLESS_SESSION_NAME` /
  `SESSION_DIR` is unique per agent, and never let two agents share one session dir.

Never reuse another agent's account, session dir, or save dir.

### 2.6 Handling chat-API rate limits / quota exhaustion

The narrator runs on an LLM. If its quota or rate limit runs out, the turn will surface an error
(GUI shows an error banner; headless writes `[ENGINE ERROR: ...]` into `game_response.json`).
When this happens:

1. **Do not abandon the run.** Pause and wait for the API to come back.
2. **Poll every 10 minutes** until it recovers — use the `Monitor` tool (or an
   `until`-loop with `sleep 600`) so you're notified when it's alive again, rather than busy-
   waiting. A lightweight liveness check is a single cheap turn/request; if it still errors,
   wait another 10 minutes and retry.
3. Once the API responds normally, **resume from the last good turn** (reload the autosave /
   session snapshot if the failing turn corrupted state) and continue.
4. Log the outage window (start, end, retries) in `summary.md`.

### 2.7 Always play to the end

A run is only complete when the game reaches an ending (`game_over: true` with an `ending`
id) or a death (collapse / capture). **Do not stop early** because the story got slow, an
error occurred (see §2.6 — wait and resume), or you "got the idea." Play every turn through to
a genuine ending, then finalize the summary, bugs, and improvements.

### 2.8 Screenshots (sparingly — only the genuinely notable)

GUI mode only. Capture a screenshot with `preview_screenshot` and save it to
`screenshots/` in **two** cases only:

1. **A genuinely exciting moment** — a major reveal, a dramatic ending, a striking scene. Be
   *selective*: a handful across a whole run, not one per turn.
2. **Bug evidence** — anything that demonstrates a defect. Bugs are not only backend logic
   errors; capture **frontend** ones too: broken layout, overlapping/clipped text, misaligned
   panels, a button that does nothing, broken interaction or state, missing/garbled
   (e.g. unescaped) text, or anything that looks wrong on screen.

Name files `turn-<N>-<short-slug>.png` and reference them from the relevant bug write-up or the
summary. Do not over-capture; screenshots are evidence, not a scrapbook.

### 2.9 Bug reports (how to write and store them)

When you hit a bug, record it in **both** places: a JSON line for indexing and a Markdown file
for detail. A bug may be a **backend logic error** (wrong state, broken trace/ending check,
crash, nonsensical mechanic), a **frontend layout error** (broken/clipped/overlapping UI), a
**frontend interaction error** (unresponsive button, stuck input, wrong update), a
**content/narrative** error (contradiction, spoiler leak, language/format slip), or
**performance** (hang, excessive latency).

**Append one line to `bugs/bugs.jsonl`:**

```json
{"id":"BUG-20260615-01","timestamp":"2026-06-15T10:42:00Z","turn":12,"severity":"major","category":"frontend-layout","title":"Knowledge panel overflows on long fact names","summary":"Long fact strings clip outside the panel and overlap the trace list.","steps_to_reproduce":["Reach >6 known facts","Open the Knowledge panel"],"expected":"Facts wrap or scroll within the panel","actual":"Text overflows and overlaps adjacent panel","evidence":{"screenshot":"screenshots/turn-12-knowledge-overflow.png","console_log":null,"response_file":null,"log_excerpt":null},"state_context":{"location":"the_sprawl — rain_alley","integrity":"2/3","traces":4,"turn":12},"suggested_fix":"Add overflow:auto + word-break to .knowledge-panel","status":"open"}
```

**Field spec:**

| Field | Meaning |
|-------|---------|
| `id` | `BUG-YYYYMMDD-NN`, unique per run |
| `timestamp` | ISO-8601 UTC |
| `turn` | turn number when observed |
| `severity` | `blocker` \| `major` \| `minor` \| `cosmetic` |
| `category` | `backend-logic` \| `frontend-layout` \| `frontend-interaction` \| `content` \| `performance` \| `other` |
| `title` | one-line label |
| `summary` | 1–3 sentences |
| `steps_to_reproduce` | ordered list |
| `expected` / `actual` | the contrast that makes it a bug |
| `evidence` | `{screenshot, console_log, response_file, log_excerpt}` — fill what applies (console/network logs from `preview_console_logs`/`preview_network`; `game_response.json` excerpt in headless) |
| `state_context` | `{location, integrity, traces, turn}` at the time |
| `suggested_fix` | optional pointer at the likely cause/fix |
| `status` | `open` (this run only reports; it does not fix) |

**Also write `bugs/BUG-<id>.md`** with the same facts in prose plus the embedded screenshot
(`![](../screenshots/turn-12-knowledge-overflow.png)`) and any console/network output. The
JSONL is the index; the Markdown is the readable write-up.

### 2.10 Pros/cons summary (always write one)

Maintain `summary.md` throughout the run and finalize it at game end. Required sections:

- **Run overview** — character, difficulty, provider, turns played, ending reached, any API
  outages.
- **Pros** — what worked: pacing, writing quality, mechanics that felt good, standout moments
  (link screenshots).
- **Cons** — what dragged: confusing UI, weak pacing, unclear mechanics, repetition.
- **Balance/difficulty notes** — did integrity / NEXUS alert / trace gating feel fair?
- **Bugs** — short list linking to `bugs/bugs.jsonl` entries.
- **Verdict** — would you recommend it, and to whom.

Be specific and cite turns. "Turn 14's reveal landed" beats "the story was good."

### 2.11 Improvement suggestions (separate from bugs)

A **bug** is something broken; an **improvement** is something that works but could be better.
Keep these in `improvements.md`, each as:

- **Area** (e.g. onboarding, suggested actions, dashboard, narration, difficulty curve).
- **Current behavior** — what it does today.
- **Proposed change** — concrete and actionable.
- **Rationale** — the player-experience win.
- **Priority / effort** — `high|med|low` value vs. `S|M|L` effort.

Ground suggestions in what you actually experienced during the run, and point at the relevant
module where you can (`engine/prompts.py`, `gui/static/`, `engine/game_data.py`, etc.). Flag
anything you'd otherwise mention as a "by the way" here rather than acting on it yourself.

### 2.12 Agent checklist

- [ ] Ran the pre-play interview; wrote **every** answer to `play_config.json`.
- [ ] Created a dedicated account/session (one per agent if running in parallel).
- [ ] Applied save cadence `N`; disabled `suggested_actions` if the user said "never".
- [ ] Played **every turn to a real ending** — no early stop.
- [ ] On API limits: waited and re-checked every 10 min with a monitor, then resumed.
- [ ] Captured screenshots only for genuinely exciting moments and bug evidence.
- [ ] Logged bugs to `bugs/bugs.jsonl` + `bugs/BUG-*.md` with full evidence.
- [ ] Finalized `summary.md` (pros/cons) and `improvements.md`.
