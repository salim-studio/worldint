"""Conflict, military, aviation, maritime, infra, cyber, health, news, tech, gov. All free, no keys."""
from __future__ import annotations
import os
from ..core.registry import tool
from ..core import fetcher as F

# ---- news ----
@tool("gdelt_search", "GDELT 2.0 global news search (free, best-effort: GDELT throttles aggressively)")
async def gdelt_search(query: str = "conflict", limit: int = 10):
    r = await F.get_json("https://api.gdeltproject.org/api/v2/doc/doc",
        "gdelt", f"wi:gdelt:{query}:{limit}", 600, retries=3,
        params={"query": query, "mode": "artlist", "format": "json", "maxrecords": max(1, min(limit, 100))})
    return r

@tool("acled_events", "ACLED conflict events (needs ACLED_ACCESS_TOKEN else guidance)")
async def acled_events(country: str = "", limit: int = 20):
    tok = os.environ.get("ACLED_ACCESS_TOKEN")
    if not tok:
        return {"note": "set ACLED_ACCESS_TOKEN for live ACLED; use crisis_watch + gdelt_search instead",
                "hint": "https://acleddata.com", "country": country}
    return await F.get_json("https://acleddata.com/api/acled/read",
        "acled", f"wi:acled:{country}", 1800, params={"key": tok, "country": country, "limit": limit})

@tool("news_feed", "Curated world RSS (BBC, AlJazeera, WHO-DON-page fallback) with optional keyword filter")
async def news_feed(limit: int = 15, query: str = ""):
    import feedparser
    feeds = {"BBC-World": "https://feeds.bbci.co.uk/news/world/rss.xml",
             "AlJazeera": "https://www.aljazeera.com/xml/rss/all.xml"}
    import asyncio
    async def one(name, url):
        t = await F.get_text(url, "rss", f"wi:rss:{name}", 900)
        try:
            d = feedparser.parse(t["text"])
            return [{"feed": name, "title": e.get("title", "")[:180], "link": e.get("link", "")} for e in d.entries[:40]]
        except Exception:
            return []
    parts = await asyncio.gather(*[one(k, v) for k, v in feeds.items()])
    items = [x for p in parts for x in p]
    if query:
        q = query.lower().split()
        items = [x for x in items if any(w in x["title"].lower() for w in q)]
    return {"count": len(items), "headlines": items[:limit * 2], "filter": query or "none"}

