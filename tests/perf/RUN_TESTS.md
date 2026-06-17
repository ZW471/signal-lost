# Signal Lost — Performance / Quality Test Suite (agent runbook)

~100 ready-to-run test cases that probe a build's **plot**, **backend**, and
**frontend** behaviour. Each case is a pre-built game save + a short action script
(≤3 turns) + pass/fail criteria. Cases are designed to be executed by an **agent**
against **any model/provider**.

```
tests/perf/
  generate.py     # (re)builds saves/ + cases.json   →  uv run tests/perf/generate.py
  check.py        # auto-grades the objective asserts  →  uv run tests/perf/check.py <id> <out.json>
  cases.json      # the manifest: every case's save, actions, asserts, rubric
  saves/<id>/     # one ready-to-load game state per case
  RUN_TESTS.md    # this file
```

## 0. Pick the build under test
Set the provider/model once; every headless case uses it:
```
P="HEADLESS_PROVIDER=openrouter HEADLESS_MODEL=deepseek/deepseek-chat"   # or claude-code/sonnet, codex/gpt-5.5, …
```
Capable reference models: `claude-code/sonnet`, `codex/gpt-5.5`, `openrouter/deepseek-chat`, `openrouter/deepseek-r1`.

## 1. The manifest (`cases.json`)
Each case object:
| field | meaning |
|---|---|
| `id` | unique case id (also the save dir name) |
| `category` | `plot/*`, `backend/*`, `frontend/*` |
| `lang` | `en` / `zh` (game language baked into the save) |
| `channel` | **how to run it**: `headless`, `gui`, or `backend` |
| `save` | `saves/<id>` — the state to load |
| `first_turn` | the turn number to submit for the **first** action |
| `actions` | 0–3 player inputs to send, in order |
| `assert` | machine-checkable guards (graded by `check.py`) |
| `rubric` | the human/agent judgement for the subjective part |
| `setup` | extra setup notes (mostly for `gui`/`backend`) |

A case PASSES only if **both** the machine `assert` (where present) and the
`rubric` judgement pass.

---

## 2. Running a `headless` case (plot + backend/input)
The save is loaded by copying it into a live session dir, then each action is one
blocking call to the shared one-shot driver (`tests/scripts/oneshot_turn.py`),
which loads state from disk, runs ONE turn through the real engine, and prints a
JSON result (`narrative`, `game_over`, `state_summary`, `system_notices`).

For a case with id `C`, `first_turn` `T`, and actions `[a1, a2, a3]`:
```bash
ID=plot_recall_code_en          # example
T=$(python3 -c "import json;print([c for c in json.load(open('tests/perf/cases.json'))['cases'] if c['id']=='$ID'][0]['first_turn'])")

rm -rf "session/perf_$ID"
cp -r "tests/perf/saves/$ID" "session/perf_$ID"

# one call PER action, incrementing the turn number; capture the LAST turn's JSON:
eval $P HEADLESS_SESSION_NAME=perf_$ID HEADLESS_LANGUAGE=<lang> \
  uv run tests/scripts/oneshot_turn.py --turn $T --action "<a1>" | tee /tmp/perf_$ID.json
# (if more actions: rerun with --turn $((T+1)) "<a2>", then $((T+2)) "<a3>")

# auto-grade the objective asserts against the LAST turn's JSON:
uv run tests/perf/check.py "$ID" /tmp/perf_$ID.json
```
Then read the `narrative` and apply the `rubric` yourself for the final verdict.

Rules:
- One **blocking** Bash call per turn. NEVER use Monitor / background / sleep loops.
- Pass the action text verbatim from the manifest (mind the shell-quoting; use a
  heredoc via `--action -`/stdin if it contains awkward characters — the driver
  reads stdin when `--action` is omitted).
- Always run with the **same** provider/model across a batch so results compare.
- Clean up afterwards: `rm -rf session/perf_$ID`.

What `assert` keys mean (see `check.py`): `contains_any/contains_all/excludes`
(substring, case-insensitive, on the narrative), `no_engine_error`, `game_over`,
`credits_max`, `integrity_max`, `location_excludes`.

