"""Per-source circuit breaker: 3 fails -> open 5 min."""
from __future__ import annotations
import time

_state: dict = {}
FAIL_N = 3
OPEN_S = 300

def allow(source: str) -> bool:
    s = _state.get(source)
    if not s or s.get("open_until", 0) < time.time():
        return True
    return False

def ok(source: str):
    _state[source] = {"fails": 0, "open_until": 0}

def fail(source: str):
    s = _state.setdefault(source, {"fails": 0, "open_until": 0})
    s["fails"] += 1
    if s["fails"] >= FAIL_N:
        s["open_until"] = time.time() + OPEN_S
        s["fails"] = 0

def status():
    now = time.time()
    return {k: ("OPEN" if v.get("open_until", 0) > now else "CLOSED") for k, v in _state.items()}
