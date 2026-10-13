# 🌍 worldint

**خليفة عملي وسريع** لمشروع `world-intel-mcp` — نفس الفكرة (استخبارات عالمية لحظية من APIs عامة مجانية)، لكن:

| الأصل | worldint (تحسينات) |
|---|---|
| 139 أداة + تبعيات ثقيلة (Qdrant, FastEmbed, WeasyPrint) | ~40 أداة مركّزة تغطي نفس الـ30+ مجال، بدون تبعيات ثقيلة |
| عميل HTTP لكل مصدر | **pool واحد** `httpx.AsyncClient` + semaphore + keepalive → أسرع ب much |
| كاش بسيط | **كاش مزدوج** (ذاكرة LRU + SQLite WAL) + stale-fallback عند فشل الشبكة |
| بحث دلالي يحتاج Docker+GPU | **بحث محلي فوري** (keyword-store في SQLite) + متوافق مع Qdrant اختياريًا |
| تقارير PDF تحتاج pango | **تقارير HTML/Markdown** بصفر تبعيات |
| CLI ضخم (88KB) | CLI واحد ديناميكي: `worldint <tool> k=v` يخدم كل الأدوات تلقائيًا |
| Dashboard معقد | لوحة SSE خفيفة بملف واحد + دعم عربي RTL |

## التنصيب
```bash
cd worldint
pip install -e .            # الأساس (httpx, click, feedparser فقط)
pip install -e ".[mcp]"     # سيرفر MCP
pip install -e ".[dashboard]" # اللوحة
```

## الاستعمال
```bash
worldint tools
worldint earthquakes min_mag=5 limit=5
worldint macro_signals
worldint forex_rates base=USD to=EUR,AED,EGP
worldint world_brief
worldint brief --lang ar
worldint aoi_define name=Cairo lat=30.04 lon=31.23 radius_km=80
worldint aoi_brief name=Cairo
worldint search "earthquake Taiwan"
worldint report -o brief.html
worldint status

# MCP (Claude/Cursor): worldint-mcp  (stdio)
# اللوحة: worldint-dashboard  (http://localhost:8501)
# الجامع: worldint-collector --once  |  --daemon --interval 300
```

## الأدوات (~40)
أسواق، كريبتو، ماكرو، فوركس، سلع، مركزي، FRED، بنك دولي، BTC-technicals، زلازل USGS، حرائق EONET، كوارث GDACS، مناخ Open-Meteo، طقس فضائي NOAA، NWS، أعاصير NHC، إطلاق صواريخ، براكين، GDELT، ACLED، ReliefWeb، أخبار RSS، طيران عسكري adsb.lol، مسارح 5، تأخير FAA، ملاحة NGA، حالة السحابة، BGP/RPKI، سيبر CISA+URLhaus، أوبئة WHO، ذكاء اصطناعي arXiv+HN، غيتهب، نزوح UNHCR، Polymarket، SEC EDGAR، موجز عالمي، وضع استراتيجي، ملف دولة، بحث دلالي، AOI ×7، تقرير يومي، حالة السيرفر.

## السرعة
- تجميع متوازي `asyncio.gather` + حد 16 اتصالًا.
- `world_brief` يجلب 6 مجالات في **طلب واحد متوازٍ** بدل التسلسل.
- استيرادات كسولة داخل الدوال — بدء التشغيل < 300ms.
- بدون Qdrant/FastEmbed/WeasyPrint → تنصيب < 30 ثانية.

MIT — مستوحى من marc-shade/world-intel-mcp، تنفيذ أصلي مستقل.