---

## 3. Running a `gui` case (frontend)
These check what a human sees. Use the preview tooling (`preview_start` on the
`signal-lost-gui` launch config), then:

1. **Auth:** the GUI gates New Game/Load behind a local login. Register a throwaway
   test profile once (via the auth module, not by typing a password into a field):
   `python3 -c "import sys;sys.path.insert(0,'gui');import auth;print(auth.register('perftester','test1234'))"`
   then inject the returned token into `localStorage['signal_lost_token']` and
   reload. (Restart the server first if it was already running, so it reloads the
   token store.)
2. **Load the case save:** copy `tests/perf/saves/<id>` into the test user's
   namespace as a save, then use the in-GUI **Load** dialog:
   `mkdir -p saves/<uid> && cp -r tests/perf/saves/<id> saves/<uid>/<id>` and pick it.
   (Or copy it to `session/<uid>/<id>` and use **Resume**.)
3. **Do the `setup`** (open the named panels, resize, switch language, etc.) and
   run any `actions` by typing them into the chat.
4. **Judge by the `rubric`.** Capture a `preview_screenshot` only as evidence of a
   FAIL (broken layout, mixed languages, clipped tabs, literal `**` markdown, …).
5. For i18n cases specifically: scan ALL chrome (menus, buttons, panel-tab labels,
   meter/role labels, settings) for any string in the *other* language.

---

## 4. Running a `backend` case (multiplayer / auth)
These exercise the server's WebSocket contract directly (see `gui/server.py`).
Follow the case's `setup`, typically:

- **Isolation / namespacing:** register two accounts, open two WebSocket
  connections to `/ws`, `init` each with its own token, start/resume a game on
  each, take a turn on each. Verify each only sees its own `session/<uid>` /
  `saves/<uid>` and that neither transcript/knowledge/NPC set bleeds into the
  other.
- **Same-account conflict:** `init` two sockets with the SAME token → expect a
  `session_conflict` (or a clean kick of the first), never two live shared games.
- **Foreign session / traversal:** as userA, `resume`/`load_game` with a
  `session_name`/`save_name` belonging to userB or containing `../` → expect
  "not found", never another uid's data.
- **Unauthenticated action:** send `player_input` with no/invalid token → expect
  `auth_required`, no turn run.

Judge by the `rubric`. These are about server behaviour, not model quality.

---

## 5. Recording results
For a run, produce a short table: `id | category | machine(PASS/FAIL) | rubric(PASS/FAIL) | note`.
For any FAIL, capture the minimal evidence (the offending narrative snippet, a
screenshot, or the WS response) and a one-line root-cause guess. Group failures by
category so engine/UI fixes can be batched.

## 6. Categories at a glance
- `plot/recall` — does the model recall established facts (codes, names, places, times), single- and multi-turn, en+zh?
- `plot/hallucination` — does it refuse to invent things that never happened?
- `plot/cheat` — can the player grant themselves credits/integrity/teleport/win/admin by fiat? (must not)
- `plot/spoiler` — does it withhold deep (Layer 4-5) lore from a shallow player?
- `plot/continuity` — does it reject false premises and stay consistent on revisits?
- `plot/fairness` — is a lethal integrity hit telegraphed; does high alert escalate?
- `backend/input-robustness` — empty/huge/control-char/injection/tool-spoof payloads handled without crash or obeying.
- `backend/multiplayer` + `backend/auth` — per-user isolation, conflict handling, no foreign-session access.
- `frontend/i18n` — no mixed-language UI; language switch flips the whole interface.
- `frontend/render` — markdown, panels with many NPCs/facts, tab wrapping, meter notices, quick-actions, long names, contrast.

## 7. Regenerating / extending
`uv run tests/perf/generate.py` rebuilds `saves/` and `cases.json` from the tables
in `generate.py`. Add a probe by extending the relevant table (e.g. `RECALL`,
`CHEAT`, `BACKEND_INPUT`) or adding an `emit(...)` call, then regenerate.
The committed `saves/` are read-only fixtures; running a case copies them into a
scratch `session/perf_<id>` dir, so the fixtures themselves are never mutated.
