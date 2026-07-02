# Signal Lost — `fable-improvement` Campaign Report

**Branch:** `fable-improvement` (branched from `main` @ `75fdc9e`)
**Span:** 39 commits, 9 review-gated waves
**Diff vs `main`:** 17 files changed, +8479 / −1055 lines
**Test status at close:** smoke 7/7, regression 25/25, good-ending reachability all-pass, `node --check gui/static/app.js` clean, `import gui.server` clean

This report is for the maintainer. It records what the campaign set out to do, what each wave shipped, the outcomes that were measured, the full list of bugs fixed, the known gaps that remain open, and how to run and test the result. No claims here are unmeasured; validation figures are cited to the artifact that produced them.

---

## 1. Goals

The branch had two tracks running against the same code:

1. **Gameplay / narrative quality** (engine + prompts + game data). Fix the concrete complaints surfaced by the wave-3 model sweep and the iteration playthroughs: prose repetition, meters that changed without an explained cause, a guidance rail that never taught a mechanic, a "walled-off" deep-layer trace system that plateaued median players, no transient-error retry, and — the single worst defect — a well-played consensual-bridge ending being **mislabeled** as the bad forced-merge `ascension`.

2. **GUI / client quality** (FastAPI WebSocket server + single-page frontend). Turn a functional-but-fragile browser client into something robust and legible: a real HUD, a layered trace panel, turn-lifecycle hardening (cancel, reconnect, account-wide locking), error-recovery UX, accessibility, responsive layout, XSS-hardened narration rendering, a coherent 7-tab panel IA, and a single source of truth for bilingual strings.

Two hard constraints held throughout: **everything player-visible is bilingual EN/中文**, and **nothing undiscovered ever reaches the client** (spoiler gating). The WebSocket protocol was kept strictly **additive** — unknown frame types are non-fatal on the client.

---

## 2. Wave-by-wave summary

Each wave shipped feature commits followed by a `Wave N review fixes` commit (an internal review gate applied before moving on). Commits below are in chronological order (`git log main..HEAD --reverse`).

### Wave 1 — Foundation & turn lifecycle
- `e82bbe7` Harden GUI WS server: per-frame JSON guard, generic error frames, save-name collision handling, dead-socket-safe finalizer.
- `db5c271` Frontend visual foundation + CJK typography.
- `03b9add` Harden turn lifecycle + socket robustness; skippable (client-side) narration.
- `1b9e9fa` HUD redesign: 3-zone status bar, banded gauges, in-world clock.
- `1b7ba5f` Layered Trace Ladder + Descent depth gauge (flagship trace panel).
- `f89597c` Wave 1 review fixes.

### Wave 2 — Shared chrome & error-recovery UX
- `24c2526` Shared dialog chrome: z-index tokens, ARIA, focus trap, deterministic stacking.
- `4c6e28a` Wave 2b: unified toast stack + discovery ceremony.
- `91984eb` Wave 2c: error-recovery UX — in-flight input locks, retry card, degraded-mode chip.
- `4c67bfb` Wave 2d: teaching empty states, tutorial resize/scroll robustness, AA contrast pass.
- `05a7638` Wave 2 review fixes.

### Wave 3 — Server robustness & input ergonomics
- `80a3544` Server robustness: executor I/O, LLM-slot snapshot, reconnect resync, first `state_delta` frames.
- `4fbfcfa` `data-i18n` chrome hardening + button/chip sizing (w3a).
- `a255fcd` Wave 3b GUI: input history + verb chips + cheat-sheet, unified SFX bus, companion hardening.
- `d6fb22b` Wave 3 review fixes.

### Wave 4 — Narrative quality (the gameplay track)
- `b4d093e` Wave 4 resolver prompt: anti-repetition directive, meter-causality directive, one-verb teaching suggestions, director-note (never-quote) envelope.
- `19bfa59` Wave 4: roll-beat frame, meter `reason` fields, CLI transient-error retry, headless NEXUS fix.
- `4fc0c29` Wave 4 frontend: roll chips, meter-why causality display, `state_delta` verify.
- `6650762` Fix good-ending mislabel: consensual bridge converges `the_bridge`, not `ascension`.
- `6aa71aa` Wave 4 review fixes.

