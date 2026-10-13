"""Conflict, military, aviation, maritime, infra, cyber, health, news, tech, displacement, gov."""
from __future__ import annotations
import os
from ..core.registry import tool
from ..core import fetcher as F

# ---- conflict / news ----
@tool("gdelt_search", "GDELT 2.0 global news search (free, no key)")
async def gdelt_search(query: str = "conflict", limit: int = 10):
    r = await F.get_json("https://api.gdeltproject.org/api/v2/doc/doc",
        "gdelt", f"wi:gdelt:{query}:{limit}", 600,
        params={"query": query, "mode": "artlist", "format": "json", "maxrecords": max(1, min(limit, 100))})
    return r

@tool("acled_events", "ACLED conflict events (needs ACLED_ACCESS_TOKEN else guidance)")
async def acled_events(country: str = "", limit: int = 20):
    tok = os.environ.get("ACLED_ACCESS_TOKEN")
    if not tok:
        return {"note": "set ACLED_ACCESS_TOKEN for live ACLED; fallback: use gdelt_search + relief below",
                "hint": "https://acleddata.com", "country": country}
    return await F.get_json("https://acleddata.com/api/acled/read",
        "acled", f"wi:acled:{country}", 1800, params={"key": tok, "country": country, "limit": limit})

@tool("relief_crisis", "UN OCHA ReliefWeb crises/disasters (free, no key)")
async def relief_crisis(limit: int = 10):
    r = await F.get_json("https://api.reliefweb.int/v1/disasters",
        "reliefweb", "wi:relief", 1800, params={"appname": "worldint", "limit": limit, "profile": "list"})
    try:
        return {"crises": [{"name": d["fields"]["name"], "country": [c["name"] for c in d["fields"].get("country", [])],
                             "status": d["fields"].get("status")} for d in r["data"]["data"]]}
    except Exception:
        return r

@tool("news_feed", "Curated world RSS (BBC, AlJazeera, Reuters-world, WHO, USGS) — fast parallel")
async def news_feed(limit: int = 15):
    import feedparser
    feeds = {"BBC-World": "https://feeds.bbci.co.uk/news/world/rss.xml",
             "AlJazeera": "https://www.aljazeera.com/xml/rss/all.xml",
             "WHO": "https://www.who.int/feeds/entity/csr/don/en/rss.xml"}
    import asyncio
    async def one(name, url):
        t = await F.get_text(url, "rss", f"wi:rss:{name}", 900)
        try:
            d = feedparser.parse(t["text"])
            return [{"feed": name, "title": e.get("title", "")[:180], "link": e.get("link", "")} for e in d.entries[:limit]]
        except Exception:
            return []
    parts = await asyncio.gather(*[one(k, v) for k, v in feeds.items()])
    items = [x for p in parts for x in p][:limit * 2]
    return {"count": len(items), "headlines": items}

# ---- military / aviation / maritime ----
@tool("military_flights", "Military aircraft via adsb.lol (free) + OpenSky fallback")
async def military_flights(lat: float = 35.0, lon: float = 35.0, dist: int = 250):
    r = await F.get_json(f"https://api.adsb.lol/v2/mil?lat={lat}&lon={lon}&dist={dist}",
        "adsblol", f"wi:mil:{lat}:{lon}", 300)
    if "error" in r:
        fb = await F.get_json("https://opensky-network.org/api/states/all", "opensky", "wi:opensky", 300)
        return {"primary": r, "fallback_opensky": {"states": len((fb.get("data") or {}).get("states") or [])}}
    try:
        ac = r["data"].get("ac", [])
        return {"count": len(ac), "aircraft": [{"hex": a.get("hex"), "flight": (a.get("flight") or "").strip(),
            "lat": a.get("lat"), "lon": a.get("lon"), "alt": a.get("alt_baro")} for a in ac[:50]]}
    except Exception:
        return r

