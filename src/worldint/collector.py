"""Parallel collector daemon: sweeps zero-arg tools + AOIs on an interval."""
from __future__ import annotations
import asyncio, inspect, time
import click

FAST = ["world_brief", "macro_signals", "earthquakes", "wildfires", "news_feed", "theater_posture",
        "cyber_threats", "space_weather", "disaster_alerts", "hotspot_escalation", "maritime_watch",
        "crisis_watch", "aoi_digest", "status"]

def _runnable():
    from .core.registry import REG
    out = []
    for n, v in REG.items():
        try:
            ps = inspect.signature(v["fn"]).parameters
            if all(p.default is not inspect._empty for p in ps.values()):
                out.append(n)
        except Exception:
            pass
    return out

async def cycle(only=None):
    from .core.registry import REG
    from .core import fetcher as F
    names = only or _runnable()
    jobs = {n: REG[n]["fn"]() for n in names if n in REG}
    r = await F.gather_map(jobs, limit=12)
    await F.aclose()
    return {k: ("ok" if not (isinstance(v, dict) and v.get("error")) else str(v.get("error"))[:100])
            for k, v in r.items()}

@click.command()
@click.option("--daemon/--once", default=False)
@click.option("--interval", default=300)
@click.option("--group", default="fast", help="fast | all | aoi")
def main(daemon, interval, group):
    only = {"fast": FAST, "all": None, "aoi": ["aoi_digest"]}.get(group, FAST)
    if group == "all":
        only = None
    async def once():
        return await cycle(only)
    if not daemon:
        print(asyncio.run(once()))
        return
    while True:
        print(asyncio.run(once()), flush=True)
        time.sleep(interval)
