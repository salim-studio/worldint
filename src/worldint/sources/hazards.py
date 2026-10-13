"""Hazards + climate + space: USGS, EONET, GDACS, Open-Meteo, NOAA, NWS, Meteoalarm, NHC, launches, volcanoes."""
from __future__ import annotations
from ..core.registry import tool
from ..core import fetcher as F

@tool("earthquakes", "USGS earthquakes. min_mag, hours, limit")
async def earthquakes(min_mag: float = 4.0, hours: int = 24, limit: int = 20):
    r = await F.get_json("https://earthquake.usgs.gov/fdsnws/event/1/query",
        "usgs", f"wi:quake:{min_mag}:{hours}", 300,
        params={"format": "geojson", "minmagnitude": min_mag, "limit": 200,
                "starttime": f"-{hours}H" if False else None} if False else
        {"format": "geojson", "minmagnitude": min_mag, "limit": 200})
    try:
        feats = r["data"]["features"]
        feats = sorted(feats, key=lambda f: (f["properties"].get("mag") or 0), reverse=True)[:limit]
        return {"count": len(feats), "quakes": [{"mag": f["properties"].get("mag"), "place": f["properties"].get("place"),
            "time": f["properties"].get("time"), "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0],
            "url": f["properties"].get("url")} for f in feats], "source": "USGS"}
    except Exception:
        return r

@tool("wildfires", "NASA EONET wildfire events (free, no key)")
async def wildfires(limit: int = 20):
    r = await F.get_json("https://eonet.gsfc.nasa.gov/api/v3/events?category=wildfires&limit=100&days=30",
        "eonet", "wi:fires", 1800)
    try:
        ev = r["data"]["events"][:limit]
        return {"count": len(ev), "fires": [{"title": e["title"], "date": (e["geometry"] or [{}])[0].get("date"),
            "coords": (e["geometry"] or [{}])[0].get("coordinates")} for e in ev]}
    except Exception:
        return r

@tool("disaster_alerts", "GDACS top alerts (trimmed) + EONET all-hazards count")
async def disaster_alerts(limit: int = 15):
    jobs = {
        "gdacs": F.get_json("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=EQ;TC;FL;VO;DR;WF",
            "gdacs", "wi:gdacs", 1800),
        "eonet": F.get_json("https://eonet.gsfc.nasa.gov/api/v3/events?limit=50&days=14", "eonet", "wi:eonet:all", 1800),
    }
    r = await F.gather_map(jobs)
    out = {}
    try:
        feats = r["gdacs"]["data"].get("features", [])[:limit]
        out["gdacs_top"] = [{"type": f.get("properties", {}).get("eventtype"),
                             "title": (f.get("properties", {}).get("name") or f.get("properties", {}).get("htmldescription", ""))[:140],
                             "severity": (f.get("properties", {}).get("severitydata") or {}).get("severity")} for f in feats]
        out["gdacs_count"] = len(r["gdacs"]["data"].get("features", []))
    except Exception:
        out["gdacs"] = r.get("gdacs", {}).get("error", "unavailable")
    try:
        out["eonet_count"] = len(r["eonet"]["data"]["events"])
    except Exception:
        pass
    return out

@tool("climate_anomalies", "Open-Meteo hourly temp/precip anomaly snapshot (no key)")
async def climate_anomalies(lat: float = 30.0, lon: float = 31.0):
    r = await F.get_json("https://api.open-meteo.com/v1/forecast",
        "openmeteo", f"wi:cli:{lat}:{lon}", 1800,
        params={"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation", "forecast_days": 3})
    try:
        h = r["data"]["hourly"]
        t = h["temperature_2m"][:24]
        return {"lat": lat, "lon": lon, "t24_mean": round(sum(t)/len(t), 1), "t24_max": max(t), "t24_min": min(t),
                "precip_next24": round(sum(h["precipitation"][:24]), 1)}
    except Exception:
        return r

@tool("space_weather", "NOAA SWPC: Kp, solar wind, alerts (free)")
async def space_weather():
    jobs = {
        "kp": F.get_json("https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json", "noaa", "wi:kp", 900),
        "solar_wind": F.get_json("https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json", "noaa", "wi:sw", 900),
        "alerts": F.get_json("https://services.swpc.noaa.gov/products/alerts.json", "noaa", "wi:sw:al", 900),
    }
    r = await F.gather_map(jobs)
    kp = None
    try:
        rows = r["kp"]["data"]
        kp = rows[-1][1] if isinstance(rows[-1], list) else rows[-1].get("Kp")
    except Exception:
        pass
    alerts = []
    try:
        for a in (r["alerts"]["data"] or [])[-5:]:
            alerts.append({"message": (a.get("message") or "")[:200], "time": a.get("issue_datetime")})
    except Exception:
        pass
    return {"kp_latest": kp, "recent_alerts": alerts}

@tool("weather_alerts_us", "NWS active CAP alerts (US)")
async def weather_alerts_us(state: str = ""):
    url = "https://api.weather.gov/alerts/active" + (f"?area={state.upper()}" if state else "")
    r = await F.get_json(url, "nws", f"wi:nws:{state}", 600)
    try:
        fts = r["data"]["features"][:30]
        return {"count": r["data"].get("pagination", {}).get("total", len(fts)),
                "alerts": [{"event": f["properties"].get("event"), "area": f["properties"].get("areaDesc", "")[:120],
                            "severity": f["properties"].get("severity"), "headline": f["properties"].get("headline", "")[:200]} for f in fts]}
    except Exception:
        return r

@tool("cyclones", "NHC active tropical cyclones (Atlantic + E/C Pacific)")
async def cyclones():
    r = await F.get_json("https://www.nhc.noaa.gov/CurrentStorms.json", "nhc", "wi:nhc", 900)
    return r

@tool("launches", "Upcoming rocket launches (Launch Library 2, free)")
async def launches(limit: int = 5):
    r = await F.get_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
        "ll2", "wi:ll2", 3600, params={"limit": limit})
    try:
        return {"launches": [{"name": l.get("name"), "net": l.get("net"), "pad": (l.get("pad") or {}).get("name"),
                               "agency": ((l.get("launch_service_provider") or {}).get("name"))} for l in r["data"]["results"]]}
    except Exception:
        return r

@tool("volcanoes", "Smithsonian GVP weekly volcanic activity (USGS feed)")
async def volcanoes():
    r = await F.get_text("https://volcanoes.usgs.gov/vhp/updates.html", "usgs-volc", "wi:volc", 86400)
    t = r.get("text", "") if isinstance(r, dict) else ""
    import re
    names = re.findall(r"[A-Z][a-z]+(?: [A-Z][a-z]+)? (?:Volcano|Peak|Mountain)", t)[:15]
    return {"volcano_mentions": names, "note": "weekly curated; names extracted from USGS page", "source": "USGS/SI-GVP"}

@tool("meteoalarm", "Meteoalarm EU warnings summary (France feed sample, free)")
async def meteoalarm():
    r = await F.get_json("https://feeds.meteoalarm.org/api/v1/warnings/feeds-france", "meteoalarm", "wi:meteo:fr", 1800)
    try:
        warns = r["data"].get("warnings", r["data"] if isinstance(r["data"], list) else [])
        return {"count": len(warns), "top": [{"event": (w.get("event") or w.get("type") or "")[:80],
                                              "level": w.get("severity") or w.get("level"),
                                              "area": str(w.get("area") or w.get("region") or "")[:100]} for w in warns[:15]]}
    except Exception:
        return r
