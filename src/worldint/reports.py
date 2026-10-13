"""Single-file HTML report (no native deps) + collector daemon + SSE dashboard."""
from __future__ import annotations
import asyncio, datetime

async def build_html(out="worldint-brief.html"):
    from .sources.synth import world_brief
    b = await world_brief()
    md = b.get("markdown", "")
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>worldint brief {datetime.date.today()}</title>
<style>body{{font-family:system-ui,-apple-system,sans-serif;background:#0b1220;color:#e6edf3;margin:0;padding:32px}}
.card{{background:#111c33;border:1px solid #233252;border-top:3px solid #22d3ee;border-radius:14px;padding:24px;max-width:900px;margin:auto}}
h1 span{{color:#22d3ee}}pre{{white-space:pre-wrap}}footer{{color:#5b6b86;font-size:12px;margin-top:16px}}</style></head><body><div class="card">
<h1>🌍 world<span>int</span> — Intelligence Brief</h1><p>{datetime.datetime.now():%Y-%m-%d %H:%M}</p>
<pre>{md}</pre><footer>© 2026 salim-slimani · Free public sources, no paid keys.</footer></div></body></html>"""
    open(out, "w", encoding="utf-8").write(html)
    return out
