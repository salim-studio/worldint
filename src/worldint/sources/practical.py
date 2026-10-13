"""High-value practical tools: markets depth, hotspots, convergence, nuclear, maritime, crisis, displacement."""
from __future__ import annotations
import asyncio, datetime
from ..core.registry import tool
from ..core import fetcher as F
from ..core import geo

Y = "https://query1.finance.yahoo.com/v8/finance/chart/"

async def _ymeta(sym):
    r = await F.get_json(Y + sym + "?interval=1d&range=5d", "yahoo", f"wi:y:{sym}", 600)
    try:
        m = r["data"]["chart"]["result"][0]["meta"]
        p, prev = m.get("regularMarketPrice"), m.get("chartPreviousClose")
        chg = round((p - prev) / prev * 100, 2) if p and prev else None
        return {"symbol": sym, "price": p, "chg_pct": chg}
    except Exception:
        return {"symbol": sym, "error": r.get("error", "parse")}

@tool("yield_curve", "US Treasury curve via Yahoo (3M/5Y/10Y/30Y) + 2s10s spread + inversion flag")
async def yield_curve():
    mp = {"3M": "^IRX", "5Y": "^FVX", "10Y": "^TNX", "30Y": "^TYX"}
    out = {k: await _ymeta(s) for k, s in mp.items()}
    try:
        spread = round(out["10Y"]["price"] - out["3M"]["price"], 2)
        return {"curve": out, "spread_3m10y": spread, "inverted": spread < 0, "note": "indicative Yahoo yields, not official H.15"}
    except Exception:
        return {"curve": out}

@tool("sector_heatmap", "US equity sectors: 11 SPDR ETFs daily change (parallel)")
async def sector_heatmap():
    etfs = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLRE", "XLB", "XLC"]
    res = await asyncio.gather(*[_ymeta(s) for s in etfs])
    ok = [x for x in res if x.get("chg_pct") is not None]
    ok.sort(key=lambda x: x["chg_pct"], reverse=True)
    return {"sectors": ok, "leaders": ok[:3], "laggards": ok[-3:]}

@tool("stablecoin_status", "Stablecoin peg health: USDT, USDC, DAI, FDUSD (CoinGecko)")
async def stablecoin_status():
    r = await F.get_json("https://api.coingecko.com/api/v3/coins/markets", "coingecko", "wi:stable", 600,
                         params={"vs_currency": "usd", "ids": "tether,usd-coin,dai,first-digital-usd", "price_change_percentage": "24h"})
    try:
        coins = [{"sym": c["symbol"].upper(), "price": c["current_price"],
                  "depegged": abs((c["current_price"] or 1) - 1) > 0.005} for c in r["data"]]
        return {"coins": coins, "all_pegged": all(not c["depegged"] for c in coins)}
    except Exception:
        return r