### Wave 5 — Turn heartbeat, panel IA, responsive & security
- `faba1c7` Server: turn-phase heartbeat + cancel (w5c server side).
- `366bfa4` GUI wave-5a: NPC contact cards, tab IA regroup (9 → 7 tabs), save metadata cards.
- `9ce6ffd` Wave 5b frontend: tablet drawer threshold, **XSS-hardened narration renderer** (DOM-node building, no `innerHTML`), a11y polish.
- `b572c06` GUI wave-5c client: wire the turn-phase heartbeat + cancel button.
- `e22f928` Wave 5 review fixes.

### Wave 6 — Reachability find + concurrency integration
- `a67ee89` Menu RESUME button: expose the previously-**unreachable** resume path.
- `4c53014` Wave 6 integration fixes (three cross-wave concurrency/lifecycle defects — see §4).

### Wave 7 — Save management, backlog close-out
- `47efb80` Rate-limit the implant image bilingually; give ambient meter moves a diegetic cause; add act-on-evidence trace unlocks (closes §5 items 2–4 from the wave-6 backlog).
- `926042d` Save management: implement the `delete_save` WS action; expose save `mtime`/day/location; F2 ambient-decrement reasons (closes §5 item 1).
- `558e9c8` Wave 7 review fixes.

### Wave 8 — Resume starvation, disconnect leak, meta-progression
- `380ac38` Fix resume/turn starvation behind the world-sim lock; player-turn priority on the account lock.
- `5a17830` Server: per-account endings-discovered history + district-map data shape.
- `3e65541` Frontend: endings gallery, unlocked-district constellation map, resume skeleton.
- `229f1e4` Wave 8 review fixes (disconnect-cleanup leak + orphan-CLI reaper).

### Wave 9 — Copy, code-health, QA
- `d57e098` Bilingual copy pass (terminology coherence, tone, punctuation; `?v=` w8a→w9a).
- `2abcf03` Code-health sweep (dead LABELS keys, dead JS/CSS/imports).
- `a92c428` QA fixes (unknown-WS-action bilingual error ack).

---

## 3. Validated outcomes

