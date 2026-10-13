"""MCP stdio server: exposes every registered tool. Requires `pip install worldint[mcp]`."""
from __future__ import annotations
import asyncio, json

def run():
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
    except ImportError:
        raise SystemExit("pip install 'worldint[mcp]'  (needs mcp package)")
    from . import tools
    from .core.registry import REG

    srv = Server("worldint")

    @srv.list_tools()
    async def _list():
        return [Tool(name=k, description=v["desc"], inputSchema={"type": "object", "additionalProperties": True}) for k, v in REG.items()]

    @srv.call_tool()
    async def _call(name: str, arguments: dict):
        if name not in REG:
            return [TextContent(type="text", text=json.dumps({"error": f"unknown tool {name}"}, ensure_ascii=False))]
        try:
            res = await REG[name]["fn"](**(arguments or {}))
            return [TextContent(type="text", text=json.dumps(res, ensure_ascii=False, default=str)[:30000])]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)})[:2000])]

    async def _main():
        async with stdio_server() as (r, w):
            await srv.run(r, w, srv.create_initialization_options())
    asyncio.run(_main())
