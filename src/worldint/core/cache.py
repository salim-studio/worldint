"""Two-level cache: in-memory LRU + SQLite WAL. Fast, stale-fallback."""
from __future__ import annotations
import json, sqlite3, time, os, threading
from collections import OrderedDict

DB = os.environ.get("WORLDINT_DB", os.path.expanduser("~/.cache/worldint/cache.db"))

_mem: OrderedDict = OrderedDict()
_mem_lock = threading.Lock()
MEM_MAX = 800

def _conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT, exp REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS aoi(name TEXT PRIMARY KEY, shape TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS aoi_snap(name TEXT PRIMARY KEY, snap TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS store(id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, text TEXT, ts REAL)")
    return c

def mem_get(key):
    with _mem_lock:
        it = _mem.get(key)
        if it and it[1] > time.time():
            _mem.move_to_end(key)
            return it[0]
        _mem.pop(key, None)
    return None

def mem_set(key, val, ttl):
    with _mem_lock:
        _mem[key] = (val, time.time() + ttl)
        if len(_mem) > MEM_MAX:
            _mem.popitem(last=False)

def get(key):
    v = mem_get(key)
    if v is not None:
        return v
    try:
        c = _conn()
        r = c.execute("SELECT v,exp FROM kv WHERE k=?", (key,)).fetchone()
        c.close()
        if r and float(r[1]) > time.time():
            mem_set(key, json.loads(r[0]), max(1, int(float(r[1]) - time.time())))
            return json.loads(r[0])
    except Exception:
        pass
    return None

def get_stale(key):
    try:
        c = _conn()
        r = c.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        c.close()
        if r:
            return json.loads(r[0])
    except Exception:
        pass
    return mem_get(key)

def set(key, val, ttl=300):
    mem_set(key, val, ttl)
    try:
        c = _conn()
        c.execute("INSERT OR REPLACE INTO kv VALUES(?,?,?)", (key, json.dumps(val, default=str), time.time() + ttl))
        c.commit(); c.close()
    except Exception:
        pass

def stats():
    try:
        c = _conn()
        n = c.execute("SELECT COUNT(*) FROM kv").fetchone()[0]
        c.close()
    except Exception:
        n = 0
    return {"mem_items": len(_mem), "db_items": n, "db": DB}
