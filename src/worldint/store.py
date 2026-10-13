"""Mini local store: TF-IDF-ish keyword search over SQLite (no heavy deps, instant)."""
from __future__ import annotations
import time, re, sqlite3
from .core.cache import _conn

def remember(domain: str, text: str):
    try:
        c = _conn()
        c.execute("INSERT INTO store(domain,text,ts) VALUES(?,?,?)", (domain, text[:3000], time.time()))
        c.execute("DELETE FROM store WHERE id NOT IN (SELECT id FROM store ORDER BY id DESC LIMIT 5000)")
        c.commit(); c.close()
    except Exception:
        pass

def search(query: str, limit: int = 10):
    toks = [t.lower() for t in re.findall(r"\w{3,}", query)]
    try:
        c = _conn()
        rows = c.execute("SELECT domain,text,ts FROM store ORDER BY id DESC LIMIT 800").fetchall()
        c.close()
    except Exception:
        return {"query": query, "results": []}
    scored = []
    for d, t, ts in rows:
        tl = t.lower()
        s = sum(tl.count(x) for x in toks)
        if s > 0:
            scored.append((s, {"domain": d, "snippet": t[:400], "ts": ts}))
    scored.sort(reverse=True, key=lambda x: x[0])
    return {"query": query, "results": [x[1] for x in scored[:limit]], "count": len(scored)}

def stats():
    try:
        c = _conn()
        n = c.execute("SELECT COUNT(*) FROM store").fetchone()[0]
        doms = c.execute("SELECT domain,COUNT(*) FROM store GROUP BY domain").fetchall()
        c.close()
        return {"items": n, "by_domain": dict(doms)}
    except Exception:
        return {"items": 0}
