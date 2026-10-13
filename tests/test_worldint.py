import asyncio
from worldint import tools
from worldint.core.registry import REG

def test_registry():
    assert len(REG) >= 35, f"only {len(REG)} tools"
    for must in ["market_quotes", "earthquakes", "world_brief", "aoi_brief", "semantic_search", "status"]:
        assert must in REG, must

def test_geo():
    from worldint.core.geo import hav, in_polygon, in_shape
    assert 100 < hav(30, 31, 31, 31) < 120
    assert in_polygon(0.5, 0.5, [[0, 0], [0, 1], [1, 1], [1, 0]])
    assert in_shape(30.04, 31.23, {"type": "circle", "lat": 30.04, "lon": 31.23, "radius_km": 50})

def test_cache():
    from worldint.core import cache
    cache.set("t:k", {"a": 1}, 60)
    assert cache.get("t:k") == {"a": 1}

def test_aoi():
    from worldint import aoi
    asyncio.run(aoi.aoi_define("TestCity", 30.0, 31.0, 50))
    r = asyncio.run(aoi.aoi_list())
    assert "TestCity" in r["aois"]
    asyncio.run(aoi.aoi_delete("TestCity"))

def test_store():
    from worldint import store
    store.remember("test", "earthquake magnitude Taiwan strait test")
    r = store.search("earthquake Taiwan")
    assert r["count"] >= 1