@tool("theater_posture", "5-theater posture in ONE parallel sweep (EU, Indo-Pacific, ME, Arctic, Korea)")
async def theater_posture():
    theaters = {"EU": (50, 10), "IndoPacific": (25, 120), "MiddleEast": (27, 45), "Arctic": (75, 0), "Korea": (38, 127)}
    jobs = {k: F.get_json(f"https://api.adsb.lol/v2/mil?lat={la}&lon={lo}&dist=400", "adsblol", f"wi:th:{k}", 300)
            for k, (la, lo) in theaters.items()}
    r = await F.gather_map(jobs)
    out = {}
    for k, v in r.items():
        try: out[k] = len(v["data"].get("ac", []))
        except Exception: out[k] = None
    level = "ELEVATED" if sum(x or 0 for x in out.values()) > 30 else "ROUTINE"
    return {"theaters": out, "posture": level}

@tool("airport_delays", "FAA airport delays (free)")
async def airport_delays():
    r = await F.get_json("https://nasstatus.faa.gov/api/airport-status-information", "faa", "wi:faa", 600)
    return r

@tool("nav_warnings", "NGA maritime navigation warnings (free)")
async def nav_warnings(limit: int = 10):
    r = await F.get_json("https://msi.nga.mil/api/publications/navwarnings?output=json", "nga", "wi:nga", 3600)
    try:
        d = r["data"]
        items = d if isinstance(d, list) else d.get("warnings", d.get("data", []))
        return {"count": len(items), "warnings": items[:limit]}
    except Exception:
        return r

# ---- infra / cyber ----
@tool("service_status", "Cloud status: GitHub + Cloudflare Radar (free, parallel)")
async def service_status():
    jobs = {"github": F.get_json("https://www.githubstatus.com/api/v2/status.json", "github", "wi:gh:st", 600),
            "radar_outages": F.get_json("https://api.cloudflare.com/client/v4/radar/annotations/outages",
                "cf-radar", "wi:cf:out", 1800)}
    return await F.gather_map(jobs)

@tool("bgp_status", "RIPEstat BGP/RPKI for a prefix or ASN (free)")
async def bgp_status(resource: str = "8.8.8.0/24"):
    jobs = {"visibility": F.get_json(f"https://stat.ripe.net/data/routing-status/data.json?resource={resource}", "ripestat", f"wi:bgp:{resource}", 1800),
            "rpki": F.get_json(f"https://stat.ripe.net/data/rpki-validation/data.json?resource={resource}", "ripestat", f"wi:rpki:{resource}", 1800)}
    return await F.gather_map(jobs)

