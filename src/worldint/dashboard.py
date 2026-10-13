"""Lightweight SSE dashboard (Starlette). `pip install worldint[dashboard]`."""
from __future__ import annotations
import asyncio, json

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>worldint · Live Ops</title>
<style>body{font-family:system-ui,-apple-system,sans-serif;background:#0b1220;color:#e6edf3;margin:0;padding:0}
header{background:linear-gradient(90deg,#0b1220,#123052);border-bottom:2px solid #22d3ee;padding:20px 28px}
header h1{margin:0;font-size:24px}header h1 span{color:#22d3ee}header p{margin:4px 0 0;color:#8b9bb4;font-size:13px}
main{padding:24px}pre{background:#111c33;border:1px solid #233252;padding:16px;border-radius:12px;white-space:pre-wrap}
footer{padding:12px 28px;color:#5b6b86;font-size:12px}</style></head>
<body><header><h1>🌍 world<span>int</span> · Live Ops Center</h1><p>Real-time global intelligence · free public sources</p></header>
<main><pre id="b">… connecting …</pre></main><footer>© 2026 salim-slimani · MIT</footer>
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