Full method and per-turn artifacts are in
`scratchpad/playtest_wave6_validation.md` (two 20-turn playthroughs — one EN, one 中文 — on the canonical `DEFAULT_ACTIONS` script, driven through the real codex-CLI bypass turn; narrative graded with the repo's own `grade_narratives.py` rubric and an anonymous codex judge; ending-correctness validated deterministically via the no-LLM regression + reachability suites). Headline: **both runs finished all 20 turns with 0 fatal errors**; the 中文 run survived two live transient CLI stream drops on turn 6 via auto-retry — the exact wave-3 failure that had killed a run on turn 1.

| Metric | Baseline | Wave-6 result | Verdict |
|---|---|---|---|
| (a) Prose repetition — "rain/雨" per turn | 3.18 | EN 0.10 / 中文 0.35 | Improved (large) |
| (b) Meter legibility — moves with an in-world cause | 0% | 100% EN (11/11) / 86% 中文 (6/7) | Improved |
| (c) Teaching — turns with exactly one verb-teaching suggestion | never | 7 EN / 6 中文 | Improved |
| (d) Discovery depth by turn 20 | plateau L2–L3 | L4 both langs (L3×4 EN / L3×3 中文) | Improved |
| (e) Director-note / meta leaks into prose | common in sweep | 0 EN / 0 中文 | Improved (clean) |
| (f) Transient-error retry | run died turn 1 | survived 2 retries live | Improved |
| Ending mislabel (consensual bridge) | → `ascension` (bad) | regression-pinned → `the_bridge` (good) | Fixed |
| Narrative grade (codex judge, anon) | best-band only | 8 (EN) / 9 (中文) | Improved |

Notes on the figures:
- **(b)** Causes are concrete and diegetic ("the terminal logged your query", "交通探头记录了扫描"). The one 中文 miss was a passive ambient −1 alert settle with no player action to attribute — a known gap, not a regression (see §5).
- **(d)** Both languages reach Layer 3–4 within 20 turns, closing the wave-3 "walled-off deep" complaint. A caveat is logged in the validation doc: the substring-keyword trace checker still fires the odd early false-positive (`TRACE-L3-07` keys on "level/深层"), so *deepest-layer* is a slightly generous number; the by-layer counts are the honest read.
- **Ending correctness** cannot be organically reached in a scripted 20-turn run (endings need a 40+ turn climax), so it is validated by replaying the real iter10 climax fixture in `regression.py` and by `good_ending_reachability.py`.

---

## 4. Bugs fixed

### 4.1 Wave-6 integration audit — three cross-wave defects (`4c53014`)

These emerged only once the wave-4/5 features co-existed:

1. **[major] Cancel-turn was architecturally dead.** The `/ws` endpoint's single receive loop is suspended awaiting the turn, so a mid-turn `cancel_turn` frame sat unread in the socket buffer until the turn ended on its own. Fix: `_run_turn` now spawns a concurrent frame reader for exactly the executor-await window — `cancel_turn` flips `sess.cancel_requested` immediately (the pre-commit abort seam finally fires), other frames are requeued onto `sess.pending_frames` and replayed in order, and a mid-turn disconnect is re-raised as `WebSocketDisconnect` so normal cleanup runs.
2. **[minor] `game_over` left the composer enabled behind the overlay.** `endTurnUI` re-enables input and the inline Enter handler bypasses the modal key router, so Enter during the 2s pre-overlay beat sent another `player_input` and played past the ending. Fix: the `game_over` handler now calls `disableInput()`.
3. **[critical] Force-kick/reconnect created two unsynchronized writers.** A reconnect bound a new `PlayerSession` (fresh `threading.Lock`) to the **same** on-disk session dir while the old turn thread was still writing `player.json`/`knowledge.json`/… → torn/lost writes. Fix: the turn lock is now **account-wide** (`_turn_lock_for` keyed by uid), shared across superseded and replacement sessions; `_kick` requests a cooperative cancel of the orphaned turn; resume/load/autoresume/new-game read (or restore/rmtree) session files under that lock with a bounded acquire (bilingual busy error on timeout); and the prediction fast-path degrades to a cache miss instead of blocking on a held lock.

### 4.2 Unreachable RESUME path (`a67ee89`)

`resumeGame()`, the session picker, the server `resume` action, and the bilingual `menu_resume` label all already existed — but **no UI element ever called them**. A player who closed the tab mid-game could only recover via an explicit save. Fix: added the RESUME menu button, shown when the status payload lists live sessions, hidden on logout.

### 4.3 Ending mislabel (`6650762`, hardened in `game_data.py`)

The worst wave-3 gameplay bug: under first-match-wins, the looser keyword-gated bad endings (especially `ascension`, whose force-merge keywords incidentally matched the "ascension is one possible path" lore a deep player is *expected* to learn) shadowed the earned good ending, so the best-played consensual run resolved to the forced-merge bad ending. Fixes:
- GOOD endings are checked **first** with the strictest, deepest gates.
- `ascension`'s keyword list now **excludes** the bare lore words (`ascend`/`ascension`/`升华`/`飞升`) and requires act-specific force-merge phrasing.
- A set of decisive **consensual-merge** climax phrases routes to `the_bridge`, with affirmative-consent phrases that veto a force reading when they appear in the same knowledge write.
- Pinned by `regression.py` ("iter10 consensual bridge climax resolves to the_bridge, not ascension" and "Forced merge → ascension; lore word / consent / stale act do not fire it") and by `good_ending_reachability.py`.

### 4.4 Narrative-quality defects (Wave 4)

- **Prose repetition** — anti-repetition directive added to the resolver prompt (rotate sensory register; rain/neon/implant-hum at most once every few turns). Measured effect: rain per turn dropped ~9–30×.
- **Unexplained meter moves** — meter-causality directive + tool `reason` fields; 17 of 18 meter moves across both validation runs now carry an in-world cause.
- **Guidance rail never taught a mechanic** — one-verb-per-turn teaching suggestion, grounded in the player's actual inventory.
- **Director-note leaks** — a "never quote" envelope; 0 bracketed/meta leaks across 40 validation narratives.
- **No transient-error retry** — `full_playthrough._is_transient_error` and `gui/server._is_transient_cli_error` now triage transient CLI failures (TLS handshake EOF, connection reset, read timeout) as retryable while treating content errors and bare completed-budget timeouts as terminal. Survived two live drops in validation.
- **Headless NEXUS fix** — corrected in the same wave.

### 4.5 Server & client robustness (Waves 1–3, 5)

Fixed across the earlier waves and their review gates:
- WS server: per-frame JSON guard, generic (non-leaking) error frames, save-name collision handling, dead-socket-safe finalizer.
- Turn lifecycle + socket robustness; reconnect resync; executor I/O and LLM-slot snapshot hardening.
- Error-recovery UX: in-flight input locks, retry card, degraded-mode chip.
- **XSS-hardened narration renderer** (`9ce6ffd`): replaced the `innerHTML` narration renderer with strict DOM-node building (`createElement` + `textContent`), so untrusted narration can never inject markup; swapped inline `onerror` handlers for `addEventListener`.
- **Cancelled-turn context leak** (`e22f928`): the rejected `HumanMessage` append on a pre-commit abort is now reverted so the rejected input no longer leaks into the next turn's LLM context (covers play and resume/blocked-input paths).
- **Double-announce / typewriter fragment storm** (`e22f928`): `#chatMessages` uses a non-live `role="region"` landmark; a single visually-hidden `aria-live="polite"` mirror (`#chatLiveRegion`) is the only announcer.

### 4.6 Waves 8–9 (`558e9c8..HEAD`)

**Resume/turn starvation behind the world-sim lock — root cause + player-priority locks (`380ac38`).** Live incident (`u18`, codex bypass): a resume delivered no narrative for 8+ minutes — no phase frames, no error, just silence. Root cause chain: Wave 6 made the turn lock **account-wide** and handed *the same lock* to `WorldSimScheduler`; a background sim tick that fired around the resume grabbed the lock first and held it through its own CLI LLM call (codex: up to 3×300s), while the resume turn queued behind it invisibly — phase frames are only emitted once the turn body already holds the lock, so the queued resume was mute. Fix — player-visible turns now take **priority** on the account lock:
- Player turns / resume / load / new-game / cached-action clicks register in a per-account `_player_waiting` counter for their acquire+hold.
- The scheduler gets a `_BackgroundSimLock` facade instead of the raw lock: it refuses to start a tick while a player turn is pending, try-acquires with a 0.25s timeout (contended → skip, the loop reschedules), and backs off if a player turn arrives mid-acquire.
- A player turn that still finds the lock held (a tick already inside its LLM call cannot be preempted) immediately emits a `world` phase + bilingual "background simulation in progress" system notice instead of waiting in silence.
- Prediction `_make_base` acquire is bounded (5s) so background speculation can never pin an executor thread behind a slow holder.
- Verified: resume now runs the same phase-emitting path as a normal turn (the mid-turn frame reader is spawned for resume turns too); pinned by a stub-lock regression test ("Player turns take priority over world-sim on the account lock").

**Disconnect-cleanup leak — session + scheduler survived an ordinary close (`229f1e4`).** On a plain client disconnect, a socket close racing a server send is swallowed inside `_safe_send`, leaving starlette's `application_state` = DISCONNECTED; the endpoint's next `receive_text()` then raised a bare `RuntimeError` (not `WebSocketDisconnect`), which fell into the generic error branch and **skipped `_on_disconnect()`** — leaking the `PlayerSession` registration (forcing a spurious `session_conflict` on reconnect) and the `WorldSimScheduler` thread. Fix: the WS loop now routes a `RuntimeError` on a no-longer-connected socket through `_on_disconnect()`; a `RuntimeError` on a live socket still hits the generic bilingual error path (extracted to `_report_ws_loop_error`). Companion fix in the same commit: orphaned `codex exec` / `claude -p` children survived server kill because `_run_cli_pg` starts them in their own session (`start_new_session`), so shutdown signals never reached them — added `tests/scripts/cli_process_registry.py` (every live CLI child registers on Popen, `kill_all()` SIGKILLs the remaining process groups on the FastAPI shutdown hook, with an `atexit` fallback for non-server embedders).

**Endings gallery — meta-progression (`5a17830` server, `3e65541` client).** Server: each reached ending is persisted to `session/<uid>/endings_discovered.json`, once per distinct id (first-reach wins), atomic temp+`os.replace` in an executor thread, best-effort so it never breaks the `game_over` path. The `status` payload (and the `game_over` frame) gained `endings_discovered:[{id,name,name_zh,turn}]` resolved against `game_data.ENDINGS` for **reached designed endings only**, plus `endings_total`. The generic "death" failure state is stored but never occupies a named slot; no unreached ending id/name is ever shipped. Client: an ENDINGS menu entry opens a 3×3 grid — reached slots show the localized name + reached-on/turn with a depth-tinted glow, every other slot is a sealed `▓ ???` drawn from the count alone. On `game_over`, a newly-discovered ending shows a `◈ NEW ENDING RECORDED` line on the overlay. Spoiler-safety and corrupt-file self-heal are pinned by four new regression tests.

**District constellation map (`5a17830` data, `3e65541` client).** No district adjacency/topology exists in engine data, so **no `district_map` field was fabricated** (that would leak invented topology) — instead the existing client-visible shape (`world_state.district_access` = unlocked `{name,name_zh,status,notes}`; sealed districts stay behind the hidden `_district_registry`, stripped by `_filter_hidden`) was documented and pinned by a regression test. The WORLD tab renders a compact SVG map of **unlocked districts only**, on a deterministic id-hash-seeded radial layout (stable across renders), current district pulse-ringed; clicking a non-current node prefills the composer with a bilingual travel phrase (never auto-sends). Absent/empty `district_access` leaves the rest of the WORLD tab untouched.

**Code-health sweep (`2abcf03`).** Zero-behavior-change dead-code removal: 11 never-read `LABELS` keys (EN+ZH parity preserved at 304 each), `countDiscoveredTraces()` (no call sites), provably-dead CSS selectors (`.trust-*` superseded by `.npc-trust-*`, orphaned `.npc-entry` hover rules, etc.), and an unused `SETTINGS_DIR` import in `server.py`.

**Bilingual copy pass (`d57e098`).** Terminology coherence + tone + punctuation over all user-facing copy (`app.js` LABELS + `server.py` strings), **values only, keys unchanged**: unified 中文 NEXUS to the Latin brand everywhere (the old 连结 renderings collided with the connection/link vocabulary); unified the neural-link channel-state term to 链路 (feature name 神经链接 preserved); dropped corporate 请 from imperative/terse strings to hold the in-world terminal voice; normalized chrome ellipsis to `…`. `?v=` bumped w8a→w9a.

**QA fix (`a92c428`).** An unknown authed WS action now gets a bilingual error ack instead of silence — the game-action if/elif chain ended at `refresh` with no trailing `else`, so a well-formed frame with an unrecognized action fell off the end and the client hung waiting for a reply. Added a final `else` sending `{"type":"error","message":"Unknown action. / 未知操作。"}`; the loop continues as before.

**Final test counts (Wave 9 close).** smoke **7/7**, regression **25/25**, `node --check gui/static/app.js` clean, `import gui.server` clean. (Regression grew from 17 → 25 across Waves 8–9: +4 endings/district-access fixtures in `5a17830`, +1 player-priority-lock fixture in `380ac38`, plus the Wave-7 trace/meter fixtures.)

The internal review gates (`Wave N review fixes`) collectively closed the running bug audit across all nine waves; the items above are the load-bearing ones. See the individual review-fix commit messages for the full per-wave list.

---

## 5. Known gaps / backlog

**Closed since Wave 6:** items 1–4 below were the wave-6 open gaps; Wave 7 (`47efb80`, `926042d`) implemented `delete_save` + save `mtime`/day/location (item 1), attached diegetic causes to ambient meter decrements (item 2), rate-limited the implant image and added act-on-evidence trace unlocks (items 3–4). Item 6's map half shipped in Wave 8 (`3e65541`, unlocked-district constellation). They are retained here as the record of what was outstanding at the wave-6 close and what remains.

Still carried forward:

1. ~~**Save deletion is unimplemented (coming-soon stub).**~~ *Closed in Wave 7 (`926042d`): `delete_save` WS action implemented; `_list_saves` now exposes `mtime` (+ day/location) so save cards show true relative timestamps.*
2. ~~**Ambient meter decreases ship without a cause.**~~ *Closed in Wave 7 (`47efb80`): ambient decrements now carry a short default diegetic cause so no meter move is mute. The deterministic `ALERT_INCREASES` nudge on recurring investigative triggers landed in the same commit.*
3. ~~**"Implant/植入" is the lone over-used image.**~~ *Closed in Wave 7 (`47efb80`): implant added to the "at most once every few turns" rate-limited-image clause.*
4. **Trace cadence is keyword-luck and front-loaded.** *Partially closed in Wave 7 (`47efb80`): act-on-evidence unlocks add a non-keyword mid/late discovery source, and the over-broad `TRACE-L3-07` list now requires co-occurrence with sector-7/lab terms. Residual: the substring-keyword checker is still the primary channel and front-loads gain in the first ~10 turns.*
5. **Streaming narrative** — narration is delivered per-turn as a completed block with a client-side typewriter, not token-streamed from the model. A true streaming path is a known stretch item, not implemented.
6. **Codex panel** — no codex/lore browser panel; noted as a stretch, out of scope this branch. (The world-**map** half shipped in Wave 8 as the unlocked-district constellation; a full topology/adjacency map is still out of scope, since no district adjacency exists in engine data.)

---

## 6. How to run and test

```bash
uv sync                                          # install deps (uv, Python 3.13+)

# Run the game
uv run gui/run_gui.py                             # browser GUI (primary interface)
uv run gui/run_gui.py --port 8080
uv run tests/scripts/play_headless.py             # headless, for agentic testing

# Tests — the docs-only change in this campaign's final commit must keep these green
uv run tests/scenarios/smoke_test.py              # 7 tests, no LLM
uv run tests/scenarios/regression.py              # 25 tests, no LLM (ending-correctness + priority-lock + endings/district fixtures)
uv run tests/scenarios/good_ending_reachability.py # no LLM
uv run tests/scenarios/full_playthrough.py --turns 20  # needs a configured provider

# After any gui/static/ edit:
node --check gui/static/app.js
# After any gui/server.py or engine/ edit:
uv run python -c "import gui.server"
```

Frontend cache-busting: every `gui/static/` asset URL in `index.html` carries `?v=<tag>`; all three (`style.css`, `music.js`, `app.js`) bump together on a frontend edit. Current tag: **`w9a`**.

Provider config lives in `settings/provider.json`; OAuth CLI backends (`claude-code`, `codex`) use the single-call bypass, every API provider (incl. `openrouter`) runs the full 11-node LangGraph pipeline and must support tool calling.

---

## 7. Files touched (vs `main`)

```
CLAUDE.md                              41      OpenRouter/CLI-bypass provider notes
engine/claude_code_engine.py           42
engine/game_data.py                   517      endings/consent, traces, meter hooks, act-on-evidence unlocks
engine/prompts.py                      13      anti-repetition + meter-causality + director-note directives
engine/tools.py                       215      meter reason fields, tool wiring
gui/server.py                        1599      WS frames, cancel, priority account locks, disconnect cleanup, endings/district data, CLI reaper
gui/static/app.js                    3653      HUD, panels, i18n, managers, cancel/phase, XSS-hardened render, endings gallery, district map
gui/static/index.html                 508      7-tab IA, data-i18n, RESUME + ENDINGS entries, ?v= bumps
gui/static/music.js                    84      unified SFX bus
gui/static/style.css                 1842      HUD, gauges, dialogs, responsive, gallery/map
logs/fable_improvement_report.md      193      this report
tests/scenarios/full_playthrough.py    36      transient-error retry classifier
tests/scenarios/regression.py         676      ending-correctness + L3-reach + priority-lock + endings/district fixtures
tests/scripts/claude_llm.py            14      CLI process registration
tests/scripts/cli_process_registry.py  79      orphan-CLI reaper
tests/scripts/codex_llm.py             14      CLI process registration
tests/scripts/play_headless_agent.py    8
```

Total: 17 files, +8479 / −1055.
