"""Multi-section HTML intelligence report (no native deps)."""
from __future__ import annotations
import datetime

async def build_html(out="worldint-brief.html"):
    from .sources import synth, markets, hazards, intel, practical
    from .core import fetcher as F
    r = await F.gather_map({
        "brief": synth.world_brief(), "macro": markets.macro_signals(),
        "quakes": hazards.earthquakes(5.0, 24, 10), "cyber": intel.cyber_threats(5),
        "news": intel.news_feed(12), "hotspots": practical.hotspot_escalation(),
        "yield": practical.yield_curve(), "maritime": practical.maritime_watch()})
    await F.aclose()
    def sec(title, body):
        return f"<h2>{title}</h2><pre>{body}</pre>"
    try:
        news = "\n".join(f"- {h['title']}" for h in r["news"].get("headlines", [])[:12])
    except Exception:
        news = "unavailable"
    try:
        hs = "\n".join(f"- {h['hotspot']}: {h['score']} ({h['level']})" for h in r["hotspots"].get("top", []))
    except Exception:
        hs = "unavailable"
    try:
        qq = "\n".join(f"- M{q['mag']} {q['place']}" for q in r["quakes"].get("quakes", [])[:10])
    except Exception:
        qq = "unavailable"
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>worldint brief {datetime.date.today()}</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;background:#0b1220;color:#e6edf3;margin:0;padding:32px}}
.card{{background:#111c33;border:1px solid #233252;border-top:3px solid #22d3ee;border-radius:14px;padding:24px;max-width:960px;margin:auto}}
h1 span{{color:#22d3ee}}h2{{color:#22d3ee;font-size:16px}}pre{{white-space:pre-wrap;font-size:13px}}footer{{color:#5b6b86;font-size:12px;margin-top:16px}}</style>
</head><body><div class="card">
<h1>🌍 world<span>int</span> — Intelligence Brief</h1><p>{datetime.datetime.now():%Y-%m-%d %H:%M} UTC</p>
{sec("Executive summary", r["brief"].get("markdown", "unavailable") if isinstance(r.get("brief"), dict) else "unavailable")}
{sec("Top escalation hotspots", hs)}
{sec("Strong quakes M5+ (24h)", qq)}
{sec("Headlines", news)}
<footer>© 2026 salim-slimani · Free public sources, no paid keys.</footer></div></body></html>"""
    open(out, "w", encoding="utf-8").write(html)
    return out