@tool("earnings_calendar", "Earnings calendar for a date (Nasdaq API, free). date=YYYY-MM-DD")
async def earnings_calendar(date: str = ""):
    d = date or datetime.date.today().isoformat()
    r = await F.get_json("https://api.nasdaq.com/api/calendar/earnings", "nasdaq", f"wi:earn:{d}", 21600,
                         params={"date": d}, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        rows = (r["data"].get("data") or {}).get("rows") or []
        return {"date": d, "count": len(rows),
                "earnings": [{"symbol": x.get("symbol"), "name": (x.get("name") or "")[:60],
                              "time": x.get("time"), "mcap": x.get("marketCap")} for x in rows[:30]]}
    except Exception:
        return r

@tool("company_profile", "Composite company profile: quote + SEC filings + fresh news")
async def company_profile(ticker: str = "NVDA"):
    from . import intel
    q, sec, news = await asyncio.gather(
        _ymeta(ticker), intel.sec_company(ticker), intel.news_feed(20, ticker))
    return {"ticker": ticker.upper(), "quote": q, "sec": sec, "news": news.get("headlines", [])[:8]}

@tool("shipping_stress", "Dry-bulk stress proxy: BDRY ETF month-trend + crude (Yahoo)")
async def shipping_stress():
    r = await F.get_json(Y + "BDRY?interval=1d&range=1mo", "yahoo", "wi:bdry", 3600)
    try:
        cl = r["data"]["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        cl = [x for x in cl if x]
        trend = round((cl[-1] - cl[0]) / cl[0] * 100, 1)
    except Exception:
        trend = None
    brent, wti = await asyncio.gather(_ymeta("BZ=F"), _ymeta("CL=F"))
    stress = "ELEVATED" if trend is not None and trend < -10 else ("FIRM" if trend and trend > 10 else "NORMAL")
    return {"bdry_month_pct": trend, "brent": brent.get("price"), "wti": wti.get("price"), "stress": stress}

HOTSPOTS = [
    ("Taiwan Strait", 24.5, 119.5), ("South China Sea", 15.0, 114.0), ("Korean DMZ", 38.3, 127.2),
    ("Kashmir LoC", 34.5, 76.0), ("Eastern Ukraine", 48.5, 38.0), ("Gaza", 31.5, 34.3),
    ("South Lebanon", 33.2, 35.5), ("North Syria", 36.5, 38.0), ("Central Iraq", 33.3, 44.3),
    ("Yemen", 15.5, 45.0), ("Bab el-Mandeb", 12.5, 43.5), ("Strait of Hormuz", 26.5, 56.5),
    ("Khartoum", 15.5, 32.5), ("Sahel (Gao)", 16.3, 0.0), ("Tripoli", 32.9, 13.2),
    ("Kosovo", 42.6, 21.0), ("Transnistria", 47.3, 29.3), ("South Caucasus", 40.3, 45.0),
    ("Myanmar", 21.0, 96.0), ("Eastern DRC", -1.7, 29.2), ("Haiti", 18.5, -72.3), ("W. Sahara", 24.0, -13.0)]

@tool("hotspot_escalation", "Escalation scores 0-100 for 22 hotspots (quakes proximity + live news hits)")
async def hotspot_escalation():
    from . import hazards, intel
    quakes, news = await asyncio.gather(hazards.earthquakes(4.5, 720, 200), intel.news_feed(40))
    feats = []
    try:
        feats = quakes.get("quakes", [])
    except Exception:
        pass
    heads = " | ".join(h["title"] for h in news.get("headlines", [])).lower()
    out = []
    for name, la, lo in HOTSPOTS:
        nq = sum(1 for q in feats if geo.hav(la, lo, q["lat"], q["lon"]) <= 300)
        keys = [w for w in name.lower().replace("(", "").replace(")", "").split() if len(w) > 3]
        nh = sum(heads.count(k) for k in keys)
        score = min(100, 20 + min(30, nq * 10) + min(50, nh * 10))
        level = "LOW" if score < 35 else ("GUARDED" if score < 55 else ("ELEVATED" if score < 75 else "HIGH"))
        out.append({"hotspot": name, "score": score, "level": level, "quakes_near": nq, "news_hits": nh})
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"hotspots": out, "top": out[:5], "note": "heuristic: 20 base + seismic + headline velocity"}

@tool("signal_convergence", "Geographic convergence: 5° cells where quakes + wildfires coincide (30d)")
async def signal_convergence():
    from . import hazards
    quakes, fires = await asyncio.gather(hazards.earthquakes(4.5, 720, 300), hazards.wildfires(100))
    cells = {}
    def add(lat, lon, dom, label):
        k = (int(lat // 5) * 5, int(lon // 5) * 5)
        c = cells.setdefault(k, {"cell": k, "domains": set(), "items": []})
        c["domains"].add(dom)
        if len(c["items"]) < 6:
            c["items"].append(label)
    for q in quakes.get("quakes", []) or []:
        add(q["lat"], q["lon"], "quake", f"M{q.get('mag')} {q.get('place', '')[:60]}")
    evs = []
    try:
        evs = fires.get("fires", []) or []
    except Exception:
        pass
    for f in evs:
        co = f.get("coords")
        if isinstance(co, (list, tuple)) and len(co) >= 2:
            add(co[1], co[0], "fire", (f.get("title") or "")[:60])
    zones = [{"cell_center": c["cell"], "domains": sorted(c["domains"]), "items": c["items"]}
             for c in cells.values() if len(c["domains"]) >= 2]
    return {"zones": zones, "count": len(zones)}

TEST_SITES = {"Nevada NNSS": (37.1, -116.05), "Novaya Zemlya": (73.5, 54.7), "Punggye-ri": (41.28, 129.08),
              "Lop Nur": (41.6, 88.4), "Semipalatinsk": (50.4, 77.8), "Mururoa": (-21.8, -138.9)}

@tool("nuclear_monitor", "Seismic check near 6 nuclear test sites (USGS radius search, 30d, M2.5+)")
async def nuclear_monitor():
    async def one(name, la, lo):
        r = await F.get_json("https://earthquake.usgs.gov/fdsnws/event/1/query", "usgs",
            f"wi:nuc:{name}", 3600,
            params={"format": "geojson", "latitude": la, "longitude": lo, "maxradiuskm": 150, "minmagnitude": 2.5})
        try:
            fs = r["data"]["features"][:8]
            return name, [{"mag": f["properties"].get("mag"), "place": f["properties"].get("place"),
                           "depth": f["geometry"]["coordinates"][2]} for f in fs]
        except Exception:
            return name, []
    res = await asyncio.gather(*[one(n, la, lo) for n, (la, lo) in TEST_SITES.items()])
    return {"sites": [{"site": n, "events": e, "count": len(e)} for n, e in res],
            "note": "near-site seismicity is usually natural; tests show as shallow M4+ with official announcement"}

@tool("elections_calendar", "Major upcoming elections (curated snapshot — confirm dates)")
async def elections_calendar():
    return {"elections": [
        {"country": "USA", "event": "Midterm elections", "date": "2026-11-03"},
        {"country": "Brazil", "event": "General election", "date": "2026-10-04"},
        {"country": "Colombia", "event": "Presidential election", "date": "2026-05-31"},
        {"country": "Sweden", "event": "General election", "date": "2026-09-13"},
        {"country": "Hungary", "event": "Parliamentary election", "date": "2026-04-12"},
        {"country": "Denmark", "event": "General election (due)", "date": "2026-10-31"}],
        "note": "curated; verify against official sources"}

CHOKEPOINTS = {"Hormuz": (26.5, 56.3), "Malacca": (2.5, 100.5), "Bab el-Mandeb": (12.6, 43.4),
               "Suez South": (29.9, 32.55), "Panama": (8.9, -79.5), "Gibraltar": (35.97, -5.6),
               "Taiwan Strait": (24.5, 119.5), "Bosphorus": (41.1, 29.05), "Danish Straits": (55.5, 11.0)}

@tool("maritime_watch", "Hazard pressure on 9 strategic chokepoints (quakes + fires proximity, 14d)")
async def maritime_watch():
    from . import hazards
    quakes, fires = await asyncio.gather(hazards.earthquakes(4.5, 336, 200), hazards.wildfires(100))
    qs = quakes.get("quakes", []) or []
    fs = []
    try:
        for f in fires.get("fires", []) or []:
            co = f.get("coords")
            if isinstance(co, (list, tuple)) and len(co) >= 2:
                fs.append((co[1], co[0]))
    except Exception:
        pass
    out = []
    for name, (la, lo) in CHOKEPOINTS.items():
        nq = sum(1 for q in qs if geo.hav(la, lo, q["lat"], q["lon"]) <= 300)
        nf = sum(1 for a, o in fs if geo.hav(la, lo, a, o) <= 300)
        pressure = "HIGH" if nq >= 3 else ("WATCH" if nq or nf else "CLEAR")
        out.append({"chokepoint": name, "quakes_near": nq, "fires_near": nf, "pressure": pressure})
    return {"chokepoints": out}

@tool("crisis_watch", "Humanitarian crisis watch: GDACS top + conflict headlines (trimmed)")
async def crisis_watch(limit: int = 10):
    from . import hazards, intel
    dis, news = await asyncio.gather(hazards.disaster_alerts(limit), intel.news_feed(30, "conflict war displaced refugee"))
    return {"disasters": dis, "conflict_news": news.get("headlines", [])[:limit]}

@tool("displacement_summary", "Displacement watch: live World Bank series (multi-code) + major-situations watchlist")
async def displacement_summary(top: int = 10):
    found, errors = {}, {}
    for code in ("SM.POP.REFG", "SM.POP.REFG.OR", "VC.IDP.NWDS"):
        r = await F.get_json(f"https://api.worldbank.org/v2/country/all/indicator/{code}",
            "worldbank", f"wi:dis:{code}", 86400, params={"format": "json", "per_page": 300})
        try:
            rows = [x for x in r["data"][1] if x.get("value")]
            y = max(x["date"] for x in rows)
            rows = sorted([x for x in rows if x["date"] == y and x.get("countryiso3code")],
                          key=lambda x: -x["value"])
            found[code] = {"year": y, "top": [{"country": x["country"]["value"], "value": x["value"]} for x in rows[:top]]}
        except Exception:
            errors[code] = r.get("error", "no data") if isinstance(r, dict) else "no data"
    return {"live_series": found, "unavailable": errors,
            "watchlist": ["Syria", "Afghanistan", "Ukraine", "Venezuela", "Sudan", "South Sudan",
                          "Myanmar", "DR Congo", "Somalia", "Palestine"],
            "verify": "https://www.unhcr.org/refugee-statistics/",
            "note": "SM.POP.REFG was retired from the WB API; watchlist is qualitative" if not found else "World Bank live"}

@tool("sanctions_watch", "Sanctions chatter: live headlines mentioning sanctions (RSS scan)")
async def sanctions_watch(limit: int = 10):
    from . import intel
    return await intel.news_feed(limit, "sanction")
