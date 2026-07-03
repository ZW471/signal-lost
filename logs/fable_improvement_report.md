# Signal Lost — `fable-improvement` Campaign Report

**Branch:** `fable-improvement` (branched from `main` @ `75fdc9e`)
**Span:** 53 commits, 16 review-gated waves
**Diff vs `main`:** 20 files changed, +9649 / −1079 lines
**Test status at close:** smoke 7/7, regression 31/31, good-ending reachability all-pass, `node --check gui/static/app.js` clean, `import gui.server` clean
**Current asset cache-bust tag:** `w12`

> **Waves 1–9** (§§1–7) are the original campaign report. **Waves 10–16** — the narrative-cadence tuning track validated turn-by-turn against the codex bypass path — are recorded in **§8**, with the honest harness trade-offs in **§8.3**. The wave-1–9 figures below are unchanged; where a later wave superseded a claim it is annotated inline (e.g. the no-totals purge notes in §1, §4.6).

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
- `1b7ba5f` Layered Trace Ladder + Descent depth gauge (flagship trace panel). *(Later reworked by the no-totals purge: bands/gauge now show reached layers + discovered counts only — no per-layer denominators, no fixed 5-segment gauge.)*
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

**Endings gallery — meta-progression (`5a17830` server, `3e65541` client).** Server: each reached ending is persisted to `session/<uid>/endings_discovered.json`, once per distinct id (first-reach wins), atomic temp+`os.replace` in an executor thread, best-effort so it never breaks the `game_over` path. The `status` payload (and the `game_over` frame) gained `endings_discovered:[{id,name,name_zh,turn}]` resolved against `game_data.ENDINGS` for **reached designed endings only**. The generic "death" failure state is stored but never occupies a named slot; no unreached ending id/name is ever shipped. Client: an ENDINGS menu entry opens a gallery of reached endings — localized name + reached-on/turn with a depth-tinted glow — plus one unquantified sealed `▓ ???` hint card. On `game_over`, a newly-discovered ending shows a `◈ NEW ENDING RECORDED` line on the overlay. Spoiler-safety and corrupt-file self-heal are pinned by regression tests. *(Correction — no-totals purge: this wave originally shipped `endings_total` and drew `total − reached` sealed slots from that count, calling it spoiler-safe. Under the later no-totals rule the gallery SIZE is itself undiscovered-content scope: `endings_total` no longer ships and the sealed remainder is a single count-free card.)*

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

Total (Waves 1–9): 17 files, +8479 / −1055.

The Waves 10–16 track (§8) added `engine/suggestions.py` (recent-suggestion memory + de-dupe), touched `engine/claude_code_engine.py` (bypass teaching-verb + DIRECTOR-NOTE primer), `tests/scripts/model_sweep.py` (ACTIONS re-sync), and grew `game_data.py` / `regression.py` / the frontend for the act-gated traces, death screen, and no-totals purge. Whole-branch total at close: **20 files, +9649 / −1079**.

---

## 8. Waves 10–16 — narrative-cadence tuning track

Waves 10–16 ran the gameplay/narrative track forward against a stable GUI. Every wave was graded turn-by-turn with two 20-turn playthroughs (one **EN**, one **中文**) driven through the **real codex-CLI bypass turn** (`engine/claude_code_engine.run_turn`) on the canonical `DEFAULT_ACTIONS` script, with metrics computed by per-wave `metrics_w*.py` (repetition, meter-move legibility, suggestion de-dupe/streak) and narrative grades by the repo's own `grade_narratives.RUBRIC` (anonymous codex judge). Full per-turn artifacts are in `scratchpad/playtest_wave{10,12,14,16}_validation.md`; `settings/` was git-clean at the start and end of every pass (only `session/wave*` + scratchpad artifacts written).

### 8.1 Metric trajectory (wave-6 → 10 → 12 → 14 → 16)

Figures are EN / 中文, from the graded validations. "Back-half" = traces gained T11–20; deepest = deepest *reached* layer; grade = overall on the repo rubric.

