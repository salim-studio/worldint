"""worldint ops-center: Leaflet map + live cards + in-browser tool runner (Starlette)."""
from __future__ import annotations
import json

HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>worldint · Live Ops Center</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>:root{--bg:#0b1220;--card:#111c33;--line:#233252;--txt:#e6edf3;--mut:#8b9bb4;--acc:#22d3ee}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--txt)}
header{background:linear-gradient(90deg,#0b1220,#123052);border-bottom:2px solid var(--acc);padding:14px 22px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}
header h1{margin:0;font-size:20px}header h1 span{color:var(--acc)}#clock{color:var(--mut);font-size:12px}
main{display:grid;grid-template-columns:1fr 340px;gap:14px;padding:14px}section{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
h2{margin:0 0 10px;font-size:15px;color:var(--acc)}#map{height:420px;border-radius:10px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kard{background:#0a1322;border:1px solid var(--line);border-radius:10px;padding:10px}.kard b{font-size:18px;display:block}.kard small{color:var(--mut)}
select,textarea,button{width:100%;margin:6px 0;padding:9px;border-radius:8px;border:1px solid var(--line);background:#0a1322;color:var(--txt)}
button{background:var(--acc);color:#04202a;font-weight:700;border:none;cursor:pointer}
#out{white-space:pre-wrap;font-size:12px;max-height:300px;overflow:auto;background:#070d18;border-radius:8px;padding:10px}
footer{padding:10px 22px;color:#5b6b86;font-size:12px}
@media(max-width:900px){main{grid-template-columns:1fr}}</style></head>
<body><header><h1>🌍 world<span>int</span> · Live Ops Center</h1><div id="clock">…</div></header>
<main><div>
<section><h2>🗺️ Earthquakes M4.5+ (live)</h2><div id="map"></div></section>
<section><h2>📊 Live signals</h2><div class="cards" id="cards"></div></section>
</div><div>
<section><h2>🩺 Health</h2><div id="health" style="font-size:13px">…</div></section>
<section><h2>▶️ Tool runner</h2><select id="tool"></select>
<textarea id="args" rows="3" placeholder='{"min_mag": 5, "limit": 5}'></textarea>
<button onclick="runTool()">Run</button><div id="out" style="margin-top:8px">—</div></section>
</div></main><footer>© 2026 salim-slimani · free public sources · auto-refresh 60s</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([25,20],2);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:12,attribution:'© OpenStreetMap'}).addTo(map);
let layer=L.layerGroup().addTo(map);
async function tick(){
 try{
  const q=await (await fetch('/api/quakes')).json();
  layer.clearLayers();
  (q.quakes||[]).forEach(e=>{L.circleMarker([e.lat,e.lon],{radius:3+e.mag,color:'#f97316'}).bindPopup(`M${e.mag} ${e.place}`).addTo(layer);});
  const b=await (await fetch('/api/brief')).json();
  document.getElementById('cards').innerHTML=
   `<div class="kard"><small>Markets</small><b>${b.signals?.macro_verdict||'—'}</b></div>`+
   `<div class="kard"><small>Quakes M5+</small><b>${b.signals?.quakes??'—'}</b></div>`+
   `<div class="kard"><small>Kp index</small><b>${b.signals?.kp??'—'}</b></div>`+
   `<div class="kard"><small>Theater</small><b>${b.signals?.theater||'—'}</b></div>`;
  const h=await (await fetch('/api/status')).json();
  document.getElementById('health').innerHTML=`Tools: ${h.tools}<br>Cache: ${h.cache.mem_items} mem / ${h.cache.db_items} db<br>Breakers: ${JSON.stringify(h.breakers)||'all closed'}`;
  document.getElementById('clock').textContent=new Date().toLocaleString();
 }catch(e){}
}
async function tools(){const t=await (await fetch('/api/tools')).json();
 document.getElementById('tool').innerHTML=t.map(x=>`<option value="${x.name}">${x.name}</option>`).join('');}
async function runTool(){const t=document.getElementById('tool').value;let a={};
 try{a=JSON.parse(document.getElementById('args').value||'{}')}catch(e){document.getElementById('out').textContent='bad JSON args';return}
 const r=await (await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool:t,args:a})})).json();
 document.getElementById('out').textContent=JSON.stringify(r,null,1).slice(0,6000);}
tools();tick();setInterval(tick,60000);
</script></body></html>"""

def run(port: int = 8501):
    try:
        from starlette.applications import Starlette
        from starlette.responses import HTMLResponse, JSONResponse
        from starlette.routing import Route
    except ImportError:
        raise SystemExit("pip install 'worldint[dashboard]'")
    import asyncio as _a

    async def home(req): return HTMLResponse(HTML)

    async def api_tools(req):
        from .tools import describe
        return JSONResponse(describe())

    async def api_status(req):
        from .sources.synth import status
        return JSONResponse(await status())

    async def api_quakes(req):
        from .sources.hazards import earthquakes
        return JSONResponse(await earthquakes(4.5, 168, 100))

    async def api_brief(req):
        from .sources.synth import world_brief
        b = await world_brief()
        raw = b.get("raw", {})
        try:
            sig = {"macro_verdict": raw["macro"].get("verdict"), "quakes": raw["quakes"].get("count"),
                   "kp": raw["spacewx"].get("kp_latest"), "theater": raw["theater"].get("posture")}
        except Exception:
            sig = {}
        return JSONResponse({"markdown": b.get("markdown"), "signals": sig})

    async def api_run(req):
        from .core.registry import REG
        try:
            body = await req.json()
            name, args = body.get("tool", ""), body.get("args", {}) or {}
            if name not in REG:
                return JSONResponse({"error": f"unknown tool {name}"})
            res = await REG[name]["fn"](**args)
            return JSONResponse(json.loads(json.dumps(res, default=str)[:20000]))
        except Exception as e:
            return JSONResponse({"error": str(e)[:500]})

    async def events(req):
        from starlette.responses import StreamingResponse
        async def gen():
            from .sources.synth import world_brief
            while True:
                try:
                    b = await world_brief()
                    yield f"data: {b['markdown'][:2000].replace(chr(10), ' | ')}\n\n"
                except Exception as e:
                    yield f"data: error {e}\n\n"
                await _a.sleep(30)
        return StreamingResponse(gen(), media_type="text/event-stream")

    import uvicorn
    app = Starlette(routes=[Route("/", home), Route("/api/tools", api_tools), Route("/api/status", api_status),
                            Route("/api/quakes", api_quakes), Route("/api/brief", api_brief),
                            Route("/api/run", api_run, methods=["POST"]), Route("/events", events)])
    uvicorn.run(app, port=port)
