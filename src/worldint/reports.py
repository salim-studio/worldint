"""Single-file HTML report (no native deps) + collector daemon + SSE dashboard."""
from __future__ import annotations
import asyncio, datetime

async def build_html(out="worldint-brief.html"):
    from .sources.synth import world_brief
    b = await world_brief()
    md = b.get("markdown", "")
    html = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>worldint brief {datetime.date.today()}</title>
<style>body{{font-family:system-ui;background:#0b1220;color:#e6edf3;margin:0;padding:32px}}
.card{{background:#111c33;border:1px solid #233252;border-radius:14px;padding:20px;max-width:900px;margin:auto}}
pre{{white-space:pre-wrap}}</style></head><body><div class="card">
<h1>🌍 worldint — موجز الاستخبارات</h1><p>{datetime.datetime.now():%Y-%m-%d %H:%M}</p>
<pre>{md}</pre></div></body></html>"""
    open(out, "w", encoding="utf-8").write(html)
    return out