| Metric | wave-6 | wave-10 | wave-12 | wave-14 | wave-16 |
|---|---|---|---|---|---|
| Run outcome | 20/20 · 20/20 | 20/20 · 20/20 | **death@T19** · death@T20 | **20/20 SURV** · **20/20 SURV** | **death@T19** · 20/20 SURV |
| implant / turn | 0.75 / 0.55 | **0.45 / 0.00** | 0.68 / 0.40 | 0.55 / 0.25 | **0.47 / 0.10** |
| rain / neon / turn (low target) | 0.10·0.00 / 0.35·0.20 | 0.10·0.00 / 0.30·0.00 | 0.05 / 0.05 | 0.25·0.00 / 0.20·0.05 | 0.21·0.00 / 0.10·0.10 |
| Meter moves explained | 100% / 86% | **100% / 100%** | 100% / 100% | 100% / 100% | 100% (16/16) / 100% (14/14) |
| Suggestion — max identical streak | — | — | 2 / **3** | **1 / 1** | 1 / 1 |
| Back-half traces (T11–20) | 3 / 2 | **5 / 1** | 1 / **3** | 1 / 1 | **3** / 1 |
| Deepest layer reached | L4 / L4 | L4 / L4 | L3 / L4 | L4 / L3 | L4 / L3 |
| Narrative grade (overall) | 8 / 9 | 8 / 9 | 8 / 9 | 8 / 9 | 8 / 9 |
| Meta / DIRECTOR-NOTE leaks | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Scope-total / unreached-layer leaks | — | — | — | — | **0 / 0** (no-totals confirmed) |

**Reading the trajectory:** repetition kept dropping (implant reached the < 0.5/turn target in both languages by wave-16), meter legibility held at 100% both languages from wave-10 on (including passive ambient settles), and suggestion de-dupe eliminated the wave-12 中文 5×-repeat monotony (max streak 1 from wave-14 on). Narrative grades were flat at **8 EN / 9 中文** throughout — the tuning did not dent prose quality. The one thing that moved *around* rather than *up* is the survival ⇄ back-half-depth axis in the **script** — see §8.3.

### 8.2 Wave-by-wave

