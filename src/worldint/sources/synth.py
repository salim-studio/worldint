"""Cross-domain synthesis: world brief, posture, dossier, convergence, semantic search, status."""
from __future__ import annotations
from ..core.registry import tool
from ..core import fetcher as F
from ..core import cache, breaker

@tool("world_brief", "One-call world brief: macro + quakes + space-wx + news + cyber + theater (parallel)")
async def world_brief():
    from . import markets, hazards, intel
    jobs = {"macro": markets.macro_signals(), "quakes": hazards.earthquakes(5.0, 24, 8),
            "spacewx": hazards.space_weather(), "news": intel.news_feed(8),
            "theater": intel.theater_posture(), "cyber": intel.cyber_threats(5)}
    r = await F.gather_map(jobs)
    cites = ["[1] Yahoo/Alternative.me/Coingecko", "[2] USGS", "[3] NOAA SWPC", "[4] RSS", "[5] adsb.lol", "[6] CISA/URLhaus"]
    md = ["# World Brief (worldint)"]
    try: md.append(f"- Markets: {r['macro'].get('verdict')} (score {r['macro'].get('composite')}) [1]")
    except Exception: pass
    try: md.append(f"- Quakes M5+: {r['quakes'].get('count')} strongest: {(r['quakes'].get('quakes') or [{}])[0].get('place')} [2]")
    except Exception: pass
    try: md.append(f"- Kp: {r['spacewx'].get('kp_latest')} [3]")
    except Exception: pass
    try: md.append(f"- Theater: {r['theater'].get('posture')} {r['theater'].get('theaters')} [5]")
    except Exception: pass
    md.append(f"\nSources: {'; '.join(cites)}")
    return {"markdown": "\n".join(md), "raw": r, "sources": cites}

@tool("strategic_posture", "Composite global risk 0-100 from quakes+theater+macro+spacewx")
async def strategic_posture():
    b = await world_brief()
    raw = b["raw"]
    score = 30
    try:
        if (raw["quakes"].get("count") or 0) > 5: score += 15
        th = sum((x or 0) for x in (raw["theater"].get("theaters") or {}).values())
        score += min(25, th)
        if str(raw["macro"].get("verdict")) == "CAUTION": score += 10
        kp = float(raw["spacewx"].get("kp_latest") or 0)
        if kp >= 5: score += 10
    except Exception: pass
    level = "LOW" if score < 40 else ("GUARDED" if score < 60 else ("ELEVATED" if score < 80 else "HIGH"))
    return {"score": min(100, score), "level": level, "brief": b["markdown"]}

@tool("country_dossier", "Country dossier: WB GDP + Switzerland-free FX context + quakes + news (parallel)")
async def country_dossier(country: str = "EG"):
    from . import markets, hazards, intel
    jobs = {"gdp": markets.worldbank_indicator(country, "NY.GDP.MKTP.CD", 3),
            "quakes": hazards.earthquakes(4.5, 168, 10),
            "news": intel.gdelt_search(country, 8)}
    r = await F.gather_map(jobs)
    return {"country": country, "data": r, "note": "combine with aoi_brief for geo-scoped view"}

@tool("semantic_search", "Local instant search across collected intel (no GPU, no server)")
async def semantic_search(query: str, limit: int = 10):
    from .. import store
    return store.search(query, limit)

@tool("store_stats", "Local intel-store stats")
async def store_stats():
    from .. import store
    s = store.stats()
    s.update(cache.stats())
    s["breakers"] = breaker.status()
    return s

@tool("status", "worldint health: cache + breakers + tools count")
async def status():
    from ..core.registry import REG
    return {"tools": len(REG), "cache": cache.stats(), "breakers": breaker.status(), "version": "1.1.0"}

@tool("daily_digest", "Cited markdown morning brief")
async def daily_digest():
    b = await world_brief()
    return {"markdown": "# worldint Daily Digest\n\n" + b["markdown"] + "\n\n_Free public sources, no paid keys._"}
