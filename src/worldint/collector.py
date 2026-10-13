"""Parallel collector daemon: sweeps key domains + AOIs every N minutes."""
from __future__ import annotations
import asyncio, time
import click

GROUPS = {"fast": ["macro_signals", "earthquakes", "military_flights", "news_feed"],
          "all": None, "aoi": ["aoi_digest"]}

async def cycle(only=None):
    from .core.registry import REG
    names = only or [n for n in REG if n not in ("aoi_define", "aoi_define_polygon", "aoi_define_corridor")]
    jobs = {}
    for n in names:
        try:
            jobs[n] = REG[n]["fn"]()
        except Exception:
            pass
    from .core import fetcher as F
    r = await F.gather_map(jobs)
    await F.aclose()
    return {k: ("ok" if "error" not in (v or {}) else v.get("error")) for k, v in r.items()}

@click.command()
@click.option("--daemon/--once", default=False)
@click.option("--interval", default=300)
@click.option("--group", default="fast")
def main(daemon, interval, group):
    from .core.registry import REG
    import sys
    sys.path.insert(0, "src")
    only = GROUPS.get(group)
    if group == "all":
        only = None
    async def once():
        return await cycle(only)
    if not daemon:
        print(asyncio.run(once())); return
    while True:
        print(asyncio.run(once()), flush=True)
        time.sleep(interval)