# ---- military / aviation (adsb.lol -> OpenSky cascade; OpenSky anonymous works) ----
async def _opensky(lamin, lamax, lomin, lomax):
    return await F.get_json("https://opensky-network.org/api/states/all", "opensky",
        f"wi:osky:{lamin}:{lamax}:{lomin}:{lomax}", 300,
        params={"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax})

@tool("military_flights", "Military aircraft: adsb.lol mil-filtered, OpenSky bbox fallback (flagged)")
async def military_flights(lat: float = 35.0, lon: float = 35.0, dist: int = 250):
    r = await F.get_json(f"https://api.adsb.lol/v2/mil?lat={lat}&lon={lon}&dist={dist}",
        "adsblol", f"wi:mil:{lat}:{lon}", 300)
    if "error" not in r:
        try:
            ac = r["data"].get("ac", [])
            return {"count": len(ac), "filtered": "military",
                    "aircraft": [{"hex": a.get("hex"), "flight": (a.get("flight") or "").strip(),
                                  "lat": a.get("lat"), "lon": a.get("lon"), "alt": a.get("alt_baro")} for a in ac[:50]]}
        except Exception:
            pass
    d = max(1, dist) / 111.0
    fb = await _opensky(lat - d, lat + d, lon - d, lon + d)
    try:
        st = (fb.get("data") or {}).get("states") or []
        return {"count": len(st), "filtered": "unfiltered-opensky-fallback", "adsblol_error": r.get("error"),
                "sample": [{"icao": s[0], "callsign": (s[1] or "").strip(), "lat": s[6], "lon": s[5], "alt": s[7]} for s in st[:30]]}
    except Exception:
        return {"primary": r, "fallback": fb}

@tool("theater_posture", "5-theater air-activity sweep via OpenSky bboxes (parallel)")
async def theater_posture():
    boxes = {"EU": (45, 55, 0, 20), "IndoPacific": (15, 35, 110, 130), "MiddleEast": (20, 33, 38, 52),
             "Korea": (33, 42, 122, 132), "MedSea": (31, 40, 10, 30)}
    jobs = {k: _opensky(*b) for k, b in boxes.items()}
    r = await F.gather_map(jobs)
    out = {}
    for k, v in r.items():
        try:
            out[k] = len((v["data"] or {}).get("states") or [])
        except Exception:
            out[k] = None
    known = [x for x in out.values() if x is not None]
    level = "ROUTINE" if not known else ("ELEVATED" if sum(known) > 3000 else "ROUTINE")
    return {"theaters": out, "posture": level, "note": "unfiltered ADS-B traffic counts per theater bbox"}

@tool("airport_delays", "FAA airport status: ground delays, closures, ground stops (XML feed, free)")
async def airport_delays():
    import xml.etree.ElementTree as ET
    t = await F.get_text("https://nasstatus.faa.gov/api/airport-status-information", "faa", "wi:faa", 600)
    if "error" in t and "text" not in t:
        return t
    try:
        root = ET.fromstring(t["text"])
        out = {"updated": (root.findtext("Update_Time") or "").strip(), "delays": [], "closures": [], "stops": []}
        for gd in root.findall(".//Ground_Delay"):
            out["delays"].append({"airport": gd.findtext("ARPT"), "reason": gd.findtext("Reason"),
                                  "avg": gd.findtext("Avg"), "max": gd.findtext("Max")})
        for c in root.findall(".//Airport_Closure_List/Airport"):
            out["closures"].append({"airport": c.findtext("ARPT"), "reason": (c.findtext("Reason") or "")[:160]})
        for s in root.findall(".//Ground_Stop"):
            out["stops"].append({"airport": s.findtext("ARPT"), "reason": s.findtext("Reason")})
        out["summary"] = f"{len(out['delays'])} delays, {len(out['closures'])} closures, {len(out['stops'])} stops"
        return out
    except Exception as e:
        return {"error": f"faa-parse: {e}"}

# ---- infra / cyber ----
@tool("service_status", "GitHub status + Cloudflare radar (best-effort, parallel)")
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

@tool("cyber_threats", "CISA KEV summary + SANS ISC + URLhaus sample (trimmed, parallel)")
async def cyber_threats(limit: int = 10):
    jobs = {"kev": F.get_json("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                              "cisa", "wi:kev", 86400),
            "sans": F.get_json("https://isc.sans.edu/api/infocon?json", "sans", "wi:sans:info", 1800),
            "sans_ports": F.get_json("https://isc.sans.edu/api/topports/records/10?json", "sans", "wi:sans:ports", 1800),
            "urlhaus": F.get_text("https://urlhaus.abuse.ch/browse/", "urlhaus", "wi:urlhaus", 1800)}
    r = await F.gather_map(jobs)
    out = {}
    try:
        vulns = r["kev"]["data"]["vulnerabilities"]
        out["kev_count"] = len(vulns)
        out["kev_latest"] = [{"cve": v["cveID"], "vendor": v["vendorProject"], "name": v["vulnerabilityName"][:100]} for v in vulns[:limit]]
    except Exception:
        out["kev"] = r.get("kev", {}).get("error", "unavailable")
    try:
        out["sans_infocon"] = r["sans"]["data"]
    except Exception:
        pass
    try:
        d = r["sans_ports"]["data"]
        out["sans_top_ports"] = [{"port": v["targetport"], "sources": v["sources"]} for k, v in d.items() if k.isdigit()]
    except Exception:
        pass
    out["sources"] = ["cisa.gov", "isc.sans.edu"]
    return out

@tool("disease_outbreaks", "Outbreak watch: RSS keyword scan (reliable) + GDELT disease search (best-effort)")
async def disease_outbreaks(limit: int = 10):
    news = await news_feed(40, "outbreak virus epidemic cholera ebola measles dengue")
    g = await gdelt_search("disease outbreak", 5)
    items = news.get("headlines", [])[:limit]
    return {"count": len(items), "outbreaks": items,
            "gdelt": (g.get("data", {}).get("articles", []) if isinstance(g.get("data"), dict) else "unavailable")}

# ---- tech / gov ----
@tool("ai_releases", "arXiv AI papers + Hacker News titles (free, parallel)")
async def ai_releases(limit: int = 8):
    import feedparser, re
    import asyncio
    jobs = {"arxiv": F.get_text("https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submitted&sortOrder=descending&max_results=10",
                                "arxiv", "wi:arxiv", 3600),
            "hn": F.get_json("https://hacker-news.firebaseio.com/v0/topstories.json", "hn", "wi:hn", 900)}
    r = await F.gather_map(jobs)
    papers = []
    try:
        for e in feedparser.parse(r["arxiv"]["text"]).entries[:limit]:
            papers.append({"title": re.sub(r"\s+", " ", e.get("title", ""))[:180]})
    except Exception:
        pass
    hn = []
    try:
        ids = r["hn"]["data"][:limit]
        async def one(i):
            d = await F.get_json(f"https://hacker-news.firebaseio.com/v0/item/{i}.json", "hn", f"wi:hn:{i}", 3600)
            try:
                return {"title": d["data"].get("title", "")[:160], "score": d["data"].get("score")}
            except Exception:
                return None
        hn = [x for x in await asyncio.gather(*[one(i) for i in ids]) if x]
    except Exception:
        pass
    return {"papers": papers, "hn_top": hn}

@tool("github_trending", "Top-starred repos by language (GitHub search, free)")
async def github_trending(lang: str = "python"):
    q = "" if lang.lower() in ("", "en", "all") else f"language:{lang}"
    q = (q + " stars:>1000").strip()
    r = await F.get_json("https://api.github.com/search/repositories",
        "github", f"wi:ght:{lang}", 3600, params={"q": q or "stars:>5000", "sort": "stars", "order": "desc", "per_page": 8})
    try:
        return {"repos": [{"name": x["full_name"], "stars": x["stargazers_count"], "desc": (x["description"] or "")[:140]} for x in r["data"]["items"]]}
    except Exception:
        return r

@tool("prediction_markets", "Polymarket events (free)")
async def prediction_markets(limit: int = 8):
    r = await F.get_json("https://gamma-api.polymarket.com/events", "polymarket", "wi:poly", 1800, params={"limit": limit})
    try:
        return {"events": [{"title": e.get("title", "")[:160], "volume": e.get("volume")} for e in r["data"][:limit]]}
    except Exception:
        return r

@tool("usa_spending", "Top federal awards via USAspending POST search (free)")
async def usa_spending(limit: int = 5):
    body = {"filters": {"award_type_codes": ["A", "B", "C", "D"]},
            "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency", "Award Type"],
            "limit": max(1, min(limit, 20)), "sort": "Award Amount", "order": "desc"}
    r = await F.post_json("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                          body, "usaspending", "wi:usa:top", 3600)
    try:
        return {"awards": r["data"]["results"][:limit], "total": r["data"].get("page_metadata", {}).get("total")}
    except Exception:
        return r

@tool("sec_company", "SEC EDGAR company filings by ticker (free, no key)")
async def sec_company(ticker: str = "NVDA", forms: str = "10-K,10-Q,8-K", limit: int = 10):
    m = await F.get_json("https://www.sec.gov/files/company_tickers.json", "sec", "wi:sec:tick", 86400,
                         headers={"User-Agent": "worldint/1.0 contact@example.com", "Accept": "application/json"})
    cik = None
    try:
        for v in m["data"].values():
            if str(v.get("ticker", "")).upper() == ticker.upper():
                cik = str(int(v["cik_str"])).zfill(10)
                break
    except Exception:
        pass
    if not cik:
        return {"error": f"ticker {ticker} not found (sec unreachable?)", "detail": m.get("error")}
    r = await F.get_json(f"https://data.sec.gov/submissions/CIK{cik}.json", "sec", f"wi:sec:{cik}", 3600,
                         headers={"User-Agent": "worldint/1.0 contact@example.com", "Accept": "application/json"})
    try:
        fl = r["data"]["filings"]["recent"]
        want = [f.strip() for f in forms.split(",")]
        out = []
        for i in range(min(len(fl["form"]), 300)):
            if fl["form"][i] in want:
                out.append({"form": fl["form"][i], "date": fl["filingDate"][i], "accession": fl["accessionNumber"][i]})
            if len(out) >= limit:
                break
        return {"ticker": ticker.upper(), "cik": cik, "filings": out}
    except Exception:
        return r
