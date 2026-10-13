"""Markets, forex, crypto, econ — free APIs, parallel-friendly."""
from __future__ import annotations
import os
from ..core.registry import tool
from ..core import fetcher as F

Y = "https://query1.finance.yahoo.com/v8/finance/chart/"

@tool("market_quotes", "Stock indices quotes: S&P500, Dow, Nasdaq, FTSE, Nikkei, DAX")
async def market_quotes(symbols: str = "^GSPC,^DJI,^IXIC,^FTSE,^N225,^GDAXI"):
    out = {}
    async def one(s):
        return await F.get_json(Y + s.strip() + "?interval=1d&range=5d", "yahoo", f"wi:mkt:{s.strip()}", 300)
    import asyncio
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    res = await asyncio.gather(*[one(s) for s in syms])
    quotes = []
    for s, r in zip(syms, res):
        try:
            m = r["data"]["chart"]["result"][0]["meta"]
            quotes.append({"symbol": s, "price": m.get("regularMarketPrice"), "prev": m.get("chartPreviousClose"), "currency": m.get("currency")})
        except Exception:
            quotes.append({"symbol": s, "error": r.get("error", "parse")})
    return {"quotes": quotes, "count": len(quotes)}

@tool("crypto_quotes", "Top crypto prices via CoinGecko (free, no key)")
async def crypto_quotes(limit: int = 10):
    r = await F.get_json("https://api.coingecko.com/api/v3/coins/markets",
        "coingecko", "wi:crypto:top", 300, params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": max(1, min(limit, 50)), "page": 1})
    try:
        return {"coins": [{"id": c["id"], "price": c["current_price"], "mcap": c["market_cap"], "chg24": c.get("price_change_percentage_24h")} for c in r["data"]]}
    except Exception:
        return r

@tool("macro_signals", "Macro: Fear&Greed + BTC + DXY proxy + gold + 10Y in ONE parallel call")
async def macro_signals():
    jobs = {
        "fear_greed": F.get_json("https://api.alternative.me/fng/?limit=1", "fng", "wi:fng", 900),
        "btc": F.get_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", "coingecko", "wi:btc", 300),
        "dxy": F.get_json(Y + "DX-Y.NYB?interval=1d&range=5d", "yahoo", "wi:dxy", 600),
        "gold": F.get_json(Y + "GC=F?interval=1d&range=5d", "yahoo", "wi:gold", 600),
        "t10y": F.get_json(Y + "^TNX?interval=1d&range=5d", "yahoo", "wi:t10y", 600),
    }
    r = await F.gather_map(jobs)
    def px(x):
        try: return x["data"]["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception: return None
    fg = None
    try: fg = r["fear_greed"]["data"]["data"][0]
    except Exception: pass
    score = 50
    if fg:
        try: score = int(fg["value"])
        except Exception: pass
    verdict = "NEUTRAL" if 40 <= score <= 60 else ("RISK_ON" if score > 60 else "CAUTION")
    return {"fear_greed": fg, "btc_usd": (r["btc"].get("data", {}).get("bitcoin", {}) or {}).get("usd"),
            "dxy": px(r["dxy"]), "gold": px(r["gold"]), "yield10y": px(r["t10y"]),
            "composite": score, "verdict": verdict, "sources": ["alternative.me", "coingecko", "yahoo"]}

@tool("forex_rates", "FX rates via Frankfurter/ECB (free). base=X&to=Y,Z")
async def forex_rates(base: str = "USD", to: str = "EUR,GBP,JPY,AED,SAR,EGP"):
    r = await F.get_json(f"https://api.frankfurter.app/latest?from={base.upper()}&to={to.upper()}", "frankfurter", f"wi:fx:{base}:{to}", 1800)
    return r

@tool("commodities", "Commodity futures: gold silver crude natgas (Yahoo, free)")
async def commodities():
    mp = {"gold": "GC=F", "silver": "SI=F", "wti": "CL=F", "brent": "BZ=F", "natgas": "NG=F", "wheat": "ZW=F"}
    import asyncio
    async def one(k, s): return k, await F.get_json(Y + s + "?interval=1d&range=5d", "yahoo", f"wi:cmd:{k}", 900)
    res = await asyncio.gather(*[one(k, s) for k, s in mp.items()])
    out = {}
    for k, r in res:
        try: out[k] = r["data"]["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception: out[k] = None
    return {"prices": out}

@tool("central_bank_rates", "Policy rates: 15 central banks (curated, updated)")
async def central_bank_rates():
    return {"rates": {"Fed": 4.5, "ECB": 2.15, "BoE": 4.0, "BoJ": 0.5, "SNB": 0.0, "BoC": 2.75,
        "RBA": 3.6, "RBNZ": 3.0, "CNB_PBoC": 3.0, "RBI": 5.5, "BCB": 15.0, "SARB": 7.0,
        "CBRT": 40.5, "CBE_Egypt": 22.0, "CBUAE": 4.4}, "note": "curated snapshot; use FRED for US series", "sources": ["worldint-curated"]}

@tool("fred_series", "FRED macro series (needs FRED_API_KEY else curated fallback)")
async def fred_series(series: str = "CPIAUCSL", limit: int = 5):
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return {"series": series, "note": "set FRED_API_KEY for live data", "fallback": {"CPI": 320.1, "UNRATE": 4.2, "FEDFUNDS": 4.33, "GDP": 29000}}
    return await F.get_json("https://api.stlouisfed.org/fred/series/observations",
        "fred", f"wi:fred:{series}", 3600, params={"series_id": series, "api_key": key, "file_type": "json", "limit": limit, "sort_order": "desc"})

@tool("worldbank_indicator", "World Bank indicator by country (free, no key)")
async def worldbank_indicator(country: str = "EG", indicator: str = "NY.GDP.MKTP.CD", years: int = 5):
    r = await F.get_json(f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?format=json&per_page={years}",
        "worldbank", f"wi:wb:{country}:{indicator}", 86400)
    return r

@tool("btc_technicals", "BTC SMA50/200 + Mayer Multiple (CoinGecko history, free)")
async def btc_technicals():
    r = await F.get_json("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=220",
        "coingecko", "wi:btc:hist", 1800)
    try:
        px = [p[1] for p in r["data"]["prices"]]
        def sma(n): return sum(px[-n:]) / n
        s50, s200 = sma(50), sma(200)
        return {"price": px[-1], "sma50": round(s50, 1), "sma200": round(s200, 1),
                "signal": "GOLDEN_CROSS" if s50 > s200 else "DEATH_CROSS", "mayer": round(px[-1] / (sum(px[-200:]) / 200), 3)}
    except Exception:
        return r
