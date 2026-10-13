"""Shared async HTTP pool: keepalive, semaphore, retries, cache+breaker+stale fallback."""
from __future__ import annotations
import asyncio, os
import httpx
from . import cache, breaker

_client: httpx.AsyncClient | None = None
_sem = asyncio.Semaphore(int(os.environ.get("WORLDINT_CONCURRENCY", "16")))
UA = {"User-Agent": "worldint/1.0 (+free-osint)"}

async def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(headers=UA, timeout=httpx.Timeout(15.0, connect=8.0),
                                    limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
                                    follow_redirects=True, http2=False)
    return _client

async def aclose():
    global _client
    if _client:
        await _client.aclose(); _client = None

async def get_json(url, source, cache_key=None, ttl=300, params=None, headers=None, retries=2):
    if cache_key:
        hit = cache.get(cache_key)
        if hit is not None:
            return {"_cached": True, **(hit if isinstance(hit, dict) else {"data": hit})}
    if not breaker.allow(source):
        stale = cache.get_stale(cache_key) if cache_key else None
        return {"error": f"circuit-open:{source}", "stale": stale, "source": source}
    c = await client()
    last = None
    async with _sem:
        for i in range(retries + 1):
            try:
                r = await c.get(url, params=params, headers=headers)
                r.raise_for_status()
                data = r.json()
                breaker.ok(source)
                body = {"data": data, "source": source, "url": url}
                if cache_key:
                    cache.set(cache_key, body, ttl)
                # fire-and-forget mini vector store
                try:
                    from .. import store as _st
                    _st.remember(source, str(data)[:2000])
                except Exception:
                    pass
                return body
            except Exception as e:
                last = e
                await asyncio.sleep(0.4 * (i + 1))
    breaker.fail(source)
    stale = cache.get_stale(cache_key) if cache_key else None
    return {"error": str(last), "stale": stale, "source": source, "url": url}

async def get_text(url, source, cache_key=None, ttl=600, params=None, retries=1):
    if cache_key:
        hit = cache.get(cache_key)
        if hit is not None:
            return hit
    if not breaker.allow(source):
        return {"error": f"circuit-open:{source}", "stale": cache.get_stale(cache_key) if cache_key else None}
    c = await client()
    async with _sem:
        for i in range(retries + 1):
            try:
                r = await c.get(url, params=params)
                r.raise_for_status()
                body = {"text": r.text[:200000], "source": source, "url": url}
                breaker.ok(source)
                if cache_key:
                    cache.set(cache_key, body, ttl)
                return body
            except Exception as e:
                last = e
                await asyncio.sleep(0.4 * (i + 1))
    breaker.fail(source)
    return {"error": str(last), "source": source}

async def gather_map(coros: dict, limit=16) -> dict:
    """Run {name: coro} concurrently, never raise."""
    sem = asyncio.Semaphore(limit)
    async def wrap(k, co):
        async with sem:
            try:
                return k, await co
            except Exception as e:
                return k, {"error": str(e)}
    res = await asyncio.gather(*[wrap(k, v) for k, v in coros.items()])
    return dict(res)
