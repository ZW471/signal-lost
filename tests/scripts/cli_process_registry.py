"""
Signal Lost — live CLI child-process registry (claude / codex exec).

Both CLI wrappers (:mod:`tests.scripts.claude_llm`, :mod:`tests.scripts.codex_llm`)
spawn their child with ``start_new_session=True`` so a timeout can ``os.killpg``
the whole tree. The flip side of that deliberate detachment: the child lives in
its OWN session/process group, so a server shutdown, SIGTERM, or deploy restart
never reaches it via normal process-group signal propagation. Any ``codex exec``
or ``claude -p`` call still in flight when the server dies is re-parented to
init/launchd and keeps running — burning CPU and tokens with no parent
(observed live: two orphaned ``codex exec`` PIDs after ``pkill run_gui.py``).

This module is the fix: every live CLI child is registered here, and
:func:`kill_all` SIGKILLs the registered process groups. It is invoked from:

- the GUI server's FastAPI shutdown hook (gui/server.py) — the load-bearing
  path. It runs on the event loop during uvicorn's graceful SIGTERM/SIGINT
  shutdown, even while an executor thread is still parked in
  ``proc.communicate()``. Killing the child unblocks that thread, which lets
  the interpreter actually exit (``concurrent.futures`` joins its non-daemon
  workers before regular atexit handlers run, so without this the process
  could otherwise hang on shutdown, then get hard-killed → orphan).
- a module-level ``atexit`` hook (belt and braces for non-server embedders
  such as headless test scripts, where no CLI call is in flight at exit).

Thread-safe: register/unregister run on executor threads, kill_all on the
event loop or the atexit machinery.
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import threading

_lock = threading.Lock()
_live: set[subprocess.Popen] = set()
# Thread-keyed view of _live: the executor thread that spawned (and is blocked
# reaping) each child. A CLI call runs synchronously in its caller's thread, so
# "the proc this thread is waiting on" is exactly "this session's in-flight CLI
# call" — which lets a mid-turn cancel kill ITS OWN call without touching other
# players' turns (see kill_thread / gui/server.py cancel path).
_by_thread: dict[int, subprocess.Popen] = {}


def register(proc: subprocess.Popen) -> None:
    """Track *proc* (spawned with ``start_new_session=True``) as a live child."""
    with _lock:
        _live.add(proc)
        _by_thread[threading.get_ident()] = proc


def unregister(proc: subprocess.Popen) -> None:
    """Stop tracking *proc* once its call completed (or was killed)."""
    with _lock:
        _live.discard(proc)
        tid = threading.get_ident()
        if _by_thread.get(tid) is proc:
            del _by_thread[tid]


def kill_thread(tid: int) -> bool:
    """SIGKILL the process group of the CLI child spawned by thread *tid*.

    Used by the GUI server's mid-turn cancel: the turn's executor thread is
    parked in ``proc.communicate()``; killing the child's process group makes
    that call return immediately, so the wrapper raises and the turn aborts at
    a pre-commit point instead of burning out the rest of a cancelled model
    run. Returns True if a live child was signalled; False when that thread has
    no in-flight CLI call (already finished, or not a CLI turn) — the caller
    then simply falls back to the next cooperative cancel seam. Never raises.
    """
    with _lock:
        proc = _by_thread.get(tid)
    if proc is None:
        return False
    try:
        if proc.poll() is not None:
            return False  # already exited; its wrapper is reaping it
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            proc.kill()
        return True
    except Exception:
        return False


def kill_all() -> int:
    """SIGKILL every registered live CLI child's process group.

    Returns the number of children actually signalled. Safe to call multiple
    times and from any thread; never raises.
    """
    with _lock:
        procs = list(_live)
        _live.clear()
    killed = 0
    for proc in procs:
        try:
            if proc.poll() is not None:
                continue  # already exited; its wrapper will reap it
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                proc.kill()
            killed += 1
        except Exception:
            # Cleanup must never take the shutdown path down with it.
            continue
    return killed


atexit.register(kill_all)