**Wave 10 — re-validation after waves 7–9 (`playtest_wave10_validation.md`).** No code wave of its own; a graded re-check that waves 7–9 held. Confirmed: implant rationing (friction #1) fixed to < 0.5/turn both languages (中文 essentially eliminated the image); **100% meter-move explanations in both languages** incl. ambient settles via the `AMBIENT_CAUSE_LABELS` fallback; the turn-1 L3-07 false positive gone via the co-occurrence gate. Surfaced three carry-forward frictions that drove waves 11–13: (1) the act-on-evidence route fired but was never the *deciding* unlock on the evidence-rich script; (2) 中文 discovery flat-lined T11–18; (3) `deepest_layer` still over-read via generic-phrase keyword hits (L4-06 on 中文 T2).

**Wave 11 — cadence tuning (`7e67a97`, `3fbb078`) + two user-merged bypass tasks, gated by review fixes (`5c9a130`).**
- `7e67a97` "Cadence tuning: act-gated trace, zh keyword parity, L4-06 gate": added a `_L406_SPIRE_RE` co-occurrence gate (archive/records term must share the entry with a Spire/Tower locator) so 中文 T2 mundane phrasing no longer inflates `deepest_layer` to L4; and 中文 back-half keyword parity on L2-08/L3-02/L4-09/L4-06.
- **Process note — the act-gate attempt was REFUTED by review.** The same commit tried to make `TRACE-L3-08` **act-only** (removing the passive `_has_evidence` fallback so a decrypt/analyze act became the sole unlock — the "make the act-route load-bearing" idea from the wave-10 friction). The Wave 11 review (`5c9a130`) **reverted it on evidence**: replaying the certified wave-10 sessions *and all 8 recorded sessions that ever discovered L3-08* showed the resolver files the entity-communication topic as passive NPC hearsay/observation, while the act-tagged entries cover disjoint topics — so the act gate turned **every historical unlock into a non-discovery**. The review also found the *original* act-gate regression test only exercised hand-crafted entries that co-locate act-marker + topic (a shape real play never produces), so it green-lit a broken gate. Fix: passive branch restored, wave-7 anchored-voice regex kept as the *additional* act path, and the test replaced with `test_l3_08_reachable_on_certified_wave10_knowledge` replaying the verbatim `session/wave10_{en,zh}/knowledge.json` entries. **Lesson recorded:** a cadence gate must be validated against recorded real-play knowledge, not synthetic co-located fixtures — an 8-session replay caught what a hand-crafted test missed.
- **User-merged bypass task — teaching verb (`1c48a02` → merge `ebec11e`).** Extended wave-4 C6 (teaching suggestions) to the CLI-bypass path: the bypass `suggested_actions` spec and the standalone `_SUGGEST_SYS` generator had still hard-forced "mundane and obvious," overriding the resolver `prompts.py` guidance; aligned all three so exactly one suggestion MAY surface an afforded game verb, in-world, never UI-speak.
- **User-merged bypass task — DIRECTOR NOTE primer (`9300ab5` → merge `9300ab5`/`0d69987`).** Reframed the one-time integrity primer (`_INTEGRITY_PRIMER_EN/_ZH`) from a bracketed UI-looking prefix — which weaker models pasted verbatim into narration (the top immersion complaint in the 70-model sweep) — into an explicit DIRECTOR-NOTE envelope instructing the model never to quote or paraphrase it. Semantic content unchanged; `graph.py`'s trajectory-warning site left alone per the no-`engine/graph.py`-edits campaign constraint.

**Wave 12 — graded validation (`playtest_wave12_validation.md`).** Confirmed the wave-11 targets: 中文 back-half discovery went flat(1) → **3 traces incl. a real `TRACE-L4-09`**; the L4-06 spire gate made the 中文 `deepest_layer` honest (L3-until-T15, no spurious T2 L4); the DIRECTOR-NOTE primer conveyed integrity diegetically at T4 in **both** languages with **0 meta leaks**; the teaching-verb suggestion worked and never emitted > 1 option per set. Two new frictions drove wave 13: (1) the canonical script now **alert-saturates to a `death` in both languages** (EN@T19, 中文@T20) — designed behavior, but it turns the back half into an alert-death race rather than a discovery arc; (2) the 中文 teaching rail repeated the identical *"buy a decoder tool"* nudge on **5 turns** (T9/11/12/13/15).

**Wave 13 — de-dupe + lay-low (`6b6726b`), review fixes (`9eda602`).**
- `6b6726b` "Suggestion de-dupe + canonical script lay-low beat": added a per-session `recent_suggestions.json` (last 6 turns, 3-turn window injected) threaded into **both** suggestion paths (the bypass, which sees only `conversation.jsonl`; and the LangGraph fallback, which sees only narrative + visible state) with a compact no-repeat directive — closing the wave-12 中文 5×-repeat. Same commit inserted two **lay-low alert-bleed beats** into `DEFAULT_ACTIONS` (right after the `caught_restricted` +15 spike and before the source/confront endgame stack), replacing the two lowest-value beats so the list stays at 20 and `--turns 20` still reaches the final choice.
- Review fixes (`9eda602`) re-synced `model_sweep.py` ACTIONS with `DEFAULT_ACTIONS` (so the "Mirrors" comment is true and the sweep exercises the same mitigation), and **corrected a rationale comment**: `ALERT_INCREASES` is reference-only (a `game_data.py` NOTE); alert moves only via model-volunteered `nexus_alert_delta`, so the wave-12 saturation was *model-emergent*, not a deterministic +15/+20 — an important honesty correction (see §8.3).

**Wave 14 — death screen + graded validation (`a5c67de`, `0313145`; `playtest_wave14_validation.md`).**
- `a5c67de` "Run-summary death screen + gallery detail": rebuilt the bare game-over overlay into a roguelike run epitaph — an additive `run_summary` (turns/days, deepest reached layer + its name, knowledge counts, final meters, cause + bilingual epitaph) built from the already-spoiler-filtered session data, riding the `game_over` frame and persisted per-ending so the endings gallery can re-show it. *(Note: this wave shipped the summary with a `traces_found/total` "X/47" line and a fixed 5-band depth bar; the wave-15 no-totals purge removed both — see below.)*
- Review fixes (`0313145`) set the `--depth` CSS custom property alongside the `data-depth` attribute so the depth-scaled game-over glow actually varies with `deepest_layer`; asset bump w10 → w11.
- Validation confirmed **both languages now SURVIVE 20/20** (wave-12 both died): the lay-low beats measurably arrest the alert climb (held < 90 through T18: EN 54, 中文 37), and suggestion de-dupe is **fully met** (0 consecutive repeats, 0 within-3, max streak 1 both languages). The genuine trade-off it surfaced: buying survival cost back-half depth — 中文 back-half traces fell 3 → 1 and its deepest layer L4 → L3 (EN conversely *gained* L4 by surviving long enough to reach `TRACE-L4-09`@T19). This directly motivated wave 15's script change.

**Wave 15 — canonical-script T16 social→decrypt beat (`cb7d81b`).** "Convert T16 social beat to a deep decrypt act": wave-14 validation showed survival and back-half depth in tension — the two lay-low beats that arrest alert saturation cost the back half its discovery density. Replaced the low-yield *"look for allies"* social beat at T16 with a **decrypt act** ("Decrypt any encrypted data I'm carrying — dig for what's underneath"), keeping both lay-low placements while restoring an act-driven deep beat to T11–20. `model_sweep.py` ACTIONS re-synced byte-identical.

**Wave 15 (cont.) — no-totals spoiler purge (`61a2074`).** The load-bearing wave-15 change, on an explicit **user directive**. **Root cause:** the trace/endings scaffold shipped *verbatim* to the client — the run-summary "X/47" line, per-layer "3/8" denominators, the fixed 5-segment depth gauge, and `endings_total`/`traces_total` in payloads all revealed the *size* of undiscovered content, which is itself a spoiler. The purge makes every client payload **discovered-only**:
- Server: `_present_traces` strips the persisted scaffold to `{discovered, reached_layers:[{num,name,name_zh}], title}` — no total, no per-layer denominator, no unreached-layer names; `run_summary` drops `traces_total`; endings payloads drop `endings_total` (constant deleted); stored `run_summary` blobs are scrubbed on the way out.
- Client: descent gauge grows with reached depth (+ one unquantified `▸` affordance); bands render reached layers only with bare discovered counts; one count-free `▓ ???` sealed hint; run-summary epitaph shows "Traces 14" / "L3 <name>" (no /47, no /5); endings gallery flows to content with exactly one sealed `▓ ???` card; district-map latent sealed-count path removed. Deep-layer names removed from client `LABELS` (reached names ship from the server).
- The engine scaffold (`reconcile_trace_presentation`, `LIVE_TRACE_TOTAL`, `LIVE_TRACES_PER_LAYER`) stays intact — engine-internal gating only, never transmitted.
- Tests: the two regressions that pinned `endings_total` were rewritten to assert its *absence*; a new test pins the discovered-only client payload (**regression 31**); the perf rubric now grades denominator-free bars as PASS. CLAUDE.md gained THE SPOILER RULE; asset bump w11 → w12.

**Wave 16 — confirmation (`playtest_wave16_validation.md`).** Graded validation of the T16 decrypt swap + the no-totals purge under real play. **The no-totals purge is fully confirmed:** across all 39 narrated turns, suggestions, and notices in both languages — 0 "47"/x-of-N totals, 0 "/9"/"/8" progress strings, 0 unreached-layer names; the client traces blob is exactly `{discovered, reached_layers, title}` with `reached_layers` correctly gated to reached depth (中文 at L3 correctly *hides* L4 "The Mirror"/"镜像"; EN at L4 legitimately shows it; neither shows L5 "Full Truth"/"完整真相"). Standing metrics all held (100% meter explanations, grades 8/9, 0 leaks/stalls/retry-deaths, implant now < 0.5/turn EN). The T16 swap **partially met its targets**: it lifted EN back-half traces 1 → 3 and kept EN at L4 with strong act-driven decrypt prose — but the added alert from the active decrypt/analyze beats pushed EN to an alert-100 **death@T19** (中文 absorbed the same script and survived, but its back-half depth did *not* improve — still 1 trace, still L3). That residual tension is documented honestly in §8.3.

### 8.3 Known trade-offs & harness notes

These are honest limitations of the **validation harness and canonical script**, not engine defects. They are recorded so a future maintainer reads the wave-16 numbers correctly.

- **The alert curve is model-volunteered, not deterministic.** On the codex bypass path, NEXUS alert moves *only* via the model-emitted `nexus_alert_delta` — `ALERT_INCREASES` in `game_data.py` is a **reference-only NOTE**, not a live deterministic nudge (corrected in the wave-13 review, `9eda602`). So the run-to-run alert outcome on the *identical* `DEFAULT_ACTIONS` script is genuinely variable. The graded validations show this directly: on the canonical script the model volunteered **died/died (w12) → survived/survived (w14) → died/survived (w16)** across EN/中文. The lay-low beats measurably arrest the climb every time (verified per-turn in each wave's alert-curve block), but whether the endgame confrontation tips past alert-100 depends on the model's volunteered deltas that run.
- **Survival vs back-half depth are in tension in the SCRIPT, not the engine.** The canonical script has a fixed 20-beat budget. The two lay-low beats that keep a run alive past T19 are the same beats that, in the alternative, drove the deep 中文 discoveries; converting a zero-alert social beat to an alert-bearing decrypt beat (wave 15) restored EN back-half depth (1 → 3, L4) but removed EN's survival headroom (death@T19). No single 20-beat script yet satisfies *both* "survive 20 turns, alert < 90 through T18" *and* "≥ 2 back-half traces in both languages" — it needs either a third alert-bleed beat in the T15–T18 window or an earlier endgame. This is a **beat-budget** problem in `tests/scenarios/full_playthrough.py`'s `DEFAULT_ACTIONS`; the engine mechanics (lay-low heals, alert accrues, deep traces gate on evidence) each work as designed.
- **The T16 decrypt beat yields *knowledge*, not *traces*, by design.** The decrypt act drives the knowledge-gain route (4–5 facts/evidence added to `knowledge.json` per run) but trips **0 trace `check()`s** and fires 0 discovery notifications in either language — the act-on-evidence traces (`TRACE-L4-09` etc.) fired on *other* beats. So the decrypt beat delivers *knowledge depth*, not *trace depth*. This is consistent with how traces gate (on accumulated evidence / source counts), but it means "the decrypt beat unlocked a trace" is **not** a claim the harness supports.

### 8.4 Remaining backlog (post-wave-16)

Carried forward from §5 and the wave-16 validation:

1. **Streaming narrative (API providers).** Narration is still delivered per-turn as a completed block with a client-side typewriter, not token-streamed from the model. A true streaming path over the API providers remains a stretch item, unimplemented.
2. **中文 back-half trace depth.** 中文 discovery stays front-loaded (13–14 of its traces land by T8; the T9–T18 stretch adds ~1). The wave-15 decrypt swap lifted EN back-half depth but did **not** move 中文 — a 中文-effective deep beat (or 中文 keyword parity on the back-half act-on-evidence traces) is still open.
3. **EN endgame prose polish.** The EN grader consistently docks the final turn for cutting off mid-sentence (a transcript-length-cap artifact) plus occasional mechanical-exposition / action-paraphrasing lines. Polish-level, consistent with the standing 8/9 grade — not a mechanical defect, but the named path to a 9 in EN.
