"""Lightweight SSE dashboard (Starlette). `pip install worldint[dashboard]`."""
from __future__ import annotations
import asyncio, json

HTML = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>worldint ops</title>
<style>body{font-family:system-ui;background:#0b1220;color:#e6edf3;padding:24px}pre{background:#111c33;padding:16px;border-radius:12px;white-space:pre-wrap}</style></head>
<body><h1>🌍 worldint — لوحة العمليات</h1><pre id="b">... connecting ...</pre>
<script>const e=new EventSource('/events');e.onmessage=m=>{document.getElementById('b').textContent=m.data};</script></body></html>"""

def run(port: int = 8501):
    try:
        from starlette.applications import Starlette
        from starlette.responses import HTMLResponse, StreamingResponse
        from starlette.routing import Route
    except ImportError:
        raise SystemExit("pip install 'worldint[dashboard]'")
    async def home(req): return HTMLResponse(HTML)
    async def events(req):
        async def gen():
            from .sources.synth import world_brief
            while True:
                try:
                    b = await world_brief()
                    yield f"data: {b['markdown'][:4000].replace(chr(10),' | ')}\n\n"
                except Exception as e:
                    yield f"data: error {e}\n\n"
                await asyncio.sleep(20)
        return StreamingResponse(gen(), media_type="text/event-stream")
    import uvicorn
    app = Starlette(routes=[Route("/", home), Route("/events", events)])
    uvicorn.run(app, port=port)
