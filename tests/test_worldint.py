import asyncio
import xml.etree.ElementTree as ET
from worldint import tools
from worldint.core.registry import REG

def test_registry():
    assert len(REG) >= 60, f"only {len(REG)} tools"
    for must in ["market_quotes", "earthquakes", "world_brief", "aoi_brief", "semantic_search", "status",
                 "yield_curve", "sector_heatmap", "earnings_calendar", "hotspot_escalation",
                 "signal_convergence", "nuclear_monitor", "maritime_watch", "crisis_watch",
                 "displacement_summary", "company_profile", "airport_delays", "military_flights",
                 "theater_posture", "usa_spending", "cyber_threats", "disease_outbreaks"]:
        assert must in REG, must
    assert "relief_crisis" not in REG and "nav_warnings" not in REG  # retired dead feeds

def test_geo():
    from worldint.core.geo import hav, in_polygon, in_shape
    assert 100 < hav(30, 31, 31, 31) < 120
    assert in_polygon(0.5, 0.5, [[0, 0], [0, 1], [1, 1], [1, 0]])
    assert in_shape(30.04, 31.23, {"type": "circle", "lat": 30.04, "lon": 31.23, "radius_km": 50})

def test_cache():
    from worldint.core import cache
    cache.set("t:k", {"a": 1}, 60)
    assert cache.get("t:k") == {"a": 1}

def test_aoi_diff():
    from worldint import aoi
    asyncio.run(aoi.aoi_define("TestCity", 30.0, 31.0, 50))
    r1 = asyncio.run(aoi.aoi_changes("TestCity"))
    assert r1.get("status") == "baseline_set"
    r2 = asyncio.run(aoi.aoi_changes("TestCity"))
    assert "changed" in r2 and "diff" in r2
    b = asyncio.run(aoi.aoi_brief("TestCity"))
    assert "ids" in b and "counts" in b
    asyncio.run(aoi.aoi_delete("TestCity"))

def test_store():
    from worldint import store
    store.remember("test", "earthquake magnitude Taiwan strait test")
    r = store.search("earthquake Taiwan")
    assert r["count"] >= 1

def test_faa_xml_parse():
    xml = ("<AIRPORT_STATUS_INFORMATION><Update_Time>X</Update_Time><Delay_type><Name>Ground Delay Programs</Name>"
           "<Ground_Delay_List><Ground_Delay><ARPT>BOS</ARPT><Reason>low ceilings</Reason><Avg>1 hour</Avg><Max>2 hours</Max>"
           "</Ground_Delay></Ground_Delay_List></Delay_type></AIRPORT_STATUS_INFORMATION>")
    root = ET.fromstring(xml)
    delays = [{"airport": gd.findtext("ARPT"), "reason": gd.findtext("Reason")} for gd in root.findall(".//Ground_Delay")]
    assert delays == [{"airport": "BOS", "reason": "low ceilings"}]

def test_collector_runnable():
    from worldint import collector
    names = collector._runnable()
    assert "world_brief" in names and "aoi_brief" not in names
