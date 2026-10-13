"""AOI geofences: circle/polygon/corridor + brief/changes/digest. Persisted in SQLite."""
from __future__ import annotations
import json
from .core.cache import _conn
from .core import geo
from .core.registry import tool

def _all():
    c = _conn()
    rows = c.execute("SELECT name,shape FROM aoi").fetchall()
    c.close()
    return {n: json.loads(s) for n, s in rows}

@tool("aoi_define", "Define circular AOI: name, lat, lon, radius_km(1-2000)")
async def aoi_define(name: str, lat: float, lon: float, radius_km: float = 50):
    c = _conn()
    c.execute("INSERT OR REPLACE INTO aoi VALUES(?,?)", (name, json.dumps({"type": "circle", "lat": lat, "lon": lon, "radius_km": radius_km})))
    c.commit(); c.close()
    return {"ok": True, "name": name}

@tool("aoi_define_polygon", "Define polygon AOI: name + vertices [[lat,lon]x3..64]")
async def aoi_define_polygon(name: str, vertices: list):
    c = _conn()
    c.execute("INSERT OR REPLACE INTO aoi VALUES(?,?)", (name, json.dumps({"type": "polygon", "vertices": vertices})))
    c.commit(); c.close()
    return {"ok": True, "name": name, "vertices": len(vertices)}

@tool("aoi_define_corridor", "Define corridor AOI: name + waypoints + width_km")
async def aoi_define_corridor(name: str, waypoints: list, width_km: float = 80):
    c = _conn()
    c.execute("INSERT OR REPLACE INTO aoi VALUES(?,?)", (name, json.dumps({"type": "corridor", "waypoints": waypoints, "width_km": width_km})))
    c.commit(); c.close()
    return {"ok": True, "name": name}

@tool("aoi_list", "List all AOIs")
async def aoi_list():
    return {"aois": _all()}

@tool("aoi_delete", "Delete AOI by name")
async def aoi_delete(name: str):
    c = _conn()
    c.execute("DELETE FROM aoi WHERE name=?", (name,)); c.execute("DELETE FROM aoi_snap WHERE name=?", (name,))
    c.commit(); c.close()
    return {"ok": True, "deleted": name}

def _filter(shape, items, latf, lonf):
    out = []
    for it in items:
        try:
            if geo.in_shape(float(latf(it)), float(lonf(it)), shape):
                out.append(it)
        except Exception:
            pass
    return out

@tool("aoi_brief", "Cited multi-domain brief for an AOI (quakes, fires, mil-flights, news)")
async def aoi_brief(name: str):
    shapes = _all()
    if name not in shapes:
        return {"error": f"unknown AOI {name}", "known": list(shapes)}
    shape = shapes[name]
    from .sources import markets, hazards, intel  # lazy
    import asyncio
    lat = shape.get("lat", 30); lon = shape.get("lon", 31)
    if shape["type"] != "circle":
        pts = shape.get("vertices") or shape.get("waypoints") or [[lat, lon]]
        lat = sum(p[0] for p in pts) / len(pts); lon = sum(p[1] for p in pts) / len(pts)
    r = 300 if shape["type"] == "circle" else 500
    quakes, fires, mil = await asyncio.gather(hazards.earthquakes(4.0, 72, 50), hazards.wildfires(50), intel.military_flights(lat, lon, r))
    cites, n = [], 0
    def cite(s):
        nonlocal n; n += 1; cites.append(f"[{n}] {s}"); return f"[{n}]"
    q = (quakes.get("quakes") or []) if isinstance(quakes, dict) else []
    qin = _filter(shape, q, lambda x: x["lat"], lambda x: x["lon"])
    lines = [f"# AOI Brief: {name}", f"shape={shape.get('type')}"]
    for e in qin[:10]:
        lines.append(f"- M{e.get('mag')} {e.get('place')} {cite('USGS')}")
    ac = (mil.get("aircraft") or []) if isinstance(mil, dict) else []
    ain_ = _filter(shape, ac, lambda x: x.get("lat") or 999, lambda x: x.get("lon") or 999)
    for a in ain_[:10]:
        lines.append(f"- MIL {a.get('hex')}/{a.get('flight')} {cite('adsb.lol')}")
    lines.append(f"\nSources: {'; '.join(cites) or 'none in range'}")
    ids = {"quakes": [(e.get("url") or e.get("place")) for e in qin],
           "mil": [(a.get("hex") or a.get("flight")) for a in ain_]}
    return {"name": name, "markdown": "\n".join(lines), "counts": {"quakes_in": len(qin), "mil_in": len(ain_)},
            "ids": ids, "sources": cites}

@tool("aoi_changes", "What entered/left an AOI since last sweep (ID-based diff; first call = baseline)")
async def aoi_changes(name: str):
    import time
    b = await aoi_brief(name)
    if "error" in b:
        return b
    cur = b.get("ids", {"quakes": [], "mil": []})
    c = _conn()
    row = c.execute("SELECT snap FROM aoi_snap WHERE name=?", (name,)).fetchone()
    c.execute("INSERT OR REPLACE INTO aoi_snap VALUES(?,?)", (name, json.dumps({"ids": cur, "ts": time.time()})))
    c.commit()
    c.close()
    if not row:
        return {"name": name, "status": "baseline_set", "current_counts": b["counts"]}
    try:
        prev = json.loads(row[0]).get("ids", {})
    except Exception:
        prev = {}
    diff = {}
    for dom in ("quakes", "mil"):
        old, new = set(prev.get(dom, [])), set(cur.get(dom, []))
        diff[dom] = {"entered": sorted(new - old)[:20], "left": sorted(old - new)[:20]}
    changed = any(diff[d]["entered"] or diff[d]["left"] for d in diff)
    return {"name": name, "changed": changed, "diff": diff, "current_counts": b["counts"]}

@tool("aoi_digest", "One sweep across ALL AOIs")
async def aoi_digest():
    shapes = _all()
    out = {}
    for n in shapes:
        out[n] = await aoi_changes(n)
    return {"swept": len(out), "results": out}