@tool("cyber_threats", "CISA KEV + URLhaus (free, parallel)")
async def cyber_threats(limit: int = 15):
    jobs = {"kev": F.get_json("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                              "cisa", "wi:kev", 86400),
            "urlhaus": F.get_json("https://urlhaus-api.abuse.ch/v1/urls/recent/", "urlhaus", "wi:urlhaus", 1800)}
    r = await F.gather_map(jobs)
    try:
        vulns = r["kev"]["data"]["vulnerabilities"][:limit]
        r["kev_summary"] = [{"cve": v["cveID"], "vendor": v["vendorProject"], "name": v["vulnerabilityName"][:100]} for v in vulns]
    except Exception: pass
    return r

@tool("disease_outbreaks", "WHO DON + CIDRAP headlines (RSS, free)")
async def disease_outbreaks(limit: int = 10):
    import feedparser
    jobs = {"who": F.get_text("https://www.who.int/feeds/entity/csr/don/en/rss.xml", "rss", "wi:rss:WHO-DON", 3600),
            "cidrap": F.get_text("https://www.cidrap.umn.edu/rss/news", "rss", "wi:rss:cidrap", 3600)}
    r = await F.gather_map(jobs)
    out = []
    for k, v in r.items():
        try:
            for e in feedparser.parse(v["text"]).entries[:limit]:
                out.append({"feed": k, "title": e.get("title", "")[:180]})
        except Exception: pass
    return {"count": len(out), "outbreaks": out}

# ---- tech / gov / displacement ----
@tool("ai_releases", "arXiv AI papers + HackerNews top (free, parallel)")
async def ai_releases(limit: int = 8):
    import feedparser, re
    jobs = {"arxiv": F.get_text("http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submitted&sortOrder=descending&max_results=10",
                                "arxiv", "wi:arxiv", 3600),
            "hn": F.get_json("https://hacker-news.firebaseio.com/v0/topstories.json", "hn", "wi:hn", 900)}
    r = await F.gather_map(jobs)
    papers = []
    try:
        for e in feedparser.parse(r["arxiv"]["text"]).entries[:limit]:
            papers.append({"title": re.sub(r"\s+", " ", e.get("title", ""))[:180]})
    except Exception: pass
    hn = []
    try: hn = r["hn"]["data"][:limit]
    except Exception: pass
    return {"papers": papers, "hn_top_ids": hn}

@tool("github_trending", "GitHub trending repos (public proxy, free)")
async def github_trending(lang: str = "python"):
    r = await F.get_json("https://api.github.com/search/repositories",
        "github", f"wi:ght:{lang}", 3600, params={"q": f"language:{lang}", "sort": "stars", "order": "desc", "per_page": 8})
    try:
        return {"repos": [{"name": x["full_name"], "stars": x["stargazers_count"], "desc": (x["description"] or "")[:140]} for x in r["data"]["items"]]}
    except Exception:
        return r

@tool("displacement", "UNHCR refugee stats (free, no key)")
async def displacement(limit: int = 10):
    r = await F.get_json("https://api.unhcr.org/population/v1/refugees?limit=50&year=2024", "unhcr", "wi:unhcr", 86400)
    return r

@tool("prediction_markets", "Polymarket events (free)")
async def prediction_markets(limit: int = 8):
    r = await F.get_json("https://gamma-api.polymarket.com/events", "polymarket", "wi:poly", 1800, params={"limit": limit})
    try:
        return {"events": [{"title": e.get("title", "")[:160], "volume": e.get("volume")} for e in r["data"][:limit]]}
    except Exception:
        return r

@tool("usa_spending", "USAspending federal contracts (free)")
async def usa_spending(limit: int = 5):
    r = await F.get_json("https://api.usaspending.gov/api/v2/search/spending_by_award/",
        "usaspending", "wi:usa", 3600)
    return {"note": "POST endpoint; use site search", "hint": r}

@tool("sec_company", "SEC EDGAR company filings by ticker (free, no key)")
async def sec_company(ticker: str = "NVDA", forms: str = "10-K,10-Q,8-K", limit: int = 10):
    m = await F.get_json("https://www.sec.gov/files/company_tickers.json", "sec", "wi:sec:tick", 86400)
    cik = None
    try:
        for v in m["data"].values():
            if str(v.get("ticker", "")).upper() == ticker.upper():
                cik = str(int(v["cik_str"])).zfill(10); break
    except Exception: pass
    if not cik:
        return {"error": f"ticker {ticker} not found"}
    r = await F.get_json(f"https://data.sec.gov/submissions/CIK{cik}.json", "sec", f"wi:sec:{cik}", 3600,
                         headers={"User-Agent": "worldint/1.0 contact@example.com", "Accept": "application/json"})
    try:
        fl = r["data"]["filings"]["recent"]
        out = []
        for i in range(min(len(fl["form"]), 200)):
            if fl["form"][i] in [f.strip() for f in forms.split(",")]:
                out.append({"form": fl["form"][i], "date": fl["filingDate"][i], "accession": fl["accessionNumber"][i]})
            if len(out) >= limit: break
        return {"ticker": ticker.upper(), "cik": cik, "filings": out}
    except Exception:
        return r
