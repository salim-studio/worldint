<p align="center">
  <img src="docs/logo.svg" width="120" alt="worldint logo"/>
</p>

<h1 align="center">worldint</h1>

<p align="center"><b>Real-time global intelligence, minus the heavy stack.</b></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-22d3ee" alt="version"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="python"/>
  <img src="https://img.shields.io/badge/tools-63-orange" alt="tools"/>
  <img src="https://img.shields.io/badge/apis-free%20%7C%20no%20keys-brightgreen" alt="free apis"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license"/>
</p>

**worldint** is a fast, unified global-intelligence toolkit: a **63-tool MCP server**, a **dynamic CLI**, a **live SSE dashboard**, and a **collector daemon** — all powered exclusively by free public APIs. No paid keys, no Docker, no GPU, no heavyweight dependencies.

🌐 **Website:** https://salim-studio.github.io/worldint/

## Why worldint

| Capability | How worldint does it |
|---|---|
| One shared HTTP engine | Single `httpx.AsyncClient` pool + semaphore + keepalive |
| Never show stale UI as live | Two-level cache (in-memory LRU + SQLite WAL) with stale-fallback on outages |
| Resilient sources | Per-source circuit breaker (3 failures → 5 min cooldown) |
| Instant recall | Built-in local keyword store — zero servers, zero embeddings |
| Zero-dependency reports | Single-file HTML / Markdown briefs |
| One CLI for everything | `worldint <tool> key=value` auto-serves every registered tool |
| One-call situational awareness | `world_brief` fetches 6 domains in a single parallel sweep |

## Install

```bash
git clone https://github.com/salim-studio/worldint.git
cd worldint
pip install -e .              # core: httpx, click, feedparser only
pip install -e ".[mcp]"       # MCP stdio server
pip install -e ".[dashboard]" # live dashboard
```

## Usage

```bash
worldint tools                                # list all 63 tools
worldint earthquakes min_mag=6 limit=3       # USGS live quakes
worldint macro_signals                        # Fear&Greed + BTC + DXY + gold + 10Y in one call
worldint forex_rates base=USD to=EUR,DZD,EGP
worldint world_brief                          # cited multi-domain brief
worldint brief --lang en                      # morning digest (en/ar)
worldint aoi_define name=Cairo lat=30.04 lon=31.23 radius_km=150
worldint aoi_brief name=Cairo                 # cited brief scoped to your area
worldint search "earthquake Taiwan"           # instant local search
worldint report -o brief.html                 # standalone HTML report
worldint status                               # cache + breaker + tool health

worldint-mcp                                  # MCP stdio server (Claude / Cursor / Copilot)
worldint-dashboard                            # live ops dashboard → http://localhost:8501
worldint-collector --once                     # single collection sweep
worldint-collector --daemon --interval 300    # background sweeps every 5 min
```

### MCP clients

```json
{ "mcpServers": { "worldint": { "command": "worldint-mcp" } } }
```

## Tool coverage (63 tools, 30+ domains)

Markets, crypto, macro composite, forex, commodities, central banks, FRED, World Bank, BTC technicals, SEC EDGAR, USGS earthquakes, EONET wildfires, GDACS alerts, Open-Meteo climate, NOAA space weather, NWS alerts, NHC cyclones, rocket launches, volcanoes, GDELT, ACLED, ReliefWeb, world RSS news, military flights (adsb.lol), 5-theater posture, FAA delays, NGA nav warnings, cloud status, BGP/RPKI, CISA KEV + URLhaus cyber, WHO outbreaks, arXiv + Hacker News, GitHub trending, UNHCR displacement, Polymarket, USAspending, world brief, strategic posture, country dossier, semantic search, store stats, daily digest, 7 AOI geofence tools, server status.

## Performance

- Parallel `asyncio.gather` sweeps (16 concurrent connections) — a full world brief in seconds.
- Lazy imports inside tool functions — CLI startup under 300 ms.
- Install in under 30 seconds: three small core dependencies.

## License

MIT — © 2026 salim-slimani. See [LICENSE](LICENSE).
